"""Data models for the signal intelligence agent."""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

# Ensure scripts/ is on sys.path for lib imports
_SCRIPTS_DIR = Path(__file__).parent.parent.parent / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from lib import schema


# ── 1.1: CompactItem ──────────────────────────────────────────────────────

COMPACT_TEXT_LIMIT = 400


@dataclass
class CompactItem:
    """Minimal representation of a pipeline item for LLM processing."""

    item_id: str
    text: str          # title + body truncated to COMPACT_TEXT_LIMIT
    url: str
    source: str        # x, github, hackernews, grounding, reddit
    author: str
    date: str
    engagement: str    # compact engagement summary like "likes:42, retweets:5"
    protected: bool = False  # If True, bypasses triage scoring (Digg, Grok items)

    @classmethod
    def from_source_item(cls, item: schema.SourceItem) -> CompactItem:
        text_parts = [item.title, (item.body or "")[:300]]
        text = " | ".join(p for p in text_parts if p).strip()
        if len(text) > COMPACT_TEXT_LIMIT:
            text = text[:COMPACT_TEXT_LIMIT] + "..."

        eng_parts = []
        for key, val in (item.engagement or {}).items():
            if val and isinstance(val, (int, float)) and val > 0:
                eng_parts.append(f"{key}:{int(val)}")
        engagement = ", ".join(eng_parts[:4]) if eng_parts else "none"

        return cls(
            item_id=item.item_id,
            text=text,
            url=item.url or "",
            source=item.source,
            author=item.author or "unknown",
            date=item.published_at or "unknown",
            engagement=engagement,
            protected=bool((item.metadata or {}).get("protected")),
        )


# ── 1.2: Signal ───────────────────────────────────────────────────────────

class Signal(BaseModel):
    """A distinct signal discovered by the agent."""

    title: str
    summary: str = Field(description="2-3 sentence summary")
    why_it_matters: str = Field(description="1 sentence impact statement")
    sources: list[str] = Field(default_factory=list, description="Source URLs")
    source_types: list[str] = Field(
        default_factory=list,
        description="x, github, hackernews, grounding, reddit",
    )
    score: float = Field(ge=0, le=10)
    category: Literal[
        "launch", "trend", "tool", "insight",
        "paradigm_shift", "funding", "adoption", "drama",
        "narrative", "debate", "thought_leader", "industry_move",
        "funding_signal",
        "science", "space", "health", "economy", "disaster",
    ] = "insight"


# ── 1.3: TriagedItem ──────────────────────────────────────────────────────

class TriagedItem(BaseModel):
    """Single item after LLM triage scoring."""

    item_id: str
    score: float = Field(ge=0, le=10, description="Signal quality 0-10")
    reason: str = Field(description="One-sentence justification")


# ── 1.4: TriageBatchResult ────────────────────────────────────────────────

class TriageBatchResult(BaseModel):
    """Structured output from one triage batch."""

    items: list[TriagedItem]


# ── 1.5: DeepAnalysisResult ───────────────────────────────────────────────

class DeepAnalysisResult(BaseModel):
    """Structured output from deep analysis node."""

    signals: list[Signal]


# ── 1.6: GapAnalysis ──────────────────────────────────────────────────────

class GapSearchSuggestion(BaseModel):
    """A suggested search to fill a coverage gap."""

    query: str
    source: Literal["x", "hackernews", "github", "grounding", "tweet_url", "scrape"] = "x"
    reason: str


class GapAnalysis(BaseModel):
    """Output from the gap finder node."""

    covered_topics: list[str] = Field(default_factory=list)
    missing_topics: list[str] = Field(default_factory=list)
    suggested_searches: list[GapSearchSuggestion] = Field(default_factory=list)


# ── 1.7: GraphState ───────────────────────────────────────────────────────

@dataclass
class GraphState:
    """Mutable state flowing through the signal graph nodes."""

    # Input
    category_id: str = ""
    category_name: str = ""
    category_emoji: str = ""
    topic: str = ""

    # Node 1 output
    all_items: list[CompactItem] = field(default_factory=list)

    # Node 2 output (gap finder)
    gap_analysis: GapAnalysis | None = None

    # Node 3 output (triage)
    triage_scores: dict[str, float] = field(default_factory=dict)
    triage_reasons: dict[str, str] = field(default_factory=dict)
    high_signal_items: list[CompactItem] = field(default_factory=list)

    # Node 4 output (deep analysis)
    signals: list[Signal] = field(default_factory=list)

    # Node 5 output (report)
    html_path: str | None = None
    audio_path: str | None = None
    narration_script: str | None = None

    # Metadata
    errors: list[str] = field(default_factory=list)
    timings: dict[str, float] = field(default_factory=dict)
