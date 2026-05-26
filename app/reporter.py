"""Generate HTML reports and audio narration from pipeline Report objects."""

from __future__ import annotations

import html
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path

# Resolve the scripts directory so we can import schema
import sys
_SCRIPTS_DIR = Path(__file__).parent.parent / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from lib import schema

OUTPUT_DIR = Path.home() / "Documents" / "Pulse"

# Source label mapping
_SOURCE_LABELS = {
    "x": "X/Twitter",
    "hackernews": "Hacker News",
    "github": "GitHub",
    "grounding": "Web",
    "reddit": "Reddit",
}

# Source tag CSS classes
_SOURCE_TAGS = {
    "x": ("tag-x", "#e3f2fd", "#1565c0"),
    "hackernews": ("tag-hn", "#fff3e0", "#e65100"),
    "github": ("tag-github", "#e8f5e9", "#2e7d32"),
    "grounding": ("tag-web", "#f3e5f5", "#6a1b9a"),
    "reddit": ("tag-reddit", "#fff8e1", "#e65100"),
}


def _source_label(source: str) -> str:
    return _SOURCE_LABELS.get(source, source.title())


def _ensure_output_dir() -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    return OUTPUT_DIR


def _slugify(value: str) -> str:
    import re
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "pulse"


def generate_html_report(
    report: schema.Report,
    category_name: str,
    category_emoji: str,
) -> Path:
    """Generate a self-contained HTML report and save to ~/Documents/Pulse/."""
    out_dir = _ensure_output_dir()
    slug = _slugify(category_name)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    out_path = out_dir / f"{slug}-{timestamp}.html"

    candidate_by_id = {c.candidate_id: c for c in report.ranked_candidates}

    items_html = []
    for cluster in report.clusters[:20]:
        # Get the best representative candidate for this cluster
        for cid in cluster.representative_ids:
            candidate = candidate_by_id.get(cid)
            if not candidate:
                continue

            sources = schema.candidate_sources(candidate)
            source_tags = ""
            for src in sources:
                label = _source_label(src)
                _, bg, color = _SOURCE_TAGS.get(src, ("tag-web", "#f3e5f5", "#6a1b9a"))
                source_tags += (
                    f'<span class="tag" style="background:{bg};color:{color}">{html.escape(label)}</span>'
                )

            url_link = ""
            if candidate.url:
                url_link = f'<a class="src" href="{html.escape(candidate.url)}" target="_blank">Source</a>'

            snippet_text = html.escape(candidate.snippet or "")
            title_text = html.escape(cluster.title)

            items_html.append(f"""<div class="item">
  <div class="row">
    {source_tags}
    <div class="title">{title_text}</div>
  </div>
  <div class="desc">{snippet_text}</div>
  <div class="meta">Score: {cluster.score:.0f} &middot; {len(cluster.candidate_ids)} source{"s" if len(cluster.candidate_ids) != 1 else ""}</div>
  <div class="srcs">{url_link}</div>
</div>""")

    date_str = datetime.now().strftime("%B %d, %Y")
    n_signals = len(report.clusters)
    sources_active = [s for s, items in report.items_by_source.items() if items]
    sources_str = ", ".join(_source_label(s) for s in sources_active)

    report_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{category_emoji} {html.escape(category_name)} — {date_str}</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;background:#f5f5f7;color:#1d1d1f;padding:2rem;max-width:860px;margin:0 auto}}
