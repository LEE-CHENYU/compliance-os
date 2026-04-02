"""Shared LLM provider selection for web extraction and chat."""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from time import perf_counter
from typing import Any

from sqlalchemy.orm import Session, sessionmaker

from compliance_os.web.models.database import get_engine
from compliance_os.web.models.tables_v2 import LlmApiUsageRow

logger = logging.getLogger(__name__)


class LLMConfigError(RuntimeError):
    """Raised when LLM provider configuration is missing or invalid."""


def configured_app_environment() -> str:
    for env_name in ("APP_ENV", "ENVIRONMENT"):
        value = (os.environ.get(env_name) or "").strip().lower()
        if value:
            if value in {"production", "prod"}:
                return "prod"
            if value in {"development", "dev"}:
                return "dev"
            if value in {"testing", "test"}:
                return "test"
            if value in {"staging", "stage"}:
                return "staging"
            return value
    if os.environ.get("PYTEST_CURRENT_TEST"):
        return "test"
    if os.environ.get("FLY_APP_NAME") or os.environ.get("FLY_REGION") or os.environ.get("PRIMARY_REGION"):
        return "prod"
    return "dev"


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


def configured_llm_model(provider: str, *, task: str = "chat") -> str:
    """Return the model ID for the given provider and task.

    task="extraction" uses a cheaper/faster model (Haiku) for document extraction.
    task="chat" uses the primary model (Sonnet) for interactive chat.
    """
    if provider == "anthropic":
        if task == "extraction":
            return os.environ.get(
                "ANTHROPIC_EXTRACTION_MODEL",
                os.environ.get("ANTHROPIC_MODEL", "claude-haiku-4-5-20251001"),
            )
        return os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-6")
    if provider == "openai":
        return os.environ.get("OPENAI_MODEL", "gpt-4.1-mini")
    raise LLMConfigError(f"Unsupported provider {provider}")


def _require_api_key(provider: str) -> str:
    env_map = {"anthropic": "ANTHROPIC_API_KEY", "openai": "OPENAI_API_KEY", "google": "GOOGLE_API_KEY"}
    env_name = env_map.get(provider, f"{provider.upper()}_API_KEY")
    api_key = os.environ.get(env_name)
    if not api_key:
        raise LLMConfigError(f"{env_name} must be set when LLM_PROVIDER={provider}")
    return api_key


def _usage_to_dict(value: Any) -> dict[str, Any] | None:
    if value is None:
        return None
    if hasattr(value, "model_dump"):
        dumped = value.model_dump()
        if isinstance(dumped, dict):
            return _json_safe(dumped)
    if isinstance(value, dict):
        return _json_safe(value)
    data = {
        key: attr
        for key in dir(value)
        if not key.startswith("_") and not callable(attr := getattr(value, key))
    }
    return _json_safe(data) or None


def _json_safe(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(item) for item in value]
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.isoformat()
    if hasattr(value, "model_dump"):
        return _json_safe(value.model_dump())
    if hasattr(value, "__dict__"):
        return _json_safe(
            {
                key: item
                for key, item in vars(value).items()
                if not key.startswith("_") and not callable(item)
            }
        )
    return str(value)


def _int_or_none(value: Any) -> int | None:
    try:
        if value is None:
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


