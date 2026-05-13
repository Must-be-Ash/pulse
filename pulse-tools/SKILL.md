---
name: pulse-tools
version: "2.0.0"
description: "Pipeline-powered discovery of recently released open-source tools, MCPs, Claude Code skills ⭐, CLI utilities, and agents — biased toward the new and underrated, not the popular and mainstream."
argument-hint: 'pulse-tools, pulse-tools MCP servers, pulse-tools Claude Code skills, pulse-tools CLI'
allowed-tools: WebSearch, Bash, Read, Write
user-invocable: true
metadata:
  openclaw:
    emoji: "🔧"
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
      - tools
      - mcp
      - cli
      - skills
      - github
      - open-source
      - builder
      - hackernews
      - twitter
---

# /pulse-tools v2.0.0: Underrated Builder Tool Discovery (Pipeline)

Finds recently released open-source tools, MCPs, Claude Code skills ⭐, CLI utilities, GitHub repos, and agent harnesses that might have gone unnoticed. **Biased toward new and underrated, not popular and mainstream.** A useful repo with 50 stars released yesterday beats a viral tweet about a 3-year-old library.

**Hard rules:**
- Lookback: **14 days max** — anything older is probably already on your radar
- Reject anything with >10K GitHub stars (already mainstream — you'll hear about it anyway)
- Reject all corporate tool announcements (OpenAI, Google, Anthropic, Microsoft, Vercel, AWS)
- No Reddit — Reddit surfaces popular discussions, not new releases
- Sources: X/Twitter → HN Show HN → GitHub newly-created repos → Exa web

---

## Runtime Preflight

```bash
for py in python3.14 python3.13 python3.12 python3; do
  command -v "$py" >/dev/null 2>&1 || continue
  "$py" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 12) else 1)' || continue
  PULSE_PYTHON="$py" && break
done
[ -z "${PULSE_PYTHON:-}" ] && echo "ERROR: requires Python 3.12+" >&2 && exit 1

for dir in "." "${CLAUDE_PLUGIN_ROOT:-}" "$HOME/pulse" "$HOME/.claude/skills/pulse-tools" "$HOME/.claude/skills/pulse-tech"; do
  [ -n "$dir" ] && [ -f "$dir/scripts/pulse.py" ] && SKILL_ROOT="$dir" && break
done
[ -z "${SKILL_ROOT:-}" ] && echo "ERROR: Could not find scripts/pulse.py" >&2 && exit 1
```

---

## Step 0: Setup

Check `~/.config/pulse/.env` for `SETUP_COMPLETE=true`. If missing: run setup wizard (`"${PULSE_PYTHON}" "${SKILL_ROOT}/scripts/pulse.py" setup`), write `SETUP_COMPLETE=true`. Skip silently if already done.

---

## Step 1: Parse Intent

- `/pulse-tools` → TOPIC = "open source tool MCP CLI skill agent"
- `/pulse-tools Claude Code skills` → TOPIC = "Claude Code skill agent skill"
- `/pulse-tools MCP servers` → TOPIC = "MCP server model context protocol"

If TOPIC mentions "skill" or "agent skill" → QUERY_TYPE = SKILLS (flag all results ⭐)

Display: `🔧 /pulse-tools — hunting recently released tools for builders: {TOPIC}.`

---

## Step 0.5: Pre-Research (resolve GitHub repo or X handle if topic is specific)

Only if TOPIC is a specific named project (not a broad category):
```
WebSearch("{TOPIC} github repo site:github.com")
WebSearch("{TOPIC} X twitter site:x.com")
```
Extract `--github-repo={owner/repo}` and `--x-handle={handle}` if found.

---

## Step 0.75: Generate Query Plan (RECENCY-FIRST, UNDERRATED-BIAS)

The plan must prioritise freshness and novelty over engagement. These queries look for things *just released*, not things that are *popular*.

```json
{
  "intent": "product",
  "freshness_mode": "strict_recent",
  "cluster_mode": "none",
  "subqueries": [
    {
      "label": "show_hn_releases",
      "search_query": "Show HN {TOPIC} open source released new",
      "ranking_query": "What open-source tools, repos, MCP servers, Claude Code skills, or CLI utilities related to {TOPIC} have been newly released or shared on Hacker News Show HN in the last 2 weeks?",
      "sources": ["hackernews", "x", "github"],
      "weight": 1.0
    },
    {
      "label": "github_new_repos",
      "search_query": "{TOPIC} open source CLI MCP skill agent tool",
      "ranking_query": "What new GitHub repos, CLI tools, MCP servers, or agent frameworks related to {TOPIC} have been created in the last 2 weeks?",
      "sources": ["github", "grounding"],
      "weight": 0.9
    },
    {
      "label": "builder_shares",
      "search_query": "built open source {TOPIC} tool released MCP CLI skill",
      "ranking_query": "What have individual builders recently shared or released — tools, repos, skills, CLIs, MCP servers — related to {TOPIC}?",
      "sources": ["x", "hackernews"],
      "weight": 0.8
    }
  ]
}
```

For SKILLS query type, replace the third subquery with:
```json
{
  "label": "skills_fresh",
  "search_query": "Claude Code skill agent skill MCP plugin open source new released",
  "ranking_query": "What Claude Code skills, OpenClaw skills, agent skill harnesses, or MCP servers have been released or updated in the last 2 weeks?",
  "sources": ["x", "hackernews", "github"],
  "weight": 1.0
}
```

---

## Research Execution

**Run in FOREGROUND, 5-minute timeout. Use `--lookback-days=14` — not the default 30.**

```bash
"${PULSE_PYTHON}" "${SKILL_ROOT}/scripts/pulse.py" "$TOPIC" \
  --deep \
  --emit=compact \
  --save-dir=~/Documents/Pulse \
  --save-suffix=v2 \
  --lookback-days=14 \
  --plan "$QUERY_PLAN_JSON" \
  ${RESOLVED_HANDLE:+--x-handle=$RESOLVED_HANDLE} \
  ${RESOLVED_REPO:+--github-repo=$RESOLVED_REPO}
```

**Read the ENTIRE output.** Every section contains signal.

---

## Judge Agent: Synthesize (UNDERRATED-FIRST)

**RECENCY-FIRST RANKING — re-rank the engine output yourself:**

The Python engine ranks by engagement (likes, stars). You must **override this** and re-rank by:
1. **Age** — released in last 7 days scores highest
2. **Novelty** — genuinely new approach or category, not another wrapper around the same thing
3. **Utility** — directly useful for building web/AI apps, agents, research tools
4. **Underrated** — low star count (<500) on something genuinely useful is a positive signal

**HARD EXCLUSIONS — reject immediately regardless of score:**
- Stars > 10,000 → already mainstream, skip
- From: OpenAI, Google/DeepMind, Microsoft, Anthropic, Vercel, AWS, Meta → skip (corporate)
- Reddit as the only source → skip (community discussion ≠ new tool release)
- Older than 14 days → skip
- Not a concrete installable thing (no repo, no link to actual tool) → skip
- Generic "collection" lists or awesome-X repos → skip (you want specific tools)

**KEEP — concrete installable things:**
- Open-source GitHub repos that are new tools/libraries (especially <500 stars = underrated)
- Claude Code skills, agent skills, OpenClaw skills → **mark ⭐** (high priority)
- MCP servers → **mark ⭐**
- CLI tools or developer utilities
- Agent harnesses, scaffolds, frameworks
- Anything a builder could install and use this week

**OUTPUT FORMAT:**

```
🔧 /pulse-tools — {YYYY-MM-DD}

**{Tool or Skill Name}** {⭐ if skill/MCP/agent}
{What it does — one sentence.} {Why a builder building AI apps or research tools would reach for this — one sentence.}
Source: {HN Show HN — Npts | GitHub — owner/repo | X — @handle Nlikes}

[5–10 items, ordered: newest first, then by utility score]

KEY PATTERNS:
1. {What category of tools is suddenly appearing that wasn't before}
2. {Emerging pattern across the releases}

---
Sources: HN ({N} Show HNs, {N}pts) | GitHub ({N} repos, {N} new this week) | X ({N} posts) | Web ({N} pages)
🔧 Raw: ~/Documents/Pulse/{slug}-raw-v2.md
---
```

**No raw URLs. Source name or handle only. 2 sentences per item max.**

---

## Step: Audio Read-Out (macOS say — free)

After displaying the text output, write a narration (~60–90 seconds, ~150–200 words) and play it.

Structure: *"Here's your tools pulse for [weekday]."* → top 4–6 items (one punchy sentence each: what it is + why it matters) → if any ⭐ skills: *"Top skill find: [Name] — a Claude Code skill that..."* → *"That's your tools pulse. Full details in your terminal."*

Rules: no markdown, no URLs, no handles, spell out numbers, present tense.

```bash
DATE=$(date +%Y%m%d)
SCRIPT_FILE="/tmp/pulse-tools-script-${DATE}.txt"
OUTFILE="/Users/ashnouruzi/Downloads/pulse-tools-${DATE}.aiff"
```

Write the narration text to `$SCRIPT_FILE` using the Write tool, then:

```bash
say -v Samantha -r 175 -o "${OUTFILE}" -f "${SCRIPT_FILE}"
afplay "${OUTFILE}"
```

Confirm: `🔊 Audio: ~/Downloads/pulse-tools-{YYYYMMDD}.aiff`

---

## Step: HTML Report

Generate self-contained HTML with clickable source links using the Write tool.

Tag class mapping: HN → `tag-hn` (orange), GitHub → `tag-github` (green), X → `tag-x` (blue), Web → `tag-web` (purple), Skill/MCP → `tag-skills` (pink)

```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Pulse Tools — {DATE}</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;background:#f5f5f7;color:#1d1d1f;padding:2rem;max-width:860px;margin:0 auto}
h1{font-size:1.6rem;font-weight:700;letter-spacing:-.02em}
.sub{color:#6e6e73;font-size:.9rem;margin:.3rem 0 2rem}
.item{background:#fff;border-radius:12px;padding:1.25rem 1.5rem;margin-bottom:1rem;box-shadow:0 1px 4px rgba(0,0,0,.08)}
.row{display:flex;align-items:flex-start;gap:.75rem;margin-bottom:.5rem}
.tag{flex-shrink:0;font-size:.65rem;font-weight:700;padding:.25rem .55rem;border-radius:5px;text-transform:uppercase;letter-spacing:.06em;margin-top:.2rem}
.tag-hn{background:#fff3e0;color:#e65100}
.tag-github{background:#e8f5e9;color:#2e7d32}
.tag-x{background:#e3f2fd;color:#1565c0}
.tag-web{background:#f3e5f5;color:#6a1b9a}
.tag-skills{background:#fce4ec;color:#880e4f}
.title{font-size:1rem;font-weight:600;line-height:1.35}
.desc{font-size:.875rem;color:#444;line-height:1.6;margin-bottom:.9rem}
.badge{font-size:.75rem;font-weight:700;color:#c2185b;margin-left:.3rem}
.srcs{display:flex;gap:.5rem;flex-wrap:wrap}
.src{font-size:.78rem;padding:.3rem .75rem;border-radius:6px;border:1px solid #d2d2d7;text-decoration:none;color:#0066cc;background:#fff}
.src:hover{background:#f0f5ff;border-color:#0066cc}
footer{margin-top:2rem;color:#999;font-size:.78rem;border-top:1px solid #e5e5ea;padding-top:1rem}
</style>
</head>
<body>
<h1>🔧 Pulse Tools</h1>
<div class="sub">{DATE} · {N} items · underrated-first · last 14 days</div>
{ITEMS}
<footer>github.com/Must-be-Ash/pulse · /pulse-tools v2.0.0</footer>
</body>
</html>
```

Each item block:
```html
<div class="item">
  <div class="row">
    <span class="tag tag-{TYPE}">{LABEL}</span>
    <div class="title">{TITLE}{if_skill: <span class="badge">★ Skill</span>}</div>
  </div>
  <div class="desc">{DESCRIPTION}</div>
  <div class="srcs">
    <a class="src" href="{URL}" target="_blank">{SOURCE_LABEL}</a>
  </div>
</div>
```

Save to `/Users/ashnouruzi/Downloads/pulse-tools-{YYYYMMDD}.html`, then:
```bash
open "/Users/ashnouruzi/Downloads/pulse-tools-$(date +%Y%m%d).html"
```
Confirm: `📄 Report: ~/Downloads/pulse-tools-{YYYYMMDD}.html`
