"""Signal intelligence graph — 5-node pipeline replacing rerank/cluster/report."""

from __future__ import annotations

import json
import random
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

# Ensure scripts/ is on sys.path for lib imports
_SCRIPTS_DIR = Path(__file__).parent.parent.parent / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from lib import schema

from .llm import chat_json, chat_text
from .models import (
    CompactItem,
    DeepAnalysisResult,
    GapAnalysis,
    GraphState,
    Signal,
    TriageBatchResult,
)
from .prompts import (
    AUDIO_SCRIPT_SYSTEM,
    AUDIO_SCRIPT_USER,
    DEEP_ANALYSIS_USER,
    GAP_FINDER_SYSTEM,
    GAP_FINDER_USER,
    TRIAGE_USER,
    build_deep_analysis_system,
    build_triage_system,
)
from .tools import run_gap_searches, tool_firecrawl_scrape


BATCH_SIZE = 75


# ── Node 1: Ingest & Prepare ──────────────────────────────────────────────

# Engagement floor per category. Trends needs high engagement (zeitgeist).
# Tool categories need a lighter filter (cut zero-engagement noise but keep indie devs).
_MIN_LIKES = {
    "tech": 20,     # Trends: engagement IS the signal
    "repos": 5,     # Tools: cut noise but keep indie dev posts
    "cli": 5,
    "skills": 5,
    "news": 0,      # News: no engagement filter (web sources don't have likes)
}


def node_ingest(state: GraphState, report: schema.Report) -> None:
    """Node 1: Ingest all items from pipeline output, deduplicate, compact.

    Pre-filters X items by engagement and date to cut noise.
    Protected items (Digg, Grok) bypass date and engagement filters.
    """
    t0 = time.time()
    seen_urls: set[str] = set()
    items: list[CompactItem] = []
    skipped_low_engagement = 0
    skipped_old = 0
    skipped_no_date = 0
    min_likes = _MIN_LIKES.get(state.category_id, 0)

    # Date cutoff based on the report's date range
    cutoff_date = report.range_from  # e.g. "2026-05-25"

    for source, source_items in report.items_by_source.items():
        for item in source_items:
            key = (item.url or "").strip().lower() or item.item_id
            if key in seen_urls:
                continue
            seen_urls.add(key)

            is_protected = bool((item.metadata or {}).get("protected"))

            # Protected items (Digg, Grok) bypass date and engagement filters
            if not is_protected:
                # Filter items older than the lookback window
                if cutoff_date and item.published_at and len(item.published_at) >= 10:
                    item_date = item.published_at[:10]
                    if item_date < cutoff_date:
                        skipped_old += 1
                        continue
                elif cutoff_date and not item.published_at:
                    # No date at all — drop it (can't verify recency)
                    skipped_no_date += 1
                    continue

                # Filter low-engagement X items
                if source == "x" and min_likes > 0:
                    likes = 0
                    eng = item.engagement or {}
                    for k in ("likes", "likeCount", "favorite_count"):
                        v = eng.get(k)
                        if isinstance(v, (int, float)) and v > likes:
                            likes = v
                    if likes < min_likes:
                        skipped_low_engagement += 1
                        continue

            items.append(CompactItem.from_source_item(item))

    state.all_items = items
    state.timings["ingest"] = time.time() - t0
    protected_count = sum(1 for item in items if item.protected)
    skipped_parts = []
    if skipped_low_engagement:
        skipped_parts.append(f"{skipped_low_engagement} low-engagement")
    if skipped_old:
        skipped_parts.append(f"{skipped_old} outside date range")
    if skipped_no_date:
        skipped_parts.append(f"{skipped_no_date} no date")
    extra = f" (skipped {', '.join(skipped_parts)})" if skipped_parts else ""
    prot_extra = f" ({protected_count} protected)" if protected_count else ""
    sys.stderr.write(
        f"[SignalAgent] Node 1 (Ingest): {len(items)} unique items{prot_extra} "
        f"from {len(report.items_by_source)} sources{extra} "
        f"in {state.timings['ingest']:.1f}s\n"
    )


# ── Node 2: Gap Finder + Autonomous Fill ──────────────────────────────────

