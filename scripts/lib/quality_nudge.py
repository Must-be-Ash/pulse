"""Post-research quality score and upgrade nudge.

Computes a quality score based on the crypto pipeline's core sources and
builds a nudge message describing what the user missed and how to fix it.
"""

from typing import List


CORE_SOURCES = ["x", "grounding", "hackernews", "github"]

SOURCE_LABELS = {
    "x": "X/Twitter (primary qualitative)",
    "grounding": "Web search (Serper/Exa)",
    "reddit": "Reddit",
    "github": "GitHub",
}

NUDGE_HINTS = {
    "x": "Add AUTH_TOKEN + CT0, XAI_API_KEY, or HERMES_TWEET_API_KEY for primary qualitative coverage.",
    "grounding": "Add SERPER_API_KEY or EXA_API_KEY for web grounding.",
}


def _has_x_credentials(config: dict) -> bool:
    return bool(
        config.get("AUTH_TOKEN")
        or config.get("XAI_API_KEY")
        or config.get("HERMES_TWEET_API_KEY")
        or config.get("XQUIK_API_KEY")
    )


def _is_active(source: str, config: dict, research_results: dict) -> bool:
    """A source is active if it has credentials AND didn't error this run."""
    cred_check = {
        "x": _has_x_credentials(config),
        "grounding": bool(config.get("SERPER_API_KEY") or config.get("EXA_API_KEY")),
    }
    if not cred_check.get(source, False):
        return False
    if research_results.get(f"{source}_error"):
        return False
    return True


def compute_quality_score(config: dict, research_results: dict) -> dict:
    """Compute research quality score based on core crypto pipeline sources."""
    core_active: List[str] = []
    core_missing: List[str] = []
    core_errored: List[str] = []

    for source in CORE_SOURCES:
        if _is_active(source, config, research_results):
            core_active.append(source)
        else:
            core_missing.append(source)
            has_cred = {
                "x": _has_x_credentials(config),
                "grounding": bool(config.get("SERPER_API_KEY") or config.get("EXA_API_KEY")),
                                    }.get(source, False)
            if has_cred and research_results.get(f"{source}_error"):
                core_errored.append(source)

    score_pct = int(len(core_active) / len(CORE_SOURCES) * 100)
    nudge_text = _build_nudge_text(core_missing, core_errored) if core_missing else None

    return {
        "score_pct": score_pct,
        "core_active": core_active,
        "core_missing": core_missing,
        "core_errored": core_errored,
        "nudge_text": nudge_text,
    }


def _build_nudge_text(core_missing: List[str], core_errored: List[str]) -> str:
    lines: List[str] = []

    missed_parts: List[str] = []
    for src in core_missing:
        label = SOURCE_LABELS.get(src, src)
        if src in core_errored:
            missed_parts.append(f"{label} (errored this run)")
        else:
            missed_parts.append(label)
    if missed_parts:
        lines.append(f"Skipped: {', '.join(missed_parts)}")
        lines.append("")

    free_suggestions: List[str] = []
    for src in core_missing:
        hint = NUDGE_HINTS.get(src)
        if hint and src not in core_errored:
            free_suggestions.append(hint)

    if free_suggestions:
        lines.append("To fix:")
        for s in free_suggestions:
            lines.append(f"  - {s}")
        lines.append("")

    lines.append("pulse has no affiliation with any API provider.")

    return "\n".join(lines)
