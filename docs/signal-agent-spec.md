# Pulse Signal Intelligence Agent — Technical Specification

## Overview

Replace the current dumb keyword-overlap + engagement-based ranking pipeline with an LLM-powered signal agent that:
1. Collects data exhaustively from all sources (existing pipeline + X lists/home timeline)
2. Uses an LLM to identify coverage gaps and autonomously fills them with targeted tool calls
3. Triages all items with an LLM (ignoring engagement, scoring on content quality)
4. Groups high-signal items into distinct signals using examples of what the user considers valuable
5. Deep-dives on promising signals using tools (Firecrawl scrape, Exa search, Bird search)
6. Generates HTML report + audio narration with no arbitrary cap on signal count

Applies to **all 4 categories** (Open-Source Repos, CLI Tools, Skills & MCP, Tech & AI Trends).

---

## Architecture

```
Phase 1: COLLECT (existing, unchanged)
  pipeline.run() → 18 keyword searches across X/HN/GitHub/Web
  _fetch_timeline_sources() → 3 X lists + home timeline
  Result: ~2,000+ raw SourceItems in report.items_by_source

Phase 2: SIGNAL AGENT (new)
  ┌─────────────────────────────────────────────────────────────┐
  │                                                             │
  │  Node 1: INGEST                                             │
  │  Dedupe, compact all items to LLM-friendly format           │
  │                                                             │
  │  Node 2: GAP FINDER + AUTONOMOUS FILL                      │
  │  LLM reviews collected topics → identifies gaps             │
  │  → uses tools (Bird, Exa, GitHub, HN) to fill gaps          │
  │  → merges new items back into the pool                      │
  │                                                             │
  │  Node 3: TRIAGE                                             │
  │  LLM scores ALL items 0-10 in batches (gpt-4o-mini)        │
  │  Uses few-shot examples from signal-examples.json           │
  │  Items scoring ≥7 advance                                   │
  │                                                             │
  │  Node 4: DEEP ANALYSIS + ENRICHMENT                         │
  │  LLM groups high-signal items into distinct Signals          │
  │  For top signals: uses tools to scrape URLs, get more       │
  │  context (Firecrawl for blog posts, GitHub for READMEs)     │
  │                                                             │
  │  Node 5: REPORT                                             │
  │  Generate HTML + audio from Signal objects                   │
  │  No cap — however many signals the LLM found                │
  │                                                             │
  └─────────────────────────────────────────────────────────────┘
```

---

## Implementation Checklist

### Phase 0: Setup & Dependencies

- [x] **0.1** Create `app/signal_agent/` directory with `__init__.py`
- [x] **0.2** Create `~/.config/pulse/signal-examples.json` with mock examples structure:
  ```json
  {
    "examples": [
      {
        "title": "Perplexity open-sources Bumblebee security scanner",
        "why_good": "Real open-source tool launch from major company, useful for developers",
        "category": "launch"
      },
      {
        "title": "Indie dev ships terminal-first AI coding agent in Rust",
        "why_good": "Individual builder shipping a working tool, not vaporware",
        "category": "tool"
      }
    ],
    "anti_examples": [
      {
        "title": "AI will change everything! 10 tools you need to know",
        "why_bad": "Engagement bait listicle, no substance"
      }
    ]
  }
  ```
- [x] **0.3** Verify OpenAI API key works: test call to `gpt-4o-mini` with `response_format: json_object`

---

### Phase 1: Data Models (`app/signal_agent/models.py`)

- [x] **1.1** Define `CompactItem` dataclass — minimal item representation for LLM processing:
  - Fields: `item_id`, `text` (≤400 chars), `url`, `source`, `author`, `date`, `engagement` (compact string)
  - Constructor: `CompactItem.from_source_item(item: schema.SourceItem) -> CompactItem`

- [x] **1.2** Define `Signal` Pydantic model — the final output unit:
  - Fields: `title`, `summary` (2-3 sentences), `why_it_matters` (1 sentence), `sources` (list of URLs), `source_types` (list of source names), `score` (0-10), `category` (launch/trend/tool/insight/paradigm_shift/funding/adoption/drama)

- [x] **1.3** Define `TriagedItem` Pydantic model — per-item triage result:
  - Fields: `item_id`, `score` (0-10), `reason` (1 sentence)

- [x] **1.4** Define `TriageBatchResult` Pydantic model — batch output:
  - Fields: `items: list[TriagedItem]`