def _normalized_usage(provider: str, response: Any) -> dict[str, Any]:
    usage = getattr(response, "usage", None)
    usage_details = _usage_to_dict(usage) or {}

    if provider == "anthropic":
        input_tokens = _int_or_none(getattr(usage, "input_tokens", None))
        output_tokens = _int_or_none(getattr(usage, "output_tokens", None))
        cache_creation_tokens = _int_or_none(
            getattr(usage, "cache_creation_input_tokens", None)
        )
        cache_read_tokens = _int_or_none(getattr(usage, "cache_read_input_tokens", None))
        total_tokens = sum(
            value or 0
            for value in (
                input_tokens,
                output_tokens,
                cache_creation_tokens,
                cache_read_tokens,
            )
        ) or None
        return {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": total_tokens,
            "cache_creation_input_tokens": cache_creation_tokens,
            "cache_read_input_tokens": cache_read_tokens,
            "usage_details": usage_details or None,
        }

    input_tokens = _int_or_none(getattr(usage, "prompt_tokens", None))
    output_tokens = _int_or_none(getattr(usage, "completion_tokens", None))
    total_tokens = _int_or_none(getattr(usage, "total_tokens", None))
    prompt_details = getattr(usage, "prompt_tokens_details", None)
    cache_read_tokens = None
    if prompt_details is not None:
        cache_read_tokens = _int_or_none(getattr(prompt_details, "cached_tokens", None))
    if total_tokens is None:
        total_tokens = sum(value or 0 for value in (input_tokens, output_tokens)) or None
    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": total_tokens,
        "cache_creation_input_tokens": None,
        "cache_read_input_tokens": cache_read_tokens,
        "usage_details": usage_details or None,
    }


def _persist_usage_record(
    *,
    provider: str,
    model: str,
    status: str,
    started_at: datetime,
    completed_at: datetime,
    latency_ms: int,
    usage_context: dict[str, Any] | None,
    usage_payload: dict[str, Any] | None,
    error: Exception | None,
) -> None:
    context = dict(usage_context or {})
    db_session = context.pop("db_session", None)
    request_metadata = dict(context.pop("request_metadata", {}) or {})
    operation = str(context.pop("operation", "llm_request"))
    check_id = context.pop("check_id", None)
    document_id = context.pop("document_id", None)
    user_id = context.pop("user_id", None)
    if context:
        request_metadata.update(context)

    payload = dict(usage_payload or {})
    row = LlmApiUsageRow(
        check_id=check_id,
        document_id=document_id,
        user_id=user_id,
        environment=configured_app_environment(),
        provider=provider,
        model=model,
        operation=operation,
        status=status,
        input_tokens=payload.get("input_tokens"),
        output_tokens=payload.get("output_tokens"),
        total_tokens=payload.get("total_tokens"),
        cache_creation_input_tokens=payload.get("cache_creation_input_tokens"),
        cache_read_input_tokens=payload.get("cache_read_input_tokens"),
        latency_ms=latency_ms,
        error_type=type(error).__name__ if error else None,
        error_message=str(error) if error else None,
        request_metadata=_json_safe(request_metadata) if request_metadata else None,
        usage_details=_json_safe(payload.get("usage_details")),
        started_at=started_at,
        completed_at=completed_at,
    )

    try:
        if isinstance(db_session, Session):
            db_session.add(row)
            db_session.flush()
            return

        SessionLocal = sessionmaker(bind=get_engine())
        session = SessionLocal()
        try:
            session.add(row)
            session.commit()
        finally:
            session.close()
    except Exception as exc:  # pragma: no cover - tracking must not break requests
        logger.warning("Failed to persist LLM API usage row: %s", exc)


