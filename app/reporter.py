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

    items_html = []
    for i, signal in enumerate(signals):
        source_tags = ""
        for src in sorted(set(signal.source_types)):
            label = _SOURCE_LABELS.get(src, src.title())
            source_tags += f'<span class="tag">{html.escape(label)}</span>'

        source_links = ""
        for url in signal.sources[:5]:
            domain = url.split("/")[2] if "/" in url and len(url.split("/")) > 2 else "link"
            # Shorten common domains
            domain = domain.replace("news.ycombinator.com", "HN").replace("x.com", "X").replace("github.com", "GitHub")
            source_links += f'<a class="src" href="{html.escape(url)}" target="_blank">{html.escape(domain)}</a>'

        cat_label = signal.category.replace("_", " ")
        score_bar_width = max(0, min(100, signal.score * 10))

        items_html.append(f"""<article>
  <div class="signal-header">
    <span class="signal-num">{i + 1:02d}</span>
    <div class="signal-meta-top">
      <span class="cat">{html.escape(cat_label)}</span>
      {source_tags}
    </div>
  </div>
  <h2>{html.escape(signal.title)}</h2>
  <p class="summary">{html.escape(signal.summary)}</p>
  <p class="insight">{html.escape(signal.why_it_matters)}</p>
  <div class="signal-footer">
    <div class="score-row">
      <div class="score-bar"><div class="score-fill" style="width:{score_bar_width}%"></div></div>
      <span class="score-label">{signal.score:.1f}</span>
    </div>
    <div class="srcs">{source_links}</div>
  </div>
</article>""")

    date_str = datetime.now().strftime("%B %d, %Y")
    source_types_all = set()
    for s in signals:
        source_types_all.update(s.source_types)
    sources_str = ", ".join(_SOURCE_LABELS.get(s, s) for s in sorted(source_types_all))

    report_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<link href="https://fonts.googleapis.com/css2?family=Libre+Baskerville:wght@400;700&display=swap" rel="stylesheet">