def node_gap_finder(state: GraphState) -> None:
    """Node 2: Identify coverage gaps and autonomously fill them."""
    t0 = time.time()

    if not state.all_items:
        state.errors.append("No items for gap analysis")
        return

    # Sample ~50 representative titles for the LLM to review
    sample_size = min(50, len(state.all_items))
    sample = random.sample(state.all_items, sample_size)
    topic_summary = "\n".join(
        f"- [{item.source}] {item.text[:120]}" for item in sample
    )

    prompt_user = GAP_FINDER_USER.format(
        total_items=len(state.all_items),
        category_name=state.category_name,
        topic=state.topic,
        topic_summary=topic_summary,
    )

    try:
        raw = chat_json(GAP_FINDER_SYSTEM, prompt_user, tier="triage", timeout=30)
        gap = GapAnalysis.model_validate(raw)
        state.gap_analysis = gap

        sys.stderr.write(
            f"[SignalAgent] Node 2 (Gap Finder): "
            f"{len(gap.covered_topics)} covered, "
            f"{len(gap.missing_topics)} gaps, "
            f"{len(gap.suggested_searches)} searches suggested\n"
        )

        # Autonomously fill gaps
        if gap.suggested_searches:
            searches = [s.model_dump() for s in gap.suggested_searches]
            # Determine lookback from category (default 3 days)
            lookback = 3
            new_items = run_gap_searches(searches, lookback_days=lookback, max_searches=5)

            # Dedupe against existing items
            existing_urls = {item.url.strip().lower() for item in state.all_items if item.url}
            unique_new = [
                item for item in new_items
                if item.url and item.url.strip().lower() not in existing_urls
            ]

            state.all_items.extend(unique_new)
            sys.stderr.write(
                f"[SignalAgent] Node 2 (Gap Fill): added {len(unique_new)} "
                f"new items (total now {len(state.all_items)})\n"
            )

    except Exception as exc:
        state.errors.append(f"Gap finder failed: {type(exc).__name__}: {exc}")
        sys.stderr.write(f"[SignalAgent] Node 2 (Gap Finder) error: {exc}\n")

    state.timings["gap_finder"] = time.time() - t0


# ── Node 3: LLM Triage (batched) ──────────────────────────────────────────

def _format_items_for_triage(items: list[CompactItem], include_engagement: bool = False) -> str:
    lines = []
    for item in items:
        eng_line = f"\n  Engagement: {item.engagement}" if include_engagement and item.engagement != "none" else ""
        lines.append(
            f"[{item.item_id}] ({item.source}) @{item.author} ({item.date})\n"
            f"  {item.text}\n"
            f"  URL: {item.url}{eng_line}"
        )
    return "\n\n".join(lines)


def _triage_batch(
    batch: list[CompactItem],
    batch_num: int,
    total_batches: int,
    topic: str,
    system_prompt: str,
    include_engagement: bool = False,
) -> dict[str, tuple[float, str]]:
    """Triage a single batch. Returns {item_id: (score, reason)}."""
    items_block = _format_items_for_triage(batch, include_engagement=include_engagement)
    prompt_user = TRIAGE_USER.format(
        topic=topic,
        batch_num=batch_num,
        total_batches=total_batches,
        items_block=items_block,
    )

    try:
        raw = chat_json(system_prompt, prompt_user, tier="triage", timeout=120)
        result = TriageBatchResult.model_validate(raw)
        return {item.item_id: (item.score, item.reason) for item in result.items}
    except json.JSONDecodeError:
        # Retry with smaller batch if JSON was truncated
        if len(batch) > 40:
            sys.stderr.write(
                f"[SignalAgent] Triage batch {batch_num} JSON failed, retrying with half batch\n"
            )
            half = len(batch) // 2
            r1 = _triage_batch(batch[:half], batch_num, total_batches, topic, system_prompt, include_engagement)
            r2 = _triage_batch(batch[half:], batch_num, total_batches, topic, system_prompt, include_engagement)
            return {**r1, **r2}
        sys.stderr.write(f"[SignalAgent] Triage batch {batch_num} failed: JSON parse error\n")
        return {}
    except Exception as exc:
        sys.stderr.write(
            f"[SignalAgent] Triage batch {batch_num} failed: "
            f"{type(exc).__name__}: {exc}\n"
        )
        return {}


