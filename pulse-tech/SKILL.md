---
name: pulse-tech
version: "2.1.0"
description: "Zeitgeist tracker for builders — what the builder community is actually adopting, excited about, and talking about. Trends, viral tools, paradigm shifts, YC launches, funding. pulse-tools finds hidden value; pulse-tech tracks what's resonating."
argument-hint: 'pulse-tech, pulse-tech YC, pulse-tech AI agents, pulse-tech trends'
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
      - zeitgeist
      - builder-intel
      - twitter
      - hackernews
---

# /pulse-tech v2.1.0: Builder Zeitgeist (Pipeline)

Tracks what the builder community is actually adopting, excited about, and talking about right now. Trends, viral tools, paradigm shifts, YC launches, funding signals. This is the pulse of builder culture — not a quality judgment, but a calibration tool for staying in sync with the ecosystem.

**The split between pulse-tools and pulse-tech:**
- **`/pulse-tools`** — finds things builders *should* know about but might not. Value-first, underrated-first. Ignores hype.
- **`/pulse-tech`** — tracks things builders *do* know about and are actively excited about. Trend-first, adoption-first. Hype is the signal.

**What belongs here:** gstack has 95K stars because Garry Tan posted it and his followers loved it. That's Zeitgeist — builders are actually using it. Knowing that gstack is trending tells you something real about what the community values right now. That's pulse-tech territory.

**What does NOT belong here:**
- Corporate product announcements from OpenAI, Google, Anthropic, Vercel, AWS — these are PR, not organic builder excitement
- Investor/VC press releases about valuations — unless builders are organically excited
- News articles covering tech companies — unless there's genuine builder discussion behind it
- Things builders are NOT actually adopting (papers nobody implements, launches nobody uses)

**The test:** "Are independent builders genuinely excited about and adopting this — or is it just PR from a company with marketing budget?" If independent builders are talking enthusiastically about something a prominent person shipped, that's Zeitgeist. If it's just a company's press release that nobody discussed organically, it's not.

**Lookback: 7 days.** This is a weekly briefing — run it once a week. Anything older than 7 days is last week's news.

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

Check `~/.config/pulse/.env` for `SETUP_COMPLETE=true`. Run setup wizard if missing. Skip silently if done.

---

## Step 1: Parse Intent

- `/pulse-tech` → TOPIC = "developer tools AI agent building startup trend"
- `/pulse-tech YC` → TOPIC = "Y Combinator YC startup launch"
- `/pulse-tech AI agents` → TOPIC = "AI agent builder tooling"

Display: `📡 /pulse-tech — scanning for what builders are actually adopting: {TOPIC}.`

---

## Step 0.75: Generate Query Plan (ADOPTION-SIGNAL-FIRST)

The goal is to find what builders are genuinely excited about and using — high engagement from the builder community is THE signal here, not something to filter out.

```json
{
  "intent": "breaking_news",
  "freshness_mode": "strict_recent",
  "cluster_mode": "story",
  "subqueries": [
    {
      "label": "builder_excitement",
      "search_query": "{TOPIC} builders using loving shipped tool 2026",
      "ranking_query": "What tools, frameworks, approaches, or launches related to {TOPIC} are independent builders genuinely excited about, actively using, or recommending to each other this week?",
      "sources": ["x", "hackernews"],
      "weight": 1.0
    },
    {
      "label": "trending_adoption",
      "search_query": "{TOPIC} trending popular builders 2026",
      "ranking_query": "What is getting significant organic traction among builders and developers related to {TOPIC} this week? What are they actively installing, starring, and discussing?",
      "sources": ["x", "hackernews", "github"],
      "weight": 0.9
    },
    {
      "label": "yc_and_funding",
      "search_query": "YC W26 S26 startup launched AI developer tools 2026",
      "ranking_query": "What YC-funded or recently funded startups in developer tools or AI have launched and are getting genuine builder traction this week?",
      "sources": ["x", "hackernews", "grounding"],
      "weight": 0.8
    },
    {
      "label": "paradigm_shifts",
      "search_query": "{TOPIC} paradigm shift how builders work changing approach",
      "ranking_query": "What is genuinely changing how builders work this week — new workflows, adopted patterns, or tools that builders are switching to?",
      "sources": ["x", "hackernews"],
      "weight": 0.6
    }
  ]
}
```

**Source weights for pulse-tech:** X/Twitter = 1.0 (primary — this is where builder culture lives). HN = 0.8 (high signal for builder discussion). GitHub = 0.4 (trending as adoption signal). Reddit = not used — too slow and noisy for a 7-day weekly signal.

---

## Research Execution

**Run FOREGROUND, 5-minute timeout. `--lookback-days=7` — weekly signal only.**

```bash
"${PULSE_PYTHON}" "${SKILL_ROOT}/scripts/pulse.py" "$TOPIC" \
  --deep \
  --emit=compact \
  --save-dir=~/Documents/Pulse \
  --save-suffix=v2 \
  --lookback-days=7 \
  --plan "$QUERY_PLAN_JSON"
```

---

## Judge Agent: Synthesize (BUILDER ADOPTION SIGNAL)

**This is NOT a quality filter — it's an adoption/resonance filter.**

The question for each item is not "is this the best tool?" but "are builders actually adopting and excited about this?"

**KEEP — genuine builder Zeitgeist:**
- Tools or frameworks that builders are actively using, recommending, discussing — even if they're not technically the most impressive
- YC launches or funded startups getting real organic traction from independent builders
- Paradigm shifts — patterns that builders are genuinely switching to ("I've been doing X but now everyone's using Y")
- What's trending on HN front page among builders
- Repos gaining stars organically from builder community (not just from follower count of poster)
- Things people are building WITH (not just building) — "everyone's using X to make Y now"

