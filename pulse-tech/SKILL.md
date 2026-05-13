---
name: pulse-tech
version: "2.0.0"
description: "Pipeline-powered builder intelligence — emerging techniques, YC launches, funding signals, and ecosystem shifts that would go unnoticed. Biased toward fresh signals over viral noise. Ends with ElevenLabs audio + HTML report."
argument-hint: 'pulse-tech, pulse-tech YC, pulse-tech AI agents, pulse-tech knowledge graph'
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

# /pulse-tech v2.0.0: Fresh Builder Intelligence (Pipeline)

Surfaces signals about where the builder ecosystem is heading — YC launches, funding, emerging techniques, paradigm shifts — with a bias toward **what's new and under-discussed**, not what's already viral. The signal you want is the one most people haven't noticed yet.

**Hard rules:**
- Lookback: **21 days** for signals (trends develop a bit slower than tool releases)
- Reject: mainstream corporate news (OpenAI announcements, Google I/O, Vercel releases)
- Reject: anything that's already in every newsletter — if it got >10K likes on a single tweet it's already viral
- Prefer: founder threads, niche builder discussions, YC launches that aren't front-page yet
- No Reddit — Reddit engagement lags and inflates old discussions

---

## Runtime Preflight

```bash
for py in python3.14 python3.13 python3.12 python3; do
  command -v "$py" >/dev/null 2>&1 || continue
  "$py" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 12) else 1)' || continue
  PULSE_PYTHON="$py" && break
done
[ -z "${PULSE_PYTHON:-}" ] && echo "ERROR: requires Python 3.12+" >&2 && exit 1

for dir in "." "${CLAUDE_PLUGIN_ROOT:-}" "$HOME/pulse" "$HOME/.claude/skills/pulse-tech" "$HOME/.claude/skills/pulse-tools"; do
  [ -n "$dir" ] && [ -f "$dir/scripts/pulse.py" ] && SKILL_ROOT="$dir" && break
done
[ -z "${SKILL_ROOT:-}" ] && echo "ERROR: Could not find scripts/pulse.py" >&2 && exit 1
```

---

## Step 0: Setup

Check `~/.config/pulse/.env` for `SETUP_COMPLETE=true`. If missing: run setup wizard (`"${PULSE_PYTHON}" "${SKILL_ROOT}/scripts/pulse.py" setup`). Skip silently if done.

---

## Step 1: Parse Intent

- `/pulse-tech` → TOPIC = "developer tools AI agent building startup trend 2026"
- `/pulse-tech YC` → TOPIC = "Y Combinator YC startup launch 2026"
- `/pulse-tech knowledge graph` → TOPIC = "knowledge graph technique AI builder"

Display: `📡 /pulse-tech — scanning for fresh signals on {TOPIC}.`

---

## Step 0.75: Generate Query Plan (FRESHNESS-FIRST, UNDER-THE-RADAR)

The goal is to find signals that are real but not yet mainstream. Prioritise: founder/builder posts over press releases, niche HN discussions over front-page threads, small funded startups over unicorns.

```json
{
  "intent": "breaking_news",
  "freshness_mode": "strict_recent",
  "cluster_mode": "story",
  "subqueries": [
    {
      "label": "fresh_builder_x",
      "search_query": "{TOPIC} launched announced released shipped 2026",
      "ranking_query": "What new startups, tools, techniques, or approaches related to {TOPIC} have founders or builders announced or shipped in the last 3 weeks that haven't been widely covered yet?",
      "sources": ["x", "hackernews"],
      "weight": 1.0
    },
    {
      "label": "yc_niche_launches",
      "search_query": "YC W26 S26 launched developer AI builder tool small startup 2026",
      "ranking_query": "What smaller or less-covered YC-backed startups focused on developer tools, AI infrastructure, or research tooling have recently launched or shared updates?",
      "sources": ["x", "hackernews", "grounding"],
      "weight": 0.9
    },
    {
      "label": "technique_discovery",
      "search_query": "{TOPIC} technique approach method pattern how builders use 2026",
      "ranking_query": "What emerging techniques, implementation approaches, or architectural patterns related to {TOPIC} are builders discussing that represent genuine new approaches vs repackaging old ideas?",
      "sources": ["hackernews", "x", "grounding"],
      "weight": 0.8
    },
    {
      "label": "funding_niche",
      "search_query": "seed round Series A developer tool AI infrastructure 2026 small",
      "ranking_query": "What seed-stage or early Series A companies in the developer tools or AI space have announced funding recently that signal where investors see opportunity?",
      "sources": ["grounding", "x"],
      "weight": 0.6
    }
  ]
}
```