def node_triage(state: GraphState) -> None:
    """Node 3: Score items in batches. Protected items (Digg, Grok) bypass scoring."""
    t0 = time.time()
    items = state.all_items
    if not items:
        state.errors.append("No items to triage")
        return

    # Separate protected items (Digg, Grok) — they skip triage entirely
    protected_items = [item for item in items if item.protected]
    triageable_items = [item for item in items if not item.protected]

    if protected_items:
        sys.stderr.write(
            f"[SignalAgent] Node 3 (Triage): {len(protected_items)} protected items (Digg/Grok) bypass scoring\n"
        )

    system_prompt = build_triage_system(state.category_id)

    batches = [triageable_items[i:i + BATCH_SIZE] for i in range(0, len(triageable_items), BATCH_SIZE)]
    total_batches = len(batches)
    sys.stderr.write(
        f"[SignalAgent] Node 3 (Triage): {len(triageable_items)} items "
        f"in {total_batches} batches\n"
    )

    # For trends category, include engagement so the LLM can weight by visibility
    include_engagement = state.category_id == "tech"

    all_scores: dict[str, tuple[float, str]] = {}
    max_workers = min(4, total_batches) if total_batches > 0 else 1

    if batches:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(
                    _triage_batch, batch, i + 1, total_batches,
                    state.topic, system_prompt, include_engagement,
                ): i
                for i, batch in enumerate(batches)
            }
            for future in as_completed(futures):
                batch_idx = futures[future]
                try:
                    batch_scores = future.result()
                    all_scores.update(batch_scores)
                    sys.stderr.write(
                        f"[SignalAgent] Triage batch {batch_idx + 1}/{total_batches}: "
                        f"{len(batch_scores)} scored\n"
                    )
                except Exception as exc:
                    state.errors.append(f"Triage batch {batch_idx} failed: {exc}")

    # Store scores
    item_lookup = {item.item_id: item for item in triageable_items}
    state.triage_scores = {k: v[0] for k, v in all_scores.items()}
    state.triage_reasons = {k: v[1] for k, v in all_scores.items()}

    # Filter: items scoring >= 7 advance
    threshold = 7.0
    high_signal = [
        item_lookup[iid]
        for iid, (score, _) in sorted(
            all_scores.items(), key=lambda x: x[1][0], reverse=True,
        )
        if score >= threshold and iid in item_lookup
    ]

    # Adaptive threshold
    if len(high_signal) > 300:
        threshold = 8.0
        high_signal = [
            item_lookup[iid]
            for iid, (score, _) in sorted(
                all_scores.items(), key=lambda x: x[1][0], reverse=True,
            )
            if score >= threshold and iid in item_lookup
        ]
    elif len(high_signal) < 20 and len(all_scores) >= 20:
        threshold = 5.0
        high_signal = [
            item_lookup[iid]
            for iid, (score, _) in sorted(
                all_scores.items(), key=lambda x: x[1][0], reverse=True,
            )
            if score >= threshold and iid in item_lookup
        ][:200]

    # Add protected items — they always make it through (dedup happens in deep analysis)
    high_signal = protected_items + high_signal

    state.high_signal_items = high_signal
    state.timings["triage"] = time.time() - t0
    sys.stderr.write(
        f"[SignalAgent] Node 3 (Triage): scored {len(all_scores)}/{len(triageable_items)}, "
        f"{len(high_signal)} passed ({len(protected_items)} protected + "
        f"{len(high_signal) - len(protected_items)} triaged at {threshold}) "
        f"in {state.timings['triage']:.1f}s\n"
    )


# ── Node 4: Deep Analysis + Enrichment ────────────────────────────────────

def _format_items_for_analysis(items: list[CompactItem], include_engagement: bool = False) -> str:
    lines = []
    for item in items:
        eng_line = f"\n  Engagement: {item.engagement}" if include_engagement and item.engagement != "none" else ""
        lines.append(
            f"[{item.item_id}] ({item.source}) @{item.author}\n"
            f"  {item.text}\n"
            f"  URL: {item.url}{eng_line}"
        )
    return "\n\n".join(lines)


def _dedupe_signals(signals: list[Signal]) -> list[Signal]:
    """Merge signals with very similar titles."""
    from lib.dedupe import _PreparedText, prepared_similarity

    result: list[Signal] = []
    for signal in signals:
        merged = False
        sig_prep = _PreparedText(signal.title + " " + signal.summary[:100])
        for idx, existing in enumerate(result):
            existing_prep = _PreparedText(
                existing.title + " " + existing.summary[:100]
            )
            if prepared_similarity(sig_prep, existing_prep) > 0.55:
                # Keep higher-scored, merge sources
                if signal.score > existing.score:
                    signal.sources = list(dict.fromkeys(signal.sources + existing.sources))
                    signal.source_types = list(set(signal.source_types) | set(existing.source_types))
                    result[idx] = signal
                else:
                    existing.sources = list(dict.fromkeys(existing.sources + signal.sources))
                    existing.source_types = list(set(existing.source_types) | set(signal.source_types))
                merged = True
                break
        if not merged:
            result.append(signal)
    return result


