from __future__ import annotations

import json
import random
import statistics
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Callable, Dict, Iterable, List, Optional, Sequence, Tuple

from .llm import build_responder
from .models import (
    AggregatedIdea,
    AgentProfile,
    SimulationConfig,
    SimulationRunResult,
    SimulationSummary,
    TeamResult,
)


@dataclass
class AgentState:
    profile: AgentProfile
    idea: str
    origin_idea: str
    collaborators: set[str] = field(default_factory=set)
    history: List[str] = field(default_factory=list)
    commitment: float = 0.4
    energy: float = 0.6
    research_done: bool = False


class HackathonSimulator:
    def __init__(self, profiles: Sequence[AgentProfile], config: SimulationConfig | None = None):
        if not profiles:
            raise ValueError("At least one agent profile is required.")
        self.profiles = list(profiles)
        self.config = config or SimulationConfig()
        self.llm = None
        self.progress_hook: Optional[Callable[[str], None]] = None
        self._current_run_idx = 0

    def set_progress_hook(self, hook: Optional[Callable[[str], None]]) -> None:
        self.progress_hook = hook

    def _emit(self, message: str) -> None:
        if self.progress_hook:
            self.progress_hook(message)
        else:
            print(message)

    def run(self) -> SimulationSummary:
        master_rng = random.Random(self.config.seed)
        runs: List[SimulationRunResult] = []
        halt_reason: Optional[Tuple[int, str]] = None

        for run_idx in range(1, self.config.runs + 1):
            run_seed = master_rng.randint(0, 10_000)
            run_rng = random.Random(run_seed)
            self.llm = build_responder(self.config)
            self._current_run_idx = run_idx
            run_summary, reason = self._simulate_single_run(run_idx, run_seed, run_rng)
            runs.append(run_summary)
            if reason:
                halt_reason = (run_idx, reason)
                break

        leaderboard = self._aggregate_runs(runs)
        if halt_reason:
            _, reason = halt_reason
            leaderboard.insert(
                0,
                AggregatedIdea(
                    slug="early-stop",
                    idea_name=f"Simulation halted early: {reason}",
                    appearances=0,
                    avg_score=0.0,
                    wins=0,
                    best_team="",
                    best_run=0,
                    best_reason="",
                    sample_plan=[],
                ),
            )
        return SimulationSummary(runs=runs, leaderboard=leaderboard[:8])

    def _simulate_single_run(
        self,
        run_idx: int,
        run_seed: int,
        rng: random.Random,
    ) -> Tuple[SimulationRunResult, Optional[str]]:
        states = self._initialise_states()
        interactions: List[str] = []

        for round_idx in range(1, self.config.conversation_rounds + 1):
            groups = self._plan_conversations(states, rng)
            self._emit(f"[run {run_idx} · round {round_idx}] {len(groups)} conversation groups queued.")
            for group in groups:
                try:
                    recap = self._facilitate_conversation(round_idx, group, rng)
                    interactions.append(recap)
                except RuntimeError as exc:
                    message = str(exc)
                    if "LLM call cap reached" in message or "Gemini call failed" in message:
                        self._emit(f"[run {run_idx} · round {round_idx}] stopping early → {message}")
                        run_summary, _ = self._summarise(states, interactions, rng, run_idx, run_seed, halted=True, reason=message)
                        return run_summary, message
                    raise
                if self.llm.remaining_calls == 0:
                    reason = "LLM call cap reached for this simulation."
                    self._emit(f"[run {run_idx} · round {round_idx}] stopping early → {reason}")
                    run_summary, _ = self._summarise(states, interactions, rng, run_idx, run_seed, halted=True, reason=reason)
                    return run_summary, reason
            self._apply_reflection(states, rng)

        self._emit(f"[run {run_idx}] completed planned conversation rounds.")
        run_summary, _ = self._summarise(states, interactions, rng, run_idx, run_seed, halted=False, reason="")
        return run_summary, None

    def _initialise_states(self) -> List[AgentState]:
        return [
            AgentState(
                profile=agent,
                idea=agent.idea,
                origin_idea=agent.idea,
                commitment=0.45 if agent.xp_level == "senior" else 0.35,
                energy=0.6 + (0.05 * idx),
            )
            for idx, agent in enumerate(self.profiles)
        ]

    def _plan_conversations(self, states: List[AgentState], rng: random.Random) -> List[List[AgentState]]:
        available = states[:]
        rng.shuffle(available)
        scheduled: List[List[AgentState]] = []
        engaged: set[str] = set()

        for state in available:
            if state.profile.name in engaged:
                continue
            engaged.add(state.profile.name)
            candidates = [
                (self._compatibility_score(state.profile, other.profile), other)
                for other in available
                if other.profile.name not in engaged and other.profile.name != state.profile.name
            ]
            candidates.sort(key=lambda item: item[0], reverse=True)
            group = [state]
            if candidates:
                group.append(candidates[0][1])
                engaged.add(candidates[0][1].profile.name)
                if len(candidates) > 1 and rng.random() < 0.35:
                    group.append(candidates[1][1])
                    engaged.add(candidates[1][1].profile.name)
            scheduled.append(group)
        return scheduled

    def _facilitate_conversation(
        self,
        round_idx: int,
        group: List[AgentState],
        rng: random.Random,
    ) -> str:
        context_lines = [
            f"- {state.profile.name} ({state.profile.role}) idea: {state.idea}"
            for state in group
        ]
        prompt = (
            f"You are moderating round {round_idx} of a hackathon ideation sprint.\n"
            f"Participants:\n" + "\n".join(context_lines) + "\n\n"
            "Respond with JSON containing keys:\n"
            "\"conversation_summary\": string,\n"
            "\"consensus_idea\": string,\n"
            "\"should_collaborate\": boolean,\n"
            "\"recommended_actions\": array of strings.\n"
            "Keep the summary concise but specific. Surface at least one candid critique or skeptical take if it comes up,"
            " and allow the tone to be lively (a bit spicy is fine) while staying constructive."
        )

        response_text = self.llm.generate_team_update(
            [state.profile for state in group],
            idea=" | ".join(state.idea for state in group),
            phase=f"round {round_idx}",
            prompt_override=prompt,
        )
        data = self._parse_conversation_response(response_text)
        summary = data["conversation_summary"]
        consensus = data["consensus_idea"] or self._merge_group_ideas([state.idea for state in group])
        recommended = data["recommended_actions"]
        should_collaborate = data["should_collaborate"]

        compat = self._group_compatibility(group)
        collab_probability = 0.2 + (compat * 0.6) + (sum(state.commitment for state in group) / len(group) * 0.2)
        collaborate = should_collaborate or (rng.random() < collab_probability)

        for state in group:
            state.history.append(f"Round {round_idx}: {summary}")
            for action in recommended:
                state.history.append(f"→ Action: {action}")
            state.energy = min(1.0, state.energy + 0.05)
            if collaborate:
                state.collaborators.update(s.profile.name for s in group if s.profile.name != state.profile.name)

        if collaborate:
            for state in group:
                state.idea = consensus
                state.commitment = min(1.0, state.commitment + 0.2)
        else:
            for state in group:
                state.commitment = max(0.1, state.commitment - 0.05)

        self._emit(
            f"[run {self._current_run_idx} · round {round_idx}] {'🤝' if collaborate else '💬'} "
            f"{', '.join(s.profile.name for s in group)} — {summary}"
        )
        return summary

    def _apply_reflection(self, states: List[AgentState], rng: random.Random) -> None:
        for state in states:
            if state.research_done:
                continue
            if rng.random() < 0.2 + (state.commitment * 0.2):
                state.research_done = True
                state.history.append("↻ Conducted quick user research and gathered validation.")

    def _summarise(
        self,
        states: List[AgentState],
        interactions: List[str],
        rng: random.Random,
        run_idx: int,
        run_seed: int,
        halted: bool,
        reason: str,
    ) -> Tuple[SimulationRunResult, Optional[str]]:
        clusters = self._derive_clusters(states)
        results: List[TeamResult] = []
        for cluster_states in clusters:
            if not cluster_states:
                continue
            profiles = [state.profile for state in cluster_states]
            idea = cluster_states[0].idea or cluster_states[0].origin_idea
            metrics = self._assess_idea_for_group(idea, cluster_states, rng)
            score_breakdown = self._score_outcome(
                metrics,
                cohesion=self._cluster_cohesion(cluster_states),
                energy=sum(state.energy for state in cluster_states) / len(cluster_states),
                research_done=any(state.research_done for state in cluster_states),
                rng=rng,
            )
            total_score = sum(score_breakdown.values())
            team_result = TeamResult(
                team_name=self._generate_cluster_name(cluster_states, rng),
                members=[state.profile.name for state in cluster_states],
                final_idea=idea,
                idea_origin=cluster_states[0].origin_idea,
                pivoted=any(state.idea != state.origin_idea for state in cluster_states),
                research_done=any(state.research_done for state in cluster_states),
                conversation_log=self._cluster_conversation_log(cluster_states),
                score_breakdown=score_breakdown,
                total_score=total_score,
                six_hour_plan=self._build_six_hour_plan(idea, profiles, metrics, rng),
            )
            results.append(team_result)

        results.sort(key=lambda t: t.total_score, reverse=True)
        for idx, team in enumerate(results, start=1):
            team.run_rank = idx

        run_summary = SimulationRunResult(run_index=run_idx, seed=run_seed, teams=results)
        return run_summary, (reason if halted else None)

    def _derive_clusters(self, states: List[AgentState]) -> List[List[AgentState]]:
        buckets: Dict[str, List[AgentState]] = defaultdict(list)
        for state in states:
            key = self._slugify(state.idea)
            buckets[key].append(state)
        return list(buckets.values())

    def _cluster_conversation_log(self, states: List[AgentState]) -> List[str]:
        logs: List[str] = []
        for state in states:
            logs.extend(state.history)
        seen = set()
        unique_logs = []
        for entry in logs:
            if entry not in seen:
                seen.add(entry)
                unique_logs.append(entry)
        return unique_logs[:30]

    def _cluster_cohesion(self, states: List[AgentState]) -> float:
        tokens = [token for state in states for token in self._tokenize(state.profile.personality)]
        counts = Counter(tokens)
        dominant = counts.most_common(1)[0][1] if counts else 1
        cohesion = dominant / max(len(states), 1)
        xp_levels = Counter(state.profile.xp_level for state in states)
        if len(xp_levels) > 1:
            cohesion += 0.1
        return min(cohesion, 1.2)

    def _generate_cluster_name(self, states: List[AgentState], rng: random.Random) -> str:
        anchors = [state.profile.role.split()[0] for state in states]
        adjectives = ["Signal", "Catalyst", "Momentum", "Insight", "Pulse", "Vector", "Fusion", "Orbit", "Sprint", "Arc"]
        nouns = ["Circle", "Crew", "Collective", "Guild", "Forum", "Loop", "Bridge", "Pod", "Squad", "Guild"]
        return f"{rng.choice(adjectives)} {rng.choice(nouns)} ({'-'.join(sorted(set(anchors)))})"

    def _parse_conversation_response(self, text: str) -> Dict[str, object]:
        try:
            start = text.index("{")
            end = text.rindex("}") + 1
            payload = json.loads(text[start:end])
        except Exception:
            payload = {}
        summary = payload.get("conversation_summary") if isinstance(payload, dict) else None
        consensus = payload.get("consensus_idea") if isinstance(payload, dict) else None
        should_collab = payload.get("should_collaborate") if isinstance(payload, dict) else False
        recommendations = payload.get("recommended_actions") if isinstance(payload, dict) else []
        if not isinstance(recommendations, list):
            recommendations = [str(recommendations)]
        return {
            "conversation_summary": summary or text.strip(),
            "consensus_idea": consensus or "",
            "should_collaborate": bool(should_collab),
            "recommended_actions": [str(item) for item in recommendations if str(item).strip()],
        }

    def _compatibility_score(self, a: AgentProfile, b: AgentProfile) -> float:
        overlap = len(set(a.skills) & set(b.skills))
        diversity = len(set(a.skills) ^ set(b.skills))
        personality = self._personality_affinity(a.personality, b.personality)
        alignment = self._idea_alignment(a.idea, b.idea)
        xp_bonus = 0.5 if a.xp_level != b.xp_level else 0.0
        return (overlap * 0.6) + (diversity * 0.9) + personality + alignment + xp_bonus

    def _personality_affinity(self, a: str, b: str) -> float:
        keywords = {
            "visionary": 1.2,
            "facilitator": 1.0,
            "analytical": 0.9,
            "builder": 1.1,
            "empathetic": 1.0,
            "challenger": 0.7,
            "focused": 0.9,
            "architect": 1.0,
            "energetic": 0.8,
            "catalyst": 0.9,
            "synthesis": 0.8,
            "calm": 0.7,
            "optimizer": 0.8,
            "supportive": 0.8,
            "realist": 0.7,
            "bold": 1.1,
            "experimenter": 1.0,
            "outcome": 0.9,
            "driver": 0.9,
            "detail": 0.8,
            "advocate": 0.8,
            "strategic": 0.9,
            "connector": 0.9,
            "inclusive": 0.9,
            "spark": 1.0,
            "principled": 0.8,
            "mediator": 0.7,
            "enthusiastic": 0.9,
            "storyteller": 0.9,
        }
        tokens_a = [token.strip(" ,.-").lower() for token in a.split()]
        tokens_b = [token.strip(" ,.-").lower() for token in b.split()]
        affinity = 0.0
        for ta in tokens_a:
            for tb in tokens_b:
                if ta == tb:
                    affinity += 1.1 * keywords.get(ta, 0.5)
                elif ta in keywords and tb in keywords:
                    affinity += 0.2 * (keywords[ta] + keywords[tb]) / 2
        return affinity

    def _idea_alignment(self, a: str, b: str) -> float:
        tokens_a = self._tokenize(a)
        tokens_b = self._tokenize(b)
        if not tokens_a or not tokens_b:
            return 0.0
        overlap = len(tokens_a & tokens_b)
        if overlap == 0:
            return 0.1
        jaccard = overlap / len(tokens_a | tokens_b)
        return 1.0 + (jaccard * 1.5)

    def _merge_ideas(self, idea_a: str, idea_b: str) -> str:
        tokens_a = list(self._tokenize(idea_a))
        tokens_b = list(self._tokenize(idea_b))
        shared = set(tokens_a) & set(tokens_b)
        headline = list(shared)[:3]
        extra = [token for token in tokens_a + tokens_b if token not in shared][:5]
        stitched = " ".join(headline + extra)
        base = idea_a.split(".")[0]
        addition = idea_b.split(".")[0]
        return f"{base} Now enriched with {addition.lower()} to create a {stitched} play."

    def _merge_group_ideas(self, ideas: List[str]) -> str:
        merged = ideas[0]
        for idea in ideas[1:]:
            merged = self._merge_ideas(merged, idea)
        return merged

    def _group_compatibility(self, group: List[AgentState]) -> float:
        if len(group) == 1:
            return 0.5
        scores = []
        for i in range(len(group)):
            for j in range(i + 1, len(group)):
                scores.append(self._compatibility_score(group[i].profile, group[j].profile))
        return sum(scores) / len(scores)

    def _assess_idea_for_group(
        self,
        idea: str,
        states: List[AgentState],
        rng: random.Random,
    ) -> Dict[str, float]:
        profiles = [state.profile for state in states]
        return self._assess_idea_for_team(idea, profiles, rng)

    def _assess_idea_for_team(
        self,
        idea: str,
        team: List[AgentProfile],
        rng: random.Random,
    ) -> Dict[str, float]:
        tokens = self._tokenize(idea)
        skill_pool = set(skill for member in team for skill in member.skills)
        buzz = {"ai", "agent", "automation", "realtime", "predictive", "dynamic"}
        defensibility_terms = {"platform", "loop", "dashboard", "engine", "simulator", "monitor"}
        user_words = {"founder", "team", "user", "customer", "judge", "product"}

        novelty = 0.6 + (len(tokens & buzz) * 0.2) + rng.uniform(-0.05, 0.1)
        feasibility = 0.7 + (len(skill_pool) / 20) + rng.uniform(-0.05, 0.05)
        user_value = 0.55 + (len(tokens & user_words) * 0.15) + rng.uniform(-0.05, 0.1)
        clarity = 0.5 + (min(len(idea), 200) / 400) + rng.uniform(-0.05, 0.1)
        defensibility = 0.4 + (len(tokens & defensibility_terms) * 0.12)

        novelty = min(novelty, 1.2)
        feasibility = min(feasibility, 1.15)
        user_value = min(user_value, 1.2)
        clarity = min(clarity, 1.1)
        defensibility = min(defensibility, 1.0)

        composite = (
            (novelty * 0.25)
            + (feasibility * 0.25)
            + (user_value * 0.2)
            + (clarity * 0.15)
            + (defensibility * 0.15)
        )

        return {
            "novelty": novelty,
            "feasibility": feasibility,
            "user_value": user_value,
            "clarity": clarity,
            "defensibility": defensibility,
            "composite": composite,
        }

    def _score_outcome(
        self,
        metrics: Dict[str, float],
        cohesion: float,
        energy: float,
        research_done: bool,
        rng: random.Random,
    ) -> Dict[str, float]:
        impact = (metrics["novelty"] * 0.4) + (metrics["user_value"] * 0.4) + rng.uniform(0, 0.15)
        feasibility = (metrics["feasibility"] * 0.6) + (metrics["defensibility"] * 0.35)
        cohesion_score = (cohesion * 0.6) + (energy * 0.3) + (0.1 if research_done else 0.0)
        speed = (metrics["clarity"] * 0.5) + (energy * 0.2) + rng.uniform(0, 0.1)
        confidence = 0.45 + (metrics["clarity"] * 0.2) + (metrics["defensibility"] * 0.2)
        if research_done:
            confidence += 0.15
        return {
            "impact": round(impact, 3),
            "feasibility": round(feasibility, 3),
            "cohesion": round(cohesion_score, 3),
            "speed": round(speed, 3),
            "confidence": round(min(confidence, 1.3), 3),
        }

    def _build_six_hour_plan(
        self,
        idea: str,
        team: List[AgentProfile],
        metrics: Dict[str, float],
        rng: random.Random,
    ) -> List[str]:
        lead = team[0].name
        technical = next(
            (m for m in team if "engineer" in m.role.lower() or "developer" in m.role.lower()),
            team[0],
        )
        designer = next((m for m in team if "design" in m.role.lower()), team[0])
        researcher = next(
            (m for m in team if "research" in m.role.lower() or "ops" in m.role.lower()),
            team[0],
        )
        plan = [
            f"Hour 1: {lead} leads alignment on the refined concept: {idea.split('.')[0]}.",
            f"Hour 2: {researcher.name} pulls two quick interviews or transcript reviews to validate assumptions.",
            f"Hour 3: {technical.name} scaffolds the core workflow; focus on the highest-signal feature.",
            f"Hour 4: {designer.name if designer else technical.name} drafts a clickable storyboard covering the end-to-end experience.",
            "Hour 5: Pair to stitch narrative + demo script; bake research insights into the storyline.",
            "Hour 6: Dry run the pitch, capture metrics in the dashboard, and tag next-day follow-ups.",
        ]
        if metrics["novelty"] > 1.0:
            plan[2] += " Shield novelty with a rapid feasibility spike test."
        if metrics["feasibility"] < 0.7:
            plan[2] += " Scope guardrails tightly to keep build tractable."
        if rng.random() < 0.4:
            plan[-1] += " Close with a crisp ask for pilots or data access."
        return plan

    def _aggregate_runs(self, runs: Sequence[SimulationRunResult]) -> List[AggregatedIdea]:
        buckets: Dict[str, List[Tuple[int, TeamResult]]] = defaultdict(list)
        for run in runs:
            for team in run.teams:
                slug = self._slugify(team.final_idea)
                buckets[slug].append((run.run_index, team))
        aggregated: List[AggregatedIdea] = []
        for slug, entries in buckets.items():
            scores = [team.total_score for _, team in entries]
            avg_score = statistics.mean(scores)
            wins = sum(1 for _, team in entries if team.run_rank == 1)
            best_run, best_team = max(entries, key=lambda item: item[1].total_score)
            aggregated.append(
                AggregatedIdea(
                    slug=slug,
                    idea_name=best_team.final_idea,
                    appearances=len(entries),
                    avg_score=round(avg_score, 3),
                    wins=wins,
                    best_team=best_team.team_name,
                    best_run=best_run,
                    best_reason=best_team.conversation_log[-1] if best_team.conversation_log else "",
                    sample_plan=best_team.six_hour_plan,
                )
            )
        aggregated.sort(key=lambda item: item.avg_score, reverse=True)
        return aggregated[:8]

    def _tokenize(self, text: str) -> set[str]:
        cleaned = "".join(ch.lower() if ch.isalnum() else " " for ch in text)
        return {token for token in cleaned.split() if token}

    def _slugify(self, text: str) -> str:
        return "".join(ch.lower() if ch.isalnum() else "-" for ch in text).strip("-")
