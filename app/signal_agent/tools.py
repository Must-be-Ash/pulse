"""Tool wrappers for the signal agent — Bird search, Exa, GitHub, HN, Firecrawl."""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure scripts/ is on sys.path for lib imports
_SCRIPTS_DIR = Path(__file__).parent.parent.parent / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

import re
from urllib.parse import unquote

from lib import bird_x, dates, env, firecrawl, github, grounding, hackernews, http

from .models import CompactItem


def _log(msg: str) -> None:
    sys.stderr.write(f"[SignalAgent:Tool] {msg}\n")
    sys.stderr.flush()


# ── 4.1: Bird Search ──────────────────────────────────────────────────────

def tool_bird_search(query: str, lookback_days: int = 3) -> list[CompactItem]:
    """Search X/Twitter via Bird using the given query."""
    from_date, to_date = dates.get_date_range(lookback_days)

    config = env.get_config()
    bird_x.set_credentials(config.get("AUTH_TOKEN"), config.get("CT0"))

    try:
        response = bird_x.search_x(query, from_date, to_date, depth="deep")
        raw_items = bird_x.parse_bird_response(response, query=query)
        items = [
            CompactItem(
                item_id=f"gap-x-{i}",
                text=(item.get("text", "") or "")[:400],
                url=item.get("url", ""),
                source="x",
                author=item.get("author_handle", "unknown"),
                date=item.get("date", "unknown"),
                engagement=_compact_engagement(item.get("engagement")),
            )
            for i, item in enumerate(raw_items)
            if item.get("url")
        ]
        _log(f"Bird search '{query}': {len(items)} items")
        return items
    except Exception as exc:
        _log(f"Bird search '{query}' failed: {exc}")
        return []


# ── 4.2: Exa Web Search ───────────────────────────────────────────────────

def tool_exa_search(query: str, lookback_days: int = 3) -> list[CompactItem]:
    """Search the web via Exa."""
    from_date, to_date = dates.get_date_range(lookback_days)
    config = env.get_config()
    exa_key = config.get("EXA_API_KEY")
    if not exa_key:
        _log("Exa search skipped: no EXA_API_KEY")
        return []

    try:
        raw_items, _ = grounding.exa_search(query, (from_date, to_date), exa_key, count=10)
        items = [
            CompactItem(
                item_id=f"gap-web-{i}",
                text=f"{item.get('title', '')} | {item.get('snippet', '')}"[:400],
                url=item.get("url", ""),
                source="grounding",
                author=item.get("source_domain", "unknown"),
                date=item.get("date", "unknown"),
                engagement="none",
            )
            for i, item in enumerate(raw_items)
            if item.get("url")
        ]
        _log(f"Exa search '{query}': {len(items)} items")
        return items
    except Exception as exc:
        _log(f"Exa search '{query}' failed: {exc}")
        return []


# ── 4.3: GitHub Search ────────────────────────────────────────────────────

def tool_github_search(query: str, lookback_days: int = 3) -> list[CompactItem]:
    """Search GitHub issues/PRs/repos."""
    from_date, to_date = dates.get_date_range(lookback_days)
    config = env.get_config()

    try:
        raw_items = github.search_github(
            query, from_date, to_date,
            depth="deep", token=config.get("GITHUB_TOKEN"),
        )
        items = [
            CompactItem(
                item_id=f"gap-gh-{i}",
                text=f"{item.get('title', '')} | {(item.get('snippet', '') or '')[:200]}"[:400],
                url=item.get("url", ""),
                source="github",
                author=item.get("author", "unknown"),
                date=item.get("date", "unknown"),
                engagement=_compact_engagement(item.get("engagement")),
            )
            for i, item in enumerate(raw_items)
            if item.get("url")
        ]
        _log(f"GitHub search '{query}': {len(items)} items")
        return items
    except Exception as exc:
        _log(f"GitHub search '{query}' failed: {exc}")
        return []


# ── 4.4: HackerNews Search ────────────────────────────────────────────────