def _enrich_signal(signal: Signal) -> Signal:
    """Scrape the top source URL to enhance the signal summary."""
    if not signal.sources:
        return signal

    # Pick the first scrapeable URL (skip x.com/twitter.com — Firecrawl can't access them)
    scrape_url = None
    for url in signal.sources:
        if "x.com" in url or "twitter.com" in url:
            continue
        if "github.com" in url or "dev.to" in url or ".blog" in url or "medium.com" in url:
            scrape_url = url
            break
    if not scrape_url:
        # Try any non-Twitter URL
        for url in signal.sources:
            if "x.com" not in url and "twitter.com" not in url:
                scrape_url = url
                break
    if not scrape_url:
        return signal  # All sources are X — can't enrich

    content = tool_firecrawl_scrape(scrape_url)
    if not content or len(content) < 50:
        return signal

    # Use LLM to enhance the summary with scraped content
    try:
        enhanced = chat_json(
            "You enhance signal summaries with additional context from scraped content. "
            "Keep the same structure but add concrete details.",
            f"Signal: {signal.title}\n"
            f"Current summary: {signal.summary}\n\n"
            f"Additional context from {scrape_url}:\n{content[:1500]}\n\n"
            f"Return JSON: {{\"summary\": \"enhanced 2-3 sentence summary\", "
            f"\"why_it_matters\": \"enhanced 1 sentence impact\"}}",
            tier="triage",
            timeout=30,
        )
        if enhanced.get("summary"):
            signal.summary = enhanced["summary"]
        if enhanced.get("why_it_matters"):
            signal.why_it_matters = enhanced["why_it_matters"]
    except Exception:
        pass  # Keep original summary on failure

    return signal


def node_deep_analysis(state: GraphState) -> None:
    """Node 4: Group high-signal items into distinct signals, enrich top ones."""
    t0 = time.time()
    items = state.high_signal_items
    if not items:
        state.errors.append("No high-signal items for deep analysis")
        return

    system_prompt = build_deep_analysis_system(state.category_id)
    include_engagement = state.category_id == "tech"
    all_signals: list[Signal] = []

    # Chunk into manageable sizes — 75 items per call to stay within output token limits
    MAX_ITEMS_PER_CALL = 75
    for chunk_start in range(0, len(items), MAX_ITEMS_PER_CALL):
        chunk = items[chunk_start:chunk_start + MAX_ITEMS_PER_CALL]
        items_block = _format_items_for_analysis(chunk, include_engagement=include_engagement)

        prompt_user = DEEP_ANALYSIS_USER.format(
            topic=state.topic,
            count=len(chunk),
            items_block=items_block,
        )

        try:
            raw = chat_json(system_prompt, prompt_user, tier="deep", timeout=180)
            result = DeepAnalysisResult.model_validate(raw)
            all_signals.extend(result.signals)
            sys.stderr.write(
                f"[SignalAgent] Deep analysis chunk: {len(result.signals)} signals "
                f"from {len(chunk)} items\n"
            )
        except (json.JSONDecodeError, Exception) as exc:
            # Retry with half-chunk if JSON was truncated
            if len(chunk) > 30:
                sys.stderr.write(
                    f"[SignalAgent] Deep analysis chunk failed ({type(exc).__name__}), "
                    f"retrying with half ({len(chunk)//2} items)...\n"
                )
                half = len(chunk) // 2
                for sub_chunk in [chunk[:half], chunk[half:]]:
                    sub_block = _format_items_for_analysis(sub_chunk, include_engagement=include_engagement)
                    sub_user = DEEP_ANALYSIS_USER.format(
                        topic=state.topic,
                        count=len(sub_chunk),
                        items_block=sub_block,
                    )
                    try:
                        raw2 = chat_json(system_prompt, sub_user, tier="deep", timeout=180)
                        result2 = DeepAnalysisResult.model_validate(raw2)
                        all_signals.extend(result2.signals)
                        sys.stderr.write(
                            f"[SignalAgent] Deep analysis retry chunk: {len(result2.signals)} signals "
                            f"from {len(sub_chunk)} items\n"
                        )
                    except Exception as exc2:
                        state.errors.append(f"Deep analysis retry failed: {type(exc2).__name__}: {exc2}")
                        sys.stderr.write(f"[SignalAgent] Deep analysis retry error: {exc2}\n")
            else:
                state.errors.append(f"Deep analysis chunk failed: {type(exc).__name__}: {exc}")
                sys.stderr.write(f"[SignalAgent] Deep analysis chunk error: {exc}\n")

    # Deduplicate signals across chunks
    if len(all_signals) > 1:
        all_signals = _dedupe_signals(all_signals)

    # Sort by score
    all_signals.sort(key=lambda s: s.score, reverse=True)

    # Enrich top 5 signals with Firecrawl scrapes (skip for trends — mostly X URLs)
    enriched_count = 0
    if state.category_id != "tech":
        for i, signal in enumerate(all_signals[:5]):
            try:
                all_signals[i] = _enrich_signal(signal)
                enriched_count += 1
            except Exception:
                pass

    state.signals = all_signals
    state.timings["deep_analysis"] = time.time() - t0
    sys.stderr.write(
        f"[SignalAgent] Node 4 (Deep Analysis): {len(all_signals)} signals "
        f"from {len(items)} items, enriched {enriched_count} "
        f"in {state.timings['deep_analysis']:.1f}s\n"
    )


