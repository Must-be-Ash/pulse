# pulse — Builder Intelligence Research Engine

A fork of [last30days-crypto](https://github.com/Must-be-Ash/last30days-crypto) repurposed for builder intelligence. Powers two Claude Code skills for discovering tools and trends in the dev/AI ecosystem.

## Skills

| Skill | Command | Purpose |
|---|---|---|
| 🔧 **tools-pulse** | `/tools-pulse` | Concrete installable things — open-source repos, MCPs, Claude Code skills ⭐, CLI tools, GitHub repos, plugins |
| 📡 **tech-pulse** | `/tech-pulse` | Signals & trends — YC launches, funding rounds, ecosystem shifts, technique discoveries. Ends with audio narration. |

## Sources

| Source | tools-pulse | tech-pulse |
|---|---|---|
| Twitter/X | ✅ Primary | ✅ Primary |
| Hacker News (Show HN / front page) | ✅ Primary | ✅ Secondary |
| GitHub (trending, topic search) | ✅ Primary | ✅ Trend signal |
| Exa / web search | ✅ High | ✅ High |
| Reddit | ✅ Light | ✅ Light |
| Firecrawl (URL scraper) | ✅ Optional | ✅ Optional |

Removed from original last30days-crypto: CoinGecko, Messari, LunarCrush, token extraction.

## Setup

### 1. Deploy skills

```bash
bash sync.sh
```

This copies `tools-pulse/SKILL.md` and `tech-pulse/SKILL.md` to `~/.claude/skills/`.

### 2. Configure API keys

Create `~/.config/pulse/.env`:

```bash
mkdir -p ~/.config/pulse

cat > ~/.config/pulse/.env << 'EOF'
# X/Twitter (primary source — pick one):
# AUTH_TOKEN=                 # From x.com cookies (F12 → Application → Cookies)
# CT0=                        # (required with AUTH_TOKEN)
# XAI_API_KEY=               # Alternative: api.x.ai key

# Web search (recommended — secondary source):
# EXA_API_KEY=                # 1K free/month at exa.ai
# BRAVE_API_KEY=              # 2K free/month at brave.com/search/api
# SERPER_API_KEY=             # Generous free tier at serper.dev

# Optional:
# GITHUB_TOKEN=               # GitHub API for deeper repo search
# FIRECRAWL_API_KEY=         # URL scraper for deep content (firecrawl.dev)

SETUP_COMPLETE=true
EOF
```

If you already have `~/.config/last30days-crypto/.env` with these keys, pulse reads the same keys — just add `SETUP_COMPLETE=true` to that file and pulse will pick them up automatically.

### 3. Use

```bash
/tools-pulse
/tools-pulse Claude Code skills
/tools-pulse MCP servers

/tech-pulse
/tech-pulse YC W26 launches
/tech-pulse graph RAG techniques
```

## tech-pulse audio

`/tech-pulse` generates a 1–2 minute ElevenLabs audio narration (~$0.026 USDC per run via agentcash x402) saved to `~/Downloads/tech-pulse-YYYYMMDD.mp3`. Falls back to macOS `say` if no balance. Also generates an HTML report with clickable source links.

## Python engine

The research engine lives in `scripts/pulse.py` (renamed from `last30days.py`) with the library modules in `scripts/lib/`. Requires Python 3.12+.

```bash
# Run directly
python3.12 scripts/pulse.py "Claude Code skills" --quick --emit=compact
```

## Credits

Forked from [Must-be-Ash/last30days-crypto](https://github.com/Must-be-Ash/last30days-crypto) v3.0.0.