def tool_hn_search(query: str, lookback_days: int = 3) -> list[CompactItem]:
    """Search Hacker News via Algolia."""
    from_date, to_date = dates.get_date_range(lookback_days)

    try:
        response = hackernews.search_hackernews(query, from_date, to_date, depth="deep")
        raw_items = hackernews.parse_hackernews_response(response, query=query)
        items = [
            CompactItem(
                item_id=f"gap-hn-{i}",
                text=f"{item.get('title', '')} | {(item.get('snippet', '') or '')[:200]}"[:400],
                url=item.get("hn_url", item.get("url", "")),
                source="hackernews",
                author=item.get("author", "unknown"),
                date=item.get("date", "unknown"),
                engagement=_compact_engagement(item.get("engagement")),
            )
            for i, item in enumerate(raw_items)
            if item.get("url") or item.get("hn_url")
        ]
        _log(f"HN search '{query}': {len(items)} items")
        return items
    except Exception as exc:
        _log(f"HN search '{query}' failed: {exc}")
        return []


# ── 4.5: Firecrawl Scrape ─────────────────────────────────────────────────

def tool_firecrawl_scrape(url: str) -> str:
    """Scrape a URL and return markdown content (truncated to 2000 chars)."""
    config = env.get_config()
    fc_key = config.get("FIRECRAWL_API_KEY")
    if not fc_key:
        _log("Firecrawl scrape skipped: no FIRECRAWL_API_KEY")
        return ""

    try:
        result = firecrawl.scrape(url, api_key=fc_key)
        if "error" in result:
            _log(f"Firecrawl scrape '{url}': {result['error']}")
            return ""
        content = (result.get("data") or {}).get("markdown", "")
        truncated = content[:2000]
        _log(f"Firecrawl scrape '{url}': {len(truncated)} chars")
        return truncated
    except Exception as exc:
        _log(f"Firecrawl scrape '{url}' failed: {exc}")
        return ""


# ── 4.6: Fetch Tweet by ID/URL ─────────────────────────────────────────────

_TWEET_ID_RE = re.compile(r"(?:x\.com|twitter\.com)/\w+/status/(\d+)")


def _extract_expanded_urls(tweet_data: dict) -> list[str]:
    """Extract expanded URLs from tweet entities, filtering out t.co and media links.

    Keeps external URLs and X Articles (x.com/i/article/...).
    Filters out x.com photo/video links and t.co shortened URLs.
    """
    urls = []
    entities = tweet_data.get("entities", {})
    for url_obj in entities.get("urls", []):
        expanded = url_obj.get("unwound_url") or url_obj.get("expanded_url", "")
        if not expanded or "t.co/" in expanded:
            continue
        # Keep X Articles (x.com/i/article/...)
        if "/i/article/" in expanded:
            urls.append(expanded)
            continue
        # Filter out x.com/twitter.com photo/video/status links
        if "x.com/" in expanded or "twitter.com/" in expanded:
            continue
        urls.append(expanded)
    return urls


def _fetch_x_article(article_url: str) -> str:
    """Fetch an X Article's content using Exa search as a proxy.

    X Articles can't be scraped directly or fetched via the API.
    We search Exa for the article URL to get cached content.
    """
    config = env.get_config()
    exa_key = config.get("EXA_API_KEY")
    if not exa_key:
        return ""

    try:
        # Search Exa for the exact URL — it often has cached content
        results, _ = grounding.exa_search(
            article_url, ("2020-01-01", "2030-01-01"), exa_key, count=1,
        )
        if results:
            snippet = results[0].get("snippet", "") or results[0].get("text", "")
            if snippet:
                _log(f"X Article via Exa: {len(snippet)} chars")
                return snippet[:1500]
    except Exception:
        pass

    return ""