**REJECT — not builder Zeitgeist:**
- Corporate press releases from OpenAI, Google, Anthropic, AWS, Vercel, Meta — even if they make good tools, the announcement itself is PR not organic builder excitement. Surface it ONLY if there's genuine builder discussion and adoption behind it.
- Investor/VC announcements about valuations or funding rounds without real builder discussion
- News articles that aren't backed by actual builder enthusiasm
- Research papers that builders aren't actually implementing
- Things that look popular but aren't builder-relevant (e.g., consumer app trends)

**SCORING — weight by builder adoption signal:**
- X likes from independent builder accounts (not corporate): high weight
- HN comments discussing actual usage ("I've been using this...") > discussion posts
- GitHub stars on repos in last 7 days: moderate weight (organic adoption signal)
- Multiple independent builders recommending same thing: strong signal
- HN comments discussing actual usage ("I've been using this for a week..."): strong signal

**For each signal, explain:**
1. What it is and what builders are doing with it
2. Why it's gaining traction — what need it fills that other things didn't

**OUTPUT FORMAT:**

```
📡 /pulse-tech — {YYYY-MM-DD} (builder Zeitgeist)

**{Trend or Tool Name}**
{What builders are doing with it — one sentence.} {Why it's resonating — what builder need it hits that wasn't being met — one sentence.}
Source: X — @{handle} ({N} builder likes) | HN — {N}pts, {N} comments | GitHub — {N}⭐ this week

[5–8 signals, ordered by adoption strength]

KEY PATTERNS:
1. {What multiple signals together reveal about where builder culture is going}
2. {What builders are moving away from or toward}

---
X ({N} posts, top: @{handle} {N} likes) | HN ({N} stories, {N} comments) | GitHub ({N} trending)
📡 Raw: ~/Documents/Pulse/{slug}-raw-v2.md
---
```

---

## Audio Narration (ElevenLabs — paid, ~$0.026/run)

### Write the script (two segments, ≤140 words each)

**Segment 1:** *"Builder Zeitgeist briefing, [weekday] [Month Day]. Here's what the builder community is actually excited about."* → Top 2–3 signals (what builders are using + why it's resonating). End: *"More signals coming up."*

**Segment 2:** Remaining 2–3 signals. Close: *"That's your pulse-tech. Use /pulse-tools if you want the underrated stuff builders haven't found yet."*

Rules: active voice, present tense, no URLs, no @handles, spell out numbers. ≤140 words per segment.

### Check balance and pick network

Call `mcp__agentcash__get_balance`. Set `CHOSEN_NETWORK`:
1. `"base"` if balance ≥ $0.03
2. `"solana"` if Base insufficient
3. No funds → macOS say fallback

### ElevenLabs TTS

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

Check `audio` or `audio_base64`. If both succeed → concatenate bytes → save `~/Downloads/pulse-tech-{YYYYMMDD}.mp3` → `afplay`.

If CHOSEN_NETWORK fails: retry with other network. If both fail: macOS say fallback — no diagnosis.

### Fallback: macOS say

Write combined narration to `/tmp/pulse-tech-script-$(date +%Y%m%d).txt` with Write tool, then:

```bash
say -v Samantha -r 175 \
  -o "/Users/ashnouruzi/Downloads/pulse-tech-$(date +%Y%m%d).aiff" \
  -f "/tmp/pulse-tech-script-$(date +%Y%m%d).txt"
afplay "/Users/ashnouruzi/Downloads/pulse-tech-$(date +%Y%m%d).aiff"
```

---

## HTML Report

Self-contained HTML with each signal as a card: title, 2-sentence description, a **Why it's resonating:** callout, clickable source links.

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
.resonance{font-size:.8rem;color:#1d6fa4;margin-bottom:.8rem;line-height:1.5;padding:.5rem .75rem;background:#e8f4fd;border-left:3px solid #1d6fa4;border-radius:0 4px 4px 0}
.srcs{display:flex;gap:.5rem;flex-wrap:wrap}
.src{font-size:.78rem;padding:.3rem .75rem;border-radius:6px;border:1px solid #d2d2d7;text-decoration:none;color:#0066cc;background:#fff}
.src:hover{background:#f0f5ff;border-color:#0066cc}
footer{margin-top:2rem;color:#999;font-size:.78rem;border-top:1px solid #e5e5ea;padding-top:1rem}
</style>
</head>
<body>
<h1>📡 Pulse Tech</h1>
<div class="sub">{DATE} · {N} signals · builder Zeitgeist · last 21 days</div>

<!-- For each signal: -->
<div class="item">
  <div class="title">{TITLE}</div>
  <div class="desc">{DESCRIPTION}</div>
  <div class="resonance">Why it's resonating: {WHAT_BUILDER_NEED_IT_FILLS}</div>
  <div class="srcs">
    <a class="src" href="{URL}" target="_blank">{SOURCE_LABEL}</a>
  </div>
</div>

<footer>github.com/Must-be-Ash/pulse · /pulse-tech v2.1.0 · pair with /pulse-tools for underrated gems</footer>
</body>
</html>
```

Save to `/Users/ashnouruzi/Downloads/pulse-tech-{YYYYMMDD}.html`, then `open`.
Confirm: `📄 Report: ~/Downloads/pulse-tech-{YYYYMMDD}.html`

---

## Persona

You are embedded in the builder community — you know what practitioners are actually shipping, adopting, and excited about. Your job is to reflect the real state of builder culture, not to curate quality. If 10,000 builders are using something mediocre, that tells you something real about where the community is. If something brilliant is going unnoticed, that's pulse-tools territory. You track the conversation.
