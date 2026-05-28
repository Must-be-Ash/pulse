# Pulse — Builder Intelligence in Your Menu Bar

A macOS menu bar app that surfaces what matters in AI/tech — tools, repos, skills, trends, and world news. Click the icon, pick a category, get an HTML report and audio narration.

Built on [mvanhorn/last30days-skill](https://github.com/mvanhorn/last30days-skill).

## Install

```bash
git clone https://github.com/Must-be-Ash/pulse ~/pulse && bash ~/pulse/install.sh
```

That's it. The 📡 icon appears in your menu bar.

## Add your API keys

Open `~/.config/pulse/.env` and fill in your keys:

```bash
AUTH_TOKEN=        # x.com → F12 → Application → Cookies
CT0=               # same place as AUTH_TOKEN
CLAUDE_API_KEY=    # console.anthropic.com
```

Those three are the minimum. Optional keys for richer results:

| Key | What it adds |
|---|---|
| `TWITTER_BEARER_TOKEN` | Fetching specific tweets |
| `EXA_API_KEY` | Neural web search |
| `SERPER_API_KEY` | Google search grounding |
| `XAI_API_KEY` | Grok scout for trends |
| `GITHUB_TOKEN` | Deeper repo search |
| `FIRECRAWL_API_KEY` | URL scraping |

## Use

Click 📡 in your menu bar. Pick a category. Click **Run Now**.

Pulse auto-starts on login. To restart manually: `open -a Pulse`

## Categories

| Category | What it finds | Sources |
|---|---|---|
| **Open-Source Repos** | Trending repos, new projects builders are starring | X lists, GitHub, HN, Exa, Digg Stars |
| **CLI Tools** | New CLI tools, terminal utilities | X lists, GitHub, HN, Exa |
| **Skills & MCP Servers** | Claude Code skills, MCP servers, agent tools | X lists, GitHub, HN, Reddit |
| **Tech & AI Trends** | Narratives, debates, zeitgeist | X lists, X home, HN, Digg, Grok, Exa |
| **World News** | Science, health, economy, major events | Exa web search |

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
4. **Deep Analysis** — Claude Sonnet groups high-signal items into distinct signals
5. **Report** — generates HTML + audio narration (macOS `say`)

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
- `{category}-{timestamp}.aiff` — audio narration (macOS `say`)
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

## Cost

| Component | Cost per run |
|---|---|
| Bird X search | Free (your cookies) |
| X Lists / Timeline | Free (your cookies) |
| HackerNews | Free (Algolia API) |
| Digg | Free (digg-pp-cli) |
| Claude Haiku triage | ~$0.03 |
| Claude Sonnet deep analysis | ~$0.15 |
| Audio (macOS say) | Free |
| **Total per category** | **~$0.18** |

## Uninstall

```bash
bash ~/pulse/uninstall.sh
```

## Credits

Built on [mvanhorn/last30days-skill](https://github.com/mvanhorn/last30days-skill). Digg source via [printing-press-library](https://github.com/mvanhorn/printing-press-library).
