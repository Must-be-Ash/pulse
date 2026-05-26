"""Background pipeline execution for the menu bar app."""

from __future__ import annotations

import sys
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

# Ensure scripts/ is on sys.path for lib imports
_SCRIPTS_DIR = Path(__file__).parent.parent / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from lib import bird_x, env, normalize, pipeline, render, schema, signals, snippet, dedupe

from . import categories as cat_mod
from . import reporter


@dataclass
class RunState:
    run_id: str
    category: cat_mod.Category
    status: str = "queued"  # queued, running, completed, failed
    started_at: str | None = None
    completed_at: str | None = None
    error: str | None = None
    report_html_path: str | None = None
    audio_path: str | None = None
    progress_messages: list[str] = field(default_factory=list)


# Global state
_current_run: RunState | None = None
_run_lock = threading.Lock()
_latest_runs: dict[str, RunState] = {}  # category_id -> most recent completed run
_run_queue: list[cat_mod.Category] = []
_queue_lock = threading.Lock()


def _restore_from_disk() -> None:
    """Scan ~/Documents/Pulse/ for existing reports and restore latest run state per category."""
    output_dir = reporter.OUTPUT_DIR
    if not output_dir.exists():
        return

    for cat in cat_mod.all_categories():
        slug = reporter._slugify(cat.name)
        # Find HTML reports matching this category
        html_files = sorted(output_dir.glob(f"{slug}-*.html"), reverse=True)
        if not html_files:
            continue

        latest_html = html_files[0]
        # Find the most recent audio file for this category (mp3 or aiff)
        audio_path = None
        audio_files = list(output_dir.glob(f"{slug}-*.mp3")) + list(output_dir.glob(f"{slug}-*.aiff"))
        if audio_files:
            audio_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
            audio_path = str(audio_files[0])

        _latest_runs[cat.id] = RunState(
            run_id=f"restored-{cat.id}",
            category=cat,
            status="completed",
            report_html_path=str(latest_html),
            audio_path=audio_path,
        )


# Restore previous runs on import
_restore_from_disk()


def is_running() -> bool:
    with _run_lock:
        return _current_run is not None and _current_run.status == "running"


def get_current_run() -> RunState | None:
    with _run_lock:
        return _current_run


def get_latest_run(category_id: str) -> RunState | None:
    return _latest_runs.get(category_id)


class _StderrCapture:
    """Tee stderr writes to both the real stderr and a progress list."""

    def __init__(self, real_stderr: Any, progress: list[str]):
        self._real = real_stderr
        self._progress = progress

    def write(self, text: str) -> int:
        self._real.write(text)
        if text.strip():
            self._progress.append(text.strip())
        return len(text)

    def flush(self) -> None:
        self._real.flush()

    def __getattr__(self, name: str) -> Any:
        return getattr(self._real, name)


def _fetch_timeline_sources(
    report: schema.Report,
    category: cat_mod.Category,
    config: dict,
) -> None:
    """Fetch tweets from X lists and home timeline, merge into the report."""
    from lib import dates

    from_date, to_date = dates.get_date_range(category.lookback_days)
    extra_items: list[dict] = []

    # Fetch from each configured X list
    for list_id in category.x_list_ids:
        items = bird_x.fetch_list_timeline(list_id, pages=5, delay_ms=1500)
        if items:
            sys.stderr.write(f"[Bird] List {list_id}: {len(items)} tweets\n")
            extra_items.extend(items)

    # Fetch home timeline
    if category.fetch_home_timeline:
        items = bird_x.fetch_home_timeline(pages=3, delay_ms=2000)
        if items:
            sys.stderr.write(f"[Bird] Home timeline: {len(items)} tweets\n")
            extra_items.extend(items)

    if not extra_items:
        return

    # Normalize and merge into the report's x source items
    normalized = normalize.normalize_source_items(
        "x", extra_items, from_date, to_date,
        freshness_mode=report.query_plan.freshness_mode,
    )
    normalized = signals.annotate_stream(normalized, category.topic, report.query_plan.freshness_mode)
    normalized = dedupe.dedupe_items(normalized)
    for item in normalized:
        item.snippet = snippet.extract_best_snippet(item, category.topic)

    # Merge with existing x items, dedup again
    existing_x = report.items_by_source.get("x", [])
    combined = existing_x + normalized
    report.items_by_source["x"] = dedupe.dedupe_items(combined)

    total_new = len(report.items_by_source["x"]) - len(existing_x)
    sys.stderr.write(f"[Bird] Timeline/list sources added {total_new} new unique tweets\n")