def extract_json(
    *,
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0,
    max_tokens: int = 4096,
    usage_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    provider = configured_llm_provider()
    model = configured_llm_model(provider, task="extraction")
    started_at = datetime.now(timezone.utc)
    started_perf = perf_counter()

    try:
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
            usage_payload = _normalized_usage(provider, response)
            content = response.content[0].text
            if content.startswith("```"):
                content = content.split("\n", 1)[1].rsplit("```", 1)[0]
            try:
                result = json.loads(content)
            except Exception as exc:
                completed_at = datetime.now(timezone.utc)
                _persist_usage_record(
                    provider=provider,
                    model=model,
                    status="error",
                    started_at=started_at,
                    completed_at=completed_at,
                    latency_ms=int((perf_counter() - started_perf) * 1000),
                    usage_context={
                        **(usage_context or {}),
                        "request_metadata": {
                            **dict((usage_context or {}).get("request_metadata") or {}),
                            "temperature": temperature,
                            "max_tokens": max_tokens,
                            "response_format": "json_object",
                        },
                    },
                    usage_payload=usage_payload,
                    error=exc,
                )
                raise
            completed_at = datetime.now(timezone.utc)
            _persist_usage_record(
                provider=provider,
                model=model,
                status="success",
                started_at=started_at,
                completed_at=completed_at,
                latency_ms=int((perf_counter() - started_perf) * 1000),
                usage_context={
                    **(usage_context or {}),
                    "request_metadata": {
                        **dict((usage_context or {}).get("request_metadata") or {}),
                        "temperature": temperature,
                        "max_tokens": max_tokens,
                        "response_format": "json_object",
                    },
                },
                usage_payload=usage_payload,
                error=None,
            )
            return result

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
            max_tokens=max_tokens,
        )
        usage_payload = _normalized_usage(provider, response)
        content = response.choices[0].message.content
        try:
            result = json.loads(content)
        except Exception as exc:
            completed_at = datetime.now(timezone.utc)
            _persist_usage_record(
                provider=provider,
                model=model,
                status="error",
                started_at=started_at,
                completed_at=completed_at,
                latency_ms=int((perf_counter() - started_perf) * 1000),
                usage_context={
                    **(usage_context or {}),
                    "request_metadata": {
                        **dict((usage_context or {}).get("request_metadata") or {}),
                        "temperature": temperature,
                        "max_tokens": max_tokens,
                        "response_format": "json_object",
                    },
                },
                usage_payload=usage_payload,
                error=exc,
            )
            raise
        completed_at = datetime.now(timezone.utc)
        _persist_usage_record(
            provider=provider,
            model=model,
            status="success",
            started_at=started_at,
            completed_at=completed_at,
            latency_ms=int((perf_counter() - started_perf) * 1000),
            usage_context={
                **(usage_context or {}),
                "request_metadata": {
                    **dict((usage_context or {}).get("request_metadata") or {}),
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "response_format": "json_object",
                },
            },
            usage_payload=usage_payload,
            error=None,
        )
        return result
    except Exception as exc:
        if isinstance(exc, (json.JSONDecodeError,)):
            raise
        completed_at = datetime.now(timezone.utc)
        _persist_usage_record(
            provider=provider,
            model=model,
            status="error",
            started_at=started_at,
            completed_at=completed_at,
            latency_ms=int((perf_counter() - started_perf) * 1000),
            usage_context={
                **(usage_context or {}),
                "request_metadata": {
                    **dict((usage_context or {}).get("request_metadata") or {}),
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "response_format": "json_object",
                },
            },
            usage_payload=None,
            error=exc,
        )
        raise


