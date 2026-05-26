"""LLM client for the signal agent — Claude Haiku for triage, OpenAI for deep analysis."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

_SCRIPTS_DIR = Path(__file__).parent.parent.parent / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from lib import env, http

# Model tiers
CLAUDE_TRIAGE_MODEL = "claude-haiku-4-5-20251001"
OPENAI_DEEP_MODEL = "gpt-4o"
OPENAI_SCRIPT_MODEL = "gpt-4o-mini"

# Fallbacks
OPENAI_TRIAGE_MODEL = "gpt-4o-mini"
XAI_TRIAGE_MODEL = "grok-4-1-fast"
XAI_DEEP_MODEL = "grok-4-1-fast"


def _get_config() -> dict:
    return env.get_config()


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
        raise RuntimeError("No CLAUDE_API_KEY")

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

    # Anthropic format: {"content": [{"type": "text", "text": "..."}]}
    content = response.get("content", [])
    for block in content:
        if isinstance(block, dict) and block.get("type") == "text":
            return block.get("text", "")
    return ""


def _chat_openai(
    prompt_system: str,
    prompt_user: str,
    model: str,
    temperature: float,
    timeout: int,
    json_mode: bool = False,
) -> str:
    """Call OpenAI-compatible chat completions, return the text content."""
    config = _get_config()

    # Try OpenAI first, then xAI
    openai_key = config.get("OPENAI_API_KEY")
    if openai_key:
        base_url = "https://api.openai.com/v1/chat/completions"
        api_key = openai_key
    else:
        xai_key = config.get("XAI_API_KEY")
        if not xai_key:
            raise RuntimeError("No OPENAI_API_KEY or XAI_API_KEY")
        base_url = "https://api.x.ai/v1/chat/completions"
        api_key = xai_key
        # Remap models for xAI
        if model in (OPENAI_DEEP_MODEL, OPENAI_SCRIPT_MODEL, OPENAI_TRIAGE_MODEL):
            model = XAI_DEEP_MODEL

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": prompt_system},
            {"role": "user", "content": prompt_user},
        ],
        "temperature": temperature,
    }
    if json_mode:
        payload["response_format"] = {"type": "json_object"}

    response = http.post(
        base_url,
        payload,
        headers={
            "Authorization": f"Bearer {api_key}",
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

    For triage: uses Claude Haiku (faster, cheaper).
    For deep/script: uses OpenAI gpt-4o.
    """
    config = _get_config()
    has_claude = bool(config.get("CLAUDE_API_KEY"))

    if tier == "triage" and has_claude:
        # Use Claude Haiku for triage — faster than gpt-4o-mini
        used_model = model or CLAUDE_TRIAGE_MODEL
        # Claude doesn't have JSON mode — ask for JSON in the prompt
        prompt_user_json = prompt_user + "\n\nIMPORTANT: Return ONLY valid JSON, no other text."
        text = _chat_claude(prompt_system, prompt_user_json, used_model, temperature, timeout)
    else:
        # Use OpenAI for deep analysis and scripts
        if model is None:
            if tier == "deep":
                model = OPENAI_DEEP_MODEL
            elif tier == "triage":
                model = OPENAI_TRIAGE_MODEL
            else:
                model = OPENAI_SCRIPT_MODEL
        text = _chat_openai(prompt_system, prompt_user, model, temperature, timeout, json_mode=True)

    # Parse JSON — handle potential markdown code blocks
    text = text.strip()
    if text.startswith("```"):
        # Strip markdown code fences
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
    """Send a chat completion and return plain text."""
    if model is None:
        model = OPENAI_SCRIPT_MODEL
    return _chat_openai(prompt_system, prompt_user, model, temperature, timeout)