def tool_fetch_tweet(tweet_id_or_url: str, scrape_linked: bool = True) -> CompactItem | None:
    """Fetch a specific tweet by ID or URL using the Twitter API v2.

    If the tweet contains links to articles/repos, automatically scrapes them
    and appends the content to the tweet text for richer context.

    Args:
        tweet_id_or_url: Either a numeric tweet ID or a full x.com/twitter.com URL.
        scrape_linked: If True, also scrape any linked articles/repos via Firecrawl.

    Returns:
        A CompactItem with the tweet content + linked article content, or None on failure.
    """
    config = env.get_config()
    bearer = config.get("TWITTER_BEARER_TOKEN")
    if not bearer:
        _log("Tweet fetch skipped: no TWITTER_BEARER_TOKEN")
        return None

    # URL-decode the bearer token (stored percent-encoded in .env)
    bearer = unquote(bearer)

    # Extract tweet ID from URL if needed
    tweet_id = tweet_id_or_url.strip()
    match = _TWEET_ID_RE.search(tweet_id)
    if match:
        tweet_id = match.group(1)

    if not tweet_id.isdigit():
        _log(f"Invalid tweet ID: {tweet_id_or_url}")
        return None

    url = (
        f"https://api.x.com/2/tweets?ids={tweet_id}"
        f"&tweet.fields=text,author_id,created_at,entities"
        f"&expansions=author_id"
        f"&user.fields=username"
    )

    try:
        resp = http.get(
            url,
            headers={"Authorization": f"Bearer {bearer}"},
            timeout=15,
        )

        tweets = resp.get("data", [])
        if not tweets:
            _log(f"Tweet {tweet_id}: not found")
            return None

        tweet = tweets[0]
        users = {u["id"]: u["username"] for u in resp.get("includes", {}).get("users", [])}
        author = users.get(tweet.get("author_id"), "unknown")
        text = tweet.get("text", "")
        created = tweet.get("created_at", "unknown")
        date = created[:10] if len(created) >= 10 else "unknown"

        # Extract and scrape linked articles/repos
        linked_content = ""
        if scrape_linked:
            expanded_urls = _extract_expanded_urls(tweet)
            for linked_url in expanded_urls[:2]:  # Max 2 linked articles per tweet
                if "/i/article/" in linked_url:
                    # X Article — use Exa search as proxy since direct scraping is blocked
                    article_text = _fetch_x_article(linked_url)
                else:
                    article_text = tool_firecrawl_scrape(linked_url)
                if article_text and len(article_text) > 50:
                    linked_content += f"\n\n[Linked: {linked_url}]\n{article_text[:800]}"
                    _log(f"Tweet {tweet_id}: scraped linked article {linked_url} ({len(article_text)} chars)")

        # Combine tweet text + linked article content
        full_text = text
        if linked_content:
            full_text = f"{text}{linked_content}"

        item = CompactItem(
            item_id=f"tweet-{tweet_id}",
            text=full_text[:800],  # Allow more space when article content is included
            url=f"https://x.com/{author}/status/{tweet_id}",
            source="x",
            author=author,
            date=date,
            engagement="none",
        )
        _log(f"Tweet {tweet_id}: @{author} — {text[:80]}" + (f" (+{len(expanded_urls)} linked)" if scrape_linked and expanded_urls else ""))
        return item

    except Exception as exc:
        _log(f"Tweet fetch {tweet_id} failed: {exc}")
        return None