def _run_trends_pipeline(run_state: RunState, config: dict) -> None:
    """Separate pipeline for Tech & AI Trends — timeline-first, no keyword search.

    Instead of searching Twitter with keywords, this pulls your curated
    X lists + home timeline + web grounding for AI news. The LLM then
    reads through everything and extracts narratives and zeitgeist.
    """
    category = run_state.category
    from lib import dates, grounding

    sys.stderr.write(
        f"[Trends] Starting trends pipeline (lists + timeline + web, no keyword search)\n"
    )

    # Step 1: Pull X lists and home timeline (the primary data source)
    bird_x.set_credentials(config.get("AUTH_TOKEN"), config.get("CT0"))
    all_x_items: list[dict] = []

    for list_id in category.x_list_ids:
        items = bird_x.fetch_list_timeline(list_id, pages=5, delay_ms=1500)
        if items:
            sys.stderr.write(f"[Trends] List {list_id}: {len(items)} tweets\n")
            all_x_items.extend(items)

    if category.fetch_home_timeline:
        items = bird_x.fetch_home_timeline(pages=3, delay_ms=2000)
        if items:
            sys.stderr.write(f"[Trends] Home timeline: {len(items)} tweets\n")
            all_x_items.extend(items)

    sys.stderr.write(f"[Trends] Total X items: {len(all_x_items)}\n")

    # Step 2: Web grounding for major AI news headlines
    from_date, to_date = dates.get_date_range(category.lookback_days)
    web_items: list[dict] = []
    web_queries = [
        "AI industry news major development today",
        "AI startup funding launch announcement",
        "AI developer tools ecosystem shift",
    ]
    for query in web_queries:
        try:
            results, _ = grounding.web_search(query, (from_date, to_date), config)
            web_items.extend(results)
            sys.stderr.write(f"[Trends] Web '{query}': {len(results)} results\n")
        except Exception as exc:
            sys.stderr.write(f"[Trends] Web search failed: {exc}\n")

    # Step 2b: HackerNews — builder conversations and front-page narratives
    from lib import hackernews
    hn_queries = ["AI", "LLM", "Claude Code", "agent", "open source"]
    hn_items: list[dict] = []
    for query in hn_queries:
        try:
            resp = hackernews.search_hackernews(query, from_date, to_date, depth="deep")
            parsed = hackernews.parse_hackernews_response(resp, query=query)
            hn_items.extend(parsed)
        except Exception:
            pass
    if hn_items:
        # Dedupe HN items by URL
        hn_seen: set[str] = set()
        for item in hn_items:
            url = item.get("hn_url") or item.get("url", "")
            if url and url.lower() not in hn_seen:
                hn_seen.add(url.lower())
                web_items.append({
                    "title": item.get("title", ""),
                    "snippet": item.get("title", ""),
                    "url": url,
                    "source_domain": "news.ycombinator.com",
                    "date": item.get("date"),
                })
        sys.stderr.write(f"[Trends] HackerNews: {len(hn_seen)} unique stories from {len(hn_items)} results\n")

    # Step 2c: Digg AI Top Stories (curated high-signal AI news — protected from triage filtering)
    try:
        from .signal_agent.digg import fetch_top_stories
        digg_stories = fetch_top_stories()
        if digg_stories:
            for item in digg_stories:
                web_items.append({
                    "title": item.text[:200],
                    "snippet": item.text,
                    "url": item.url,
                    "source_domain": "digg.com",
                    "date": item.date,
                    "_protected": True,
                })
            sys.stderr.write(f"[Trends] Digg Top Stories: {len(digg_stories)} items\n")
    except Exception as exc:
        sys.stderr.write(f"[Trends] Digg Top Stories failed: {exc}\n")

    # Step 3: Ask Grok for a 24h trends rundown (additive source)
    from .signal_agent.tools import tool_grok_trends_scout
    grok_items = tool_grok_trends_scout()
    if grok_items:
        # Convert CompactItems back to raw dicts for merging
        for item in grok_items:
            # Parse engagement back from compact string (e.g. "likes:1000, reposts:200")
            eng = {}
            if item.engagement and item.engagement != "none":
                for part in item.engagement.split(", "):
                    if ":" in part:
                        k, v = part.split(":", 1)
                        try:
                            eng[k.strip()] = int(v.strip())
                        except ValueError:
                            pass
            # Ensure Grok items pass the engagement filter (they're pre-vetted as noteworthy)
            if "likes" not in eng:
                eng["likes"] = 100  # Floor — Grok deemed them noteworthy
            all_x_items.append({
                "text": item.text,
                "url": item.url,
                "author_handle": item.author,
                "date": item.date,
                "engagement": eng,
                "_protected": True,
            })
        sys.stderr.write(f"[Trends] Grok scout: {len(grok_items)} additional tweets\n")

    # Step 4: Build a minimal Report-like object for the signal agent
    # Convert raw items to SourceItems so the signal agent can ingest them
    from lib import schema
    x_source_items = []
    seen_urls: set[str] = set()
    for i, item in enumerate(all_x_items):
        url = item.get("url", "")
        if not url or url.lower() in seen_urls:
            continue
        seen_urls.add(url.lower())
        metadata = {"protected": True} if item.get("_protected") else {}
        x_source_items.append(schema.SourceItem(
            item_id=f"trends-x-{i}",
            source="x",
            title=item.get("text", "")[:200],
            body=item.get("text", ""),
            url=url,
            author=item.get("author_handle", ""),
            published_at=item.get("date"),
            engagement={
                k: v for k, v in (item.get("engagement") or {}).items()
                if v is not None
            },
            metadata=metadata,
        ))

    web_source_items = []
    for i, item in enumerate(web_items):
        url = item.get("url", "")
        if not url or url.lower() in seen_urls:
            continue
        seen_urls.add(url.lower())
        metadata = {"protected": True} if item.get("_protected") else {}
        web_source_items.append(schema.SourceItem(
            item_id=f"trends-web-{i}",
            source="grounding",
            title=item.get("title", ""),
            body=item.get("snippet", ""),
            url=url,
            author=item.get("source_domain", ""),
            published_at=item.get("date"),
            metadata=metadata,
        ))

    sys.stderr.write(
        f"[Trends] Unique items: {len(x_source_items)} X + {len(web_source_items)} web "
        f"= {len(x_source_items) + len(web_source_items)} total\n"
    )

    # Build a stub Report for the signal agent
    stub_report = schema.Report(
        topic=category.topic,
        range_from=from_date,
        range_to=to_date,
        generated_at=datetime.now().isoformat(),
        provider_runtime=schema.ProviderRuntime(
            reasoning_provider=None,
            planner_model=None,
            rerank_model=None,
            x_search_backend=None,
        ),
        query_plan=schema.QueryPlan(
            intent="breaking_news",
            freshness_mode="strict_recent",
            cluster_mode="story",
            raw_topic=category.topic,
            subqueries=[],
            source_weights={"x": 1.0, "grounding": 0.8},
        ),
        clusters=[],
        ranked_candidates=[],
        items_by_source={
            "x": x_source_items,
            "grounding": web_source_items,
        },
        errors_by_source={},
    )

    # Step 4: Run the signal agent (with trends-specific prompts)
    from .signal_agent import run_signal_graph
    graph_state = run_signal_graph(
        stub_report, category.name, category.emoji, category_id=category.id,
    )
    if graph_state.html_path:
        run_state.report_html_path = graph_state.html_path
    if graph_state.audio_path:
        run_state.audio_path = graph_state.audio_path

    # Fail loudly if no report was produced
    if not graph_state.html_path:
        errors = "; ".join(graph_state.errors) if graph_state.errors else "unknown error"
        raise RuntimeError(f"Trends pipeline produced no report: {errors}")


