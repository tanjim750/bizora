"""Server-only LLM provider gateway with bounded Groq key failover."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any


GROQ_CHAT_COMPLETIONS_URL = "https://api.groq.com/openai/v1/chat/completions"
DEFAULT_GROQ_MODEL = "openai/gpt-oss-20b"


def _groq_api_keys() -> list[str]:
    """Return unique configured keys without logging or persisting them."""
    configured = os.environ.get("GROQ_API_KEYS", "").split(",")
    configured.append(os.environ.get("GROQ_API_KEY", ""))
    keys: list[str] = []
    for value in configured:
        key = value.strip()
        if key and key not in keys:
            keys.append(key)
    return keys


def _positive_int_env(name: str, default: int, maximum: int) -> int:
    try:
        value = int(os.environ.get(name, default))
    except (TypeError, ValueError):
        value = default
    return min(max(value, 1), maximum)


def _groq_payload(prompt: str) -> dict[str, Any]:
    return {
        "model": os.environ.get("GROQ_MODEL", DEFAULT_GROQ_MODEL).strip() or DEFAULT_GROQ_MODEL,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are Bizora Business Brain. Follow the supplied business context and "
                    "instructions exactly. Give concise, evidence-grounded answers in the user's "
                    "language. Never invent business facts, amounts, policies, or completed actions. "
                    "When verified evidence is missing, say so explicitly."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.2,
        "max_completion_tokens": _positive_int_env("GROQ_MAX_OUTPUT_TOKENS", 800, 8192),
    }


def _parse_groq_response(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise TypeError("Groq returned an invalid response envelope")
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        raise TypeError("Groq returned no response choices")
    first = choices[0]
    message = first.get("message") if isinstance(first, dict) else None
    content = message.get("content") if isinstance(message, dict) else None
    if not isinstance(content, str) or not content.strip():
        reasoning = message.get("reasoning") if isinstance(message, dict) else None
        if isinstance(reasoning, str) and reasoning.strip():
            content = reasoning
        else:
            raise TypeError("Groq returned no text content")
    usage = payload.get("usage") if isinstance(payload.get("usage"), dict) else {}
    return {
        "content": content.strip(),
        "model": str(payload.get("model") or DEFAULT_GROQ_MODEL),
        "prompt_tokens": int(usage.get("prompt_tokens", 0) or 0),
        "completion_tokens": int(usage.get("completion_tokens", 0) or 0),
        "tokens_used": int(usage.get("total_tokens", 0) or 0),
        "provider": "groq",
        "provider_status": "ok",
    }


def _call_groq(prompt: str, timeout_seconds: int) -> dict[str, Any]:
    keys = _groq_api_keys()
    if not keys:
        raise RuntimeError("Groq is not configured")

    request_body = json.dumps(_groq_payload(prompt)).encode()
    last_error = "Groq request failed"
    for key in keys:
        request = urllib.request.Request(
            GROQ_CHAT_COMPLETIONS_URL,
            data=request_body,
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
                "User-Agent": "Bizora/1.0",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=max(1, timeout_seconds)) as response:
                return _parse_groq_response(json.loads(response.read().decode()))
        except urllib.error.HTTPError as exc:
            last_error = f"Groq returned HTTP {exc.code}"
        except (urllib.error.URLError, TimeoutError, ValueError, TypeError) as exc:
            last_error = f"Groq request failed ({type(exc).__name__})"
    raise RuntimeError(last_error)


def _call_generic_gateway(prompt: str, business_id: int, timeout_seconds: int) -> dict[str, Any]:
    endpoint = os.environ.get("BIZORA_LLM_URL", "").strip()
    if not endpoint:
        raise RuntimeError("No AI provider is configured")
    request = urllib.request.Request(
        endpoint,
        data=json.dumps({"prompt": prompt, "business_id": business_id}).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=max(1, timeout_seconds)) as response:
        payload = json.loads(response.read().decode())
    if not isinstance(payload, dict) or not isinstance(payload.get("content"), str):
        raise TypeError("LLM gateway returned an invalid response")
    return payload | {"provider_status": "ok"}


def execute_llm(
    *,
    prompt: str,
    business_id: int,
    timeout_seconds: int,
    fallback_response: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Call Groq when configured, otherwise preserve the existing gateway contract."""
    fallback = fallback_response or {"content": "AI provider unavailable; no conclusion is available."}
    has_provider = bool(_groq_api_keys() or os.environ.get("BIZORA_LLM_URL", "").strip())
    if not has_provider:
        return {**fallback, "provider_status": "unavailable", "model": "fallback"}
    try:
        if _groq_api_keys():
            return _call_groq(prompt, timeout_seconds)
        return _call_generic_gateway(prompt, business_id, timeout_seconds)
    except Exception as exc:  # noqa: BLE001 - external provider failure is contained
        return {
            **fallback,
            "provider_status": "error",
            "provider_error": str(exc),
            "model": "fallback",
        }
