from __future__ import annotations

import json
import os
import time
from typing import Dict, List, Optional

from google import genai
from google.genai import types

from .models import AgentProfile, SimulationConfig


def _pretty(data: Optional[Dict[str, float]]) -> str:
    if not data:
        return "n/a"
    try:
        return json.dumps(data, sort_keys=True)
    except Exception:
        return str(data)


class LLMResponder:
    def __init__(self, model: str, temperature: float, call_cap: int, api_key: Optional[str] = None):
        self.model_id = model
        self.temperature = temperature
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError(
                "Gemini API key is required. Set GEMINI_API_KEY or GOOGLE_API_KEY before running the simulation."
            )
        self._last_call_ts = 0.0
        self._min_interval = 2.0
        try:
            self._client = genai.Client(api_key=self.api_key)
        except Exception as exc:  # pragma: no cover - client initialisation errors
            raise RuntimeError(f"Failed to initialise Gemini client: {exc}") from exc
        self.call_cap = max(1, call_cap)
        self.remaining_calls = self.call_cap

    def generate_team_update(
        self,
        team: List[AgentProfile],
        idea: str,
        phase: str,
        metrics: Optional[Dict[str, float]] = None,
        scores: Optional[Dict[str, float]] = None,
        prompt_override: Optional[str] = None,
    ) -> str:
        if self.remaining_calls == 0:
            raise RuntimeError("LLM call cap reached for this simulation.")
        member_lines = ", ".join(f"{member.name} ({member.role})" for member in team)
        if prompt_override:
            prompt = prompt_override
        else:
            prompt = (
                "You are moderating a hackathon sprint. "
                "Produce one concise insight (<=3 sentences) that reflects what this team likely says next. "
                "Focus on critique, next steps, or validation pressure.\n\n"
                f"Phase: {phase}\n"
                f"Team: {member_lines}\n"
                f"Idea: {idea}\n"
                f"Metrics: {_pretty(metrics)}\n"
                f"Scores: {_pretty(scores)}\n"
                "Insight:"
            )
        contents = [
            types.Content(
                role="user",
                parts=[types.Part.from_text(text=prompt)],
            )
        ]
        now = time.time()
        elapsed = now - self._last_call_ts
        if self._last_call_ts and elapsed < self._min_interval:
            time.sleep(self._min_interval - elapsed)
        config = types.GenerateContentConfig(
            temperature=self.temperature,
            top_p=0.95,
            max_output_tokens=1024,
        )
        try:
            response = self._client.models.generate_content(
                model=self.model_id,
                contents=contents,
                config=config,
            )
        except Exception as exc:  # pragma: no cover - Gemini errors
            raise RuntimeError(f"Gemini call failed: {exc}") from exc
        self.remaining_calls -= 1
        self._last_call_ts = time.time()
        text = extract_text(response)
        if not text:
            raise RuntimeError("Gemini returned an empty response.")
        return text.strip()


def build_responder(config: SimulationConfig) -> LLMResponder:
    return LLMResponder(config.llm_model, config.llm_temperature, config.llm_call_cap)


def extract_text(response: types.GenerateContentResponse) -> str:
    if hasattr(response, "text") and response.text:
        return response.text
    parts = []
    for candidate in getattr(response, "candidates", []) or []:
        if getattr(candidate, "content", None):
            for part in candidate.content.parts:
                if getattr(part, "text", ""):
                    parts.append(part.text)
    return "".join(parts)
