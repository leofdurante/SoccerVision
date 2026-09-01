"""AI tactical analyst.

Receives ONLY structured computer-vision output (formation, width,
depth, compactness, numerical advantages, events) — never raw video or
frames. Produces short, coaching-style commentary that is clearly
labeled as an AI interpretation layered on top of CV facts, per spec
section 16/30.

If no AI_API_KEY is configured, falls back to a deterministic rule-based
generator so the product demos fully without any external dependency.
The fallback is intentionally not called "AI" anywhere in its output.
"""

from __future__ import annotations

import json
import logging
from typing import Protocol

import httpx

from app.core.config import Settings

logger = logging.getLogger("soccervision.ai_analyst")

ANTHROPIC_API_VERSION = "2023-06-01"


class InsightGenerator(Protocol):
    def generate(self, structured_stats: dict) -> list[dict]: ...


class AnthropicInsightGenerator:
    """Calls the public Anthropic Messages API. Never sends raw video —
    only the structured stats dict."""

    def __init__(self, settings: Settings):
        self.api_key = settings.ai_api_key
        self.base_url = settings.ai_api_base_url.rstrip("/")
        self.model = settings.model_name

    def generate(self, structured_stats: dict) -> list[dict]:
        prompt = (
            "You are a soccer tactics analyst. You are given ONLY structured "
            "computer-vision statistics from one match (no video). Produce 3-5 "
            "short, concrete, coaching-style tactical observations as a JSON "
            "array of strings. Do NOT invent any statistic that is not present "
            "in the input. Reference only the numbers given.\n\n"
            f"STATS:\n{json.dumps(structured_stats, indent=2)}\n\n"
            "Respond with ONLY a JSON array of strings, nothing else."
        )
        try:
            response = httpx.post(
                f"{self.base_url}/v1/messages",
                headers={
                    "x-api-key": self.api_key,
                    "anthropic-version": ANTHROPIC_API_VERSION,
                    "content-type": "application/json",
                },
                json={
                    "model": self.model,
                    "max_tokens": 512,
                    "messages": [{"role": "user", "content": prompt}],
                },
                timeout=30.0,
            )
            response.raise_for_status()
            content = response.json()["content"][0]["text"]
            texts = json.loads(content)
            return [
                {"text": t, "based_on": list(structured_stats.keys()), "source": "ai_interpretation"}
                for t in texts
                if isinstance(t, str)
            ]
        except Exception:
            logger.exception("AI insight generation failed — falling back to rule-based insights")
            return RuleBasedInsightGenerator().generate(structured_stats)


class RuleBasedInsightGenerator:
    """Deterministic fallback: turns the same structured stats into plain
    English without any external call. Used when AI_API_KEY is unset or
    the AI call fails, so the product is always demoable."""

    def generate(self, structured_stats: dict) -> list[dict]:
        insights: list[dict] = []

        for advantage in structured_stats.get("numerical_advantages", []):
            insights.append(
                {
                    "text": (
                        f"{advantage['advantage_team'].title()} team has a "
                        f"{advantage['advantage_label']} overload in the "
                        f"{advantage['zone'].replace('_', ' ')}."
                    ),
                    "based_on": ["numerical_advantages"],
                    "source": "rule_based_fallback",
                }
            )

        for team in ("home", "away"):
            metrics = structured_stats.get(team, {})
            compactness = metrics.get("compactness")
            if compactness is not None:
                if compactness >= 0.7:
                    insights.append(
                        {
                            "text": f"{team.title()} team is very compact, limiting space between the lines.",
                            "based_on": [f"{team}.compactness"],
                            "source": "rule_based_fallback",
                        }
                    )
                elif compactness <= 0.35:
                    insights.append(
                        {
                            "text": f"{team.title()} team shape is stretched, which may open central space.",
                            "based_on": [f"{team}.compactness"],
                            "source": "rule_based_fallback",
                        }
                    )

            formation = metrics.get("formation")
            if formation:
                insights.append(
                    {
                        "text": f"{team.title()} team's average shape resembles a {formation} formation (heuristic estimate).",
                        "based_on": [f"{team}.formation"],
                        "source": "rule_based_fallback",
                    }
                )

        if not insights:
            insights.append(
                {
                    "text": "Not enough structured data was extracted from this video to generate tactical insights.",
                    "based_on": [],
                    "source": "rule_based_fallback",
                }
            )

        return insights[:5]


def build_insight_generator(settings: Settings) -> InsightGenerator:
    if settings.ai_enabled:
        return AnthropicInsightGenerator(settings)
    logger.info("AI_API_KEY not set — using rule-based insight fallback")
    return RuleBasedInsightGenerator()