def _run_pipeline(
    run_state: RunState,
    on_complete: Callable[[RunState], None] | None = None,
) -> None:
    """Execute the pipeline in the current thread."""
    global _current_run

    run_state.status = "running"
    run_state.started_at = datetime.now().isoformat()

    config = env.get_config()
    category = run_state.category

    # Capture stderr for progress tracking
    real_stderr = sys.stderr
    sys.stderr = _StderrCapture(real_stderr, run_state.progress_messages)

    try:
        # Tech & AI Trends has its own pipeline — timeline-first, no keyword search
        if category.id == "tech":
            _run_trends_pipeline(run_state, config)
        else:
            # Standard pipeline for Repos, CLI, Skills, News
            report = pipeline.run(
                topic=category.topic,
                config=config,
                depth=category.depth,
                external_plan=category.query_plan,
                lookback_days=category.lookback_days,
                subreddits=category.subreddits or None,
            )

            # Fetch additional X sources: lists and home timeline
            _fetch_timeline_sources(report, category, config)

            # Digg GitHub Stars for the repos category
            if category.id == "repos":
                try:
                    from .signal_agent.digg import fetch_github_stars
                    digg_repos = fetch_github_stars()
                    if digg_repos:
                        from lib import normalize as norm_mod
                        from lib import dates as dates_mod
                        from_d, to_d = dates_mod.get_date_range(category.lookback_days)
                        digg_source_items = []
                        for item in digg_repos:
                            digg_source_items.append(schema.SourceItem(
                                item_id=item.item_id,
                                source="github",
                                title=item.text[:200],
                                body=item.text,
                                url=item.url,
                                author=item.author,
                                engagement={},
                            ))
                        existing_gh = report.items_by_source.get("github", [])
                        report.items_by_source["github"] = existing_gh + digg_source_items
                        sys.stderr.write(f"[Digg] Added {len(digg_source_items)} GitHub Stars to repos\n")
                except Exception as exc:
                    sys.stderr.write(f"[Digg] GitHub Stars failed: {exc}\n")

            # Save full raw markdown (all clusters, all items — for debugging/reference)
            raw_md = render.render_full(report)
            slug = reporter._slugify(category.name)
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            raw_path = reporter.OUTPUT_DIR / f"{slug}-{timestamp}-raw.md"
            reporter._ensure_output_dir()
            raw_path.write_text(raw_md, encoding="utf-8")

            # Signal Agent: LLM-powered analysis
            try:
                from .signal_agent import run_signal_graph
                graph_state = run_signal_graph(report, category.name, category.emoji, category_id=category.id)
                if graph_state.html_path:
                    run_state.report_html_path = graph_state.html_path
                if graph_state.audio_path:
                    run_state.audio_path = graph_state.audio_path
            except Exception as signal_exc:
                sys.stderr.write(
                    f"[SignalAgent] Failed, falling back to legacy report: "
                    f"{type(signal_exc).__name__}: {signal_exc}\n"
                )
                html_path = reporter.generate_html_report(
                    report, category.name, category.emoji,
                )
                run_state.report_html_path = str(html_path)
                audio_path = reporter.generate_audio(
                    report, category.name, category.emoji,
                )
                if audio_path:
                    run_state.audio_path = str(audio_path)

        run_state.status = "completed"
        run_state.completed_at = datetime.now().isoformat()
        _latest_runs[category.id] = run_state

    except Exception as exc:
        run_state.status = "failed"
        run_state.error = str(exc)
        run_state.completed_at = datetime.now().isoformat()
        _latest_runs[category.id] = run_state
    finally:
        sys.stderr = real_stderr
        with _run_lock:
            _current_run = None

    if on_complete:
        on_complete(run_state)

    # Process queue if there are more runs waiting
    _process_queue(on_complete)


