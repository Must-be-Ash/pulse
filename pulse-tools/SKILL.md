---
name: pulse-tools
version: "2.1.0"
description: "Pipeline-powered discovery of recently released open-source tools, MCPs, Claude Code skills ⭐, CLI utilities, and agents — biased toward the new and underrated. X/Twitter-primary. No corporate noise."
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
---

# /pulse-tools v2.1.0: Underrated Builder Tool Discovery (Pipeline)

Finds recently released open-source tools, MCPs, Claude Code skills ⭐, CLI utilities, GitHub repos, and agent harnesses that might have gone unnoticed. **X/Twitter is the primary signal**. Reddit is minimal and targeted to specific builder subreddits only. No corporate noise — things from OpenAI/Google/Anthropic/Vercel will reach you anyway.

**Core principle:** A niche repo with 16K practitioner-earned stars (like compound-engineering-plugin) beats a viral repo with 95K follower-driven stars (from a VC with 2M followers). Quality = utility, not distribution.

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

Check `~/.config/pulse/.env` for `SETUP_COMPLETE=true`. If missing: run `"${PULSE_PYTHON}" "${SKILL_ROOT}/scripts/pulse.py" setup`. Skip silently if done.

---

## Step 1: Parse Intent

- `/pulse-tools` → TOPIC = "open source tool MCP CLI skill agent harness"
- `/pulse-tools Claude Code skills` → TOPIC = "Claude Code skill agent skill"
- `/pulse-tools MCP servers` → TOPIC = "MCP server model context protocol"

If TOPIC mentions "skill" or "agent skill" → QUERY_TYPE = SKILLS (flag all results ⭐)

Display: `🔧 /pulse-tools — last 14 days, X-first: {TOPIC}.`

---

## Step 0.75: Generate Query Plan

```json
{
  "intent": "product",
  "freshness_mode": "strict_recent",
  "cluster_mode": "none",
  "subqueries": [
    {
      "label": "show_hn_new",
      "search_query": "Show HN {TOPIC} open source released new",
      "ranking_query": "What open-source tools, repos, MCP servers, Claude Code skills, or CLI utilities related to {TOPIC} have been newly released or shared on Hacker News Show HN in the last 2 weeks by individual builders?",
      "sources": ["x", "hackernews", "github"],
      "weight": 1.0
    },
    {
      "label": "builder_x_shares",
      "search_query": "built released open source {TOPIC} tool MCP CLI skill",
      "ranking_query": "What have individual builders or makers recently released related to {TOPIC} — tools, repos, skills, CLIs, MCP servers? Prefer posts from individual developers over corporate accounts.",
      "sources": ["x", "hackernews"],
      "weight": 0.9
    },
    {
      "label": "github_fresh",
      "search_query": "{TOPIC} open source CLI MCP skill agent harness",
      "ranking_query": "What new GitHub repos related to {TOPIC} have been created recently by individual developers or small teams? Look for tools with genuine utility even if they have few stars yet.",
      "sources": ["github", "grounding"],
      "weight": 0.7
    }
  ]
}
```

For SKILLS query type, add:
```json
{
  "label": "skills_fresh",
  "search_query": "Claude Code skill agent skill MCP plugin open source new",
  "ranking_query": "What Claude Code skills, agent skills, MCP servers, or skill harnesses have been released recently by individual builders?",
  "sources": ["x", "hackernews", "github"],
  "weight": 1.0
}
```

---

## Research Execution

**High-signal subreddits — only these five, hardcoded. No random discovery.**

These are the only subreddits where builders share MCPs, skills, CLI tools, and agent harnesses before they go mainstream:
- `LocalLLaMA` — practitioners sharing open-source LLM tools, agent frameworks, local AI stacks
- `ClaudeAI` — Claude Code skills, MCPs, Claude-specific tooling shared by builders
- `AIAgents` — specifically AI agent tooling, harnesses, frameworks — the most on-target sub
- `SideProject` — builders sharing their own newly released projects before they go viral
- `selfhosted` — self-hosted AI tools and repos that haven't gotten mainstream attention yet

**Not included** (too noisy/slow/off-topic): r/MachineLearning (academic), r/linux (general), r/programming (too broad), r/ChatGPT (consumer-focused).

**Reddit weight is LOW (0.2).** X/Twitter = 1.0. HN Show HN = 0.9. Reddit is a distant third — useful for catching niche things before they trend, but not worth heavy allocation.

**Run with 14-day lookback, X as primary, targeted subreddits only:**

```bash
"${PULSE_PYTHON}" "${SKILL_ROOT}/scripts/pulse.py" "$TOPIC" \
  --deep \
  --emit=compact \
  --save-dir=~/Documents/Pulse \
  --save-suffix=v2 \
  --lookback-days=14 \
  --subreddits="LocalLLaMA,ClaudeAI,AIAgents,SideProject,selfhosted" \
  --plan "$QUERY_PLAN_JSON" \
  ${RESOLVED_HANDLE:+--x-handle=$RESOLVED_HANDLE} \
  ${RESOLVED_REPO:+--github-repo=$RESOLVED_REPO}
```

**Read the ENTIRE output.**

---

## Judge Agent: Synthesize (RECENCY + UTILITY FIRST)

**RE-RANK the engine output — override engagement scoring:**