def tool_fetch_tweets_batch(tweet_ids_or_urls: list[str], scrape_linked: bool = False) -> list[CompactItem]:
    """Fetch multiple tweets by ID/URL in a single API call (up to 100).

    Args:
        tweet_ids_or_urls: List of tweet IDs or x.com URLs.
        scrape_linked: If True, also scrape linked articles (slower, use sparingly).

    Returns:
        List of CompactItems for successfully fetched tweets.
    """
    config = env.get_config()
    bearer = config.get("TWITTER_BEARER_TOKEN")
    if not bearer:
        _log("Tweet batch fetch skipped: no TWITTER_BEARER_TOKEN")
        return []

    bearer = unquote(bearer)

    # Extract tweet IDs
    ids = []
    for raw in tweet_ids_or_urls:
        raw = raw.strip()
        match = _TWEET_ID_RE.search(raw)
        if match:
            ids.append(match.group(1))
        elif raw.isdigit():
            ids.append(raw)

    if not ids:
        return []

    # Twitter API v2 supports up to 100 IDs per request
    items: list[CompactItem] = []
    for chunk_start in range(0, len(ids), 100):
        chunk = ids[chunk_start:chunk_start + 100]
        ids_param = ",".join(chunk)
        url = (
            f"https://api.x.com/2/tweets?ids={ids_param}"
            f"&tweet.fields=text,author_id,created_at,entities"
            f"&expansions=author_id"
            f"&user.fields=username"
        )

        try:
            resp = http.get(
                url,
                headers={"Authorization": f"Bearer {bearer}"},
                timeout=20,
            )
            users = {u["id"]: u["username"] for u in resp.get("includes", {}).get("users", [])}

            for tweet in resp.get("data", []):
                author = users.get(tweet.get("author_id"), "unknown")
                text = tweet.get("text", "")
                created = tweet.get("created_at", "unknown")
                date = created[:10] if len(created) >= 10 else "unknown"
                tid = tweet["id"]

                # Scrape linked articles if requested
                linked_content = ""
                if scrape_linked:
                    expanded_urls = _extract_expanded_urls(tweet)
                    for linked_url in expanded_urls[:1]:  # Max 1 per tweet in batch mode
                        article_text = tool_firecrawl_scrape(linked_url)
                        if article_text and len(article_text) > 50:
                            linked_content = f"\n\n[Linked: {linked_url}]\n{article_text[:600]}"

                full_text = f"{text}{linked_content}" if linked_content else text

                items.append(CompactItem(
                    item_id=f"tweet-{tid}",
                    text=full_text[:800] if linked_content else text[:400],
                    url=f"https://x.com/{author}/status/{tid}",
                    source="x",
                    author=author,
                    date=date,
                    engagement="none",
                ))

            _log(f"Tweet batch: {len(resp.get('data', []))} fetched from {len(chunk)} IDs")
        except Exception as exc:
            _log(f"Tweet batch fetch failed: {exc}")

    return items


# ── 4.7: Gap Search Runner ────────────────────────────────────────────────

_SOURCE_TOOL_MAP = {
    "x": tool_bird_search,
    "hackernews": tool_hn_search,
    "github": tool_github_search,
    "grounding": tool_exa_search,
}


def run_gap_searches(
    suggested_searches: list[dict],
    lookback_days: int = 3,
    max_searches: int = 8,
) -> list[CompactItem]:
    """Execute gap-filling searches. Runs sequentially to avoid rate limits."""
    all_items: list[CompactItem] = []

    for search in suggested_searches[:max_searches]:
        query = search.get("query", "")
        source = search.get("source", "x")
        reason = search.get("reason", "")

        _log(f"Gap fill [{source}]: '{query}' ({reason})")

        if source == "tweet_url":
            # Fetch a specific tweet by URL
            item = tool_fetch_tweet(query)
            if item:
                all_items.append(item)
        elif source == "scrape":
            # Scrape a specific URL
            content = tool_firecrawl_scrape(query)
            if content:
                all_items.append(CompactItem(
                    item_id=f"gap-scrape-{len(all_items)}",
                    text=content[:400],
                    url=query,
                    source="grounding",
                    author="scraped",
                    date="unknown",
                    engagement="none",
                ))
        else:
            tool_fn = _SOURCE_TOOL_MAP.get(source, tool_bird_search)
            items = tool_fn(query, lookback_days)
            all_items.extend(items)

    _log(f"Gap fill total: {len(all_items)} new items from {min(len(suggested_searches), max_searches)} searches")
    return all_items


# ── Grok Trends Scout ──────────────────────────────────────────────────────

_GROK_SCOUT_PROMPT = """You have access to real-time X (Twitter) data. Give me a rundown of the most noteworthy tweets from the last 24 hours in AI, developer tools, and tech.

I want a LIST of specific tweets worth paying attention to — not analysis, not summaries. Just the tweets.

Focus on:
- Builder takes that went viral (high likes/retweets)
- Debates and controversies people are arguing about
- Paradigm shifts ("people are moving from X to Y")
- Major announcements that the community is reacting to
- Thought leader hot takes (Karpathy, levelsio, Garry Tan, etc.)
- Pricing/business model shifts
- Surprising developments

DO NOT include:
- Generic AI news without community reaction
- Tool launch announcements (just the tool, no discussion)
- Politics, geopolitics, sports, entertainment

Return 30-50 tweets as JSON:
{{
  "items": [
    {{
      "text": "Full tweet text",
      "url": "https://x.com/user/status/...",
      "author_handle": "username",
      "date": "YYYY-MM-DD",
      "engagement": {{"likes": 1000, "reposts": 200, "replies": 50}},
      "why_relevant": "Why this tweet matters for understanding the zeitgeist"
    }}
  ]
}}"""


