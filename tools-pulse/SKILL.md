---
name: tools-pulse
version: "1.0.0"
description: "Twitter-first discovery of open-source tools, MCPs, Claude Code skills ⭐, CLI utilities, GitHub repos, and plugins for builders. Surfaces concrete installable things — not news, not opinions."
argument-hint: 'tools-pulse, tools-pulse MCP servers, tools-pulse Claude Code skills, tools-pulse CLI'
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
        - HERMES_TWEET_API_KEY
        - XQUIK_API_KEY
        - XQUIK_BASE_URL
        - LAST30DAYS_X_BACKEND
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
      - firecrawl
---

# tools-pulse v1.0.0: Builder Tool Discovery

> **Source weights:** Twitter/X (primary) → HN Show HN → GitHub → Exa web → Reddit (light). Surfaces only concrete installable things — repos, MCPs, Claude Code skills ⭐, CLIs, plugins. Not news. Not opinions.

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
  echo "ERROR: tools-pulse requires Python 3.12+. Install python3.12 or python3.13 and rerun." >&2
  exit 1
fi
```

Find SKILL_ROOT:
```bash
for dir in \
  "." \
  "${CLAUDE_PLUGIN_ROOT:-}" \
  "$HOME/pulse" \
  "$HOME/.claude/skills/tools-pulse" \
  "$HOME/.claude/skills/tech-pulse"; do
  [ -n "$dir" ] && [ -f "$dir/scripts/pulse.py" ] && SKILL_ROOT="$dir" && break
done

if [ -z "${SKILL_ROOT:-}" ]; then
  echo "ERROR: Could not find scripts/pulse.py" >&2
  exit 1
fi
```

## Step 0: First-Run Setup

Detect first run: check if `~/.config/pulse/.env` exists and contains `SETUP_COMPLETE=true`. If it does NOT, this is a first run. Proceed silently on subsequent runs.

**When first run is detected, display:**

```
🔧 Welcome to /tools-pulse!

I search Twitter/X, Hacker News Show HN, GitHub, and the web for new open-source
tools, MCPs, Claude Code skills, CLI utilities, and plugins — the concrete
installable things builders share.

