from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class AgentProfile:
    name: str
    role: str
    idea: str
    skills: List[str]
    personality: str
    motivation: str = "Build a high-signal project fast."
    xp_level: str = "mid"


@dataclass
class SimulationConfig:
    runs: int = 5
    min_team_size: int = 2
    max_team_size: int = 4
    pivot_base_chance: float = 0.35
    research_trigger: float = 0.45
    seed: int = 42
    llm_model: str = "gemini-flash-latest"
    llm_temperature: float = 0.9
    llm_call_cap: int = 10
    progress_interval: int = 1


@dataclass
class TeamResult:
    team_name: str
    members: List[str]
    final_idea: str
    idea_origin: str
    pivoted: bool
    research_done: bool
    conversation_log: List[str]
    score_breakdown: Dict[str, float]
    total_score: float
    six_hour_plan: List[str]
    run_rank: int = 0


@dataclass
class SimulationRunResult:
    run_index: int
    seed: int
    teams: List[TeamResult]


@dataclass
class AggregatedIdea:
    slug: str
    idea_name: str
    appearances: int
    avg_score: float
    wins: int
    best_team: str
    best_run: int
    best_reason: str
    sample_plan: List[str]


@dataclass
class SimulationSummary:
    runs: List[SimulationRunResult] = field(default_factory=list)
    leaderboard: List[AggregatedIdea] = field(default_factory=list)
