"""LLM client for the signal agent — all Claude, OpenAI not required."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

_SCRIPTS_DIR = Path(__file__).parent.parent.parent / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from lib import env, http

# All tiers use Claude via Anthropic API
CLAUDE_TRIAGE_MODEL = "claude-haiku-4-5-20251001"
CLAUDE_DEEP_MODEL = "claude-sonnet-4-6"
CLAUDE_SCRIPT_MODEL = "claude-haiku-4-5-20251001"

# xAI fallback (if no Claude key)
XAI_MODEL = "grok-4-1-fast"


def _get_config() -> dict:
    return env.get_config()


def _resolve_model(tier: str) -> str:
    if tier == "triage":
        return CLAUDE_TRIAGE_MODEL
    if tier == "deep":
        return CLAUDE_DEEP_MODEL
    return CLAUDE_SCRIPT_MODEL


def _chat_claude(
    prompt_system: str,
    prompt_user: str,
    model: str,
    temperature: float,
    timeout: int,
) -> str:
    """Call Anthropic Messages API, return the text content."""
    config = _get_config()
    api_key = config.get("CLAUDE_API_KEY")
    if not api_key:
        raise RuntimeError("No CLAUDE_API_KEY in ~/.config/pulse/.env")

    payload = {
        "model": model,
        "max_tokens": 8192,
        "system": prompt_system,
        "messages": [{"role": "user", "content": prompt_user}],
        "temperature": temperature,
    }

    response = http.post(
        "https://api.anthropic.com/v1/messages",
        payload,
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        },
        timeout=timeout,
    )

    content = response.get("content", [])
    for block in content:
        if isinstance(block, dict) and block.get("type") == "text":
            return block.get("text", "")
    return ""


def _chat_xai_fallback(
    prompt_system: str,
    prompt_user: str,
    temperature: float,
    timeout: int,
) -> str:
    """Fallback to xAI if no Claude key. Uses OpenAI-compatible endpoint."""
    config = _get_config()
    xai_key = config.get("XAI_API_KEY")
    if not xai_key:
        raise RuntimeError("No CLAUDE_API_KEY or XAI_API_KEY")

    payload = {
        "model": XAI_MODEL,
        "messages": [
            {"role": "system", "content": prompt_system},
            {"role": "user", "content": prompt_user},
        ],
        "temperature": temperature,
        "response_format": {"type": "json_object"},
    }

    response = http.post(
        "https://api.x.ai/v1/chat/completions",
        payload,
        headers={
            "Authorization": f"Bearer {xai_key}",
            "Content-Type": "application/json",
        },
        timeout=timeout,
    )

    return response["choices"][0]["message"]["content"]


def chat_json(
    prompt_system: str,
    prompt_user: str,
    *,
    model: str | None = None,
    tier: str = "triage",
    temperature: float = 0,
    timeout: int = 120,
) -> dict[str, Any]:
    """Send a chat completion and parse the response as JSON.

    Uses Claude for all tiers. Falls back to xAI if no Claude key.
    """
    config = _get_config()
    has_claude = bool(config.get("CLAUDE_API_KEY"))

    if has_claude:
        used_model = model or _resolve_model(tier)
        prompt_user_json = prompt_user + "\n\nIMPORTANT: Return ONLY valid JSON, no other text."
        text = _chat_claude(prompt_system, prompt_user_json, used_model, temperature, timeout)
    else:
        text = _chat_xai_fallback(prompt_system, prompt_user, temperature, timeout)

    # Parse JSON — handle potential markdown code blocks
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()

    return json.loads(text)


def chat_text(
    prompt_system: str,
    prompt_user: str,
    *,
    model: str | None = None,
    tier: str = "script",
    temperature: float = 0.3,
    timeout: int = 60,
) -> str:
    """Send a chat completion and return plain text. Uses Claude Haiku."""
    config = _get_config()

    if config.get("CLAUDE_API_KEY"):
        used_model = model or CLAUDE_SCRIPT_MODEL
        return _chat_claude(prompt_system, prompt_user, used_model, temperature, timeout)

    # xAI fallback
    return _chat_xai_fallback(prompt_system, prompt_user, temperature, timeout)
