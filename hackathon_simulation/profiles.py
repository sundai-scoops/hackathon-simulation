from __future__ import annotations

import json
import os
from typing import List, Optional

from .models import AgentProfile


DEFAULT_PROFILES: List[AgentProfile] = [
    AgentProfile(
        name="Avery Chen",
        role="Product Strategist",
        idea="AI concierge that distills founder brainstorms into validated persona briefs within minutes.",
        skills=["product", "user_research", "storytelling", "facilitation"],
        personality="Visionary Facilitator",
        motivation="Unlock stronger ideas through collaborative synthesis.",
        xp_level="senior",
    ),
    AgentProfile(
        name="Diego Martinez",
        role="Full-Stack Engineer",
        idea="Predictive ops dashboard for AI agents building MVPs from Slack.",
        skills=["fullstack", "devops", "automation", "python", "ai_integrations"],
        personality="Analytical Builder",
        motivation="Ship resilient infra that scales.",
        xp_level="senior",
    ),
    AgentProfile(
        name="Nia Roberts",
        role="UX Researcher",
        idea="High-speed customer interview simulator driven by real transcripts.",
        skills=["user_research", "insights", "prototyping", "facilitation"],
        personality="Empathetic Challenger",
        motivation="Surface hidden user truths fast.",
        xp_level="senior",
    ),
    AgentProfile(
        name="Jonah Patel",
        role="Data Scientist",
        idea="Realtime experimentation engine ranking hackathon pitches by signal.",
        skills=["data_science", "ml", "experimentation", "python"],
        personality="Curious Analyst",
        motivation="Quantify what teams feel is subjective.",
        xp_level="mid",
    ),
    AgentProfile(
        name="Priya Singh",
        role="AI Engineer",
        idea="Agent orchestrator that critiques hackathon output against product heuristics.",
        skills=["ml", "prompt_engineering", "python", "evaluation"],
        personality="Focused Architect",
        motivation="Keep AI output grounded in product reality.",
        xp_level="senior",
    ),
    AgentProfile(
        name="Leo Wang",
        role="Growth Hacker",
        idea="Referral loop kit that prototypes go-to-market motions in hours.",
        skills=["growth", "analytics", "copywriting", "no_code"],
        personality="Energetic Catalyst",
        motivation="Find traction stories quickly.",
        xp_level="mid",
    ),
    AgentProfile(
        name="Maya Thompson",
        role="Product Designer",
        idea="Adaptive whiteboard that scores ideation sessions for novelty vs. focus.",
        skills=["design", "storytelling", "systems_thinking", "prototyping"],
        personality="Synthesis Oriented",
        motivation="Translate fuzzy concepts into tangible flows.",
        xp_level="senior",
    ),
    AgentProfile(
        name="Raj Kulkarni",
        role="Backend Engineer",
        idea="Infra accelerator bundling auth, payments, and analytics for weekend hacks.",
        skills=["backend", "python", "systems", "security"],
        personality="Calm Optimizer",
        motivation="Reduce toil for builders.",
        xp_level="senior",
    ),
    AgentProfile(
        name="Lena Fischer",
        role="Operations Lead",
        idea="Team health monitor that forecasts burnout during intense build cycles.",
        skills=["operations", "enablement", "analytics", "coaching"],
        personality="Supportive Realist",
        motivation="Keep teams aligned and sustainable.",
        xp_level="mid",
    ),
    AgentProfile(
        name="Quinn O'Neal",
        role="Creative Technologist",
        idea="Mixed reality pitch room that play-tests product walkthroughs with judges.",
        skills=["creative_coding", "design", "storytelling", "hardware"],
        personality="Bold Experimenter",
        motivation="Make ideas feel tangible fast.",
        xp_level="mid",
    ),
    AgentProfile(
        name="Sara Ibrahim",
        role="AI Product Manager",
        idea="Adaptive backlog prioritizer using real-time customer sentiment signals.",
        skills=["product", "ai_integrations", "ops", "communication"],
        personality="Outcome Driver",
        motivation="Ship the right thing next.",
        xp_level="senior",
    ),
    AgentProfile(
        name="Noah Brooks",
        role="Front-End Engineer",
        idea="Component library that turns user discovery notes into live prototypes.",
        skills=["frontend", "design_systems", "typescript", "ux"],
        personality="Detail Advocate",
        motivation="Deliver tight experiences fast.",
        xp_level="mid",
    ),
    AgentProfile(
        name="Isabella Rossi",
        role="BizOps Strategist",
        idea="Week-one KPI simulator that stress tests monetization stories.",
        skills=["ops", "finance", "market_analysis", "storytelling"],
        personality="Strategic Connector",
        motivation="Bridge product, market, and numbers.",
        xp_level="mid",
    ),
    AgentProfile(
        name="Malik Johnson",
        role="Community Builder",
        idea="Dynamic contributor graph that pairs hackers by energy and goals.",
        skills=["community", "facilitation", "growth", "storytelling"],
        personality="Inclusive Spark",
        motivation="Ensure everyone finds their lane.",
        xp_level="mid",
    ),
    AgentProfile(
        name="Camila Duarte",
        role="AI Ethics Researcher",
        idea="Bias radar that flags risk zones in AI-driven hackathon ideas.",
        skills=["ethics", "research", "analysis", "communication"],
        personality="Principled Mediator",
        motivation="Ship responsibly without slowing momentum.",
        xp_level="mid",
    ),
    AgentProfile(
        name="Ethan Park",
        role="DevRel Engineer",
        idea="Demo autopilot that records feature walkthroughs and generates docs instantly.",
        skills=["developer_relations", "content", "automation", "frontend"],
        personality="Enthusiastic Storyteller",
        motivation="Help teams craft compelling demos.",
        xp_level="mid",
    ),
]


def load_profiles(path: Optional[str]) -> List[AgentProfile]:
    if not path:
        return DEFAULT_PROFILES
    if not os.path.exists(path):
        raise FileNotFoundError(f"Profile file not found: {path}")
    with open(path, "r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, list):
        raise ValueError("Profile file must contain a list of profiles.")
    profiles: List[AgentProfile] = []
    for entry in data:
        profiles.append(
            AgentProfile(
                name=entry["name"],
                role=entry["role"],
                idea=entry["idea"],
                skills=entry.get("skills", []),
                personality=entry.get("personality", "Curious Collaborator"),
                motivation=entry.get("motivation", "Build something meaningful."),
                xp_level=entry.get("xp_level", "mid"),
            )
        )
    if not profiles:
        raise ValueError("Profile file must include at least one profile.")
    return profiles
