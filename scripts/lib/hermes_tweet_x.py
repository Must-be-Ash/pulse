"""Hermes Tweet backend for X/Twitter discovery."""

from __future__ import annotations

import os
import re
from contextlib import contextmanager
from typing import Any, Iterator

from . import log

try:
    from hermes_tweet import client as hermes_tweet_client
except ImportError:  # pragma: no cover - optional dependency
    hermes_tweet_client = None


DEPTH_CONFIG = {
    "quick": 12,
    "default": 30,
    "deep": 60,
}
API_KEY_NAMES = ("HERMES_TWEET_API_KEY", "XQUIK_API_KEY")


def _log(message: str) -> None:
    log.source_log("Hermes Tweet", message, tty_only=False)


def is_installed() -> bool:
    """Return whether the optional hermes-tweet package can be imported."""
    return hermes_tweet_client is not None


def get_api_key(config: dict[str, Any]) -> str | None:
    """Return the preferred Hermes Tweet-compatible API key."""
    for key in API_KEY_NAMES:
        value = config.get(key)
        if value:
            return str(value)
    return None


def is_available(config: dict[str, Any]) -> bool:
    """Return whether Hermes Tweet has both its package and API key."""
    return is_installed() and bool(get_api_key(config))


@contextmanager
def _patched_env(config: dict[str, Any]) -> Iterator[None]:
    """Expose config-backed Hermes Tweet env vars for the request only."""
    keys = ("HERMES_TWEET_API_KEY", "XQUIK_API_KEY", "XQUIK_BASE_URL")
    previous = {key: os.environ.get(key) for key in keys}
    try:
        api_key = get_api_key(config)
        if api_key:
            os.environ["HERMES_TWEET_API_KEY"] = api_key
            os.environ["XQUIK_API_KEY"] = api_key
        base_url = config.get("XQUIK_BASE_URL")
        if base_url:
            os.environ["XQUIK_BASE_URL"] = str(base_url)
        yield
    finally:
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def search_x(
    config: dict[str, Any],
    topic: str,
    from_date: str,
    to_date: str,
    depth: str = "default",
    mock_response: dict[str, Any] | list[dict[str, Any]] | None = None,
) -> dict[str, Any] | list[dict[str, Any]]:
    """Search X through Hermes Tweet's read-only Xquik route."""
    if mock_response is not None:
        return mock_response
    if hermes_tweet_client is None:
        return {"success": False, "error": "Install hermes-tweet to use this X backend."}

    limit = DEPTH_CONFIG.get(depth, DEPTH_CONFIG["default"])
    query = {
        "q": topic,
        "queryType": "Top",
        "sinceTime": f"{from_date}T00:00:00Z",
        "untilTime": f"{to_date}T23:59:59Z",
        "limit": str(limit),
    }
    _log(f"Searching: {topic}")
    with _patched_env(config):
        return hermes_tweet_client.request(
            "GET",
            "/api/v1/x/tweets/search",
            query=query,
        )


def parse_search_response(
    response: dict[str, Any] | list[dict[str, Any]],
    query: str = "",
) -> list[dict[str, Any]]:
    """Parse Hermes Tweet search responses into the Pulse X item shape."""
    if isinstance(response, dict) and response.get("success") is False:
        error = response.get("error") or "request failed"
        _log(f"Search failed: {error}")
        return []

    raw_items = _extract_items(response)
    items: list[dict[str, Any]] = []
    for index, tweet in enumerate(raw_items):
        if not isinstance(tweet, dict):
            continue
        text = _text(tweet)
        url = _url(tweet)
        if not text or not url:
            continue
        items.append(
            {
                "id": str(tweet.get("id") or tweet.get("tweet_id") or f"XQ{index + 1}"),
                "text": text[:500],
                "url": url,
                "author_handle": _author_handle(tweet),
                "date": _date(tweet),
                "engagement": _engagement(tweet),
                "why_relevant": f"Hermes Tweet search match for: {query}" if query else "",
                "relevance": _relevance(tweet),
            }
        )
    return items


def _extract_items(response: dict[str, Any] | list[dict[str, Any]]) -> list[Any]:
    if isinstance(response, list):
        return response
    if not isinstance(response, dict):
        return []

    for key in ("items", "tweets", "results"):
        value = response.get(key)
        if isinstance(value, list):
            return value

    data = response.get("data")
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in ("items", "tweets", "results"):
            value = data.get(key)
            if isinstance(value, list):
                return value

    return []


def _nested_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        for key in ("text", "full_text", "body", "content"):
            if value.get(key):
                return str(value[key])
    return ""


def _text(tweet: dict[str, Any]) -> str:
    for key in ("text", "full_text", "body", "content"):
        if tweet.get(key):
            return _nested_text(tweet[key]).strip()
    return ""


def _url(tweet: dict[str, Any]) -> str:
    for key in ("url", "permanent_url", "tweet_url"):
        value = tweet.get(key)
        if value:
            return str(value)

    tweet_id = tweet.get("id") or tweet.get("tweet_id")
    author = _author_handle(tweet)
    if tweet_id and author:
        return f"https://x.com/{author}/status/{tweet_id}"
    return ""


def _author_handle(tweet: dict[str, Any]) -> str:
    for key in ("author_handle", "username", "screen_name", "handle"):
        value = tweet.get(key)
        if value:
            return str(value).lstrip("@")

    for key in ("author", "user"):
        value = tweet.get(key)
        if isinstance(value, dict):
            for nested_key in ("username", "screen_name", "handle"):
                nested_value = value.get(nested_key)
                if nested_value:
                    return str(nested_value).lstrip("@")
    return ""


def _date(tweet: dict[str, Any]) -> str | None:
    for key in ("date", "created_at", "createdAt", "published_at", "timestamp"):
        value = tweet.get(key)
        if not value:
            continue
        raw = str(value)
        match = re.match(r"^(\d{4}-\d{2}-\d{2})", raw)
        if match:
            return match.group(1)
    return None


def _metric(*values: Any) -> int | None:
    for value in values:
        if value is None:
            continue
        try:
            return int(value)
        except (TypeError, ValueError):
            continue
    return None


def _engagement(tweet: dict[str, Any]) -> dict[str, int | None]:
    metrics = tweet.get("engagement") or tweet.get("public_metrics") or {}
    if not isinstance(metrics, dict):
        metrics = {}
    return {
        "likes": _metric(metrics.get("likes"), metrics.get("like_count"), tweet.get("likeCount"), tweet.get("like_count")),
        "reposts": _metric(metrics.get("reposts"), metrics.get("retweet_count"), tweet.get("retweetCount"), tweet.get("retweet_count")),
        "replies": _metric(metrics.get("replies"), metrics.get("reply_count"), tweet.get("replyCount"), tweet.get("reply_count")),
        "quotes": _metric(metrics.get("quotes"), metrics.get("quote_count"), tweet.get("quoteCount"), tweet.get("quote_count")),
    }


def _relevance(tweet: dict[str, Any]) -> float:
    try:
        value = float(tweet.get("relevance", 0.75))
    except (TypeError, ValueError):
        value = 0.75
    return max(0.0, min(1.0, value))
