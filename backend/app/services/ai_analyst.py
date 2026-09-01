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

import anthropic

from app.core.config import Settings

logger = logging.getLogger("soccervision.ai_analyst")

# The model returns its observations through a schema rather than as free
# text, so a stray sentence around the JSON can't break parsing.
INSIGHTS_SCHEMA = {
    "type": "object",
    "properties": {
        # Array length constraints (minItems/maxItems) are rejected by
        # output_config schemas, so the 3-5 range is asked for in the prompt
        # and enforced with a slice below.
        "observations": {
            "type": "array",
            "items": {"type": "string"},
        }
    },
    "required": ["observations"],
    "additionalProperties": False,
}

# Thinking is on by default on current models and its tokens count against
# max_tokens, so this needs real headroom even though the answer is short.
MAX_TOKENS = 4096

# Matches the 3-5 range asked for in the prompt.
MAX_INSIGHTS = 5


class InsightGenerator(Protocol):
    def generate(self, structured_stats: dict) -> list[dict]: ...


class AnthropicInsightGenerator:
    """Calls the Anthropic Messages API through the official SDK. Never sends
    raw video — only the structured stats dict."""

    def __init__(self, settings: Settings):
        self.model = settings.model_name
        # An identity-linked key is rejected with a 400 unless the request
        # names its workspace. Organization-scoped keys don't send it.
        headers = {}
        if settings.ai_workspace_id.strip():
            headers["anthropic-workspace-id"] = settings.ai_workspace_id.strip()

        self._client = anthropic.Anthropic(
            api_key=settings.ai_api_key,
            base_url=settings.ai_api_base_url.rstrip("/"),
            default_headers=headers or None,
            timeout=60.0,
        )

    def generate(self, structured_stats: dict) -> list[dict]:
        prompt = (
            "You are a soccer tactics analyst. You are given ONLY structured "
            "computer-vision statistics from one match (no video). Produce 3-5 "
            "short, concrete, coaching-style tactical observations. Do NOT invent "
            "any statistic that is not present in the input. Reference only the "
            "numbers given.\n\n"
            "These positions are measured relative to the camera frame, not the "
            "pitch, because the footage is from a camera that pans to follow play. "
            "Treat the figures as relative comparisons between the two teams in "
            "the same passage, not as absolute distances on the field.\n\n"
            f"STATS:\n{json.dumps(structured_stats, indent=2)}"
        )

        try:
            response = self._client.messages.create(
                model=self.model,
                max_tokens=MAX_TOKENS,
                messages=[{"role": "user", "content": prompt}],
                output_config={"format": {"type": "json_schema", "schema": INSIGHTS_SCHEMA}},
            )
        except anthropic.APIStatusError as exc:
            # The API explains exactly what it rejected, and the old code threw
            # that explanation away — which is why a misconfigured workspace id
            # looked like a generic failure for as long as it did.
            logger.error(
                "AI insight generation failed: HTTP %s — %s. Falling back to "
                "rule-based insights.",
                exc.status_code,
                _api_error_message(exc),
            )
            return RuleBasedInsightGenerator().generate(structured_stats)
        except anthropic.APIConnectionError as exc:
            logger.error(
                "Could not reach the Anthropic API (%s) — falling back to "
                "rule-based insights.",
                exc,
            )
            return RuleBasedInsightGenerator().generate(structured_stats)

        try:
            text = next(block.text for block in response.content if block.type == "text")
            observations = json.loads(text)["observations"]
        except (StopIteration, KeyError, json.JSONDecodeError, TypeError):
            logger.exception(
                "AI response did not match the expected schema (stop_reason=%s) — "
                "falling back to rule-based insights.",
                response.stop_reason,
            )
            return RuleBasedInsightGenerator().generate(structured_stats)

        return [
            {"text": t, "based_on": list(structured_stats.keys()), "source": "ai_interpretation"}
            for t in observations
            if isinstance(t, str) and t.strip()
        ][:MAX_INSIGHTS]


def _api_error_message(exc: anthropic.APIStatusError) -> str:
    """Pull the human-readable reason out of an API error body."""
    body = exc.body
    if isinstance(body, dict):
        error = body.get("error")
        if isinstance(error, dict) and error.get("message"):
            return str(error["message"])
    return str(exc)


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
    if not settings.ai_enabled:
        logger.info("AI_API_KEY not set — using rule-based insight fallback")
        return RuleBasedInsightGenerator()

    if not settings.ai_workspace_id.strip():
        # Only identity-linked keys need it, so this can't be a hard failure —
        # but silence here is what made the 400 hard to place.
        logger.warning(
            "AI_WORKSPACE_ID is not set. If AI_API_KEY is an identity-linked "
            "key, every request will be rejected with a 400 and insights will "
            "fall back to the rule-based generator."
        )

    return AnthropicInsightGenerator(settings)