- [x] **1.5** Define `DeepAnalysisResult` Pydantic model — analysis output:
  - Fields: `signals: list[Signal]`

- [x] **1.6** Define `GapAnalysis` Pydantic model — gap finder output:
  - Fields: `covered_topics: list[str]`, `missing_topics: list[str]`, `suggested_searches: list[dict]` (each with `query`, `source`, `reason`)

- [x] **1.7** Define `GraphState` dataclass — mutable state flowing through nodes:
  - Fields: `category_name`, `category_emoji`, `topic`, `all_items: list[CompactItem]`, `triage_scores: dict[str, float]`, `high_signal_items: list[CompactItem]`, `signals: list[Signal]`, `html_path`, `audio_path`, `errors: list[str]`, `timings: dict[str, float]`

---

### Phase 2: LLM Client (`app/signal_agent/llm.py`)

- [x] **2.1** Implement `_get_openai_config() -> tuple[str, str]` — returns `(api_key, base_url)`:
  - Read from `env.get_config()`, key = `OPENAI_API_KEY`
  - base_url = `https://api.openai.com/v1/chat/completions`
  - Fallback to xAI if no OpenAI key: key = `XAI_API_KEY`, base_url = `https://api.x.ai/v1/chat/completions`

- [x] **2.2** Implement `chat_json(system: str, user: str, model: str, timeout: int) -> dict`:
  - Uses `lib/http.post()` (existing, has retry + 429 handling)
  - Sends `response_format: {"type": "json_object"}`
  - Parses response `choices[0].message.content` as JSON
  - Returns parsed dict

- [x] **2.3** Implement `chat_text(system: str, user: str, model: str, timeout: int) -> str`:
  - Same as chat_json but returns plain text (for audio script generation)

- [x] **2.4** Define model constants:
  - `TRIAGE_MODEL = "gpt-4o-mini"` (fast/cheap for 0-10 scoring)
  - `DEEP_MODEL = "gpt-4o"` (smarter for grouping + synthesis)
  - `SCRIPT_MODEL = "gpt-4o-mini"` (audio narration script)
  - xAI fallbacks: `"grok-4-1-fast"` for all tiers

---

### Phase 3: Prompts (`app/signal_agent/prompts.py`)

- [x] **3.1** Write `TRIAGE_SYSTEM` prompt — scoring criteria:
  - 9-10: Genuine tool launch, paradigm-shifting insight, major open-source release
  - 7-8: Useful tool/library release, concrete technical insight, meaningful trend
  - 5-6: Interesting but derivative, decent discussion
  - 3-4: Corporate announcement, promotional content
  - 0-2: Spam, self-promotion, engagement bait
  - **Critical rule: IGNORE engagement metrics**
  - Include few-shot examples loaded from `signal-examples.json`

- [x] **3.2** Write `TRIAGE_USER` template — batch scoring prompt:
  - Takes `{topic}`, `{batch_num}/{total_batches}`, `{items_block}`, `{examples_block}`
  - Expects JSON output: `{"items": [{"item_id": "...", "score": 0-10, "reason": "..."}]}`

- [x] **3.3** Write `GAP_FINDER_SYSTEM` prompt:
  - "You are analyzing a collection of tech/builder items to identify coverage gaps"
  - "What important topics, tools, or trends are MISSING from this collection?"