Source unlock:
- Zero config: HN, GitHub (if gh CLI installed), Web (if Exa/Brave/Serper key set)
- + X (primary source): AUTH_TOKEN + CT0 from x.com cookies, XAI_API_KEY, or HERMES_TWEET_API_KEY with `LAST30DAYS_X_BACKEND=hermes_tweet`
- + Better web search: EXA_API_KEY / BRAVE_API_KEY / SERPER_API_KEY
- + Deep scraping: FIRECRAWL_API_KEY (for release notes, README deep dives)
```

Then offer setup:
- "Auto setup (~30 seconds) — scans browser cookies for X"
- "Manual setup — I'll configure keys myself"
- "Skip — use HN, GitHub, and web only"

On auto setup: run `"${PULSE_PYTHON}" "${SKILL_ROOT}/scripts/pulse.py" setup` and show results.

On manual: display the config file path: `~/.config/pulse/.env` with key names.

Write `SETUP_COMPLETE=true` to `~/.config/pulse/.env` when done.

**Skip ALL of Step 0 if SETUP_COMPLETE=true already exists. No status message.**

---

## CRITICAL: Parse User Intent

Before doing anything, parse the user's input:

1. **TOPIC**: What they want to find (e.g., "Claude Code skills", "MCP servers", "CLI tools for AI agents")
2. **QUERY_TYPE**:
   - **SKILLS** — "Claude Code skills", "agent skills", "what skills exist" → flag all results with ⭐, prioritise skill repos
   - **RECOMMENDATIONS** — "best X", "top X", "what should I use for X" → return a ranked LIST of specific tools
   - **GENERAL** — default → broad discovery of tools and repos on this topic

Store: `TOPIC`, `QUERY_TYPE`

Display: `/tools-pulse — searching X, HN, GitHub, Exa for {TOPIC}.`

---

## Step 0.5: Pre-Research Intelligence

If TOPIC could be a GitHub repo or project:
```
WebSearch("{TOPIC} github repo site:github.com")
```
Extract `owner/repo` and pass as `--github-repo={owner/repo}`.

If TOPIC could have an X/Twitter account (tool, project, creator):
```
WebSearch("{TOPIC} X twitter handle site:x.com")
```
Extract handle and pass as `--x-handle={handle}`.

---

## Step 0.75: Generate Query Plan

Generate a `--plan` JSON focused on builder tool discovery:

```json
{
  "intent": "product",
  "freshness_mode": "strict_recent",
  "cluster_mode": "none",
  "subqueries": [
    {
      "label": "tools_primary",
      "search_query": "{TOPIC} open source tool launch release",
      "ranking_query": "What new open-source tools, MCPs, CLI utilities, or Claude Code skills related to {TOPIC} have been shared or released recently?",
      "sources": ["x", "hackernews", "github", "grounding"],
      "weight": 1.0
    },
    {
      "label": "skills_mcp",
      "search_query": "Claude Code skill MCP server agent plugin {TOPIC}",
      "ranking_query": "What new Claude Code skills, agent skills, MCP servers, or plugins related to {TOPIC} are being discussed or released?",
      "sources": ["x", "hackernews", "grounding"],
      "weight": 0.8
    }
  ]
}
```

For SKILLS query type, add a third subquery:
```json
{
  "label": "skills_discovery",
  "search_query": "Claude Code skill skill-creator agent harness open source",
  "ranking_query": "What new Claude Code skills, OpenClaw skills, or agent skill frameworks have been released?",
  "sources": ["x", "hackernews", "github"],
  "weight": 0.9
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
  --x-handle={RESOLVED_HANDLE_IF_ANY} \
  --github-repo={RESOLVED_REPO_IF_ANY}
```

**Omit `--x-handle` and `--github-repo` if not resolved.**

**Read the ENTIRE output.** It contains items from X, HN, GitHub, web. Each item has a source tag.

---

## Judge Agent: Synthesize

**QUALITY FILTER — KEEP only items that are:**
- An open-source repo, library, framework, or tool (free to use)
- A Claude Code skill, agent skill, OpenClaw skill, or MCP server → **mark with ⭐**
- A CLI tool or developer utility
- A plugin, extension, or harness for an existing tool
- Something a builder can install or run today

**REJECT:**
- News about a company or product (not the tool itself)
- Opinion, blog post, or tutorial without a direct tool link
- Corporate announcements (OpenAI, Google, Microsoft, Vercel, AWS) unless they open-sourced something new
- Crypto tools, NFT tools, DeFi anything

**SOURCE CITATION PRIORITY:**
1. X @handles — "per @handle"
2. HN Show HN — "per HN"
3. GitHub stars — "per GitHub"
4. Web — only when X/HN/GitHub don't cover it

**For SKILLS queries:** Surface only Claude Code skills, agent skills, MCP servers, and skill registries. Mark every single one with ⭐.

**Output format:**

```
🔧 What I found:

**{Tool or Skill Name}** {⭐ if it's a Claude Code skill, agent skill, or MCP}
{What it is in one sentence. Why a builder should care in one sentence.}
Source: @{handle} ({N} likes) | HN — {N}pts | GitHub — {owner/repo}

[repeat for 5–10 items, ranked by signal strength]

KEY PATTERNS:
1. [Pattern or trend across the results]
2. [Pattern]

---
✅ Sources scanned:
├─ 🔵 X: {N} posts │ {N} likes
├─ 🟡 HN: {N} Show HN stories │ {N} points
├─ 🐙 GitHub: {N} repos
├─ 🌐 Web: {N} pages — {source names}
└─ 📎 Raw saved to ~/Documents/Pulse/{slug}-raw.md
---
```

**⭐ flag is the most important marker in this skill.** Claude Code skills, agent skills, and MCP servers are what builders track. Never miss one.

**CRITICAL RULE: No raw URLs in output.** Source name or handle only.

---

## WAIT FOR USER RESPONSE

After displaying the output, stop and wait. Do NOT run new searches unless the user asks.

---

## WHEN USER RESPONDS

- **Question about a tool** → Answer from research findings
- **"Tell me more about X"** → Elaborate using research data
- **"Is X open source?"** → Answer from what you found
- **"Compare X and Y"** → Compare from research context

Only search again if the user asks about a completely different topic.

---

## Security & Permissions

- Reads X/Twitter via AUTH_TOKEN/CT0 cookies, XAI_API_KEY, or Hermes Tweet with HERMES_TWEET_API_KEY
- Reads HN via Algolia API (free, no auth)
- Reads GitHub via public API or gh CLI
- Reads web via Exa/Brave/Serper key
- Optionally scrapes URLs via FIRECRAWL_API_KEY
- Saves research to `~/Documents/Pulse/`
- Config at `~/.config/pulse/.env`

Does NOT post, like, or modify content on any platform.
