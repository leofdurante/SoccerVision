"""AI tactical analyst: request shape, and every failure path.

The analyst is allowed to fail — it falls back to deterministic rule-based
commentary so the product still works. What is not allowed is failing
*silently*: a misconfigured workspace id previously surfaced as a generic
stack trace, which is why the 400 went unnoticed. These cover both the
degradation and the diagnosis.
"""

from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import anthropic
import httpx2
import pytest

from app.core.config import Settings
from app.services.ai_analyst import (
    AnthropicInsightGenerator,
    RuleBasedInsightGenerator,
    build_insight_generator,
)

STATS = {
    "home": {"compactness": 0.72, "formation": "4-4-2"},
    "away": {"compactness": 0.30, "formation": None},
    "numerical_advantages": [
        {"advantage_team": "home", "advantage_label": "3v2", "zone": "left_midfield"}
    ],
}


def _settings(**overrides) -> Settings:
    base = {"ai_api_key": "sk-ant-test", "ai_workspace_id": "", "model_name": "claude-opus-5"}
    return Settings(**{**base, **overrides})


def _text_response(payload: dict) -> SimpleNamespace:
    block = SimpleNamespace(type="text", text=json.dumps(payload))
    return SimpleNamespace(content=[block], stop_reason="end_turn")


def _status_error(status: int, message: str) -> anthropic.APIStatusError:
    request = httpx2.Request("POST", "https://api.anthropic.com/v1/messages")
    response = httpx2.Response(status, request=request)
    return anthropic.APIStatusError(
        message, response=response, body={"error": {"type": "invalid_request_error", "message": message}}
    )


# --- generator selection -------------------------------------------------


def test_falls_back_to_rules_when_no_api_key():
    assert isinstance(build_insight_generator(_settings(ai_api_key="")), RuleBasedInsightGenerator)


def test_uses_the_api_when_a_key_is_present():
    assert isinstance(build_insight_generator(_settings()), AnthropicInsightGenerator)


def test_warns_when_the_workspace_id_is_missing(caplog):
    build_insight_generator(_settings(ai_workspace_id=""))
    assert "AI_WORKSPACE_ID is not set" in caplog.text


def test_no_warning_once_the_workspace_id_is_set(caplog):
    build_insight_generator(_settings(ai_workspace_id="wrkspc_real"))
    assert "AI_WORKSPACE_ID is not set" not in caplog.text


# --- request shape -------------------------------------------------------


def test_sends_the_workspace_header_when_configured():
    with patch("anthropic.Anthropic") as client_cls:
        AnthropicInsightGenerator(_settings(ai_workspace_id="wrkspc_abc123"))
    headers = client_cls.call_args.kwargs["default_headers"]
    assert headers == {"anthropic-workspace-id": "wrkspc_abc123"}


def test_omits_the_workspace_header_when_unset():
    """Organization-scoped keys reject an empty workspace id, so send nothing."""
    with patch("anthropic.Anthropic") as client_cls:
        AnthropicInsightGenerator(_settings(ai_workspace_id=""))
    assert client_cls.call_args.kwargs["default_headers"] is None


def test_constrains_the_response_with_a_json_schema():
    generator = AnthropicInsightGenerator(_settings())
    generator._client = MagicMock()
    generator._client.messages.create.return_value = _text_response({"observations": ["a", "b", "c"]})
    generator.generate(STATS)

    kwargs = generator._client.messages.create.call_args.kwargs
    assert kwargs["output_config"]["format"]["type"] == "json_schema"
    assert kwargs["max_tokens"] >= 1024, "thinking tokens count against max_tokens"


def test_never_sends_video_only_the_stats_dict():
    generator = AnthropicInsightGenerator(_settings())
    generator._client = MagicMock()
    generator._client.messages.create.return_value = _text_response({"observations": ["a", "b", "c"]})
    generator.generate(STATS)

    prompt = generator._client.messages.create.call_args.kwargs["messages"][0]["content"]
    assert "compactness" in prompt
    assert "left_midfield" in prompt


# --- success -------------------------------------------------------------


