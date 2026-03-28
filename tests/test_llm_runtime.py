"""Tests for shared LLM runtime selection."""

import sys
from types import SimpleNamespace

import pytest

from compliance_os.web.services.llm_runtime import (
    LLMConfigError,
    chat_completion,
    configured_llm_provider,
    extract_json,
)


def test_configured_llm_provider_prefers_explicit_setting(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "anthropic")
    monkeypatch.setenv("OPENAI_API_KEY", "openai-key")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    assert configured_llm_provider() == "anthropic"


def test_extract_json_uses_anthropic_when_configured(monkeypatch):
    captured: dict[str, object] = {}

    class FakeMessages:
        def create(self, **kwargs):
            captured["kwargs"] = kwargs
            return SimpleNamespace(content=[SimpleNamespace(text='```json\n{"field":"value"}\n```')])

    class FakeAnthropic:
        def __init__(self, api_key):
            captured["api_key"] = api_key
            self.messages = FakeMessages()

    monkeypatch.setenv("LLM_PROVIDER", "anthropic")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "anthropic-test-key")
    monkeypatch.setenv("ANTHROPIC_MODEL", "claude-test-model")
    monkeypatch.setitem(sys.modules, "anthropic", SimpleNamespace(Anthropic=FakeAnthropic))

    result = extract_json(system_prompt="extract system", user_prompt="extract user")

    assert result == {"field": "value"}
    assert captured["api_key"] == "anthropic-test-key"
    assert captured["kwargs"]["model"] == "claude-test-model"
    assert captured["kwargs"]["system"] == "extract system"


def test_chat_completion_uses_openai_when_configured(monkeypatch):
    captured: dict[str, object] = {}

    class FakeCompletions:
        def create(self, **kwargs):
            captured["kwargs"] = kwargs
            return SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content="hello from openai"))]
            )

    class FakeOpenAI:
        def __init__(self, api_key):
            captured["api_key"] = api_key
            self.chat = SimpleNamespace(completions=FakeCompletions())

    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "openai-test-key")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-test-model")
    monkeypatch.setitem(sys.modules, "openai", SimpleNamespace(OpenAI=FakeOpenAI))

    reply = chat_completion(
        system_prompt="chat system",
        messages=[{"role": "user", "content": "hello"}],
    )

    assert reply == "hello from openai"
    assert captured["api_key"] == "openai-test-key"
    assert captured["kwargs"]["model"] == "gpt-test-model"
    assert captured["kwargs"]["messages"][0] == {"role": "system", "content": "chat system"}


def test_missing_provider_configuration_raises(monkeypatch):
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    with pytest.raises(LLMConfigError):
        configured_llm_provider()