h1{{font-size:1.6rem;font-weight:700;letter-spacing:-.02em}}
.sub{{color:#6e6e73;font-size:.9rem;margin:.3rem 0 2rem}}
.item{{background:#fff;border-radius:12px;padding:1.25rem 1.5rem;margin-bottom:1rem;box-shadow:0 1px 4px rgba(0,0,0,.08)}}
.row{{display:flex;align-items:flex-start;gap:.75rem;margin-bottom:.5rem;flex-wrap:wrap}}
.tag{{flex-shrink:0;font-size:.65rem;font-weight:700;padding:.25rem .55rem;border-radius:5px;text-transform:uppercase;letter-spacing:.06em;margin-top:.2rem}}
.title{{font-size:1rem;font-weight:600;line-height:1.35}}
.desc{{font-size:.875rem;color:#444;line-height:1.6;margin-bottom:.6rem}}
.meta{{font-size:.78rem;color:#999;margin-bottom:.6rem}}
.srcs{{display:flex;gap:.5rem;flex-wrap:wrap}}
.src{{font-size:.78rem;padding:.3rem .75rem;border-radius:6px;border:1px solid #d2d2d7;text-decoration:none;color:#0066cc;background:#fff}}
.src:hover{{background:#f0f5ff;border-color:#0066cc}}
.warn{{background:#fff3cd;border-left:3px solid #ffc107;padding:.75rem 1rem;border-radius:0 8px 8px 0;margin-bottom:1rem;font-size:.85rem;color:#856404}}
footer{{margin-top:2rem;color:#999;font-size:.78rem;border-top:1px solid #e5e5ea;padding-top:1rem}}
</style>
</head>
<body>
<h1>{category_emoji} {html.escape(category_name)}</h1>
<div class="sub">{date_str} &middot; {n_signals} signals &middot; {report.range_from} to {report.range_to} &middot; Sources: {html.escape(sources_str)}</div>

{"".join(f'<div class="warn">{html.escape(w)}</div>' for w in report.warnings)}

{"".join(items_html) if items_html else '<div class="item"><div class="desc">No signals found for this category.</div></div>'}

<footer>Pulse &middot; github.com/Must-be-Ash/pulse &middot; Generated {datetime.now().strftime("%Y-%m-%d %H:%M")}</footer>
</body>
</html>"""

    out_path.write_text(report_html, encoding="utf-8")
    return out_path


def generate_audio(
    report: schema.Report,
    category_name: str,
    category_emoji: str,
) -> Path | None:
    """Generate audio narration from top clusters using macOS say."""
    out_dir = _ensure_output_dir()
    slug = _slugify(category_name)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    out_path = out_dir / f"{slug}-{timestamp}.aiff"

    # Build a narration script from top clusters
    lines = [
        f"Pulse briefing. {category_name}. {datetime.now().strftime('%A, %B %d')}.",
        "",
    ]

    for i, cluster in enumerate(report.clusters[:6], start=1):
        title = cluster.title
        # Get snippet from the top representative
        candidate_by_id = {c.candidate_id: c for c in report.ranked_candidates}
        snippet = ""
        for cid in cluster.representative_ids[:1]:
            candidate = candidate_by_id.get(cid)
            if candidate and candidate.snippet:
                # Truncate long snippets for audio
                snippet = candidate.snippet[:200]
                break

        lines.append(f"Number {i}. {title}.")
        if snippet:
            lines.append(f"{snippet}.")
        lines.append("")

    lines.append(f"That's your {category_name} briefing from Pulse.")

    script = "\n".join(lines)

    # Write script to temp file and generate audio
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write(script)
        script_path = f.name

    try:
        result = subprocess.run(
            ["say", "-v", "Samantha", "-r", "175", "-o", str(out_path), "-f", script_path],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode != 0:
            return None
        return out_path
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return None
    finally:
        Path(script_path).unlink(missing_ok=True)


# ── Signal Agent report functions ──────────────────────────────────────────

def generate_signal_html(
    signals: list,
    category_name: str,
    category_emoji: str,
) -> Path:
    """Generate an HTML report from Signal objects (signal agent output)."""
    out_dir = _ensure_output_dir()
    slug = _slugify(category_name)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    out_path = out_dir / f"{slug}-{timestamp}.html"

    _CATEGORY_COLORS = {
        "launch": ("#e8f5e9", "#2e7d32"),
        "trend": ("#e3f2fd", "#1565c0"),
        "tool": ("#fff3e0", "#e65100"),
        "insight": ("#f3e5f5", "#6a1b9a"),
        "paradigm_shift": ("#fce4ec", "#880e4f"),
        "funding": ("#fff8e1", "#f57f17"),
        "funding_signal": ("#fff8e1", "#f57f17"),
        "adoption": ("#e0f7fa", "#00695c"),
        "drama": ("#fbe9e7", "#bf360c"),
        "narrative": ("#e3f2fd", "#1565c0"),
        "debate": ("#fbe9e7", "#bf360c"),
        "thought_leader": ("#f3e5f5", "#6a1b9a"),
        "industry_move": ("#e0f2f1", "#004d40"),
    }

    items_html = []
    for signal in signals:
        bg, color = _CATEGORY_COLORS.get(signal.category, ("#f5f5f5", "#333"))

        source_tags = ""
        for src in signal.source_types:
            label = _SOURCE_LABELS.get(src, src.title())
            src_bg, src_color = _SOURCE_TAGS.get(src, ("tag-web", "#f3e5f5", "#6a1b9a"))[1:]
            source_tags += (
                f'<span class="tag" style="background:{src_bg};color:{src_color}">'
                f'{html.escape(label)}</span>'
            )

        source_links = ""
        for url in signal.sources[:5]:
            domain = url.split("/")[2] if "/" in url and len(url.split("/")) > 2 else "link"
            source_links += f'<a class="src" href="{html.escape(url)}" target="_blank">{html.escape(domain)}</a>'

        items_html.append(f"""<div class="item">
  <div class="row">
    <span class="cat" style="background:{bg};color:{color}">{html.escape(signal.category)}</span>
    {source_tags}
  </div>
  <div class="title">{html.escape(signal.title)}</div>
  <div class="desc">{html.escape(signal.summary)}</div>
  <div class="resonance">Why it matters: {html.escape(signal.why_it_matters)}</div>
  <div class="meta">Score: {signal.score:.1f} &middot; {len(signal.sources)} source{"s" if len(signal.sources) != 1 else ""}</div>
  <div class="srcs">{source_links}</div>
</div>""")

    date_str = datetime.now().strftime("%B %d, %Y")
    source_types_all = set()
    for s in signals:
        source_types_all.update(s.source_types)
    sources_str = ", ".join(_SOURCE_LABELS.get(s, s) for s in sorted(source_types_all))

    report_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{category_emoji} {html.escape(category_name)} — {date_str}</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;background:#f5f5f7;color:#1d1d1f;padding:2rem;max-width:860px;margin:0 auto}}
h1{{font-size:1.6rem;font-weight:700;letter-spacing:-.02em}}
.sub{{color:#6e6e73;font-size:.9rem;margin:.3rem 0 2rem}}
.item{{background:#fff;border-radius:12px;padding:1.25rem 1.5rem;margin-bottom:1rem;box-shadow:0 1px 4px rgba(0,0,0,.08)}}
.row{{display:flex;align-items:center;gap:.5rem;margin-bottom:.5rem;flex-wrap:wrap}}
.tag{{flex-shrink:0;font-size:.65rem;font-weight:700;padding:.25rem .55rem;border-radius:5px;text-transform:uppercase;letter-spacing:.06em}}
.cat{{flex-shrink:0;font-size:.65rem;font-weight:700;padding:.25rem .55rem;border-radius:5px;text-transform:uppercase;letter-spacing:.06em}}
.title{{font-size:1.05rem;font-weight:600;line-height:1.35;margin-bottom:.4rem}}
.desc{{font-size:.875rem;color:#444;line-height:1.6;margin-bottom:.6rem}}
.resonance{{font-size:.8rem;color:#1d6fa4;margin-bottom:.8rem;line-height:1.5;padding:.5rem .75rem;background:#e8f4fd;border-left:3px solid #1d6fa4;border-radius:0 4px 4px 0}}
.meta{{font-size:.78rem;color:#999;margin-bottom:.6rem}}
.srcs{{display:flex;gap:.5rem;flex-wrap:wrap}}
.src{{font-size:.78rem;padding:.3rem .75rem;border-radius:6px;border:1px solid #d2d2d7;text-decoration:none;color:#0066cc;background:#fff}}
.src:hover{{background:#f0f5ff;border-color:#0066cc}}
footer{{margin-top:2rem;color:#999;font-size:.78rem;border-top:1px solid #e5e5ea;padding-top:1rem}}
</style>
</head>
<body>
<h1>{category_emoji} {html.escape(category_name)}</h1>
<div class="sub">{date_str} &middot; {len(signals)} signals &middot; Sources: {html.escape(sources_str)} &middot; Powered by Signal Agent</div>

{"".join(items_html) if items_html else '<div class="item"><div class="desc">No signals found.</div></div>'}

<footer>Pulse Signal Agent &middot; github.com/Must-be-Ash/pulse &middot; Generated {datetime.now().strftime("%Y-%m-%d %H:%M")}</footer>
</body>
</html>"""

    out_path.write_text(report_html, encoding="utf-8")
    return out_path


def generate_signal_audio(
    signals: list,
    narration_script: str,
    category_name: str,
) -> Path | None:
    """Generate audio narration from a pre-written script."""
    out_dir = _ensure_output_dir()
    slug = _slugify(category_name)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    out_path = out_dir / f"{slug}-{timestamp}.aiff"

    if not narration_script or not narration_script.strip():
        return None

    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write(narration_script)
        script_path = f.name

    try:
        result = subprocess.run(
            ["say", "-v", "Samantha", "-r", "175", "-o", str(out_path), "-f", script_path],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode != 0:
            return None
        return out_path
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return None
    finally:
        Path(script_path).unlink(missing_ok=True)
