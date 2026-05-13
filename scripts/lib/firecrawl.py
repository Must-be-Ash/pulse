"""Firecrawl API client for on-demand URL scraping.

Firecrawl is invoked as a tool (not a registered source). Used when:
  1. A planner-selected high-signal URL has a thin grounding snippet.
  2. The user explicitly passes ``--scrape <url>`` on the CLI.

Per-run budget is enforced module-side to avoid runaway scraping costs.
"""

from __future__ import annotations

import threading
from typing import Any
from urllib.parse import urlsplit

from . import http

BASE_URL = "https://api.firecrawl.dev/v1"
DEFAULT_TIMEOUT = 60
DEFAULT_BUDGET = 5  # max scrapes per run

_state_lock = threading.Lock()
_state: dict[str, Any] = {
    "calls": 0,
    "domains": set(),  # per-run domain dedupe
}


def reset() -> None:
    """Reset per-run state. Call at the start of each pipeline run."""
    with _state_lock:
        _state["calls"] = 0
        _state["domains"] = set()


def _headers(api_key: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def _domain(url: str) -> str:
    try:
        return (urlsplit(url).netloc or "").lower()
    except ValueError:
        return ""


def _budget_check_and_consume(url: str, budget: int) -> tuple[bool, str | None]:
    """Returns (allowed, reason). Consumes a slot if allowed."""
    domain = _domain(url)
    with _state_lock:
        if _state["calls"] >= budget:
            return False, f"firecrawl: per-run budget {budget} exhausted"
        if domain and domain in _state["domains"]:
            return False, f"firecrawl: domain {domain} already scraped this run"
        _state["calls"] += 1
        if domain:
            _state["domains"].add(domain)
    return True, None


def scrape(
    url: str,
    *,
    api_key: str,
    formats: list[str] | None = None,
    only_main: bool = True,
    budget: int = DEFAULT_BUDGET,
) -> dict[str, Any]:
    """Scrape a single URL, returning the Firecrawl response (typically with
    a ``data.markdown`` field).

    Returns ``{"error": "..."}`` on budget exhaustion or HTTP failure.
    """
    if not url or not api_key:
        return {"error": "firecrawl: missing url or api_key"}

    allowed, reason = _budget_check_and_consume(url, budget)
    if not allowed:
        return {"error": reason}

    body: dict[str, Any] = {
        "url": url,
        "formats": formats or ["markdown"],
        "onlyMainContent": only_main,
    }
    try:
        return http.post(
            f"{BASE_URL}/scrape",
            json_data=body,
            headers=_headers(api_key),
            timeout=DEFAULT_TIMEOUT,
        )
    except http.HTTPError as exc:
        return {"error": f"firecrawl: {exc}"}


def extract(
    urls: list[str],
    *,
    api_key: str,
    schema: dict[str, Any] | None = None,
    prompt: str | None = None,
    budget: int = DEFAULT_BUDGET,
) -> dict[str, Any]:
    """Structured extraction across one or more URLs."""
    if not urls or not api_key:
        return {"error": "firecrawl: missing urls or api_key"}

    # Treat extract as a single budget unit (it's one API call regardless
    # of URL count) but mark all distinct domains as scraped.
    allowed, reason = _budget_check_and_consume(urls[0], budget)
    if not allowed:
        return {"error": reason}

    body: dict[str, Any] = {"urls": urls}
    if schema is not None:
        body["schema"] = schema
    if prompt is not None:
        body["prompt"] = prompt

    try:
        return http.post(
            f"{BASE_URL}/extract",
            json_data=body,
            headers=_headers(api_key),
            timeout=DEFAULT_TIMEOUT,
        )
    except http.HTTPError as exc:
        return {"error": f"firecrawl: {exc}"}


def remaining_budget(budget: int = DEFAULT_BUDGET) -> int:
    with _state_lock:
        return max(0, budget - int(_state["calls"]))