def test_parses_observations_and_labels_them_as_ai():
    generator = AnthropicInsightGenerator(_settings())
    generator._client = MagicMock()
    generator._client.messages.create.return_value = _text_response(
        {"observations": ["Home is compact.", "Away is stretched.", "Home overloads the left."]}
    )
    insights = generator.generate(STATS)

    assert len(insights) == 3
    assert {i["source"] for i in insights} == {"ai_interpretation"}
    assert insights[0]["text"] == "Home is compact."


def test_drops_blank_observations():
    generator = AnthropicInsightGenerator(_settings())
    generator._client = MagicMock()
    generator._client.messages.create.return_value = _text_response(
        {"observations": ["Real observation.", "", "   ", None]}
    )
    assert len(generator.generate(STATS)) == 1


# --- failure paths -------------------------------------------------------


@pytest.mark.parametrize(
    "status,message",
    [
        (400, "anthropic-workspace-id is required when authenticating with an identity-linked API key"),
        (401, "invalid x-api-key"),
        (429, "rate limit exceeded"),
        (500, "internal server error"),
    ],
)
def test_api_errors_fall_back_and_log_the_real_reason(status, message, caplog):
    generator = AnthropicInsightGenerator(_settings())
    generator._client = MagicMock()
    generator._client.messages.create.side_effect = _status_error(status, message)

    insights = generator.generate(STATS)

    assert {i["source"] for i in insights} == {"rule_based_fallback"}
    assert message in caplog.text, "the API's own explanation must reach the logs"
    assert str(status) in caplog.text


def test_connection_errors_fall_back():
    generator = AnthropicInsightGenerator(_settings())
    generator._client = MagicMock()
    generator._client.messages.create.side_effect = anthropic.APIConnectionError(
        request=httpx2.Request("POST", "https://api.anthropic.com/v1/messages")
    )
    insights = generator.generate(STATS)
    assert {i["source"] for i in insights} == {"rule_based_fallback"}


def test_malformed_response_falls_back():
    generator = AnthropicInsightGenerator(_settings())
    generator._client = MagicMock()
    block = SimpleNamespace(type="text", text="not json at all")
    generator._client.messages.create.return_value = SimpleNamespace(
        content=[block], stop_reason="end_turn"
    )
    insights = generator.generate(STATS)
    assert {i["source"] for i in insights} == {"rule_based_fallback"}


def test_response_missing_the_observations_key_falls_back():
    generator = AnthropicInsightGenerator(_settings())
    generator._client = MagicMock()
    generator._client.messages.create.return_value = _text_response({"something_else": []})
    insights = generator.generate(STATS)
    assert {i["source"] for i in insights} == {"rule_based_fallback"}


# --- the fallback itself -------------------------------------------------


def test_rule_based_generator_always_returns_something():
    assert RuleBasedInsightGenerator().generate({}), "empty stats must still yield a message"


def test_rule_based_generator_caps_at_five():
    stats = {
        "numerical_advantages": [
            {"advantage_team": "home", "advantage_label": f"{n}v1", "zone": f"zone_{n}"}
            for n in range(10)
        ]
    }
    assert len(RuleBasedInsightGenerator().generate(stats)) == 5


# --- schema compatibility ------------------------------------------------


def test_schema_avoids_constraints_the_api_rejects():
    """`output_config` schemas support a narrow slice of JSON Schema.

    Array length constraints are rejected outright — `minItems` above 1 and
    `maxItems` at all each return a 400 before inference runs. Mocked tests
    can't see that (the mock accepts any schema), so this asserts the shape
    directly. The 3-5 range lives in the prompt and a slice instead.
    """
    from app.services.ai_analyst import INSIGHTS_SCHEMA

    observations = INSIGHTS_SCHEMA["properties"]["observations"]
    assert "maxItems" not in observations, "maxItems is rejected by output_config schemas"
    assert observations.get("minItems", 0) in (0, 1), "minItems above 1 is rejected"


def test_insights_are_capped():
    from app.services.ai_analyst import MAX_INSIGHTS

    generator = AnthropicInsightGenerator(_settings())
    generator._client = MagicMock()
    generator._client.messages.create.return_value = _text_response(
        {"observations": [f"observation {n}" for n in range(20)]}
    )
    assert len(generator.generate(STATS)) == MAX_INSIGHTS