def extract_json_with_model(
    *,
    provider: str,
    model: str,
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0,
    max_tokens: int = 4096,
    usage_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Like extract_json but with an explicit provider and model.

    Supports "anthropic", "openai", and "google" providers.
    """
    started_at = datetime.now(timezone.utc)
    started_perf = perf_counter()

    def _meta() -> dict:
        return {
            **(usage_context or {}),
            "request_metadata": {
                **dict((usage_context or {}).get("request_metadata") or {}),
                "temperature": temperature,
                "max_tokens": max_tokens,
                "response_format": "json_object",
                "routed_provider": provider,
                "routed_model": model,
            },
        }

    try:
        if provider == "anthropic":
            import anthropic
            client = anthropic.Anthropic(api_key=_require_api_key(provider))
            response = client.messages.create(
                model=model, max_tokens=max_tokens, system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
                temperature=temperature,
            )
            usage_payload = _normalized_usage(provider, response)
            content = response.content[0].text
            if content.startswith("```"):
                content = content.split("\n", 1)[1].rsplit("```", 1)[0]

        elif provider == "openai":
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
                max_completion_tokens=max_tokens,
            )
            usage_payload = _normalized_usage(provider, response)
            content = response.choices[0].message.content

        elif provider == "google":
            import google.generativeai as genai
            genai.configure(api_key=_require_api_key(provider))
            gen_model = genai.GenerativeModel(
                model_name=model,
                system_instruction=system_prompt,
                generation_config=genai.GenerationConfig(
                    response_mime_type="application/json",
                    temperature=temperature,
                    max_output_tokens=max_tokens,
                ),
            )
            response = gen_model.generate_content(user_prompt)
            content = response.text
            usage_meta = response.usage_metadata
            usage_payload = {
                "input_tokens": getattr(usage_meta, "prompt_token_count", None),
                "output_tokens": getattr(usage_meta, "candidates_token_count", None),
                "total_tokens": getattr(usage_meta, "total_token_count", None),
                "cache_creation_input_tokens": None,
                "cache_read_input_tokens": None,
                "usage_details": None,
            }
        else:
            raise LLMConfigError(f"Unsupported provider for routed extraction: {provider}")

        result = json.loads(content)

        completed_at = datetime.now(timezone.utc)
        _persist_usage_record(
            provider=provider, model=model, status="success",
            started_at=started_at, completed_at=completed_at,
            latency_ms=int((perf_counter() - started_perf) * 1000),
            usage_context=_meta(), usage_payload=usage_payload, error=None,
        )
        return result

    except json.JSONDecodeError as exc:
        completed_at = datetime.now(timezone.utc)
        _persist_usage_record(
            provider=provider, model=model, status="error",
            started_at=started_at, completed_at=completed_at,
            latency_ms=int((perf_counter() - started_perf) * 1000),
            usage_context=_meta(), usage_payload=locals().get("usage_payload"), error=exc,
        )
        raise
    except Exception as exc:
        completed_at = datetime.now(timezone.utc)
        _persist_usage_record(
            provider=provider, model=model, status="error",
            started_at=started_at, completed_at=completed_at,
            latency_ms=int((perf_counter() - started_perf) * 1000),
            usage_context=_meta(), usage_payload=None, error=exc,
        )
        raise


def chat_completion(
    *,
    system_prompt: str,
    messages: list[dict[str, str]],
    temperature: float = 0.3,
    max_tokens: int = 1024,
    usage_context: dict[str, Any] | None = None,
) -> str:
    provider = configured_llm_provider()
    model = configured_llm_model(provider)
    started_at = datetime.now(timezone.utc)
    started_perf = perf_counter()

    try:
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
            completed_at = datetime.now(timezone.utc)
            _persist_usage_record(
                provider=provider,
                model=model,
                status="success",
                started_at=started_at,
                completed_at=completed_at,
                latency_ms=int((perf_counter() - started_perf) * 1000),
                usage_context={
                    **(usage_context or {}),
                    "request_metadata": {
                        **dict((usage_context or {}).get("request_metadata") or {}),
                        "temperature": temperature,
                        "max_tokens": max_tokens,
                        "message_count": len(messages),
                    },
                },
                usage_payload=_normalized_usage(provider, response),
                error=None,
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
        completed_at = datetime.now(timezone.utc)
        _persist_usage_record(
            provider=provider,
            model=model,
            status="success",
            started_at=started_at,
            completed_at=completed_at,
            latency_ms=int((perf_counter() - started_perf) * 1000),
            usage_context={
                **(usage_context or {}),
                "request_metadata": {
                    **dict((usage_context or {}).get("request_metadata") or {}),
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "message_count": len(messages),
                },
            },
            usage_payload=_normalized_usage(provider, response),
            error=None,
        )
        return response.choices[0].message.content or ""
    except Exception as exc:
        completed_at = datetime.now(timezone.utc)
        _persist_usage_record(
            provider=provider,
            model=model,
            status="error",
            started_at=started_at,
            completed_at=completed_at,
            latency_ms=int((perf_counter() - started_perf) * 1000),
            usage_context={
                **(usage_context or {}),
                "request_metadata": {
                    **dict((usage_context or {}).get("request_metadata") or {}),
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "message_count": len(messages),
                },
            },
            usage_payload=None,
            error=exc,
        )
        raise
