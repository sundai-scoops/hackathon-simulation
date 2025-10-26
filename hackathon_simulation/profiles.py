from __future__ import annotations

import json
import os
from typing import List, Optional

from .models import AgentProfile


def load_profiles(path: Optional[str]) -> List[AgentProfile]:
    if not path:
        raise ValueError("No profiles provided. Supply --profiles JSON file or use the UI form.")
    if not os.path.exists(path):
        raise FileNotFoundError(f"Profile file not found: {path}")
    with open(path, "r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, list):
        raise ValueError("Profile file must contain a list of profiles.")
    profiles: List[AgentProfile] = []
    for entry in data:
        if not isinstance(entry, dict):
            raise ValueError("Profile entries must be objects.")
        try:
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
        except KeyError as missing:
            raise ValueError(f"Profile missing required field: {missing}") from missing
    if not profiles:
        raise ValueError("Profile list cannot be empty.")
    return profiles