def tool_grok_trends_scout() -> list[CompactItem]:
    """Ask Grok to surface the most noteworthy AI/tech tweets from the last 24h.

    Uses xAI's responses API with x_search tool for real-time X access.
    Returns a list of CompactItems ready for the signal agent pipeline.
    """
    config = env.get_config()
    xai_key = config.get("XAI_API_KEY")
    if not xai_key:
        _log("Grok scout skipped: no XAI_API_KEY")
        return []

    from lib import dates as dates_mod
    from_date, _ = dates_mod.get_date_range(1)

    payload = {
        "model": "grok-3-fast",
        "tools": [
            {"type": "x_search", "from_date": from_date}
        ],
        "input": [
            {"role": "user", "content": _GROK_SCOUT_PROMPT}
        ],
    }

    _log("Grok scout: asking for 24h AI/tech rundown...")

    try:
        resp = http.post(
            "https://api.x.ai/v1/responses",
            payload,
            headers={
                "Authorization": f"Bearer {xai_key}",
                "Content-Type": "application/json",
            },
            timeout=120,
        )

        # Extract text from xAI responses format
        # The response has: output[0]=reasoning, output[1]=tool_call, ..., output[N]=message
        # The message contains content[0].text with the actual JSON
        # There's also a top-level "text" field as a shortcut
        output_text = ""

        # Try the top-level "text" field first (simplest) — but only if it's a string
        top_text = resp.get("text")
        if isinstance(top_text, str) and top_text.strip():
            output_text = top_text
        elif "output" in resp:
            output = resp["output"]
            if isinstance(output, str):
                output_text = output
            elif isinstance(output, list):
                # Walk backwards — the message is usually last
                for item in reversed(output):
                    if not isinstance(item, dict):
                        continue
                    if item.get("type") == "message":
                        for content_item in item.get("content", []):
                            if isinstance(content_item, dict) and content_item.get("type") == "output_text":
                                output_text = content_item.get("text", "")
                                break
                    if output_text:
                        break

        if not output_text:
            _log("Grok scout: no output text in response")
            return []

        # Parse JSON from the response
        import json as _json
        # Try to find JSON in the output
        json_match = re.search(r'\{[\s\S]*"items"[\s\S]*\}', output_text)
        if not json_match:
            _log(f"Grok scout: no JSON found in output ({len(output_text)} chars)")
            return []

        data = _json.loads(json_match.group())
        raw_items = data.get("items", [])

        items = []
        for i, item in enumerate(raw_items):
            if not isinstance(item, dict):
                continue
            url = item.get("url", "")
            text = item.get("text", "")
            if not url or not text:
                continue

            eng = item.get("engagement") or {}
            eng_str = _compact_engagement(eng)

            items.append(CompactItem(
                item_id=f"grok-{i}",
                text=text[:400],
                url=url,
                source="x",
                author=item.get("author_handle", "unknown"),
                date=item.get("date", "unknown"),
                engagement=eng_str,
            ))

        _log(f"Grok scout: {len(items)} tweets surfaced")
        return items

    except Exception as exc:
        _log(f"Grok scout failed: {type(exc).__name__}: {exc}")
        return []


# ── Helper ─────────────────────────────────────────────────────────────────

def _compact_engagement(eng: dict | None) -> str:
    """Convert an engagement dict to a compact string."""
    if not eng or not isinstance(eng, dict):
        return "none"
    parts = []
    for key, val in eng.items():
        if val and isinstance(val, (int, float)) and val > 0:
            parts.append(f"{key}:{int(val)}")
    return ", ".join(parts[:4]) if parts else "none"
