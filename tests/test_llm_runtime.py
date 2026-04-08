"""Tests for shared LLM runtime selection."""

import json
import sys
from types import SimpleNamespace

import pytest

from compliance_os.web.services.llm_runtime import (
    LLMConfigError,
    chat_completion,
    configured_app_environment,
    configured_llm_model,
    configured_llm_provider,
    extract_json,
)


def test_configured_llm_provider_prefers_explicit_setting(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "anthropic")
    monkeypatch.setenv("OPENAI_API_KEY", "openai-key")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    assert configured_llm_provider() == "anthropic"


def test_configured_llm_provider_supports_voice_override(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "anthropic")
    monkeypatch.setenv("VOICE_LLM_PROVIDER", "openai")

    assert configured_llm_provider(task="voice") == "openai"
    assert configured_llm_provider(task="chat") == "anthropic"


def test_configured_llm_model_supports_openai_voice_override(monkeypatch):
    monkeypatch.setenv("OPENAI_MODEL", "gpt-base")
    monkeypatch.setenv("OPENAI_VOICE_MODEL", "gpt-voice")

    assert configured_llm_model("openai", task="voice") == "gpt-voice"
    assert configured_llm_model("openai", task="chat") == "gpt-base"


def test_extract_json_uses_anthropic_when_configured(monkeypatch):
    captured: dict[str, object] = {}
    recorded: dict[str, object] = {}

    class FakeMessages:
        def create(self, **kwargs):
            captured["kwargs"] = kwargs
            return SimpleNamespace(
                content=[SimpleNamespace(text='```json\n{"field":"value"}\n```')],
                usage=SimpleNamespace(
                    input_tokens=123,
                    output_tokens=45,
                    cache_creation_input_tokens=10,
                    cache_read_input_tokens=4,
                ),
            )

    class FakeAnthropic:
        def __init__(self, api_key):
            captured["api_key"] = api_key
            self.messages = FakeMessages()

    monkeypatch.setenv("LLM_PROVIDER", "anthropic")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "anthropic-test-key")
    monkeypatch.setenv("ANTHROPIC_MODEL", "claude-test-model")
    monkeypatch.setenv("ANTHROPIC_EXTRACTION_MODEL", "claude-extraction-model")
    monkeypatch.setitem(sys.modules, "anthropic", SimpleNamespace(Anthropic=FakeAnthropic))
    monkeypatch.setattr(
        "compliance_os.web.services.llm_runtime._persist_usage_record",
        lambda **kwargs: recorded.update(kwargs),
    )

    result = extract_json(
        system_prompt="extract system",
        user_prompt="extract user",
        usage_context={"operation": "document_extraction", "check_id": "check-1"},
    )

    assert result == {"field": "value"}
    assert captured["api_key"] == "anthropic-test-key"
    assert captured["kwargs"]["model"] == "claude-extraction-model"
    assert captured["kwargs"]["system"] == "extract system"
    assert recorded["provider"] == "anthropic"
    assert recorded["status"] == "success"
    assert recorded["usage_payload"]["input_tokens"] == 123
    assert recorded["usage_payload"]["output_tokens"] == 45
    assert recorded["usage_payload"]["cache_creation_input_tokens"] == 10
    assert recorded["usage_payload"]["cache_read_input_tokens"] == 4


def test_chat_completion_uses_openai_when_configured(monkeypatch):
    captured: dict[str, object] = {}
    recorded: dict[str, object] = {}

    class FakeCompletions:
        def create(self, **kwargs):
            captured["kwargs"] = kwargs
            return SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content="hello from openai"))],
                usage=SimpleNamespace(
                    prompt_tokens=90,
                    completion_tokens=12,
                    total_tokens=102,
                    prompt_tokens_details=SimpleNamespace(cached_tokens=8),
                ),
            )

    class FakeOpenAI:
        def __init__(self, api_key):
            captured["api_key"] = api_key
            self.chat = SimpleNamespace(completions=FakeCompletions())

    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "openai-test-key")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-test-model")
    monkeypatch.setitem(sys.modules, "openai", SimpleNamespace(OpenAI=FakeOpenAI))
    monkeypatch.setattr(
        "compliance_os.web.services.llm_runtime._persist_usage_record",
        lambda **kwargs: recorded.update(kwargs),
    )

    reply = chat_completion(
        system_prompt="chat system",
        messages=[{"role": "user", "content": "hello"}],
        usage_context={"operation": "chat_assistant", "user_id": "user-1"},
    )

    assert reply == "hello from openai"
    assert captured["api_key"] == "openai-test-key"
    assert captured["kwargs"]["model"] == "gpt-test-model"
    assert captured["kwargs"]["messages"][0] == {"role": "system", "content": "chat system"}
    assert recorded["provider"] == "openai"
    assert recorded["status"] == "success"
    assert recorded["usage_payload"]["input_tokens"] == 90
    assert recorded["usage_payload"]["output_tokens"] == 12
    assert recorded["usage_payload"]["total_tokens"] == 102
    assert recorded["usage_payload"]["cache_read_input_tokens"] == 8


def test_configured_app_environment_infers_prod_on_fly(monkeypatch):
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.setenv("FLY_REGION", "sjc")

    assert configured_app_environment() == "prod"


def test_extract_json_records_error_usage_when_json_invalid(monkeypatch):
    recorded: dict[str, object] = {}

    class FakeMessages:
        def create(self, **kwargs):
            return SimpleNamespace(
                content=[SimpleNamespace(text="not-json")],
                usage=SimpleNamespace(input_tokens=7, output_tokens=3),
            )

    class FakeAnthropic:
        def __init__(self, api_key):
            self.messages = FakeMessages()

    monkeypatch.setenv("LLM_PROVIDER", "anthropic")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "anthropic-test-key")
    monkeypatch.setitem(sys.modules, "anthropic", SimpleNamespace(Anthropic=FakeAnthropic))
    monkeypatch.setattr(
        "compliance_os.web.services.llm_runtime._persist_usage_record",
        lambda **kwargs: recorded.update(kwargs),
    )

    with pytest.raises(json.JSONDecodeError):
        extract_json(system_prompt="extract system", user_prompt="extract user")

    assert recorded["status"] == "error"
    assert recorded["usage_payload"]["input_tokens"] == 7
    assert recorded["usage_payload"]["output_tokens"] == 3
    assert recorded["error"].__class__.__name__ == "JSONDecodeError"


def test_missing_provider_configuration_raises(monkeypatch):
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    with pytest.raises(LLMConfigError):
        configured_llm_provider()
