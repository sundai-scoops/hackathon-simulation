from __future__ import annotations

import json
import os
from typing import List, Optional

try:
    from langchain_google_genai import ChatGoogleGenerativeAI  # type: ignore
except Exception:  # pragma: no cover - optional dependency may be missing or outdated
    ChatGoogleGenerativeAI = None

from .models import AgentProfile, SimulationConfig


class LLMResponder:
    def __init__(self, model: str, temperature: float, call_cap: int, api_key: Optional[str] = None):
        self.model_id = model
        self.temperature = temperature
        self.api_key = api_key or os.environ.get("GOOGLE_API_KEY")
        self.call_cap = max(0, call_cap)
        self.remaining_calls = self.call_cap
        self._client = None
        if self.api_key and ChatGoogleGenerativeAI is not None:
            self._client = ChatGoogleGenerativeAI(
                model=self.model_id,
                temperature=self.temperature,
                max_retries=2,
                google_api_key=self.api_key,
            )

    @property
    def available(self) -> bool:
        return self._client is not None

    def generate_team_update(
        self,
        team: List[AgentProfile],
        idea: str,
        phase: str,
        metrics: Optional[dict[str, float]] = None,
        scores: Optional[dict[str, float]] = None,
    ) -> Optional[str]:
        if not self._client:
            return None
        if self.remaining_calls == 0:
            return None
        member_lines = ", ".join(f"{member.name} ({member.role})" for member in team)
        metrics_str = json_pretty(metrics) if metrics else "Not supplied"
        scores_str = json_pretty(scores) if scores else "Not yet scored"
        prompt = (
            "You are moderating a hackathon simulation. "
            "Given the current team context, write one concise insight (max 3 sentences) "
            "that reflects probable team conversation. "
            "Focus on next steps, critique, or validation pressure.\n\n"
            f"Phase: {phase}\n"
            f"Team: {member_lines}\n"
            f"Idea: {idea}\n"
            f"Metrics snapshot: {metrics_str}\n"
            f"Score snapshot: {scores_str}\n"
            "Insight:"
        )
        try:
            response = self._client.invoke(prompt)
        except Exception:
            self._client = None
            return None
        self.remaining_calls = max(0, self.remaining_calls - 1)
        text = ""
        if hasattr(response, "content"):
            text = response.content if isinstance(response.content, str) else "".join(map(str, response.content))
        else:
            text = str(response)
        return text.strip() or None


def build_responder(config: SimulationConfig) -> Optional[LLMResponder]:
    responder = LLMResponder(config.llm_model, config.llm_temperature, config.llm_call_cap)
    if responder.available:
        return responder
    return None


def json_pretty(payload: Optional[dict[str, float]]) -> str:
    if not payload:
        return "Not supplied"
    try:
        return json.dumps(payload, sort_keys=True)
    except (TypeError, ValueError):
        return str(payload)
