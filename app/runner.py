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
        # Try to find matching audio file (same timestamp)
        stem = latest_html.stem  # e.g. "cli-tools-20260524-183200"
        audio_path = None
        for ext in (".aiff", ".mp3"):
            candidate = latest_html.with_suffix(ext)
            if candidate.exists():
                audio_path = str(candidate)
                break

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

        # Save full raw markdown (all clusters, all items — for debugging/reference)
        raw_md = render.render_full(report)
        slug = reporter._slugify(category.name)
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        raw_path = reporter.OUTPUT_DIR / f"{slug}-{timestamp}-raw.md"
        reporter._ensure_output_dir()
        raw_path.write_text(raw_md, encoding="utf-8")

        # Generate HTML report
        html_path = reporter.generate_html_report(
            report, category.name, category.emoji,
        )
        run_state.report_html_path = str(html_path)

        # Generate audio narration
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
