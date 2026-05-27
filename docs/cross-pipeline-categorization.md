# Cross-Pipeline Categorization: Score Once, Route to the Right Pipeline

## Problem

The 3 tool pipelines (Open-Source Repos, CLI Tools, Skills & MCP Servers) share the same 6 X lists (~2700 tweets). Currently each pipeline scores these items independently with its own triage prompt, and throws away items that don't match its category.

**Real example from May 26 runs:**
- Skills pipeline found Bumblebee (Perplexity's security scanner) → scored it 2.0 ("not an MCP or skill") → threw it away
- Bumblebee is a great open-source repo signal, but Repos pipeline never saw it because its keyword searches didn't find that specific tweet
- Result: a high-value signal fell through the cracks between two pipelines

This happens constantly. Each pipeline independently discovers ~1500 items but only keeps ~100-200 for its category. The rest — potentially hundreds of high-signal items — get discarded even though they'd be valuable to another pipeline.

## Solution

Replace the 3 separate category-specific triage prompts with one **unified triage prompt** that scores AND categorizes every item. Items that score high but belong to a different pipeline get cached for that pipeline to use when it runs.

## What We're NOT Touching

- **Tech & AI Trends** — separate pipeline, engagement-based scoring, completely different purpose. Has its own `_run_trends_pipeline()` and `TRENDS_TRIAGE_SYSTEM`
- **World News** — separate pipeline, grounding-only data sources. Has its own `NEWS_TRIAGE_SYSTEM`
- **Each pipeline's keyword searches** — still category-specific, still run independently. Skills searches for "introducing MCP", Repos searches for "open sourced", etc.
- **Deep analysis prompts** — already category-specific. Skills deep analysis only produces skill/MCP signals. Repos only produces repo signals. This doesn't change.
- **Data collection, X list fetching, ingest, gap finder** — all unchanged

## Explicit Category Definitions

These go into the unified triage prompt so the LLM knows exactly what belongs where:

### `skills_mcp`
MCP servers, Claude Code skills (.md skill files), skill packs, agent plugins, extensions, integrations, skill harnesses, skill managers, skill marketplaces, browser skills, memory plugins — anything a builder installs as a SKILL, MCP, or PLUGIN to enhance an agent's capabilities.

**Examples:** Base MCP, Compound Engineering skill, taw-computer MCP server, Browserbase skills hub, MCPSafe security scanner for MCP servers

### `repos`
Open-source repositories, tools, apps, libraries, frameworks, SDKs — full projects on GitHub you clone/star/fork. NOT skills or MCPs (those go in `skills_mcp`). NOT CLI-only tools (those go in `cli`).

**Examples:** Bumblebee security scanner, autoresearch by Karpathy, last30days, Agyn distributed agent runtime, PlanBridge

### `cli`
CLI tools, terminal utilities, command-line developer tools — things invoked from the terminal with a command. Must have a CLI interface as the primary interaction mode.

**Examples:** digg-pp-cli, gh CLI extensions, terminal-based coding agents, shell automation tools

### `none`
Not useful for builders. Spam, marketing, engagement bait, general AI news, research papers without usable code, corporate announcements without a concrete tool, benchmarks, opinions, industry commentary.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        RUN ALL                               │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────┐     │
│  │  Repos        │  │  CLI Tools   │  │  Skills/MCP   │     │
│  │  keyword      │  │  keyword     │  │  keyword      │     │
│  │  search       │  │  search      │  │  search       │     │
│  │  (8 queries)  │  │  (6 queries) │  │  (8 queries)  │     │
│  └──────┬───────┘  └──────┬───────┘  └──────┬────────┘     │
│         │                  │                  │              │
│         ▼                  ▼                  ▼              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  + SHARED X LISTS (6 lists, ~2700 tweets each run)   │   │
│  │  + HN stories, GitHub, Reddit, web grounding         │   │
│  └──────────────────────┬───────────────────────────────┘   │
│                         │                                    │
│                         ▼                                    │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  NODE 1: INGEST (dedup, date filter, engagement)     │   │
│  │  NODE 2: GAP FINDER (fill coverage gaps)             │   │
│  └──────────────────────┬───────────────────────────────┘   │
│                         │                                    │
│                         ▼                                    │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  NODE 3: UNIFIED TRIAGE                              │   │
│  │  (score 0-10 + assign category for each item)        │   │
│  │                                                       │   │
│  │  Input: ~1500 items                                   │   │
│  │  Output per item:                                     │   │
│  │    { item_id, score, category, reason }               │   │
│  │                                                       │   │
│  │  Routing:                                             │   │
│  │    score >= 7 + matches current pipeline → PASS       │   │
│  │    score >= 7 + matches OTHER pipeline  → CACHE       │   │
│  │    score < 7 or category "none"         → DROP        │   │
│  └────────┬──────────────┬───────────────┬──────────────┘   │
│           │              │               │                   │
│       current        other cats       dropped                │
│       pipeline's     saved to                                │
│       items          cache file                              │
│           │              │                                   │
│           │              ▼                                   │
│           │   ┌────────────────────────┐                    │
│           │   │  PIPELINE CACHE        │                    │
│           │   │  .pipeline-cache.json  │                    │
│           │   │                        │                    │
│           │   │  skills_mcp: [items]   │                    │
│           │   │  repos: [items]        │                    │
│           │   │  cli: [items]          │                    │
│           │   └───────────┬────────────┘                    │
│           │               │                                  │
│           │    loaded by next pipeline                       │
│           │    that matches category                         │
│           │               │                                  │
│           ▼               ▼                                  │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  NODE 4: DEEP ANALYSIS (category-specific prompt)    │   │
│  │  Repos → only produces repo signals                  │   │
│  │  CLI → only produces CLI signals                     │   │
│  │  Skills → only produces skill/MCP signals            │   │
│  └──────────────────────┬───────────────────────────────┘   │
│                         │                                    │
│                         ▼                                    │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  NODE 5: REPORT (HTML + optional audio)              │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  SEPARATE (untouched):                                       │
│  Tech & AI Trends ──► own data ──► own triage ──► own report │
│  World News ──────► own data ──► own triage ──► own report   │
└─────────────────────────────────────────────────────────────┘
```

## Step-by-Step Flow Example

### Run All triggered — pipelines run in order: Repos → CLI → Skills

**Run 1: Open-Source Repos**
1. Keyword search: "open sourced", "just released open source", "introducing open source", etc.
2. Fetch 6 X lists (~2700 tweets) + HN + GitHub
3. Ingest: dedup, filter → ~1500 items
4. Gap finder: +50 items → ~1550 items
5. Unified triage scores all 1550 items:
   - 120 items score 7+ as `repos` → pass to deep analysis
   - 25 items score 7+ as `skills_mcp` → **cached**
   - 10 items score 7+ as `cli` → **cached**
   - 1395 items score <7 or `none` → dropped
6. Load cache: empty (first pipeline to run)
7. Deep analysis (repos prompt): 120 items → 35 repo signals
8. Report: 35 signals rendered

**Run 2: CLI Tools**
1. Keyword search: "introducing CLI", "shipped CLI terminal", "built CLI", etc.
2. Fetch same 6 X lists (from cache, same tweets) + HN
3. Ingest → ~1400 items
4. Gap finder → ~1430 items
5. Unified triage scores all 1430 items:
   - 45 items score 7+ as `cli` → pass to deep analysis
   - 18 items score 7+ as `repos` → cached (appended)
   - 12 items score 7+ as `skills_mcp` → cached (appended)
   - Rest dropped
6. **Load cache: 10 `cli` items from Repos run** → injected into deep analysis pool
7. Deep analysis (CLI prompt): 55 items (45 own + 10 cached) → 20 CLI signals
8. Report: 20 signals rendered

**Run 3: Skills & MCP Servers**
1. Keyword search: "introducing MCP", "built MCP server", "Claude Code", etc.
2. Fetch same 6 X lists + HN + Reddit
3. Ingest → ~1550 items
4. Gap finder → ~1600 items
5. Unified triage scores all 1600 items:
   - 160 items score 7+ as `skills_mcp` → pass to deep analysis
   - 20 items score 7+ as `repos` → cached
   - 8 items score 7+ as `cli` → cached
   - Rest dropped
6. **Load cache: 37 `skills_mcp` items from Repos + CLI runs** → injected into deep analysis pool
7. Deep analysis (skills prompt): 197 items (160 own + 37 cached) → 50 skill/MCP signals
8. Report: 50 signals rendered

### Result: Each pipeline benefits from items discovered by other pipelines' keyword searches, while maintaining its own focused output.

## Cache File Specification

**Location:** `~/Documents/Pulse/.pipeline-cache.json`

**Structure:**
```json
{
  "created_at": "2026-05-26T17:00:00",
  "skills_mcp": [
    {
      "item_id": "X1234",
      "text": "Perplexity open-sourced Bumblebee...",
      "url": "https://x.com/WesRoth/status/...",
      "source": "x",
      "author": "WesRoth",
      "date": "2026-05-26",
      "engagement": "likes:22, reposts:1",
      "triage_score": 8.0,
      "triage_reason": "Open-source security scanner with working code...",
      "originating_pipeline": "repos"
    }
  ],
  "repos": [...],
  "cli": [...]
}
```

**Lifecycle:**
- Created when the first pipeline in a session caches items for other categories
- Each subsequent pipeline APPENDS items for other categories, READS + CLEARS its own category
- Expires after 24 hours (items older than `created_at + 24h` are discarded on load)
- Cleared at the start of a new "Run All" session

## Files to Modify

### 1. `app/signal_agent/models.py`
- Add `category: str = "none"` field to `TriagedItem`
- Add `triage_categories: dict[str, str] = field(default_factory=dict)` to `GraphState`

### 2. `app/signal_agent/prompts.py`
- Create `UNIFIED_TRIAGE_SYSTEM` prompt with the explicit category definitions
- This replaces `SKILLS_TRIAGE_SYSTEM`, `REPOS_TRIAGE_SYSTEM`, `CLI_TRIAGE_SYSTEM` (which can be removed)
- Same unified prompt used for all 3 tool pipelines
- Keep `TRENDS_TRIAGE_SYSTEM` and `NEWS_TRIAGE_SYSTEM` untouched
- Update `TRIAGE_USER` to include `category` in the requested JSON format
- Update `build_triage_system()` routing:
  - `"tech"` → `TRENDS_TRIAGE_SYSTEM`
  - `"news"` → `NEWS_TRIAGE_SYSTEM`
  - `"skills"`, `"repos"`, `"cli"` → `UNIFIED_TRIAGE_SYSTEM`

### 3. `app/signal_agent/graph.py`
- Update `_triage_batch()` return type to include category: `dict[str, tuple[float, str, str]]` (score, reason, category)
- Update `node_triage()`:
  - Store categories in `state.triage_categories`
  - Map current pipeline's category_id to the triage category name (`"skills"` → `"skills_mcp"`, `"repos"` → `"repos"`, `"cli"` → `"cli"`)
  - Items matching current pipeline's category + score >= threshold → `high_signal_items`
  - Items matching OTHER tool categories + score >= threshold → save to cache
- Add `_load_pipeline_cache(category: str) -> list[CompactItem]`
- Add `_save_pipeline_cache(category: str, items: list[CompactItem], scores, reasons)`
- After triage + cache save, load cached items for current category and append to `high_signal_items`
- Update `_write_run_log()` to include `triage_category` per item

### 4. No changes needed:
- `app/runner.py` — pipeline orchestration stays the same (sequential, one at a time)
- `app/categories.py` — keyword searches stay category-specific
- `app/signal_agent/prompts.py` deep analysis prompts — already category-specific, untouched
- Tech & AI Trends — completely separate pipeline
- World News — completely separate pipeline
- `app/menubar.py` — no UI changes needed

## Verification Checklist

1. Run "Run All" from the menu bar
2. Check run logs for each pipeline:
   - Should see: `"Cached X items for repos, Y for cli"` (or similar categories)
   - Should see: `"Loaded Z cached items from previous pipeline runs"`
3. Check `~/Documents/Pulse/.pipeline-cache.json` exists and has expected structure
4. Verify cross-pollination: an item found by Skills keyword search that's actually a repo should appear in the Repos report
5. Verify no cross-contamination: Skills report should ONLY contain skill/MCP signals (deep analysis prompt enforces this)
6. Verify Tech & AI Trends and World News are completely unaffected
7. Check run log JSON: each item should have a `triage_category` field showing what the LLM categorized it as
8. Run Skills alone (not Run All): should work normally, caches items for repos/cli but has no cached items to load (no previous runs)
