from langchain_google_genai import ChatGoogleGenerativeAI
import os
import random
from typing import List

from pydantic import BaseModel


class MemoryEntry(BaseModel):
    speaker: str
    text: str


class Agent(BaseModel):
    name: str
    personality: str
    idea: str
    memory: List[MemoryEntry]
    conversation_group: int


# Define agent personalities and ideas (hard-coded)
agents: List[Agent] = [
    Agent(
        name="Agent 1",
        personality="Visionary product thinker who connects dots and inspires momentum",
        idea="A neighborhood micro-meetup app that suggests 30-minute gatherings based on shared context",
        memory=[],
        conversation_group=1,
    ),
    Agent(
        name="Agent 2",
        personality="Pragmatic systems optimizer focused on measurable efficiency gains",
        idea="An automatic cloud cost tuner that right-sizes resources and flags waste",
        memory=[],
        conversation_group=1,
    ),
    Agent(
        name="Agent 3",
        personality="Applied ML researcher obsessed with on-device models and privacy",
        idea="An on-device meeting summarizer that extracts action items locally",
        memory=[],
        conversation_group=1,
    ),
    Agent(
        name="Agent 4",
        personality="Empathetic UX advocate who reduces friction and cognitive load",
        idea="A frustration-free journaling assistant with gentle prompts and mood tagging",
        memory=[],
        conversation_group=1,
    ),
    Agent(
        name="Agent 5",
        personality="Security-first skeptic who anticipates threat models",
        idea="A lightweight secrets hygiene scanner for repos and CI pipelines",
        memory=[],
        conversation_group=1,
    ),
    Agent(
        name="Agent 6",
        personality="Data storyteller who turns metrics into narratives",
        idea="A KPI dashboard that explains changes in plain English with context links",
        memory=[],
        conversation_group=1,
    ),
    Agent(
        name="Agent 7",
        personality="Automation tinkerer who loves simplifying repetitive flows",
        idea="A no-code routine builder that chains personal workflows across apps",
        memory=[],
        conversation_group=1,
    ),
    Agent(
        name="Agent 8",
        personality="Privacy maximalist with a practical streak",
        idea="An on-device photo deduper that never uploads images off device",
        memory=[],
        conversation_group=1,
    ),
    Agent(
        name="Agent 9",
        personality="Latency chaser obsessed with fast paths and caches",
        idea="A CDN prefetch planner that warms critical routes based on live traffic",
        memory=[],
        conversation_group=1,
    ),
    Agent(
        name="Agent 10",
        personality="Backend reliability engineer who seeks calm systems",
        idea="An on-device photo deduper that never uploads images off device",
        memory=[],
        conversation_group=1,
    ),
    Agent(
        name="Agent 11",
        personality="Frontend craftsperson focused on accessibility and polish",
        idea="A design token visualizer that previews themes across components",
        memory=[],
        conversation_group=1,
    ),
    Agent(
        name="Agent 12",
        personality="DevOps enabler who removes friction from delivery",
        idea="An IaC drift detector with one-click remediation PRs",
        memory=[],
        conversation_group=1,
    ),
    Agent(
        name="Agent 13",
        personality="Growth strategist who experiments systematically",
        idea="An activation experiment planner with guardrails and sample size guidance",
        memory=[],
        conversation_group=1,
    ),
    Agent(
        name="Agent 14",
        personality="Open-source maintainer who cares about clarity and upgrades",
        idea="A dependency change explainer that summarizes risks and migration steps",
        memory=[],
        conversation_group=1,
    ),
    Agent(
        name="Agent 15",
        personality="Healthcare technologist balancing safety and usability",
        idea="A medication reminder that generates doctor-handoff notes",
        memory=[],
        conversation_group=1,
    ),
    Agent(
        name="Agent 16",
        personality="Sustainability engineer optimizing for efficiency and impact",
        idea="A carbon-aware job scheduler that shifts workloads to greener windows",
        memory=[],
        conversation_group=1,
    ),
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


def get_conversation_groups() -> List[int]:
    return list(set(agent.conversation_group for agent in agents))


def get_agents_in_conversation_group(group_id: int) -> List[Agent]:
    return [agent for agent in agents if agent.conversation_group == group_id]


def _seeded_personality_bias(personality: str) -> float:
    rnd = random.Random(hash(personality) & 0xFFFFFFFF)
    return 0.3 + rnd.random() * 0.7  # 0.3..1.0


def _get_time_since_last_spoken(agent: Agent) -> int:
    last_spoken_index = -1
    for index, entry in enumerate(agent.memory):
        if entry.speaker == agent.name:
            last_spoken_index = index
    return last_spoken_index


def _compute_desire(agent: Agent) -> float:
    total_messages = len(agent.memory)
    last_spoken_message = _get_time_since_last_spoken(agent)
    noise = random.random() * 0.1
    if total_messages == 0:
        return noise
    recency_penalty = last_spoken_message / total_messages

    return max(0, 1 - recency_penalty - noise)


def _get_leaving_desire(agent: Agent) -> float:
    # Leaving desire increases as speaking desire decreases; clamp to [0,1]
    desire = max(0.0, min(1.0, _compute_desire(agent)))
    return 1.0 - desire


def _build_prompt(agent: Agent) -> str:
    context_lines = []
    for msg in agent.memory[-10:]:
        context_lines.append(f"{msg.speaker}: {msg.text}")
    context = "\n".join(context_lines) if context_lines else "(no prior context)"
    intro = (
        f"You are {agent.name} with {agent.personality}. "
        f"Your idea: {agent.idea}. Respond concisely to move the conversation forward."
    )
    return f"{intro}\n\nConversation so far:\n{context}\n\nYour turn:"


# Run a "turn" where, for each conversation, one person may speak.
# On the very first turn (no prior messages), agents are randomly assigned to groups.
# After each turn, there is a chance a low-desire agent moves to another group.
def simulate_hackathon_turn():
    """
    Run a single global turn:
      - On the very first turn (no prior messages), randomly assign agents into 2..4 groups.
      - For each conversation group, one agent speaks; their message is appended to that group's memory.
      - After speaking, there is a chance a low-desire agent moves to a different group.
    Returns:
      A list of dicts describing the messages emitted this turn:
        { "group": int, "turn": int, "speaker": str, "text": str }
    """
    emitted = []

    # First-turn random grouping if no messages exist
    total_messages = sum(len(a.memory) for a in agents)
    if total_messages == 0:
        idxs = list(range(len(agents)))
        random.shuffle(idxs)
        num_agents = len(agents)
        # Choose a reasonable number of groups based on roster size (2..4)
        num_groups = max(2, min(4, max(1, num_agents // 4)))
        for i, idx in enumerate(idxs):
            agents[idx].conversation_group = (i % num_groups) + 1

    # Have one speaker per active conversation group
    for conversation_group in get_conversation_groups():
        agents_in_group = get_agents_in_conversation_group(conversation_group)
        if not agents_in_group:
            continue

        # Capture pre-turn length to compute "turn" index for this group's message
        before_len = len(agents_in_group[0].memory) if agents_in_group else 0

        desires = [(agent, _compute_desire(agent)) for agent in agents_in_group]
        speaker, _ = max(desires, key=lambda t: t[1])
        prompt = _build_prompt(speaker)
        response = model.invoke(prompt)
        text = (
            response.content
            if getattr(response, "content", None)
            else getattr(response, "message", "")
        )
        entry = MemoryEntry(speaker=speaker.name, text=text)
        for agent in agents_in_group:
            agent.memory.append(entry)

        emitted.append(
            {
                "group": conversation_group,
                "turn": before_len + 1,
                "speaker": speaker.name,
                "text": text,
            }
        )

    # Post-turn: maybe move one low-desire agent to a different conversation
    groups = get_conversation_groups()
    if len(groups) > 1:
        # Pick the agent with the highest leaving desire
        candidate = max(agents, key=_get_leaving_desire)
        leave_prob = min(1.0, max(0.0, _get_leaving_desire(candidate)))
        # So movement happens occasionally; scale probability
        if random.random() < (0.5 * leave_prob):
            current = candidate.conversation_group
            choices = [g for g in groups if g != current]
            if choices:
                candidate.conversation_group = random.choice(choices)

    return emitted