- [x] **3.4** Write `GAP_FINDER_USER` template:
  - Takes `{topic}`, `{category_name}`, `{topic_summary}` (LLM-generated summary of what's already collected)
  - Expects JSON output: `{"covered_topics": [...], "missing_topics": [...], "suggested_searches": [{"query": "...", "source": "x|hackernews|github|grounding", "reason": "..."}]}`

- [x] **3.5** Write `DEEP_ANALYSIS_SYSTEM` prompt:
  - Group items into distinct signals
  - Decide how many signals actually exist (no arbitrary cap)
  - Include few-shot examples from `signal-examples.json`

- [x] **3.6** Write `DEEP_ANALYSIS_USER` template:
  - Takes `{topic}`, `{count}`, `{items_block}`
  - Expects JSON output: `{"signals": [Signal schema]}`

- [x] **3.7** Write `AUDIO_SCRIPT_SYSTEM` and `AUDIO_SCRIPT_USER` prompts:
  - Concise, engaging briefing script
  - 15-20 seconds per signal, 1-2 minutes total
  - Cover top signals, mention "and N more in the full report" if many

---

### Phase 4: Tool Wrappers (`app/signal_agent/tools.py`)

These wrap existing `lib/` functions so the gap finder and enrichment nodes can call them.

- [x] **4.1** Implement `tool_bird_search(query: str, lookback_days: int) -> list[CompactItem]`:
  - Calls `bird_x.search_x(query, from_date, to_date, depth="deep")`
  - Parses with `bird_x.parse_bird_response()`
  - Converts each item to `CompactItem`
  - Logs: `[SignalAgent:Tool] Bird search '{query}': {N} items`

- [x] **4.2** Implement `tool_exa_search(query: str, lookback_days: int) -> list[CompactItem]`:
  - Calls `grounding.exa_search(query, date_range, api_key)`
  - Converts to `CompactItem`

- [x] **4.3** Implement `tool_github_search(query: str, lookback_days: int) -> list[CompactItem]`:
  - Calls `github.search_github(query, from_date, to_date, depth="deep")`
  - Converts to `CompactItem`

- [x] **4.4** Implement `tool_hn_search(query: str, lookback_days: int) -> list[CompactItem]`:
  - Calls `hackernews.search_hackernews(query, from_date, to_date, depth="deep")`
  - Parses with `hackernews.parse_hackernews_response()`
  - Converts to `CompactItem`

- [x] **4.5** Implement `tool_firecrawl_scrape(url: str) -> str`:
  - Calls `firecrawl.scrape(url, api_key=config["FIRECRAWL_API_KEY"])`
  - Returns `data.markdown` content (truncated to 2000 chars)
  - Returns empty string on error

- [x] **4.6** Implement `run_gap_searches(suggested_searches: list[dict], lookback_days: int) -> list[CompactItem]`:
  - Takes the gap finder's `suggested_searches` output
  - Routes each search to the appropriate tool based on `source` field
  - Runs searches sequentially (to avoid rate limits)
  - Returns all new items merged

---

### Phase 5: Graph Nodes (`app/signal_agent/graph.py`)

- [x] **5.1** Implement `node_ingest(state: GraphState, report: schema.Report) -> None`:
  - Iterate all `report.items_by_source` items
  - Deduplicate by URL (case-insensitive)
  - Convert each `SourceItem` to `CompactItem`
  - Store in `state.all_items`
  - Log: `[SignalAgent] Node 1 (Ingest): {N} unique items from {M} sources`

- [x] **5.2** Implement `node_gap_finder(state: GraphState) -> None`:
  - Generate a topic summary by sampling ~50 item titles from `state.all_items`
  - Send to LLM with `GAP_FINDER` prompt (gpt-4o-mini)
  - Parse `GapAnalysis` response
  - Call `run_gap_searches()` with `suggested_searches` (cap at 5 searches)
  - Dedupe new items against existing, add to `state.all_items`
  - Log: `[SignalAgent] Node 2 (Gap Finder): found {N} gaps, ran {M} searches, added {K} new items`

- [x] **5.3** Implement `node_triage(state: GraphState) -> None`:
  - Load examples from `~/.config/pulse/signal-examples.json` (if exists)
  - Batch items into groups of 100
  - For each batch: call LLM with `TRIAGE` prompt (gpt-4o-mini), parse `TriageBatchResult`
  - Run batches in parallel (4 concurrent via `ThreadPoolExecutor`)
  - Store scores in `state.triage_scores`
  - Filter items with score ≥ 7 into `state.high_signal_items`
  - Adaptive threshold: if > 300 pass, raise to 8; if < 20 pass, lower to 5
  - Log: `[SignalAgent] Node 3 (Triage): scored {N}/{M} items, {K} passed threshold`

- [x] **5.4** Implement `node_deep_analysis(state: GraphState) -> None`:
  - Take `state.high_signal_items`
  - If > 200 items, chunk into groups of 200 and analyze each chunk separately
  - For each chunk: call LLM with `DEEP_ANALYSIS` prompt (gpt-4o), parse `DeepAnalysisResult`
  - Merge signals across chunks, deduplicate by title similarity (using `lib/dedupe.prepared_similarity()`)
  - **Enrichment step**: for top 5-10 signals that reference a specific URL (GitHub repo, blog post):
    - Call `tool_firecrawl_scrape(url)` to get full content
    - Send scraped content + signal to LLM to enhance the summary
  - Sort signals by score descending
  - Store in `state.signals`
  - Log: `[SignalAgent] Node 4 (Deep Analysis): {N} signals from {M} items, enriched {K}`

- [x] **5.5** Implement `node_report(state: GraphState) -> None`:
  - Generate HTML report from `state.signals` using `reporter.generate_signal_html()`
  - Generate audio: send signals to LLM with `AUDIO_SCRIPT` prompt, get narration text, run macOS `say`
  - Store paths in `state.html_path` and `state.audio_path`
  - Log: `[SignalAgent] Node 5 (Report): {N} signals rendered`

- [x] **5.6** Implement `run_signal_graph(report, category_name, category_emoji) -> GraphState`:
  - Orchestrator that calls nodes 1-5 sequentially
  - Wraps each node in try/except, appends errors to `state.errors`
  - Logs total timing breakdown
  - Returns completed `GraphState`

---

### Phase 6: Reporter Updates (`app/reporter.py`)

- [x] **6.1** Implement `generate_signal_html(signals: list[Signal], category_name: str, category_emoji: str) -> Path`:
  - Self-contained HTML with Apple aesthetic (same CSS as existing reports)
  - Each signal rendered as a card:
    ```
    [category badge] [source tags]
    TITLE
    Summary text (2-3 sentences)
    Why it matters: impact statement
    Score: 9.2
    [Source link 1] [Source link 2] ...
    ```
  - No cap — render ALL signals
  - Save to `~/Documents/Pulse/{slug}-{timestamp}.html`

- [x] **6.2** Implement `generate_signal_audio(signals: list[Signal], narration_script: str, category_name: str) -> Path | None`:
  - Takes pre-generated narration script from Node 5
  - Writes to temp file, runs `say -v Samantha -r 175 -o output.aiff -f script.txt`
  - Save to `~/Documents/Pulse/{slug}-{timestamp}.aiff`

---

### Phase 7: Runner Integration (`app/runner.py`)

- [x] **7.1** Modify `_run_pipeline()` to call signal agent after data collection:
  ```python
  # After pipeline.run() and _fetch_timeline_sources():
  try:
      from .signal_agent import run_signal_graph
      graph_state = run_signal_graph(report, category.name, category.emoji)
      if graph_state.html_path:
          run_state.report_html_path = graph_state.html_path
      if graph_state.audio_path:
          run_state.audio_path = graph_state.audio_path
  except Exception as exc:
      # Fallback to existing cluster-based report
      html_path = reporter.generate_html_report(report, category.name, category.emoji)
      run_state.report_html_path = str(html_path)
  ```

- [x] **7.2** Update all 4 categories to use X lists + home timeline:
  - Add `x_list_ids` and `fetch_home_timeline=True` to repos, cli, and skills categories

---

### Phase 8: Category Updates (`app/categories.py`)

- [x] **8.1** Add `x_list_ids` to Open-Source Repos category:
  - Same 3 lists: `["1953536336675365173", "1539497752140206080", "2058775422171803800"]`
  - `fetch_home_timeline=True`

- [x] **8.2** Add `x_list_ids` to CLI Tools category:
  - Same 3 lists + `fetch_home_timeline=True`

- [x] **8.3** Add `x_list_ids` to Skills & MCP category:
  - Same 3 lists + `fetch_home_timeline=True`

- [x] **8.4** Update all categories to `depth="exhaustive"` (they currently use `"deep"`)

---

### Phase 9: Signal Examples File

- [x] **9.1** Create `~/.config/pulse/signal-examples.json` with initial mock structure
- [x] **9.2** Implement `load_signal_examples() -> dict` in `app/signal_agent/prompts.py` (via `_load_examples_block()`):
  - Reads from `~/.config/pulse/signal-examples.json`
  - Returns `{"examples": [...], "anti_examples": [...]}` or empty defaults if file doesn't exist
  - Formats examples into a prompt block for triage and deep analysis

---

### Phase 10: Testing & Verification

- [x] **10.1** Verify all imports: `python3 -c "from app.signal_agent import run_signal_graph; print('OK')"`
- [x] **10.2** Test LLM client: `python3 -c "from app.signal_agent.llm import chat_json; ..."` with a simple prompt
- [x] **10.3** Test triage on 3 mock items — real tool=10, MCP launch=8, spam=0. Examples file working.
- [x] **10.4** Test gap finder — found 6 gaps, ran 5 autonomous searches, added 153 items
- [ ] **10.5** INTEGRATION TEST: Run Tech & AI from menu bar, check `/tmp/pulse-app.err` for:
  - `[SignalAgent] Node 1 (Ingest): ~2000 items`
  - `[SignalAgent] Node 2 (Gap Finder): found N gaps, ran M searches`
  - `[SignalAgent] Node 3 (Triage): scored X items, Y passed threshold`
  - `[SignalAgent] Node 4 (Deep Analysis): Z signals, enriched K`
  - `[SignalAgent] Node 5 (Report): Z signals rendered`
- [ ] **10.6** Verify HTML report has variable signal count (not capped at 20)
- [ ] **10.7** Verify audio narration plays correctly
- [ ] **10.8** Verify fallback: kill OpenAI key, run again → should fall back to existing cluster report
- [ ] **10.9** Verify cost: check OpenAI usage dashboard, confirm ~$0.25 per run
- [ ] **10.10** Test all 4 categories work with signal agent

---

## File Manifest

### New Files
| File | Purpose |
|------|---------|
| `app/signal_agent/__init__.py` | Package exports: `run_signal_graph`, `Signal`, `GraphState` |
| `app/signal_agent/models.py` | Data models: `CompactItem`, `Signal`, `GraphState`, `TriageBatchResult`, `DeepAnalysisResult`, `GapAnalysis` |
| `app/signal_agent/llm.py` | LLM client wrapping `lib/http.post()` for OpenAI/xAI |
| `app/signal_agent/prompts.py` | All LLM prompt templates |
| `app/signal_agent/tools.py` | Tool wrappers: Bird search, Exa, GitHub, HN, Firecrawl |
| `app/signal_agent/graph.py` | 5 node functions + `run_signal_graph()` orchestrator |
| `~/.config/pulse/signal-examples.json` | User-maintained signal taste examples |

### Modified Files
| File | Changes |
|------|---------|
| `app/runner.py` | Call `signal_agent.run_signal_graph()` with fallback to existing reporter |
| `app/reporter.py` | Add `generate_signal_html()` and `generate_signal_audio()` for Signal objects |
| `app/categories.py` | Add X lists + home timeline to all 4 categories, set all to exhaustive depth |

### Unchanged Files (used as libraries)
| File | Used By |
|------|---------|
| `scripts/lib/bird_x.py` | `tools.py` — `search_x()`, `fetch_list_timeline()`, `fetch_home_timeline()` |
| `scripts/lib/grounding.py` | `tools.py` — `exa_search()` |
| `scripts/lib/hackernews.py` | `tools.py` — `search_hackernews()`, `parse_hackernews_response()` |
| `scripts/lib/github.py` | `tools.py` — `search_github()` |
| `scripts/lib/firecrawl.py` | `tools.py` — `scrape()` |
| `scripts/lib/http.py` | `llm.py` — `http.post()` for LLM API calls |
| `scripts/lib/schema.py` | `graph.py` — `Report`, `SourceItem` types |
| `scripts/lib/dedupe.py` | `graph.py` — `prepared_similarity()` for signal dedup |
| `scripts/lib/env.py` | `llm.py` — `get_config()` for API keys |
| `scripts/lib/dates.py` | `tools.py` — `get_date_range()` for search dates |

---

## Cost Estimate Per Run

| Node | Model | Est. Input Tokens | Est. Output Tokens | Cost |
|------|-------|-------------------|--------------------|----|
| Gap Finder | gpt-4o-mini | ~3K | ~1K | ~$0.001 |
| Triage (20 batches) | gpt-4o-mini | ~400K total | ~60K total | ~$0.07 |
| Deep Analysis | gpt-4o | ~40K | ~8K | ~$0.15 |
| Enrichment (5 scrapes + LLM) | gpt-4o-mini + Firecrawl | ~15K | ~3K | ~$0.03 |
| Audio Script | gpt-4o-mini | ~5K | ~2K | ~$0.005 |
| **Total per run** | | | | **~$0.25** |
| **Total per day (all 4 categories)** | | | | **~$1.00** |

---

## Runtime Estimate Per Run

| Node | Duration |
|------|----------|
| Ingest | ~1s |
| Gap Finder + Searches | ~15-30s |
| Triage (20 batches, 4 parallel) | ~30-45s |
| Deep Analysis + Enrichment | ~30-60s |
| Report Generation | ~5-10s |
| **Total** | **~1.5-2.5 minutes** |
