"""Shared LLM provider selection for web extraction and chat."""
from __future__ import annotations

import json
import os
from typing import Any


class LLMConfigError(RuntimeError):
    """Raised when LLM provider configuration is missing or invalid."""


def configured_llm_provider() -> str:
    provider = (os.environ.get("LLM_PROVIDER") or "").strip().lower()
    if provider:
        if provider not in {"anthropic", "openai"}:
            raise LLMConfigError(f"Unsupported LLM_PROVIDER {provider}")
        return provider

    if os.environ.get("ANTHROPIC_API_KEY"):
        return "anthropic"
    if os.environ.get("OPENAI_API_KEY"):
        return "openai"
    raise LLMConfigError(
        "No LLM provider configured. Set LLM_PROVIDER plus the matching API key, "
        "or set ANTHROPIC_API_KEY / OPENAI_API_KEY."
    )


def configured_llm_model(provider: str) -> str:
    if provider == "anthropic":
        return os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")
    if provider == "openai":
        return os.environ.get("OPENAI_MODEL", "gpt-4.1-mini")
    raise LLMConfigError(f"Unsupported provider {provider}")


def _require_api_key(provider: str) -> str:
    env_name = "ANTHROPIC_API_KEY" if provider == "anthropic" else "OPENAI_API_KEY"
    api_key = os.environ.get(env_name)
    if not api_key:
        raise LLMConfigError(f"{env_name} must be set when LLM_PROVIDER={provider}")
    return api_key


def extract_json(
    *,
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0,
    max_tokens: int = 4096,
) -> dict[str, Any]:
    provider = configured_llm_provider()
    model = configured_llm_model(provider)

    if provider == "anthropic":
        import anthropic

        client = anthropic.Anthropic(api_key=_require_api_key(provider))
        response = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
            temperature=temperature,
        )
        content = response.content[0].text
        if content.startswith("```"):
            content = content.split("\n", 1)[1].rsplit("```", 1)[0]
        return json.loads(content)

    from openai import OpenAI

    client = OpenAI(api_key=_require_api_key(provider))
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        response_format={"type": "json_object"},
        temperature=temperature,
    )
    content = response.choices[0].message.content
    return json.loads(content)


def chat_completion(
    *,
    system_prompt: str,
    messages: list[dict[str, str]],
    temperature: float = 0.3,
    max_tokens: int = 1024,
) -> str:
    provider = configured_llm_provider()
    model = configured_llm_model(provider)

    if provider == "anthropic":
        import anthropic

        client = anthropic.Anthropic(api_key=_require_api_key(provider))
        response = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system_prompt,
            messages=messages,
            temperature=temperature,
        )
        return response.content[0].text

    from openai import OpenAI

    client = OpenAI(api_key=_require_api_key(provider))
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "system", "content": system_prompt}] + messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return response.choices[0].message.content or ""