Rank by:
1. **Recency** — released in last 7 days is highest priority
2. **Creator signal** — solo builder or small team > corporate account
3. **Utility density** — how much of this is actually usable vs demo/boilerplate?
4. **Discovery gap** — would most builders already know this? If yes, deprioritise

**HARD EXCLUSIONS — reject these regardless of quality:**

Reject if the primary creator/source is an **incumbent organisation with massive distribution**:
- OpenAI, Anthropic, Google/DeepMind, Microsoft, Meta, AWS, Vercel, Replit
- High-follower VCs or tech executives posting tools (their audience will see it anyway)
- Official accounts of major frameworks (LangChain, LlamaIndex, Hugging Face) for their own products
- Press coverage of any of the above

**What this means in practice:** A useful repo with 16K stars built by a solo developer is HIGH signal. A hyped repo with 95K stars promoted by a YC president's personal account is LOW signal — not because of star count, but because it already has distribution. The question is: "would this person's Twitter followers see this anyway?" If yes (millions of followers), skip it.

**KEEP — genuinely useful things:**
- Open-source repos from individual builders or small teams
- Claude Code skills, agent skills, MCP servers → **mark ⭐**
- CLI tools or developer utilities with real use cases
- Agent harnesses, scaffolds, frameworks from practitioners
- Anything shared on Show HN or niche subreddits before going mainstream

**DO NOT penalise for star count in either direction.** A useful 50-star repo is better than a hyped 50K-star one. A practitioner-made 20K-star repo (like compound-engineering-plugin) is exactly what we want.

**OUTPUT:**

```
🔧 /pulse-tools — {YYYY-MM-DD} (last 14 days)

**{Tool or Skill Name}** {⭐ if skill/MCP/agent}
{What it does — one sentence.} {Why a builder making AI apps or research tools would genuinely use this — one sentence.}
Source: X — @{handle} | HN — {N}pts | GitHub — {owner/repo} | r/{sub}

[5–10 items, newest first, highest-utility first within same age]

KEY PATTERNS:
1. {Emerging category that's just starting to appear}
2. {Pattern in what individual builders are building}

---
X ({N} posts) | HN ({N} Show HNs) | GitHub ({N} repos) | r/LocalLLaMA,ClaudeAI,SideProject ({N} threads)
🔧 Raw: ~/Documents/Pulse/{slug}-raw-v2.md
---
```

---

## Audio (macOS say — free)

Write narration (~60–90s, ~150–200 words). No markdown, no URLs, no handles.

Open: *"Here's your tools pulse for [weekday]."* → 4–6 items (what + why) → if ⭐ skills: lead with them → *"That's your tools pulse. Full details in your terminal."*

```bash
DATE=$(date +%Y%m%d)
OUTFILE="/Users/ashnouruzi/Downloads/pulse-tools-${DATE}.aiff"
# Write narration to /tmp/pulse-tools-script-${DATE}.txt using Write tool, then:
say -v Samantha -r 175 -o "${OUTFILE}" -f "/tmp/pulse-tools-script-${DATE}.txt"
afplay "${OUTFILE}"
```

Confirm: `🔊 ~/Downloads/pulse-tools-{YYYYMMDD}.aiff`

---

## HTML Report

Self-contained HTML, clickable source links. Save to `~/Downloads/pulse-tools-{YYYYMMDD}.html`.

```html
<!DOCTYPE html><html lang="en"><head>
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
.tag-hn{background:#fff3e0;color:#e65100}.tag-github{background:#e8f5e9;color:#2e7d32}
.tag-x{background:#e3f2fd;color:#1565c0}.tag-web{background:#f3e5f5;color:#6a1b9a}
.tag-reddit{background:#fff8e1;color:#e65100}.tag-skills{background:#fce4ec;color:#880e4f}
.title{font-size:1rem;font-weight:600;line-height:1.35}
.desc{font-size:.875rem;color:#444;line-height:1.6;margin-bottom:.9rem}
.badge{font-size:.75rem;font-weight:700;color:#c2185b;margin-left:.3rem}
.srcs{display:flex;gap:.5rem;flex-wrap:wrap}
.src{font-size:.78rem;padding:.3rem .75rem;border-radius:6px;border:1px solid #d2d2d7;text-decoration:none;color:#0066cc;background:#fff}
.src:hover{background:#f0f5ff;border-color:#0066cc}
footer{margin-top:2rem;color:#999;font-size:.78rem;border-top:1px solid #e5e5ea;padding-top:1rem}
</style></head><body>
<h1>🔧 Pulse Tools</h1>
<div class="sub">{DATE} · {N} items · last 14 days · underrated-first</div>
{ITEMS}
<footer>github.com/Must-be-Ash/pulse · /pulse-tools v2.1.0</footer>
</body></html>
```

Each item:
```html
<div class="item">
  <div class="row">
    <span class="tag tag-{TYPE}">{LABEL}</span>
    <div class="title">{TITLE}{if_skill: <span class="badge">★ Skill</span>}</div>
  </div>
  <div class="desc">{DESCRIPTION}</div>
  <div class="srcs"><a class="src" href="{URL}" target="_blank">{SOURCE_LABEL}</a></div>
</div>
```

```bash
open "/Users/ashnouruzi/Downloads/pulse-tools-$(date +%Y%m%d).html"
```
Confirm: `📄 ~/Downloads/pulse-tools-{YYYYMMDD}.html`
