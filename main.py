from langchain_google_genai import ChatGoogleGenerativeAI
import os
import random
import threading
import json
from typing import Callable, Dict, List, Optional, Tuple

# Define agent personalities and ideas (hard-coded)
agents = [
    {
        "name": "Agent 1",
        "personality": "Visionary product thinker who connects dots and inspires momentum",
        "idea": "A neighborhood micro-meetup app that suggests 30-minute gatherings based on shared context",
        "memory": [],
        "last_spoke_turn": -1,
        "setup_done": True,
    },
    {
        "name": "Agent 2",
        "personality": "Pragmatic systems optimizer focused on measurable efficiency gains",
        "idea": "An automatic cloud cost tuner that right-sizes resources and flags waste",
        "memory": [],
        "last_spoke_turn": -1,
        "setup_done": True,
    },
    {
        "name": "Agent 3",
        "personality": "Applied ML researcher obsessed with on-device models and privacy",
        "idea": "An on-device meeting summarizer that extracts action items locally",
        "memory": [],
        "last_spoke_turn": -1,
        "setup_done": True,
    },
    {
        "name": "Agent 4",
        "personality": "Empathetic UX advocate who reduces friction and cognitive load",
        "idea": "A frustration-free journaling assistant with gentle prompts and mood tagging",
        "memory": [],
        "last_spoke_turn": -1,
        "setup_done": True,
    },
    {
        "name": "Agent 5",
        "personality": "Security-first skeptic who anticipates threat models",
        "idea": "A lightweight secrets hygiene scanner for repos and CI pipelines",
        "memory": [],
        "last_spoke_turn": -1,
        "setup_done": True,
    },
    {
        "name": "Agent 6",
        "personality": "Data storyteller who turns metrics into narratives",
        "idea": "A KPI dashboard that explains changes in plain English with context links",
        "memory": [],
        "last_spoke_turn": -1,
        "setup_done": True,
    },
    {
        "name": "Agent 7",
        "personality": "Automation tinkerer who loves simplifying repetitive flows",
        "idea": "A no-code routine builder that chains personal workflows across apps",
        "memory": [],
        "last_spoke_turn": -1,
        "setup_done": True,
    },
    {
        "name": "Agent 8",
        "personality": "Privacy maximalist with a practical streak",
        "idea": "An on-device photo deduper that never uploads images off device",
        "memory": [],
        "last_spoke_turn": -1,
        "setup_done": True,
    },
    {
        "name": "Agent 9",
        "personality": "Latency chaser obsessed with fast paths and caches",
        "idea": "A CDN prefetch planner that warms critical routes based on live traffic",
        "memory": [],
        "last_spoke_turn": -1,
        "setup_done": True,
    },
    {
        "name": "Agent 10",
        "personality": "Backend reliability engineer who seeks calm systems",
        "idea": "An incident timeline generator that correlates logs, deploys, and alerts",
        "memory": [],
        "last_spoke_turn": -1,
        "setup_done": True,
    },
    {
        "name": "Agent 11",
        "personality": "Frontend craftsperson focused on accessibility and polish",
        "idea": "A design token visualizer that previews themes across components",
        "memory": [],
        "last_spoke_turn": -1,
        "setup_done": True,
    },
    {
        "name": "Agent 12",
        "personality": "DevOps enabler who removes friction from delivery",
        "idea": "An IaC drift detector with one-click remediation PRs",
        "memory": [],
        "last_spoke_turn": -1,
        "setup_done": True,
    },
    {
        "name": "Agent 13",
        "personality": "Growth strategist who experiments systematically",
        "idea": "An activation experiment planner with guardrails and sample size guidance",
        "memory": [],
        "last_spoke_turn": -1,
        "setup_done": True,
    },
    {
        "name": "Agent 14",
        "personality": "Open-source maintainer who cares about clarity and upgrades",
        "idea": "A dependency change explainer that summarizes risks and migration steps",
        "memory": [],
        "last_spoke_turn": -1,
        "setup_done": True,
    },
    {
        "name": "Agent 15",
        "personality": "Healthcare technologist balancing safety and usability",
        "idea": "A medication reminder that generates doctor-handoff notes",
        "memory": [],
        "last_spoke_turn": -1,
        "setup_done": True,
    },
    {
        "name": "Agent 16",
        "personality": "Sustainability engineer optimizing for efficiency and impact",
        "idea": "A carbon-aware job scheduler that shifts workloads to greener windows",
        "memory": [],
        "last_spoke_turn": -1,
        "setup_done": True,
    },
]

# Create LLM class
llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=1.0,
    max_retries=2,
    google_api_key=os.environ.get("GOOGLE_API_KEY"),
)

# Bind tools to the model
model = llm.bind_tools([])


def _seeded_personality_bias(personality: str) -> float:
    rnd = random.Random(hash(personality) & 0xFFFFFFFF)
    return 0.3 + rnd.random() * 0.7  # 0.3..1.0


def _compute_desire(agent: Dict, history: List[Dict], turn: int) -> float:
    base = _seeded_personality_bias(agent.get("personality", agent["name"]))
    time_since_spoke = (turn - agent.get("last_spoke_turn", -1)) if agent.get("last_spoke_turn", -1) >= 0 else turn + 1
    recency_bonus = min(1.0, max(0.0, time_since_spoke) / 5.0)
    momentum = min(1.0, len(history) / 10.0)
    noise = random.random() * 0.1
    return base + recency_bonus + 0.5 * momentum + noise