# ── Node 5: Report Generation ──────────────────────────────────────────────

def node_report(state: GraphState) -> None:
    """Node 5: Generate HTML report and audio narration from signals."""
    t0 = time.time()

    if not state.signals:
        state.errors.append("No signals to report")
        return

    # Import here to avoid circular imports
    from .. import reporter

    # Generate HTML
    html_path = reporter.generate_signal_html(
        state.signals, state.category_name, state.category_emoji,
    )
    state.html_path = str(html_path)

    # Only generate audio for Tech & AI and World News
    if state.category_id not in ("tech", "news"):
        state.timings["report"] = time.time() - t0
        sys.stderr.write(
            f"[SignalAgent] Node 5 (Report): {len(state.signals)} signals "
            f"rendered (no audio for {state.category_id}) in {state.timings['report']:.1f}s\n"
        )
        return

    # Generate audio narration script via LLM
    signals_block = "\n".join(
        f"{i}. [{s.category}] {s.title} (score: {s.score})\n"
        f"   {s.summary}\n"
        f"   Why it matters: {s.why_it_matters}"
        for i, s in enumerate(state.signals, 1)
    )

    remaining = max(0, len(state.signals) - 8)
    sys.stderr.write(f"[SignalAgent] Generating audio narration for {state.category_id}...\n")
    try:
        script = chat_text(
            AUDIO_SCRIPT_SYSTEM,
            AUDIO_SCRIPT_USER.format(
                category_name=state.category_name,
                date=datetime.now().strftime("%A, %B %d"),
                signal_count=len(state.signals),
                signals_block=signals_block,
                remaining=remaining,
            ),
            tier="script",
            timeout=60,
        )
        state.narration_script = script
        sys.stderr.write(f"[SignalAgent] Narration script: {len(script)} chars\n")

        # Generate audio file
        audio_path = reporter.generate_signal_audio(
            state.signals, script, state.category_name,
        )
        if audio_path:
            state.audio_path = str(audio_path)
            sys.stderr.write(f"[SignalAgent] Audio saved: {audio_path}\n")
        else:
            sys.stderr.write("[SignalAgent] Audio generation returned None\n")
    except Exception as exc:
        state.errors.append(f"Audio generation failed: {exc}")
        sys.stderr.write(f"[SignalAgent] Audio generation error: {type(exc).__name__}: {exc}\n")

    state.timings["report"] = time.time() - t0
    sys.stderr.write(
        f"[SignalAgent] Node 5 (Report): {len(state.signals)} signals "
        f"rendered in {state.timings['report']:.1f}s\n"
    )


# ── Graph Orchestrator ─────────────────────────────────────────────────────

