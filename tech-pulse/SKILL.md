---
name: tech-pulse
version: "1.0.0"
description: "Twitter-first tech intelligence — YC launches, funding signals, technique discoveries, and ecosystem trends. What's getting built and funded, read aloud. Ends with ElevenLabs audio saved to ~/Downloads/."
argument-hint: 'tech-pulse, tech-pulse YC, tech-pulse AI agents, tech-pulse knowledge graph'
allowed-tools: WebSearch, Bash, Read, Write, mcp__agentcash__fetch, mcp__agentcash__get_balance
user-invocable: true
metadata:
  openclaw:
    emoji: "📡"
    requires:
      env:
        - AUTH_TOKEN
        - CT0
      optionalEnv:
        - XAI_API_KEY
        - EXA_API_KEY
        - BRAVE_API_KEY
        - SERPER_API_KEY
        - GITHUB_TOKEN
        - FIRECRAWL_API_KEY
    primaryEnv: AUTH_TOKEN
    files:
      - "scripts/*"
    homepage: https://github.com/Must-be-Ash/pulse
    repository: https://github.com/Must-be-Ash/pulse
    tags:
      - trends
      - yc
      - funding
      - signals
      - zeitgeist
      - builder-intel
      - twitter
      - hackernews
---

# tech-pulse v1.0.0: Builder Intelligence Briefing

> **Source weights:** Twitter/X (primary) → Exa web search → HN front page → GitHub (trend signal) → Reddit (light). Surfaces signals — YC launches, funding, emerging techniques, ecosystem shifts — not tools to install (use `/tools-pulse` for those). Ends with ElevenLabs audio narration saved to `~/Downloads/`.

## Runtime Preflight

Before running any `pulse.py` command, resolve a Python 3.12+ interpreter once:

```bash
for py in python3.14 python3.13 python3.12 python3; do
  command -v "$py" >/dev/null 2>&1 || continue
  "$py" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 12) else 1)' || continue
  PULSE_PYTHON="$py"
  break
done

if [ -z "${PULSE_PYTHON:-}" ]; then
  echo "ERROR: tech-pulse requires Python 3.12+." >&2
  exit 1
fi
```

Find SKILL_ROOT:
```bash
for dir in \
  "." \
  "${CLAUDE_PLUGIN_ROOT:-}" \
  "$HOME/pulse" \
  "$HOME/.claude/skills/tech-pulse" \
  "$HOME/.claude/skills/tools-pulse"; do
  [ -n "$dir" ] && [ -f "$dir/scripts/pulse.py" ] && SKILL_ROOT="$dir" && break
done

if [ -z "${SKILL_ROOT:-}" ]; then
  echo "ERROR: Could not find scripts/pulse.py" >&2
  exit 1
fi
```

## Step 0: First-Run Setup

Check `~/.config/pulse/.env` for `SETUP_COMPLETE=true`. If missing, run the same setup wizard as tools-pulse (shared config). **Skip silently if already set up.**

---

## CRITICAL: Parse User Intent

1. **TOPIC**: What they want signals on (e.g., "YC W26", "AI agent funding", "graph RAG techniques")
2. **QUERY_TYPE**:
   - **FUNDING** — "what's getting funded", "YC", "investments", "seed" → focus on YC, a16z, seed rounds
   - **TECHNIQUE** — "technique", "method", "how builders are", "emerging" → focus on paradigm shifts
   - **TRENDS** — default → broad signal sweep

Store: `TOPIC`, `QUERY_TYPE`

Display: `/tech-pulse — scanning X, HN, Exa for signals on {TOPIC}.`

---

## Step 0.5: Pre-Research Intelligence

Resolve X handles for relevant accounts (YC, prominent VCs, builder figures):

For FUNDING queries: look for `@ycombinator`, `@garrytan`, `@paulg` handles.
For TECHNIQUE queries: look for prominent builders in that area.

```
WebSearch("{TOPIC} site:x.com OR site:twitter.com founder launched funded")
WebSearch("{TOPIC} news {CURRENT_MONTH} {CURRENT_YEAR}")
```

---

## Step 0.75: Generate Query Plan

For FUNDING/GENERAL:
```json
{
  "intent": "breaking_news",
  "freshness_mode": "strict_recent",
  "cluster_mode": "story",
  "subqueries": [
    {
      "label": "funding_x",
      "search_query": "{TOPIC} startup funded launched seed Series A 2026",
      "ranking_query": "What new YC-funded or seed-funded startups, product launches, or funding announcements related to {TOPIC} are being discussed on X?",
      "sources": ["x", "grounding", "hackernews"],
      "weight": 1.0
    },
    {
      "label": "yc_launches",
      "search_query": "YC W26 S26 developer AI tool launched 2026",
      "ranking_query": "What new Y Combinator companies focused on developer tools or AI have launched or announced?",
      "sources": ["x", "grounding"],
      "weight": 0.8
    },
    {
      "label": "builder_signal",
      "search_query": "{TOPIC} builder trend paradigm shift ecosystem 2026",
      "ranking_query": "What ecosystem shifts, paradigm changes, or emerging patterns in {TOPIC} are builders discussing?",
      "sources": ["x", "hackernews", "reddit"],
      "weight": 0.7
    }
  ]
}
```