<title>{html.escape(category_name)} — {date_str}</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:-apple-system,BlinkMacSystemFont,"SF Pro Text","Helvetica Neue",sans-serif;background:#efefef;color:#1d1d1f;padding:3rem 1.5rem;max-width:720px;margin:0 auto;-webkit-font-smoothing:antialiased}}
header{{margin-bottom:2rem;padding-bottom:1.5rem;border-bottom:2px solid #1d1d1f}}
header h1{{font-family:"Libre Baskerville",Georgia,"Times New Roman",serif;font-size:1.6rem;font-weight:700;letter-spacing:-.02em;color:#1d1d1f;margin-bottom:.35rem}}
header .sub{{color:#86868b;font-size:.8rem;letter-spacing:.01em}}
.content{{background:#fff;border-radius:8px;padding:.5rem 1.5rem;box-shadow:0 1px 3px rgba(0,0,0,.06)}}
article{{padding:1.5rem 0;border-bottom:1px solid #d8d8d8}}
article:last-of-type{{border-bottom:none}}
.signal-header{{display:flex;align-items:center;gap:.75rem;margin-bottom:.6rem}}
.signal-num{{font-size:.7rem;font-weight:600;color:#86868b;font-variant-numeric:tabular-nums;min-width:1.4rem}}
.signal-meta-top{{display:flex;align-items:center;gap:.4rem;flex-wrap:wrap}}
.cat{{font-size:.65rem;font-weight:600;text-transform:uppercase;letter-spacing:.06em;color:#86868b;padding:.2rem .5rem;background:#f5f5f5;border-radius:3px}}
.tag{{font-size:.6rem;font-weight:500;text-transform:uppercase;letter-spacing:.05em;color:#aeaeb2;padding:.15rem .4rem;border:1px solid #e5e5e5;border-radius:3px}}
h2{{font-size:1.05rem;font-weight:600;line-height:1.4;color:#1d1d1f;margin-bottom:.5rem;letter-spacing:-.01em}}
.summary{{font-size:.875rem;color:#424245;line-height:1.65;margin-bottom:.5rem}}
.insight{{font-size:.8rem;color:#6e6e73;line-height:1.55;margin-bottom:.75rem;font-style:italic}}
.signal-footer{{display:flex;align-items:center;justify-content:space-between;gap:1rem}}
.score-row{{display:flex;align-items:center;gap:.5rem;flex-shrink:0}}
.score-bar{{width:3.5rem;height:3px;background:#e5e5e5;border-radius:2px;overflow:hidden}}
.score-fill{{height:100%;background:#1d1d1f;border-radius:2px;transition:width .3s}}
.score-label{{font-size:.7rem;color:#86868b;font-weight:500;font-variant-numeric:tabular-nums}}
.srcs{{display:flex;gap:.35rem;flex-wrap:wrap;justify-content:flex-end}}
.src{{font-size:.7rem;padding:.2rem .5rem;border-radius:3px;text-decoration:none;color:#86868b;background:transparent;border:1px solid #e5e5e5;transition:all .15s}}
.src:hover{{color:#1d1d1f;border-color:#1d1d1f}}
footer{{margin-top:1.5rem;padding-top:1rem;color:#aeaeb2;font-size:.7rem;display:flex;justify-content:space-between}}
</style>
</head>
<body>
<header>
  <h1>{html.escape(category_name)}</h1>
  <div class="sub">{date_str} &middot; {len(signals)} signals &middot; {html.escape(sources_str)}</div>
</header>

<div class="content">
{"".join(items_html) if items_html else '<article><p class="summary">No signals found.</p></article>'}
</div>

<footer>
  <span>Pulse</span>
  <span>{datetime.now().strftime("%Y-%m-%d %H:%M")}</span>
</footer>
</body>
</html>"""

    out_path.write_text(report_html, encoding="utf-8")
    return out_path


def _elevenlabs_tts(text: str, out_path: Path) -> bool:
    """Generate audio via ElevenLabs API. Returns True on success."""
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
    from lib import env

    config = env.get_config()
    api_key = config.get("ELEVENLABS_API_KEY")
    if not api_key:
        return False

    import requests

    voice_id = "21m00Tcm4TlvDq8ikWAM"  # Rachel — clear, professional
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"

    try:
        resp = requests.post(
            url,
            headers={
                "xi-api-key": api_key,
                "Content-Type": "application/json",
            },
            json={
                "text": text,
                "model_id": "eleven_turbo_v2_5",
                "voice_settings": {
                    "stability": 0.5,
                    "similarity_boost": 0.75,
                },
            },
            timeout=30,
        )
        if resp.status_code == 200 and len(resp.content) > 1000:
            mp3_path = out_path.with_suffix(".mp3")
            mp3_path.write_bytes(resp.content)
            return True
        return False
    except Exception:
        return False


def generate_signal_audio(
    signals: list,
    narration_script: str,
    category_name: str,
) -> Path | None:
    """Generate audio narration. ElevenLabs first, macOS say fallback."""
    out_dir = _ensure_output_dir()
    slug = _slugify(category_name)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    out_path = out_dir / f"{slug}-{timestamp}"

    if not narration_script or not narration_script.strip():
        return None

    # Try ElevenLabs first
    if _elevenlabs_tts(narration_script, Path(f"{out_path}")):
        mp3_path = Path(f"{out_path}.mp3")
        if mp3_path.exists():
            return mp3_path

    # Fallback to macOS say
    aiff_path = Path(f"{out_path}.aiff")
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write(narration_script)
        script_path = f.name

    try:
        result = subprocess.run(
            ["say", "-v", "Samantha", "-r", "175", "-o", str(aiff_path), "-f", script_path],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode != 0:
            return None
        return aiff_path
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return None
    finally:
        Path(script_path).unlink(missing_ok=True)
