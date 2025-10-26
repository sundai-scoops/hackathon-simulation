from __future__ import annotations

import random
import statistics
from collections import Counter, defaultdict
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from .llm import build_responder
from .models import (
    AggregatedIdea,
    AgentProfile,
    SimulationConfig,
    SimulationRunResult,
    SimulationSummary,
    TeamResult,
)


class HackathonSimulator:
    def __init__(self, profiles: Sequence[AgentProfile], config: SimulationConfig | None = None):
        if not profiles:
            raise ValueError("At least one agent profile is required.")
        self.profiles = list(profiles)
        self.config = config or SimulationConfig()
        self.llm = build_responder(self.config) if self.config.llm_enabled else None
        self._llm_notified = False
        self._llm_cap_notified = False

    def run(self) -> SimulationSummary:
        rng = random.Random(self.config.seed)
        runs: List[SimulationRunResult] = []
        for run_idx in range(1, self.config.runs + 1):
            run_seed = rng.randint(0, 10_000)
            run_rng = random.Random(run_seed)
            teams = self._form_teams(self.profiles, run_rng)
            results = [self._simulate_team(team, run_rng) for team in teams]
            results.sort(key=lambda t: t.total_score, reverse=True)
            for rank, team in enumerate(results, start=1):
                team.run_rank = rank
            runs.append(SimulationRunResult(run_index=run_idx, seed=run_seed, teams=results))
        leaderboard = self._aggregate_runs(runs)
        return SimulationSummary(runs=runs, leaderboard=leaderboard)

    def _form_teams(self, profiles: Sequence[AgentProfile], rng: random.Random) -> List[List[AgentProfile]]:
        pool = profiles[:]
        rng.shuffle(pool)
        teams: List[List[AgentProfile]] = []
        used = set()
        while pool:
            captain = pool.pop()
            if captain.name in used:
                continue
            team = [captain]
            used.add(captain.name)
            desired_size = rng.randint(self.config.min_team_size, self.config.max_team_size)
            candidates = self._rank_candidates(team, pool, used)
            while len(team) < desired_size and candidates:
                _, pick = candidates.pop(0)
                if pick.name in used:
                    continue
                used.add(pick.name)
                team.append(pick)
                if len(team) < desired_size:
                    candidates = self._rank_candidates(team, pool, used)
            teams.append(team)
        return teams

    def _rank_candidates(
        self,
        current_team: Sequence[AgentProfile],
        pool: Sequence[AgentProfile],
        used: Iterable[str],
    ) -> List[Tuple[float, AgentProfile]]:
        scores: List[Tuple[float, AgentProfile]] = []
        for candidate in pool:
            if candidate.name in used:
                continue
            affinity = sum(self._compatibility_score(member, candidate) for member in current_team) / len(current_team)
            scores.append((affinity, candidate))
        scores.sort(key=lambda item: item[0], reverse=True)
        return scores

    def _compatibility_score(self, a: AgentProfile, b: AgentProfile) -> float:
        overlap = len(set(a.skills) & set(b.skills))
        diversity = len(set(a.skills) ^ set(b.skills))
        personality = self._personality_affinity(a.personality, b.personality)
        alignment = self._idea_alignment(a.idea, b.idea)
        xp_bonus = 0.5 if a.xp_level != b.xp_level else 0.0
        return (overlap * 0.6) + (diversity * 0.9) + personality + alignment + xp_bonus

    def _personality_affinity(self, a: str, b: str) -> float:
        weights = {
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
                    affinity += 1.1 * weights.get(ta, 0.5)
                elif ta in weights and tb in weights:
                    affinity += 0.2 * (weights[ta] + weights[tb]) / 2
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

    def _simulate_team(self, team: List[AgentProfile], rng: random.Random) -> TeamResult:
        name = self._generate_team_name(team, rng)
        candidates = [
            (member, member.idea, self._assess_idea_for_team(member.idea, team, rng)) for member in team
        ]
        candidates.sort(key=lambda item: item[2]["composite"], reverse=True)
        primary_owner, working_idea, metrics = candidates[0]
        log = [
            f"Team pairs around {primary_owner.name}'s concept after scoring highest on feasibility ({metrics['feasibility']:.2f}) and novelty ({metrics['novelty']:.2f})."
        ]
        alignment_note = self._llm_insight(
            team=team,
            idea=working_idea,
            phase="team alignment",
            metrics=metrics,
        )
        if alignment_note:
            log.append(f"LLM insight: {alignment_note}")
        if len(candidates) > 1 and rng.random() < 0.55:
            merger = candidates[1]
            working_idea = self._merge_ideas(working_idea, merger[1])
            metrics = self._assess_idea_for_team(working_idea, team, rng)
            log.append(
                f"They blend in elements from {merger[0].name}'s pitch to improve user pull ({metrics['user_value']:.2f})."
            )
            merge_note = self._llm_insight(
                team=team,
                idea=working_idea,
                phase="idea blending",
                metrics=metrics,
            )
            if merge_note:
                log.append(f"LLM insight: {merge_note}")
        cohesion = self._team_cohesion(team)
        energy = self._social_energy(team)
        critique_push = rng.uniform(0.8, 1.2) + (energy * 0.05)
        metrics["clarity"] *= critique_push
        log.append(f"Critique round boosts clarity to {metrics['clarity']:.2f} thanks to high social energy ({energy:.2f}).")
        critique_note = self._llm_insight(
            team=team,
            idea=working_idea,
            phase="post-critique",
            metrics=metrics,
        )
        if critique_note:
            log.append(f"LLM insight: {critique_note}")
        pressure = self._pivot_pressure(team, metrics)
        pivoted = False
        if rng.random() < pressure:
            pivoted = True
            log.append("Pivot pressure spikes; team reframes the concept to de-risk execution.")
            working_idea = self._generate_pivot(working_idea, team, rng)
            metrics = self._assess_idea_for_team(working_idea, team, rng)
            log.append(
                f"After pivot, feasibility {metrics['feasibility']:.2f} and novelty {metrics['novelty']:.2f} rebalance."
            )
            pivot_note = self._llm_insight(
                team=team,
                idea=working_idea,
                phase="post-pivot",
                metrics=metrics,
            )
            if pivot_note:
                log.append(f"LLM insight: {pivot_note}")
        research_done = rng.random() < (self.config.research_trigger + cohesion * 0.05)
        if research_done:
            metrics["user_value"] *= 1.15
            metrics["clarity"] *= 1.1
            log.append("They squeeze in lightweight user research, validating assumptions and sharpening messaging.")
            research_note = self._llm_insight(
                team=team,
                idea=working_idea,
                phase="post-research",
                metrics=metrics,
            )
            if research_note:
                log.append(f"LLM insight: {research_note}")
        score_breakdown = self._score_outcome(metrics, cohesion, energy, research_done, rng)
        total_score = sum(score_breakdown.values())
        plan = self._build_six_hour_plan(working_idea, team, metrics, rng)
        llm_note = self._llm_insight(
            team=team,
            idea=working_idea,
            phase="post-evaluation",
            metrics=metrics,
            scores=score_breakdown,
        )
        if llm_note:
            log.append(f"LLM insight: {llm_note}")
        return TeamResult(
            team_name=name,
            members=[member.name for member in team],
            final_idea=working_idea,
            idea_origin=primary_owner.name,
            pivoted=pivoted,
            research_done=research_done,
            conversation_log=log,
            score_breakdown=score_breakdown,
            total_score=total_score,
            six_hour_plan=plan,
        )

    def _assess_idea_for_team(
        self,
        idea: str,
        team: List[AgentProfile],
        rng: random.Random,
    ) -> Dict[str, float]:
        tokens = self._tokenize(idea)
        skills = set(skill for member in team for skill in member.skills)
        buzz = {"ai", "agent", "automation", "realtime", "predictive", "dynamic"}
        defensibility_terms = {"platform", "loop", "dashboard", "engine", "simulator", "monitor"}
        user_words = {"founder", "team", "user", "customer", "judge", "product"}
        novelty = 0.6 + (len(tokens & buzz) * 0.2) + rng.uniform(-0.05, 0.1)
        feasibility = 0.7 + (len(skills) / 20) + rng.uniform(-0.05, 0.05)
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

    def _team_cohesion(self, team: List[AgentProfile]) -> float:
        tokens = [token for member in team for token in self._tokenize(member.personality)]
        counts = Counter(tokens)
        dominant = counts.most_common(1)[0][1] if counts else 1
        cohesion = dominant / max(len(team), 1)
        xp_levels = Counter(member.xp_level for member in team)
        if len(xp_levels) > 1:
            cohesion += 0.1
        return min(cohesion, 1.2)

    def _social_energy(self, team: List[AgentProfile]) -> float:
        energy_words = {"energetic", "spark", "enthusiastic", "catalyst", "bold", "visionary"}
        calm_words = {"calm", "focused", "analytical", "detail"}
        score = 0.6
        for member in team:
            tokens = self._tokenize(member.personality)
            if tokens & energy_words:
                score += 0.15
            if tokens & calm_words:
                score -= 0.05
        score += len(team) * 0.03
        return max(0.4, min(score, 1.3))

    def _pivot_pressure(self, team: List[AgentProfile], metrics: Dict[str, float]) -> float:
        tokens = [self._tokenize(member.personality) for member in team]
        ambition = sum(1 for t in tokens if "visionary" in t or "bold" in t)
        caution = sum(1 for t in tokens if "detail" in t or "calm" in t or "principled" in t)
        pressure = self.config.pivot_base_chance + (ambition * 0.08) - (caution * 0.05)
        if metrics["novelty"] < 0.7:
            pressure += 0.1
        if metrics["feasibility"] < 0.6:
            pressure += 0.07
        return max(0.05, min(pressure, 0.8))

    def _generate_pivot(self, idea: str, team: List[AgentProfile], rng: random.Random) -> str:
        focus = rng.choice(
            ["user research", "developers", "judges", "growth loops", "team health", "ethics guardrails"]
        )
        style = rng.choice(["lightweight", "data-backed", "real-time", "narrative-driven", "automated"])
        dominant_skill = Counter(skill for member in team for skill in member.skills).most_common(1)
        skill_focus = dominant_skill[0][0].replace("_", " ") if dominant_skill else "multi-disciplinary"
        return (
            f"{idea.split('.')[0]}. Pivoted toward a {style} toolkit for {focus} "
            f"that leans on the team's {skill_focus} strength."
        )

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

    def _generate_team_name(self, team: List[AgentProfile], rng: random.Random) -> str:
        adjectives = [
            "Signal",
            "Catalyst",
            "Momentum",
            "Insight",
            "Pulse",
            "Vector",
            "Fusion",
            "Orbit",
            "Sprint",
            "Arc",
        ]
        nouns = [
            "Builders",
            "Weavers",
            "Operators",
            "Synthesizers",
            "Architects",
            "Explorers",
            "Analysts",
            "Navigators",
            "Allies",
            "Conduits",
        ]
        token = rng.choice(adjectives)
        roles = "-".join(sorted({member.role.split()[0] for member in team}))
        return f"Team {token} {rng.choice(nouns)} ({roles})"

    def _slugify(self, text: str) -> str:
        return "".join(ch.lower() if ch.isalnum() else "-" for ch in text).strip("-")

    def _llm_insight(
        self,
        team: List[AgentProfile],
        idea: str,
        phase: str,
        metrics: Optional[Dict[str, float]] = None,
        scores: Optional[Dict[str, float]] = None,
    ) -> Optional[str]:
        if not self.llm:
            if self.config.llm_enabled and not self._llm_notified:
                self._llm_notified = True
                print("LLM requested but no API key found; falling back to heuristic output.")
            return None
        insight = self.llm.generate_team_update(team, idea, phase, metrics, scores)
        if insight is None and self.llm.remaining_calls == 0 and not self._llm_cap_notified:
            self._llm_cap_notified = True
            print("LLM call cap reached; remaining phases will use heuristic narration.")
        return insight