For TECHNIQUE:
```json
{
  "intent": "concept",
  "freshness_mode": "balanced_recent",
  "cluster_mode": "none",
  "subqueries": [
    {
      "label": "technique_primary",
      "search_query": "{TOPIC} technique method approach implementation 2026",
      "ranking_query": "What new techniques, research findings, or implementation approaches for {TOPIC} are builders sharing?",
      "sources": ["x", "hackernews", "github", "grounding"],
      "weight": 1.0
    },
    {
      "label": "technique_discussion",
      "search_query": "{TOPIC} how builders use approach method production",
      "ranking_query": "How are builders actually using {TOPIC} in production? What patterns are emerging?",
      "sources": ["x", "reddit", "hackernews"],
      "weight": 0.8
    }
  ]
}
```

---

## Research Execution

**Run the research script in the FOREGROUND with a 5-minute timeout:**

```bash
"${PULSE_PYTHON}" "${SKILL_ROOT}/scripts/pulse.py" "$TOPIC" \
  --deep \
  --emit=compact \
  --save-dir=~/Documents/Pulse \
  --save-suffix=v1 \
  --plan "$QUERY_PLAN_JSON" \
  --x-handle={RESOLVED_HANDLE_IF_ANY}
```

**Read the ENTIRE output.** Items from X, HN, GitHub, Reddit, web — all carry signal.

---

## Judge Agent: Synthesize

**QUALITY FILTER — KEEP signals that are:**
- YC batch launch, seed/Series A funding announcement (developer tools or AI focus)
- Ecosystem trend with evidence: "builders moving from X to Y", "CLI replacing MCP"
- Research technique or paradigm shift with practical implications
- What prominent builders, VCs, or YC partners are publicly excited about
- Funding patterns that reveal where money is flowing in tech