def run_signal_graph(
    report: schema.Report,
    category_name: str,
    category_emoji: str,
    category_id: str = "",
) -> GraphState:
    """Execute the full 5-node signal intelligence graph.

    Called from runner.py after pipeline.run() + timeline fetch completes.
    """
    # Set active category so prompts load the right bookmark examples
    from .prompts import set_active_category
    set_active_category(category_id)

    state = GraphState(
        category_id=category_id,
        category_name=category_name,
        category_emoji=category_emoji,
        topic=report.topic,
    )

    t_total = time.time()
    sys.stderr.write(
        f"[SignalAgent] Starting signal graph for '{category_name}'\n"
    )

    # Node 1: Ingest
    node_ingest(state, report)

    # Node 2: Gap Finder + Fill (skip for trends — timeline data is already curated)
    if state.category_id != "tech":
        node_gap_finder(state)
    else:
        sys.stderr.write("[SignalAgent] Node 2 (Gap Finder): skipped for trends (timeline is the source)\n")

    # Node 3: Triage
    node_triage(state)

    # Node 4: Deep Analysis + Enrichment
    node_deep_analysis(state)

    # Node 5: Report
    node_report(state)

    total_time = time.time() - t_total
    sys.stderr.write(
        f"[SignalAgent] Complete: {len(state.signals)} signals in {total_time:.1f}s "
        f"(ingest={state.timings.get('ingest', 0):.1f}s, "
        f"gap={state.timings.get('gap_finder', 0):.1f}s, "
        f"triage={state.timings.get('triage', 0):.1f}s, "
        f"deep={state.timings.get('deep_analysis', 0):.1f}s, "
        f"report={state.timings.get('report', 0):.1f}s)\n"
    )

    if state.errors:
        sys.stderr.write(
            f"[SignalAgent] Errors: {len(state.errors)}\n"
        )
        for err in state.errors:
            sys.stderr.write(f"  - {err}\n")

    # Write structured run log — all this data already exists, just serializing it
    _write_run_log(state, total_time)

    return state


def _write_run_log(state: GraphState, total_time: float) -> None:
    """Write a structured JSON run log for observability."""
    from .. import reporter

    out_dir = reporter._ensure_output_dir()
    slug = reporter._slugify(state.category_name)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    log_path = out_dir / f"{slug}-{timestamp}-run.json"

    # Build the triage detail: every item and what happened to it
    triage_detail = []
    for item in state.all_items:
        score = state.triage_scores.get(item.item_id)
        reason = state.triage_reasons.get(item.item_id)
        passed = any(h.item_id == item.item_id for h in state.high_signal_items)
        triage_detail.append({
            "item_id": item.item_id,
            "text": item.text[:200],
            "url": item.url,
            "source": item.source,
            "author": item.author,
            "date": item.date,
            "engagement": item.engagement,
            "protected": item.protected,
            "triage_score": score,
            "triage_reason": reason,
            "passed_to_deep_analysis": passed,
        })

    # Sort: passed items first (by score desc), then failed items (by score desc)
    triage_detail.sort(key=lambda x: (not x["passed_to_deep_analysis"], -(x["triage_score"] or 0)))

    run_log = {
        "category_id": state.category_id,
        "category_name": state.category_name,
        "timestamp": timestamp,
        "total_time_seconds": round(total_time, 1),
        "timings": {k: round(v, 1) for k, v in state.timings.items()},
        "errors": state.errors,
        "ingest": {
            "total_items": len(state.all_items),
            "protected_items": sum(1 for i in state.all_items if i.protected),
        },
        "gap_finder": {
            "covered_topics": state.gap_analysis.covered_topics if state.gap_analysis else [],
            "missing_topics": state.gap_analysis.missing_topics if state.gap_analysis else [],
            "searches_run": len(state.gap_analysis.suggested_searches) if state.gap_analysis else 0,
        },
        "triage": {
            "total_scored": len(state.triage_scores),
            "passed_threshold": len(state.high_signal_items),
            "protected_bypassed": sum(1 for i in state.high_signal_items if i.protected),
        },
        "deep_analysis": {
            "signals_produced": len(state.signals),
            "signals": [
                {
                    "title": s.title,
                    "score": s.score,
                    "category": s.category,
                    "sources": s.sources,
                    "source_types": s.source_types,
                    "summary": s.summary[:200],
                }
                for s in state.signals
            ],
        },
        "report": {
            "html_path": state.html_path,
            "audio_path": state.audio_path,
        },
        "items": triage_detail,
    }

    try:
        log_path.write_text(json.dumps(run_log, indent=2, default=str), encoding="utf-8")
        sys.stderr.write(f"[SignalAgent] Run log: {log_path}\n")
    except Exception as exc:
        sys.stderr.write(f"[SignalAgent] Failed to write run log: {exc}\n")