def _process_queue(on_complete: Callable[[RunState], None] | None = None) -> None:
    """Start the next queued run if any."""
    with _queue_lock:
        if not _run_queue:
            return
        next_cat = _run_queue.pop(0)

    start_run(next_cat, on_complete=on_complete)


def start_run(
    category: cat_mod.Category,
    on_complete: Callable[[RunState], None] | None = None,
) -> RunState | None:
    """Start a pipeline run for the given category. Returns None if already running."""
    global _current_run

    with _run_lock:
        if _current_run is not None and _current_run.status == "running":
            return None

        run_state = RunState(
            run_id=str(uuid.uuid4())[:8],
            category=category,
        )
        _current_run = run_state

    thread = threading.Thread(
        target=_run_pipeline,
        args=(run_state, on_complete),
        daemon=True,
    )
    thread.start()
    return run_state


def queue_run(
    category: cat_mod.Category,
    on_complete: Callable[[RunState], None] | None = None,
) -> None:
    """Add a category to the run queue. Starts immediately if nothing is running."""
    with _run_lock:
        if _current_run is not None and _current_run.status == "running":
            with _queue_lock:
                _run_queue.append(category)
            return

    start_run(category, on_complete=on_complete)


def queue_all(on_complete: Callable[[RunState], None] | None = None) -> None:
    """Queue all 4 categories to run sequentially."""
    cats = cat_mod.all_categories()
    if not cats:
        return

    # Start the first one, queue the rest
    first = cats[0]
    with _queue_lock:
        _run_queue.extend(cats[1:])

    start_run(first, on_complete=on_complete)