**REJECT:**
- Specific installable tools (that's `/tools-pulse`)
- Corporate announcements from incumbents (OpenAI blog, Google I/O) unless genuinely novel
- Opinion without a signal or data point
- Anything political, crypto/DeFi, or unrelated to building

**For each signal, provide:**
1. What happened / what the trend is
2. **Why it matters as a signal** — what it tells you about where things are heading

**Output format:**

```
📡 What I learned:

**{Signal or Trend Name}**
{What it is — one sentence.} {Why it matters as a signal — one sentence.}
Source: @{handle} ({N} likes) | HN — {N}pts | {publication}

[5–8 signals ranked by strength]

KEY PATTERNS:
1. [Cross-signal pattern: what multiple signals together suggest]
2. [Pattern]

---
✅ Sources scanned:
├─ 🔵 X: {N} posts │ {N} likes │ 🗣️ Top voices: @{handle1}, @{handle2}
├─ 🟡 HN: {N} stories │ {N} points
├─ 🐙 GitHub: {N} repos (trend signal)
├─ 🌐 Web: {N} pages — {source names}
└─ 📎 Raw saved to ~/Documents/Pulse/{slug}-raw.md
---
```

**Always say WHY something matters as a signal, not just what it is.**

---

## Step 7: Audio Narration (ElevenLabs TTS)

After displaying the text briefing, generate audio and play it.

### 7.1 — Write the narration script

Write a broadcast narration split into two segments, each **≤140 words**.

**Segment 1 — Intro + top signals:**
- Open: *"Builder intelligence briefing, [weekday] [Month Day]. Here's what's moving in the ecosystem."*
- Top 2–3 signals: one sentence on WHAT, one on WHY it matters.
- End: *"More signals coming up."*

**Segment 2 — Remaining signals + close:**
- Remaining 2–3 signals.
- Close: *"That's your tech pulse for today. Tomorrow's signals load fresh."*

Rules: active voice, present tense, no URLs, no @handles, no markdown, no numbers as digits.
Count words. Trim to ≤140 per segment.

### 7.2 — Check balance and pick network

```
NETWORK_PRIORITY:
1. "base"    — prefer if balance ≥ $0.03 USDC
2. "solana"  — try if Base is insufficient
3. no funds  — skip to Step 7.4 (say fallback)
```

Call `mcp__agentcash__get_balance`. Set `CHOSEN_NETWORK`.

### 7.3 — Attempt ElevenLabs TTS (paid)

- URL: `https://x402helper.xyz/v1/tools/text-to-speech`
- `paymentProtocol`: `"x402"`
- `paymentNetwork`: `CHOSEN_NETWORK`
- `maxAmount`: `0.02`
- Body: `{"text": "..."}` — ≤140 words per segment

```python
result1 = mcp__agentcash__fetch(
    url="https://x402helper.xyz/v1/tools/text-to-speech",
    method="POST",
    body={"text": SEGMENT_1},
    paymentNetwork=CHOSEN_NETWORK,
    paymentProtocol="x402",
    maxAmount=0.02
)

result2 = mcp__agentcash__fetch(
    url="https://x402helper.xyz/v1/tools/text-to-speech",
    method="POST",
    body={"text": SEGMENT_2},
    paymentNetwork=CHOSEN_NETWORK,
    paymentProtocol="x402",
    maxAmount=0.02
)
```

Check response for `audio` or `audio_base64` key. If both calls succeed:

```python
import base64, datetime
date = datetime.date.today().strftime('%Y%m%d')
path = f"/Users/ashnouruzi/Downloads/tech-pulse-{date}.mp3"
with open(path, 'wb') as f:
    f.write(base64.b64decode(result1.get('audio') or result1.get('audio_base64')))
    f.write(base64.b64decode(result2.get('audio') or result2.get('audio_base64')))
```

Play: `afplay "/Users/ashnouruzi/Downloads/tech-pulse-$(date +%Y%m%d).mp3"`

**If payment fails on CHOSEN_NETWORK and other network has balance:** retry with other network.
**If both fail:** go to Step 7.4. No diagnosis, no retrying.

### 7.4 — Fallback: macOS say

```bash
DATE=$(date +%Y%m%d)
SCRIPT_FILE="/tmp/tech-pulse-script-${DATE}.txt"
OUTFILE="/Users/ashnouruzi/Downloads/tech-pulse-${DATE}.aiff"
# Write full narration to SCRIPT_FILE using Write tool, then:
say -v Samantha -r 175 -o "${OUTFILE}" -f "${SCRIPT_FILE}"
afplay "${OUTFILE}"
```

### 7.5 — Confirm

```
🎙 Audio saved: ~/Downloads/tech-pulse-{YYYYMMDD}.mp3 (~120s, ~$0.026 USDC via {CHOSEN_NETWORK})
```
or: `🔊 Audio (fallback): ~/Downloads/tech-pulse-{YYYYMMDD}.aiff`

---

## Step 8: HTML Report

Generate a self-contained HTML file and open it in browser.

For each signal, include: title, 2-sentence description, Signal: line (why it matters), source with clickable link.

Save to `/Users/ashnouruzi/Downloads/tech-pulse-{YYYYMMDD}.html`.
Open with: `open "/Users/ashnouruzi/Downloads/tech-pulse-$(date +%Y%m%d).html"`

Template (self-contained, no CDN):

```html
<!DOCTYPE html><html lang="en"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Tech Pulse — {DATE}</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;background:#f5f5f7;color:#1d1d1f;padding:2rem;max-width:860px;margin:0 auto}
h1{font-size:1.6rem;font-weight:700;letter-spacing:-.02em;margin-bottom:.3rem}
.subtitle{color:#6e6e73;font-size:.9rem;margin-bottom:2rem}
.item{background:#fff;border-radius:12px;padding:1.25rem 1.5rem;margin-bottom:1rem;box-shadow:0 1px 4px rgba(0,0,0,.08)}
.item-title{font-size:1rem;font-weight:600;margin-bottom:.4rem}
.item-desc{font-size:.875rem;color:#444;line-height:1.6;margin-bottom:.6rem}
.item-signal{font-size:.8rem;color:#6e6e73;font-style:italic;margin-bottom:.8rem;line-height:1.5}
.sources{display:flex;gap:.5rem;flex-wrap:wrap}
.src{font-size:.78rem;padding:.3rem .75rem;border-radius:6px;border:1px solid #d2d2d7;text-decoration:none;color:#0066cc;background:#fff}
.src:hover{background:#f0f5ff;border-color:#0066cc}
footer{margin-top:2rem;color:#999;font-size:.78rem;border-top:1px solid #e5e5ea;padding-top:1rem}
</style></head><body>
<h1>📡 Tech Pulse</h1>
<div class="subtitle">{DATE} · {N} signals</div>
{ITEMS}
<footer>Generated by /tech-pulse · pulse v1.0.0 · github.com/Must-be-Ash/pulse</footer>
</body></html>
```

Each item:
```html
<div class="item">
  <div class="item-title">{TITLE}</div>
  <div class="item-desc">{DESCRIPTION}</div>
  <div class="item-signal">Signal: {WHY_IT_MATTERS}</div>
  <div class="sources">
    <a class="src" href="{URL}" target="_blank">{SOURCE_LABEL}</a>
  </div>
</div>
```

Confirm: `📄 Report: ~/Downloads/tech-pulse-{YYYYMMDD}.html`

---

## WAIT FOR USER RESPONSE

After displaying output, audio, and HTML — stop and wait. Do NOT run new searches.

---

## Security & Permissions

- Reads X/Twitter via AUTH_TOKEN/CT0 or XAI_API_KEY
- Reads HN via Algolia API (free, no auth)
- Reads GitHub via public API or gh CLI
- Reads web via Exa/Brave/Serper
- Optionally scrapes URLs via FIRECRAWL_API_KEY
- TTS via agentcash x402 (~$0.026 USDC per run)
- Saves research to `~/Documents/Pulse/`, audio to `~/Downloads/`, HTML to `~/Downloads/`
- Config at `~/.config/pulse/.env`

Does NOT post, like, or modify content on any platform.