def _build_prompt(speaker: Dict, history: List[Dict]) -> str:
    context_lines = []
    for msg in history[-10:]:
        context_lines.append(f"{msg['speaker']}: {msg['text']}")
    context = "\n".join(context_lines) if context_lines else "(no prior context)"
    intro = (
        f"You are {speaker['name']} with {speaker['personality']}. "
        f"Your idea: {speaker['idea']}. Respond concisely to move the conversation forward."
    )
    return f"{intro}\n\nConversation so far:\n{context}\n\nYour turn:"


# Setup: have one agent generate personalities and ideas for all
def _setup_prompt(speaker: Dict, agent_names: List[str]) -> str:
    names_str = ", ".join(agent_names)
    return (
        f"You are {speaker['name']} with {speaker['personality']}. You will initialize the team.\n"
        f"For the following agents [{names_str}], produce realistic, diverse personalities and a concise project idea each.\n"
        f"Respond ONLY with JSON array of objects: "
        f"[{{\"name\": string, \"personality\": string, \"idea\": string}}, ...] covering all names."
    )


def _generate_setup_mapping(speaker: Dict, agents: List[Dict]) -> Tuple[List[Dict], str]:
    prompt = _setup_prompt(speaker, [a["name"] for a in agents])
    response = model.invoke(prompt)
    text = getattr(response, "content", str(response))
    # Try strict JSON parse; if content contains text, try to extract JSON substring
    mapping: List[Dict] = []
    try:
        mapping = json.loads(text)
        if not isinstance(mapping, list):
            mapping = []
    except Exception:
        try:
            start = text.find("[")
            end = text.rfind("]")
            if start != -1 and end != -1 and end > start:
                mapping = json.loads(text[start : end + 1])
        except Exception:
            mapping = []
    # Fallback if model didn't return usable JSON
    if not mapping:
        fallback_personas = [
            ("Visionary product thinker", "A social app for spontaneous micro-meetups"),
            ("Pragmatic systems optimizer", "A tool to auto-tune cloud costs"),
            ("Empathetic UX advocate", "A low-friction journaling assistant"),
            ("Security-first skeptic", "A lightweight secrets hygiene scanner"),
            ("Data storyteller", "A dashboard that narrates KPI changes in plain English"),
            ("Automation tinkerer", "A no-code workflow for personal routines"),
            ("Privacy maximalist", "An on-device photo deduper"),
            ("Latency chaser", "A CDN warm-up prefetch service"),
        ]
        rnd = random.Random()
        mapping = []
        for a in agents:
            persona, idea = rnd.choice(fallback_personas)
            mapping.append({"name": a["name"], "personality": persona, "idea": idea})
    return mapping, text


# Single-conversation simulation: one speaker per turn based on desire
def simulate_hackathon(
    agents: List[Dict],
    turns: int = 5,
    callback: Optional[Callable[[str, str], None]] = None,
    seed_history: Optional[List[Dict]] = None,
):
    global token_usage
    token_usage = 0
    token_usage_lock = threading.Lock()
    history: List[Dict] = list(seed_history) if seed_history else []  # global conversation history
    conversation_log: List[Dict] = []

    # Setup phase (idempotent)
    if not all(a.get("setup_done", False) for a in agents):
        setup_agent = random.choice(agents)
        # Ensure setup agent has some baseline personality for prompt
        setup_agent.setdefault("personality", "curious coordinator")
        setup_map, raw_text = _generate_setup_mapping(setup_agent, agents)
        name_to_update = {e.get("name"): e for e in setup_map if isinstance(e, dict)}
        for a in agents:
            upd = name_to_update.get(a["name"], {})
            if upd.get("personality"):
                a["personality"] = upd["personality"]
            if upd.get("idea"):
                a["idea"] = upd["idea"]
            a["setup_done"] = True
        setup_entry = {
            "speaker": setup_agent["name"],
            "text": "Initialized team personalities and ideas.",
            "turn": 0,
            "type": "setup",
        }
        history.append(setup_entry)
        for a in agents:
            a.setdefault("memory", []).append(setup_entry)
        if callback:
            try:
                callback(setup_agent["name"], setup_entry["text"])
            except Exception:
                pass

    start_turn = (history[-1]["turn"] if history else 0) + 1
    for i in range(turns):
        turn = start_turn + i
        desires = [(agent, _compute_desire(agent, history, turn)) for agent in agents]
        speaker, _ = max(desires, key=lambda t: t[1])

        prompt = _build_prompt(speaker, history)
        response = model.invoke(prompt)
        text = getattr(response, "content", str(response))

        with token_usage_lock:
            # best-effort accounting if metadata exists
            try:
                used = 0
                meta = getattr(response, "additional_kwargs", {}) or {}
                used = (meta.get("usage_metadata", {}) or {}).get("total_tokens", 0)
                token_usage += used
            except Exception:
                pass

        entry = {"speaker": speaker["name"], "text": text, "turn": turn}
        history.append(entry)
        speaker["last_spoke_turn"] = turn

        for agent in agents:
            agent.setdefault("memory", []).append(entry)

        if callback:
            try:
                callback(speaker["name"], text)
            except Exception:
                pass

        conversation_log.append({"turn": turn, "speaker": speaker["name"], "text": text})

    return {
        "history": history,
        "conversation_log": conversation_log,
        "token_usage": token_usage,
    }


if __name__ == "__main__":
    result = simulate_hackathon(agents, turns=5)
    print("--- Simulation Summary ---")
    for item in result["conversation_log"]:
        print(f"Turn {item['turn']}: {item['speaker']} -> {item['text']}")
    print(f"Total token usage: {result['token_usage']}")
