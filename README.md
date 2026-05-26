# Pulse — Builder Intelligence in Your Menu Bar

A macOS menu bar app that surfaces what matters in AI/tech — tools, repos, skills, trends, and world news. Click the icon, pick a category, get an HTML report and audio narration.

Built on [mvanhorn/last30days-skill](https://github.com/mvanhorn/last30days-skill).

## Categories

| Category | What it finds | Sources |
|---|---|---|
| **Open-Source Repos** | Trending repos, new projects builders are starring | X lists, GitHub, HN, Exa, Digg Stars |
| **CLI Tools** | New CLI tools, terminal utilities | X lists, GitHub, HN, Exa |
| **Skills & MCP Servers** | Claude Code skills, MCP servers, agent tools | X lists, GitHub, HN, Reddit |
| **Tech & AI Trends** | Narratives, debates, zeitgeist | X lists, X home, HN, Digg, Grok, Exa |
| **World News** | Science, health, economy, major events | Exa web search |

## Install

```bash
git clone https://github.com/Must-be-Ash/pulse ~/pulse
cd ~/pulse
pip install -e ".[app]"
```

### Optional: Digg source

```bash
npx -y @mvanhorn/printing-press-library install digg --cli-only
```

## Configure

Create `~/.config/pulse/.env`:

```bash
mkdir -p ~/.config/pulse

cat > ~/.config/pulse/.env << 'EOF'
# X/Twitter cookies (free search via Bird — primary source)
LAST30DAYS_X_BACKEND=bird
AUTH_TOKEN=           # From x.com cookies (F12 > Application > Cookies)
CT0=                  # Required with AUTH_TOKEN

# Twitter API v2 (for fetching specific tweets)
TWITTER_BEARER_TOKEN= # From developer.x.com

# LLM (required — powers the signal agent)
OPENAI_API_KEY=       # For deep analysis (gpt-4o)
CLAUDE_API_KEY=       # For triage (claude-haiku-4-5 — faster)

# Web search (recommended)
EXA_API_KEY=          # exa.ai
SERPER_API_KEY=       # serper.dev

# Optional
XAI_API_KEY=          # Grok scout for trends
GITHUB_TOKEN=         # Deeper repo search
FIRECRAWL_API_KEY=    # URL scraping for signal enrichment
ELEVENLABS_API_KEY=   # Pro audio narration (falls back to macOS say)

SETUP_COMPLETE=true
EOF
```

**Minimum to get started:** `AUTH_TOKEN` + `CT0` + `OPENAI_API_KEY`.

## Run

```bash
pulse-app
```

A satellite dish icon appears in your menu bar. Click it to see the categories. Click **Run Now** on any category.

### Auto-start on login

```bash
launchctl load ~/Library/LaunchAgents/com.pulse.app.plist
```

To stop: `launchctl unload ~/Library/LaunchAgents/com.pulse.app.plist`

## How it works

### Collection

Each category pulls data from multiple sources in parallel:
- **Bird** — searches X/Twitter using your cookies (free, no API cost)
- **X Lists** — pulls your curated Twitter lists for high-signal content
- **HackerNews** — Algolia API (free, no key needed)
- **GitHub** — issue/PR search + star enrichment
- **Exa** — neural web search for grounding
- **Digg** — curated AI news clusters and GitHub stars via `digg-pp-cli`
- **Grok** — xAI's real-time X/Twitter rundown (Tech & AI Trends only)

### Signal Agent

An LLM-powered pipeline replaces traditional keyword-based ranking:

1. **Ingest** — deduplicate, compact items, filter by engagement
2. **Gap Finder** — LLM identifies missing topics, runs targeted follow-up searches
3. **Triage** — Claude Haiku scores every item 0-10 (batched, parallel)
4. **Deep Analysis** — GPT-4o groups high-signal items into distinct signals
5. **Report** — generates HTML + ElevenLabs audio narration

The agent reads `~/.config/pulse/SOUL.md` for your preferences and `~/.config/pulse/signal-examples-*.json` for taste calibration from your bookmarks.

### Tech & AI Trends (separate pipeline)

Unlike the tool-finding categories, Tech & AI Trends uses a timeline-first approach:
- No keyword search — your X lists and home timeline ARE the data
- Engagement is a positive signal (what the community is talking about)
- LLM extracts narratives, debates, and paradigm shifts instead of tools
- HN, Digg, Grok, and web grounding complement the X timeline

## Output

Reports save to `~/Documents/Pulse/`:
- `{category}-{timestamp}.html` — self-contained HTML report
- `{category}-{timestamp}.mp3` — ElevenLabs audio narration (or `.aiff` via macOS say)
- `{category}-{timestamp}-raw.md` — full raw data dump (for tool categories)

## Taste calibration

The signal agent learns what you value from example files:

```
~/.config/pulse/
  SOUL.md                              — your preferences in plain English
  signal-examples.json                 — general good/bad examples
  signal-examples-tech-and-ai.json     — tech/AI bookmark examples
  signal-examples-repos-and-cli.json   — repo/CLI bookmark examples
  signal-examples-skills-and-mcp.json  — skills/MCP bookmark examples
  signal-examples-design.json          — design bookmark examples
```

To refresh from your Twitter bookmarks, the agent can pull and classify them automatically.

## Cost

| Component | Cost per run |
|---|---|
| Bird X search | Free (your cookies) |
| X Lists / Timeline | Free (your cookies) |
| HackerNews | Free (Algolia API) |
| Digg | Free (digg-pp-cli) |
| Claude Haiku triage | ~$0.03 |
| GPT-4o deep analysis | ~$0.15 |
| ElevenLabs audio | ~$0.03 |
| **Total per category** | **~$0.20** |

## CLI usage

The research engine also works standalone:

```bash
python3.12 scripts/pulse.py "Claude Code skills" --deep --emit=compact
```

## Credits

Built on [mvanhorn/last30days-skill](https://github.com/mvanhorn/last30days-skill). Digg source via [printing-press-library](https://github.com/mvanhorn/printing-press-library).