---

## Research Execution

**Run in FOREGROUND, 5-minute timeout. Use `--lookback-days=21`.**

```bash
"${PULSE_PYTHON}" "${SKILL_ROOT}/scripts/pulse.py" "$TOPIC" \
  --deep \
  --emit=compact \
  --save-dir=~/Documents/Pulse \
  --save-suffix=v2 \
  --lookback-days=21 \
  --plan "$QUERY_PLAN_JSON"
```

**Read the ENTIRE output.**

---

## Judge Agent: Synthesize (UNDER-THE-RADAR FIRST)

**RE-RANK the engine output yourself — override engagement-based scoring:**

Rank by:
1. **Recency** — last 7 days scores highest
2. **Novelty of signal** — genuine paradigm shift vs derivative opinion
3. **Under-the-radar** — fewer than 500 likes/upvotes but substantive = higher score than 5K likes on something obvious
4. **Actionability** — does this change what you'd build or how you'd build it?

**HARD EXCLUSIONS:**
- Corporate press releases from: OpenAI, Anthropic, Google, Microsoft, AWS, Vercel, Meta, Apple → skip (you'll see these anyway)
- Anything already front-page viral (>5K likes on a single X post) → skip (already in your feed)
- "Thoughts on X" opinion without new data or evidence → skip
- Funding rounds >$50M → skip (already covered everywhere)
- Older than 21 days → skip

**KEEP — genuine signals:**
- Founder/builder posts announcing what they shipped (not press releases)
- YC S26/W26 launches that haven't been picked up widely yet
- Seed rounds (<$10M) in interesting categories that signal where smart money is going
- Technique discoveries shared in HN threads or niche X posts by practitioners
- Behavioural signals: "builders are moving from X to Y", "CLI is replacing MCP for X use case"
- Anything that would make you say "I didn't know this was happening"

**For each signal, output WHY it matters** — not just what it is, but what it implies about where things are heading.

**OUTPUT FORMAT:**

```
📡 /pulse-tech — {YYYY-MM-DD}

**{Signal Name}**
{What happened — one sentence.} {Why this matters as a signal: what it tells you about where the ecosystem is heading — one sentence.}
Source: X — @{handle} ({N} likes) | HN — {N}pts | {publication}

[5–8 signals, freshest and most underrated first]

KEY PATTERNS (synthesise across all signals):
1. {What these signals together suggest — a trend that isn't obvious from any single signal}
2. {Second pattern}

---
X ({N} posts, top underrated: @{handle}) | HN ({N} stories) | Web ({N} pages) | {N} new signals
📡 Raw: ~/Documents/Pulse/{slug}-raw-v2.md
---
```

---

## Step: Audio Narration (ElevenLabs — paid, ~$0.026/run)

### Write the script first (two segments, each ≤140 words)

**Segment 1:** Open: *"Builder intelligence briefing, [weekday] [Month Day]. Here's what's moving under the radar."* → Top 2–3 signals (WHAT + WHY it matters as a signal). End: *"More signals coming up."*

**Segment 2:** Remaining 2–3 signals → Close: *"That's your pulse-tech briefing. These signals are fresh — act on them before they're everywhere."*

Rules: active voice, present tense, no URLs, no @handles, no markdown, spell out numbers. Trim to ≤140 words per segment.

### Check balance and pick network

Call `mcp__agentcash__get_balance`. Set `CHOSEN_NETWORK`:
1. `"base"` if balance ≥ $0.03
2. `"solana"` if Base is insufficient
3. No funds → skip to macOS say fallback

### Attempt ElevenLabs TTS

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

Check each for `audio` or `audio_base64`. If both succeed:

```python
import base64, datetime
date = datetime.date.today().strftime('%Y%m%d')
path = f"/Users/ashnouruzi/Downloads/pulse-tech-{date}.mp3"
with open(path, 'wb') as f:
    f.write(base64.b64decode(result1.get('audio') or result1.get('audio_base64')))
    f.write(base64.b64decode(result2.get('audio') or result2.get('audio_base64')))
```

Play: `afplay "/Users/ashnouruzi/Downloads/pulse-tech-$(date +%Y%m%d).mp3"`

**If payment fails:** retry with other network if it has balance. If both fail: macOS say fallback (below). No diagnosis, no retrying.

### Fallback: macOS say (free)

Write full narration (both segments combined) to `/tmp/pulse-tech-script-$(date +%Y%m%d).txt` using Write tool, then:

```bash
say -v Samantha -r 175 \
  -o "/Users/ashnouruzi/Downloads/pulse-tech-$(date +%Y%m%d).aiff" \
  -f "/tmp/pulse-tech-script-$(date +%Y%m%d).txt"
afplay "/Users/ashnouruzi/Downloads/pulse-tech-$(date +%Y%m%d).aiff"
```

Confirm: `🎙 ~/Downloads/pulse-tech-{YYYYMMDD}.mp3 (~120s, ~$0.026 USDC via {CHOSEN_NETWORK})` or `🔊 ~/Downloads/pulse-tech-{YYYYMMDD}.aiff (fallback)`

---

## Step: HTML Report

Generate self-contained HTML using the Write tool. Each signal gets a card: title, 2-sentence description, a **Signal:** line (what this implies about where things are heading), and clickable source links.

```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Pulse Tech — {DATE}</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;background:#f5f5f7;color:#1d1d1f;padding:2rem;max-width:860px;margin:0 auto}
h1{font-size:1.6rem;font-weight:700;letter-spacing:-.02em}
.sub{color:#6e6e73;font-size:.9rem;margin:.3rem 0 2rem}
.item{background:#fff;border-radius:12px;padding:1.25rem 1.5rem;margin-bottom:1rem;box-shadow:0 1px 4px rgba(0,0,0,.08)}
.title{font-size:1rem;font-weight:600;margin-bottom:.4rem}
.desc{font-size:.875rem;color:#444;line-height:1.6;margin-bottom:.6rem}
.signal{font-size:.8rem;color:#6e6e73;font-style:italic;margin-bottom:.8rem;line-height:1.5;padding:.5rem .75rem;background:#f0f5ff;border-left:3px solid #0066cc;border-radius:0 4px 4px 0}
.srcs{display:flex;gap:.5rem;flex-wrap:wrap}
.src{font-size:.78rem;padding:.3rem .75rem;border-radius:6px;border:1px solid #d2d2d7;text-decoration:none;color:#0066cc;background:#fff}
.src:hover{background:#f0f5ff;border-color:#0066cc}
footer{margin-top:2rem;color:#999;font-size:.78rem;border-top:1px solid #e5e5ea;padding-top:1rem}
</style>
</head>
<body>
<h1>📡 Pulse Tech</h1>
<div class="sub">{DATE} · {N} signals · under-the-radar first · last 21 days</div>

<!-- For each signal: -->
<div class="item">
  <div class="title">{TITLE}</div>
  <div class="desc">{DESCRIPTION}</div>
  <div class="signal">Signal: {WHAT_THIS_IMPLIES_ABOUT_WHERE_THINGS_ARE_HEADING}</div>
  <div class="srcs">
    <a class="src" href="{URL}" target="_blank">{SOURCE_LABEL}</a>
  </div>
</div>

<footer>github.com/Must-be-Ash/pulse · /pulse-tech v2.0.0</footer>
</body>
</html>
```

Note: the `signal` box uses a blue left-border style to visually distinguish the "so what" from the description.

Save to `/Users/ashnouruzi/Downloads/pulse-tech-{YYYYMMDD}.html`, then:
```bash
open "/Users/ashnouruzi/Downloads/pulse-tech-$(date +%Y%m%d).html"
```
Confirm: `📄 Report: ~/Downloads/pulse-tech-{YYYYMMDD}.html`
