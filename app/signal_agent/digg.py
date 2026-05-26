"""Digg AI source — uses digg-pp-cli for top stories and GitHub stars.

No API key needed. Read-only CLI that scrapes digg.com/ai.
Install: npx -y @mvanhorn/printing-press-library install digg --cli-only
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).parent.parent.parent / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from .models import CompactItem

# Try common install locations
_CLI_PATHS = [
    "digg-pp-cli",
    str(Path.home() / "go" / "bin" / "digg-pp-cli"),
]


def _log(msg: str) -> None:
    sys.stderr.write(f"[Digg] {msg}\n")
    sys.stderr.flush()


def _find_cli() -> str | None:
    """Find the digg-pp-cli binary."""
    for path in _CLI_PATHS:
        if shutil.which(path) or Path(path).is_file():
            return path
    return None


def _run_cli(args: list[str], timeout: int = 30) -> list[dict]:
    """Run digg-pp-cli and parse JSON output."""
    cli = _find_cli()
    if not cli:
        _log("digg-pp-cli not found (install: npx -y @mvanhorn/printing-press-library install digg --cli-only)")
        return []

    cmd = [cli] + args
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            env={**os.environ, "PATH": f"{Path.home() / 'go' / 'bin'}:{os.environ.get('PATH', '')}"},
        )
        if result.returncode != 0:
            _log(f"CLI exit {result.returncode}: {(result.stderr or '').strip()[:200]}")
            return []

        output = (result.stdout or "").strip()
        if not output:
            return []

        data = json.loads(output)
        if isinstance(data, list):
            return data
        return data.get("results", [])

    except subprocess.TimeoutExpired:
        _log(f"CLI timed out ({timeout}s)")
        return []
    except json.JSONDecodeError as exc:
        _log(f"JSON parse failed: {exc}")
        return []
    except Exception as exc:
        _log(f"CLI error: {exc}")
        return []


def _ensure_synced() -> None:
    """Sync the local store if needed."""
    cli = _find_cli()
    if not cli:
        return
    try:
        subprocess.run(
            [cli, "sync"],
            capture_output=True,
            text=True,
            timeout=30,
            env={**os.environ, "PATH": f"{Path.home() / 'go' / 'bin'}:{os.environ.get('PATH', '')}"},
        )
    except Exception:
        pass


def fetch_top_stories(limit: int = 20) -> list[CompactItem]:
    """Fetch Digg AI Top Stories using digg-pp-cli.

    Returns CompactItems for the Tech & AI Trends pipeline.
    """
    _ensure_synced()
    raw = _run_cli(["top", "--limit", str(limit), "--json"])
    if not raw:
        return []

    items = []
    for i, cluster in enumerate(raw):
        if not isinstance(cluster, dict):
            continue
        title = cluster.get("title", "")
        tldr = cluster.get("tldr", "")
        cluster_url_id = cluster.get("clusterUrlId", "")
        rank = cluster.get("currentRank") or cluster.get("rank")
        likes = cluster.get("likes", 0)
        views = cluster.get("views", 0)

        if not title:
            continue
        if not cluster_url_id:
            continue  # Skip items without a unique URL

        text = f"{title} | {tldr}" if tldr else title
        url = f"https://di.gg/ai/{cluster_url_id}"
        eng = f"rank:{rank}, likes:{likes}, views:{views}" if rank else f"likes:{likes}, views:{views}"

        items.append(CompactItem(
            item_id=f"digg-{i}",
            text=text[:400],
            url=url,
            source="grounding",
            author="Digg AI",
            date=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            engagement=eng,
            protected=True,
        ))

    _log(f"Top Stories: {len(items)} clusters")
    return items


def fetch_github_stars(limit: int = 15) -> list[CompactItem]:
    """Fetch Digg AI GitHub Stars using digg-pp-cli.

    Returns CompactItems for the Open-Source Repos pipeline.
    """
    raw = _run_cli(["github", "stars", "--limit", str(limit), "--json"])
    if not raw:
        return []

    items = []
    for i, entry in enumerate(raw):
        if not isinstance(entry, dict):
            continue
        repo = entry.get("repo", {})
        judgment = entry.get("judgment", {})

        full_name = repo.get("full_name", "")
        if not full_name:
            continue

        stars = repo.get("stargazers_count", 0)
        lang = repo.get("language", "")
        desc = repo.get("description", "") or judgment.get("description", "")
        ai_score = judgment.get("ai_related_score", 0)
        novel_score = judgment.get("novel_score", 0)
        distinct_starrers = repo.get("distinct_starrers", 0)

        # Build starrer context
        starrers = repo.get("starrers", [])
        starrer_names = [s.get("username", "") for s in starrers[:3] if s.get("username")]
        starrer_str = f" (starred by: {', '.join(starrer_names)})" if starrer_names else ""

        text = f"{full_name} ({stars} stars, {lang}) | {desc[:200]}{starrer_str}"

        items.append(CompactItem(
            item_id=f"digg-gh-{i}",
            text=text[:400],
            url=f"https://github.com/{full_name}",
            source="github",
            author=full_name.split("/")[0] if "/" in full_name else full_name,
            date=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            engagement=f"stars:{stars}, ai_score:{ai_score}, novel:{novel_score}, starrers:{distinct_starrers}",
            protected=True,
        ))

    _log(f"GitHub Stars: {len(items)} repos")
    return items
