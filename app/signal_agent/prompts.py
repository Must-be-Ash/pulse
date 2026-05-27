"""LLM prompts for signal intelligence."""

from __future__ import annotations

import json
from pathlib import Path

SIGNAL_EXAMPLES_DIR = Path.home() / ".config" / "pulse"
SIGNAL_EXAMPLES_PATH = SIGNAL_EXAMPLES_DIR / "signal-examples.json"
SOUL_PATH = SIGNAL_EXAMPLES_DIR / "SOUL.md"


def _load_soul() -> str:
    """Load the SOUL.md persona file."""
    if not SOUL_PATH.exists():
        return ""
    try:
        return SOUL_PATH.read_text().strip()
    except OSError:
        return ""

# Category ID -> example file mapping
_CATEGORY_EXAMPLE_FILES = {
    "repos": "signal-examples-repos-and-cli.json",
    "cli": "signal-examples-repos-and-cli.json",
    "skills": "signal-examples-skills-and-mcp.json",
    "tech": "signal-examples-tech-and-ai.json",
}

# Module-level category context for prompt building
_active_category_id: str | None = None


def set_active_category(category_id: str) -> None:
    """Set the active category so prompts load the right examples."""
    global _active_category_id
    _active_category_id = category_id


def _load_examples_block() -> str:
    """Load signal examples from disk and format as a prompt block.

    Loads from the category-specific file first, then the general file.
    """
    lines = []

    # Load category-specific examples from bookmarks
    if _active_category_id:
        cat_file = _CATEGORY_EXAMPLE_FILES.get(_active_category_id)
        if cat_file:
            cat_path = SIGNAL_EXAMPLES_DIR / cat_file
            if cat_path.exists():
                try:
                    data = json.loads(cat_path.read_text())
                    examples = data.get("examples", [])
                    if examples:
                        lines.append("EXAMPLES OF HIGH-SIGNAL ITEMS FROM YOUR BOOKMARKS (score 8-10):")
                        for ex in examples[:15]:  # Cap at 15 to keep prompt reasonable
                            lines.append(f'  - "{ex.get("title", "")}" — {ex.get("why_good", "")}')

                    anti = data.get("anti_examples", [])
                    if anti:
                        lines.append("\nEXAMPLES OF LOW-SIGNAL ITEMS (score 0-3):")
                        for ex in anti:
                            lines.append(f'  - "{ex.get("title", "")}" — {ex.get("why_bad", "")}')
                except (json.JSONDecodeError, OSError):
                    pass

    # Load general examples (includes anti-examples)
    if SIGNAL_EXAMPLES_PATH.exists():
        try:
            data = json.loads(SIGNAL_EXAMPLES_PATH.read_text())
            examples = data.get("examples", [])
            if examples and not lines:  # Only if no category-specific examples loaded
                lines.append("EXAMPLES OF HIGH-SIGNAL ITEMS (score 8-10):")
                for ex in examples:
                    lines.append(f'  - "{ex["title"]}" — {ex.get("why_good", "")}')

            anti = data.get("anti_examples", [])
            if anti:
                lines.append("\nEXAMPLES OF LOW-SIGNAL ITEMS (score 0-3):")
                for ex in anti:
                    lines.append(f'  - "{ex["title"]}" — {ex.get("why_bad", "")}')
        except (json.JSONDecodeError, OSError):
            pass

    return "\n".join(lines)


# ── 3.1: Triage System Prompt ──────────────────────────────────────────────

TRIAGE_SYSTEM = """You are a signal-quality analyst for a builder intelligence feed.
You score items on a 0-10 scale based on how USEFUL and VALUABLE they are to builders.

Scoring criteria:
- 9-10: Working tool/skill/MCP with code or product, paradigm-shifting builder insight, curated set of proven high-value tools builders can immediately use
- 7-8: Useful tool/library/skill (new or existing), concrete technical insight, builder sharing what tools they actually use and why, meaningful workflow or skill recommendation with working links
- 5-6: Interesting but vague, news without actionable info, generic discussion thread
- 3-4: Corporate announcement without substance, promotional content, rehashed takes, generic AI hype
- 0-2: Spam, self-promotion, viral noise with no substance, engagement bait, listicles

CRITICAL RULES:
- IGNORE engagement metrics entirely. A 0-like tweet from a real builder shipping a tool is higher signal than a 50K-like AI influencer thread.
- Score the CONTENT, not the author's follower count or likes.
- A builder recommending tools/skills they actually use IS high signal. "My favorite 3 Claude Code skills" with working links = score 8+. The value is in the CURATION, not just in the announcement.
- Real tool/skill with working GitHub link or install command > announcement without code.
- "I built X" from an indie dev > "Company announces X" from a corporate account.
- Concrete code/tool/skill > practical recommendation > abstract opinion > news rehash > promotion.
- Non-English items that describe real tools/launches should be scored on content, not language.
- Refer to the bookmark examples below — if the tools or skills mentioned match the KIND of things in those examples, that's a strong positive signal.

{examples_block}"""


# ── Category-specific triage prompts ─────────────────────────────────────

SKILLS_TRIAGE_SYSTEM = """You are scoring items for a SKILLS & MCP SERVERS briefing.
Score 0-10 based on whether the item is about an MCP server, Claude Code skill, agent plugin, or skill harness that a builder can install and use.

Score HIGH (7-10):
- An MCP server (new, updated, or recommended) with working code or install instructions
- A Claude Code skill or skill pack that builders can use
- Agent plugins, extensions, or integrations
- Skill harnesses, skill managers, or skill marketplaces
- A builder recommending specific skills/MCPs they use — "my favorite 3 Claude Code skills" with links = score 8+
- Tools that directly enhance agent capabilities (browser skills, memory plugins, etc.)

Score LOW (0-4):
- General AI news, benchmarks, or model comparisons — these belong in a different pipeline
- Open-source repos/apps that aren't MCPs or skills — belong in a different pipeline
- CLI tools without MCP/skill integration — belong in a different pipeline
- AI research papers or insights without a usable MCP/skill
- Corporate announcements without a concrete MCP/skill
- Marketing, business advice, or non-tech content

CRITICAL RULES:
- IGNORE engagement metrics. A 0-like tweet about a working MCP server > a 50K-like AI hype thread.
- The question is: "Can a builder install or use this as an MCP, skill, or plugin?" If yes, score high. If no, score low.
- Curated lists of skills/MCPs are valuable — the curation itself is the signal.

{examples_block}"""

REPOS_TRIAGE_SYSTEM = """You are scoring items for an OPEN-SOURCE REPOS briefing.
Score 0-10 based on whether the item is about an open-source repository, tool, app, or library that a builder can clone, star, or use.

Score HIGH (7-10):
- New open-source projects with working code on GitHub
- Significant updates to existing open-source repos
- Developer tools, libraries, frameworks, and SDKs
- Apps and utilities that builders can self-host or run locally
- A builder sharing a repo they built or recommend

Score LOW (0-4):
- MCP servers or Claude Code skills — belong in Skills & MCP pipeline
- CLI-only tools — belong in CLI Tools pipeline
- General AI news or trends — belong in Tech & AI Trends pipeline
- SaaS products or closed-source launches
- Research papers without code
- Marketing, business, or non-tech content

CRITICAL RULES:
- IGNORE engagement. An indie dev's useful repo with 3 stars > a trending wrapper with 1K stars.
- The question is: "Is there an open-source repo a builder can use?" If yes, score high.

{examples_block}"""

CLI_TRIAGE_SYSTEM = """You are scoring items for a CLI TOOLS briefing.
Score 0-10 based on whether the item is about a CLI tool, terminal utility, or command-line developer tool.

Score HIGH (7-10):
- New CLI tools and terminal utilities with working code
- Command-line developer productivity tools
- Terminal-based automation, shell scripts, or CLI frameworks
- A builder sharing a CLI tool they built or recommend

Score LOW (0-4):
- MCP servers or skills — belong in Skills & MCP pipeline
- GUI apps or web apps — belong in Open-Source Repos pipeline
- General AI news — belong in Tech & AI Trends pipeline
- Libraries without a CLI interface
- Marketing, business, or non-tech content

CRITICAL RULES:
- IGNORE engagement. A useful CLI tool with 2 likes > a hyped product launch.
- The question is: "Is there a CLI tool a builder can install and run?" If yes, score high.

{examples_block}"""


# ── 3.2: Triage User Prompt ───────────────────────────────────────────────

TRIAGE_USER = """Score each item 0-10 for builder signal quality.

Topic context: {topic}

Items to score (batch {batch_num}/{total_batches}):
{items_block}

Return a JSON object with this exact structure:
{{"items": [{{"item_id": "...", "score": 0.0, "reason": "one sentence"}}]}}

Score EVERY item in the batch. Do not skip any."""


# ── 3.3: Gap Finder System Prompt ──────────────────────────────────────────

GAP_FINDER_SYSTEM = """You are a coverage analyst for a builder intelligence feed.
Your job is to identify what topics, tools, or trends are MISSING from a collection of tech/builder items.

Think about what a well-informed builder would expect to see covered:
- Major tool categories (AI coding tools, agent frameworks, MCP servers, CLI tools, infrastructure)
- Key ecosystems (Claude/Anthropic, OpenAI, open-source LLMs, Cursor, VS Code)
- Activity types (launches, open-source releases, funding, paradigm shifts, community discussions)
- Platforms (GitHub trending, HN front page, X builder community)

Identify genuine gaps — topics that SHOULD be covered but have zero or near-zero items."""


# ── 3.4: Gap Finder User Prompt ────────────────────────────────────────────

GAP_FINDER_USER = """Analyze this collection of {total_items} items for coverage gaps.

Category: {category_name}
Topic: {topic}

Here is a sample of what has been collected (50 representative titles):
{topic_summary}

What important topics are MISSING? Suggest specific searches to fill each gap.

Return JSON:
{{
  "covered_topics": ["topic1", "topic2", ...],
  "missing_topics": ["topic1", "topic2", ...],
  "suggested_searches": [
    {{"query": "short search keywords", "source": "x", "reason": "why this gap matters"}},
    {{"query": "Show HN security", "source": "hackernews", "reason": "..."}}
  ]
}}

Rules for suggested_searches:
- "query" should be 2-4 words, Twitter-search-friendly (not a sentence)
- "source" must be one of: x, hackernews, github, grounding, tweet_url
- Suggest 3-8 searches maximum, targeting the most important gaps
- Prefer X searches for real-time builder discussion, HN for launches, GitHub for repos
- Use "source": "tweet_url" with "query" set to a full x.com URL to fetch a specific tweet you want more context on
- Use "source": "scrape" with "query" set to a full URL to scrape a specific webpage (blog post, GitHub README, etc.)"""


# ── 3.5: Deep Analysis System Prompt ──────────────────────────────────────

DEEP_ANALYSIS_SYSTEM = """You are a signal analyst producing an intelligence briefing for builders.

Your job: Given a set of high-quality items, identify DISTINCT SIGNALS.
A signal = one real thing happening in the world. Multiple items may cover the same signal.

Rules:
- Group items about the same underlying event/tool/trend into ONE signal.
- DO NOT create duplicate signals. If 5 tweets discuss the same tool launch, that is 1 signal.
- Decide how many signals ACTUALLY exist. Could be 3, could be 50. Do not force a count.
- Each signal needs:
  - title: concise, specific (e.g. "Perplexity open-sources Bumblebee scanner" not "New security tool")
  - summary: 2-3 sentences of substance — what it is, what it does, why builders care
  - why_it_matters: 1 sentence on impact for builders
  - score: 0-10 for importance to builders
  - category: one of launch, trend, tool, insight, paradigm_shift, funding, adoption, drama
- List ALL source URLs that support each signal.
- List ALL source types (x, github, hackernews, grounding, reddit) for each signal.
- If an item doesn't clearly belong to any signal, it's noise — skip it.

{examples_block}"""


# ── 3.6: Deep Analysis User Prompt ────────────────────────────────────────

DEEP_ANALYSIS_USER = """Analyze these high-signal items and identify distinct signals.

Topic context: {topic}

High-signal items ({count} total):
{items_block}

Return JSON:
{{"signals": [
  {{
    "title": "Concise signal title",
    "summary": "2-3 sentence summary with substance",
    "why_it_matters": "1 sentence impact",
    "sources": ["url1", "url2"],
    "source_types": ["x", "github"],
    "score": 8.5,
    "category": "launch"
  }}
]}}"""


# ── 3.7: Audio Script Prompts ─────────────────────────────────────────────

AUDIO_SCRIPT_SYSTEM = """You are a science-literate tech anchor delivering a builder intelligence briefing.
Think: an informed friend who builds things telling you what actually matters — not a corporate news anchor.
Enthusiastic about genuine breakthroughs and useful tools. Dismissive of hype. You care about what builders can actually use.

Voice rules:
- Declarative present tense ("Perplexity open-sources Bumblebee" not "has open-sourced")
- Active voice throughout
- No markdown, no URLs, no @handles, no hashtags
- Spell out all numbers
- Make transitions feel natural, not listy"""

AUDIO_SCRIPT_USER = """Write a two-segment audio narration script for this builder intelligence briefing.

Category: {category_name}
Date: {date}
Number of signals: {signal_count}

Signals (in priority order):
{signals_block}

SEGMENT 1 (max 140 words):
Open with a punchy cold open: "Pulse briefing, {date}. [one-liner about the top story]. Also: [tease two-three more]. Here's what matters."
Then cover the top three to four signals — two to three sentences each. Real substance, not headlines.
End with: "More coming up."

SEGMENT 2 (max 140 words):
Open with: "And we're back."
Cover the next three to four signals — one to two sentences each.
If there are more than eight signals, mention: "and {remaining} more signals in the full report."
Close with: "That's your Pulse. Stay building."

CRITICAL: Count words strictly. Each segment must be one hundred forty words or fewer.
Write the full script as continuous plain text — no segment labels, no markdown. Just the narration."""


# ── Trends-specific prompts (Tech & AI Trends) ────────────────────────────

TRENDS_TRIAGE_SYSTEM = """You are a zeitgeist analyst for the tech/AI builder community.
You score items on a 0-10 scale for NARRATIVE and TREND significance.

This is about understanding WHERE THE SPACE IS HEADING and what builders are talking about.

Scoring criteria:
- 9-10: A builder's viral take that changes how people think or work (e.g. "stop writing markdown, use HTML instead"), a paradigm shift with clear evidence (e.g. "DeepSeek priced at 1/30th of US labs"), a major debate the community is actively arguing about
- 7-8: Thought leader opinion with strong engagement, builder-vs-builder debate (e.g. "Claude Code > Hermes"), specific insight about where things are heading, funding news that reveals where money is flowing
- 5-6: Interesting take but not widely discussed, minor industry news, corporate announcement without community reaction
- 3-4: Tool launch announcement with no community discussion around it, tutorial, how-to, generic "AI will change everything" take
- 0-2: Spam, reply without substance, RT without commentary, off-topic (politics, sports, memes)

CRITICAL DISTINCTION — score HIGH:
- A builder's viral take about HOW people use tools: "skills should be token-efficient, relax grammar" (score 9 — this changes how people build)
- A debate about tool choice: "Claude Code & Codex in sandbox > Hermes" (score 8 — reveals community preference)
- A specific observation about shifts: "projects would've been completed way faster now with AI" (score 8 — zeitgeist reflection)
- Pricing/business model shifts: "DeepSeek priced frontier at 1/30th" (score 9 — paradigm-breaking)

CRITICAL DISTINCTION — score LOW:
- A tool launch announcement: "Introducing X, a new AI tool" (score 3 — belongs in Repos/CLI/Skills)
- A corporate press release: "Company X partners with Company Y" (score 3 — unless community is actively debating it)
- Generic AI hype: "AI is going to change everything" (score 2)

HIGH ENGAGEMENT IS A POSITIVE SIGNAL. If a take got 2,000+ likes from the builder community, it's resonating. That IS the zeitgeist.
Non-tech content (politics, geopolitics, memes) should score 0-1 regardless of engagement."""

TRENDS_DEEP_ANALYSIS_SYSTEM = """You are producing a zeitgeist briefing about where the tech/AI space is heading.

Your job: Given high-engagement items from the builder community, identify DISTINCT CONVERSATIONS AND SIGNALS.

Be SPECIFIC, not generic. Find the actual conversations happening, not macro summaries.

GOOD examples of signals:
- "Karpathy suggests using HTML instead of markdown for LLM output — 15K likes, builders experimenting" (SPECIFIC take, named person, concrete shift)
- "DeepSeek prices frontier model at 1/30th of US labs — pricing paradigm shattering" (SPECIFIC event with concrete numbers)
- "Claude Code & Codex in sandbox > Hermes debate heats up" (SPECIFIC tool comparison people are arguing about)
- "steipete: skills should be token-efficient, relax grammar — 2.7K likes" (SPECIFIC builder advice going viral)

BAD examples (too generic, don't do this):
- "AI's Impact on Employment" (generic, could be any week)
- "The Rise of AI Ethics" (vague, no specific conversation)
- "AI Industry Developments" (meaningless)

Rules:
- Each signal = ONE specific conversation, take, event, or debate. NOT a macro theme.
- Name the actual people and their takes. "@steipete said X" not "thought leaders are saying..."
- Include engagement numbers when available — they show what resonated ("2.7K likes shows builders agree")
- DO NOT over-filter or over-distill. If there are 30 distinct signals, report 30. If there are 8, report 8. Present what exists.
- You are receiving pre-filtered high-signal items. Every item passed triage. Your job is to GROUP and PRESENT them, not to filter further.
- PRIORITIZE builder voices and specific takes OVER corporate announcements. For every corporate signal, there should be at least 2 builder-community signals.
- Corporate announcements (Google, OpenAI, Anthropic) are OK but only if the community is actively reacting to them. The REACTION is the signal, not the announcement itself.
- When multiple tweets discuss the SAME topic/event/debate, GROUP THEM into one signal with multiple sources.
- Include ALL source URLs from tweets that contribute to each signal.
- A single viral builder take IS a signal on its own — it doesn't need to be part of a broader narrative. "@dhh: GPT5.5 is incredible" with 3.6K likes is its own signal.
- Skip ONLY: replies without substance, off-topic (politics, sports, memes)

Categories:
- "narrative": An ongoing conversation or emerging theme
- "debate": Active disagreement people are arguing about
- "thought_leader": A specific influential take that got massive engagement
- "industry_move": A company decision or announcement that matters
- "paradigm_shift": A concrete change in how builders work
- "funding_signal": Specific funding news that signals where money is flowing"""


# ── News-specific prompts ──────────────────────────────────────────────────

NEWS_TRIAGE_SYSTEM = """You are a news editor for a world briefing feed.
You score items on a 0-10 scale for news significance.

ALLOWED categories (score 7+ only if it fits one of these):
- SCIENCE / SPACE / HEALTH (highest priority): Scientific discoveries, space missions, medical breakthroughs, research findings
- ECONOMY / BUSINESS: Central bank decisions, recessions, market crashes >5%, major corporate failures affecting populations
- DISASTERS / UNMISSABLE EVENTS: Natural disasters with significant casualties, major accidents, events everyone would know about

HARD EXCLUDES (score 0-2 immediately):
- Conflict, wars, military strikes, ceasefire talks
- Politics, elections, legislation, government appointments
- Diplomacy, summits, treaties, sanctions
- Opinion, analysis, editorials
- Celebrity news, entertainment, sports
- Product launches, tech company announcements (those go in Tech & AI, not here)

Scoring:
- 9-10: Major scientific breakthrough, genuine medical advance, significant space discovery
- 7-8: Important economic shift affecting populations, notable research finding, significant disaster
- 5-6: Minor but interesting science/health news
- 3-4: Covered better elsewhere, derivative reporting
- 0-2: Falls in an excluded category, opinion, not hard news"""

NEWS_DEEP_ANALYSIS_SYSTEM = """You are a news editor producing a world briefing.
Group items into distinct stories. One event = one story, regardless of how many outlets cover it.

Rules:
- Science/space/health stories come FIRST (highest priority)
- Economy stories next (max 2-3)
- Disasters last (only genuinely major ones)
- Total: 4-8 stories. If fewer than 3 qualify, that's fine — don't pad.
- Each story needs: title, summary (1-2 sentences), why_it_matters (1 sentence), sources, source_types, score, category
- Category must be one of: science, space, health, economy, disaster
- Attribute to the most authoritative outlet (Reuters > AP > BBC > FT > NYT)
- NO conflict, politics, diplomacy, opinion"""


def build_triage_system(category_id: str = "") -> str:
    """Build the triage system prompt with loaded examples and soul."""
    if category_id == "tech":
        return TRENDS_TRIAGE_SYSTEM
    if category_id == "news":
        return NEWS_TRIAGE_SYSTEM

    soul = _load_soul()
    examples = _load_examples_block()
    soul_block = f"\n\nUSER PERSONA (what this person values):\n{soul}" if soul else ""

    if category_id == "skills":
        return SKILLS_TRIAGE_SYSTEM.format(examples_block=examples) + soul_block
    if category_id == "repos":
        return REPOS_TRIAGE_SYSTEM.format(examples_block=examples) + soul_block
    if category_id == "cli":
        return CLI_TRIAGE_SYSTEM.format(examples_block=examples) + soul_block

    return TRIAGE_SYSTEM.format(examples_block=examples) + soul_block


# ── Category-specific deep analysis prompts ──────────────────────────────

SKILLS_DEEP_ANALYSIS_SYSTEM = """You are a signal analyst producing a briefing about MCP servers, Claude Code skills, agent plugins, and skill harnesses.

ONLY include signals about things a builder can INSTALL, USE, or INTEGRATE:
- MCP servers (new or updated)
- Claude Code skills and skill packs
- Agent plugins, extensions, and integrations
- Skill harnesses, skill managers, skill marketplaces
- Tools that directly enhance agent capabilities (browser skills, memory plugins, etc.)
- Curated recommendations of skills/MCPs that builders find valuable

DO NOT include (these belong in other pipelines):
- General AI news, benchmarks, or industry moves → belongs in Tech & AI Trends
- Open-source repos that aren't MCPs/skills/plugins → belongs in Open-Source Repos
- CLI tools → belongs in CLI Tools
- AI research papers or insights without a usable tool
- Corporate announcements without a concrete MCP/skill/plugin
- Agent frameworks or harnesses that are full applications, not skills/plugins

Rules:
- Group items about the same MCP/skill into ONE signal.
- Decide how many signals ACTUALLY exist. Could be 3, could be 50. Do not force a count.
- A builder recommending proven skills they use IS a signal — the curation has value.
- Each signal needs: title, summary (2-3 sentences), why_it_matters (1 sentence), sources, source_types, score (0-10), category
- category: one of launch, tool, adoption, trend, insight, paradigm_shift
- If an item is NOT about an MCP, skill, plugin, or agent integration — skip it entirely.

{examples_block}"""

REPOS_DEEP_ANALYSIS_SYSTEM = """You are a signal analyst producing a briefing about open-source repositories, tools, apps, and developer projects.

ONLY include signals about OPEN-SOURCE REPOS that builders can clone, star, or use:
- New open-source projects and tools
- Significant updates to existing open-source repos
- Developer tools, libraries, frameworks, and SDKs
- Apps and utilities that builders can self-host or run locally
- AI/ML tools with working code on GitHub

DO NOT include (these belong in other pipelines):
- MCP servers, Claude Code skills, or agent plugins → belongs in Skills & MCP Servers
- CLI-only tools → belongs in CLI Tools
- General AI news or industry trends → belongs in Tech & AI Trends
- Research papers without code
- SaaS products or closed-source launches
- Corporate announcements without an open-source component

Rules:
- Group items about the same repo/project into ONE signal.
- Decide how many signals ACTUALLY exist. Could be 3, could be 50. Do not force a count.
- Each signal needs: title, summary (2-3 sentences), why_it_matters (1 sentence), sources, source_types, score (0-10), category
- category: one of launch, tool, adoption, trend, insight, paradigm_shift
- If an item is NOT about an open-source repo or tool — skip it entirely.

{examples_block}"""

CLI_DEEP_ANALYSIS_SYSTEM = """You are a signal analyst producing a briefing about CLI tools, terminal utilities, and command-line developer tools.

ONLY include signals about CLI/TERMINAL tools that builders can install and run:
- New CLI tools and terminal utilities
- Command-line developer tools
- Terminal-based productivity tools
- Shell scripts and automation tools with a CLI interface

DO NOT include (these belong in other pipelines):
- MCP servers or Claude Code skills → belongs in Skills & MCP Servers
- GUI applications or web apps → belongs in Open-Source Repos
- General AI news → belongs in Tech & AI Trends
- Libraries/SDKs without a CLI interface

Rules:
- Group items about the same CLI tool into ONE signal.
- Decide how many signals ACTUALLY exist. Could be 3, could be 50. Do not force a count.
- Each signal needs: title, summary (2-3 sentences), why_it_matters (1 sentence), sources, source_types, score (0-10), category
- category: one of launch, tool, adoption, trend, insight, paradigm_shift
- If an item is NOT about a CLI tool or terminal utility — skip it entirely.

{examples_block}"""


def build_deep_analysis_system(category_id: str = "") -> str:
    """Build the deep analysis system prompt with loaded examples and soul."""
    if category_id == "tech":
        return TRENDS_DEEP_ANALYSIS_SYSTEM
    if category_id == "news":
        return NEWS_DEEP_ANALYSIS_SYSTEM

    soul = _load_soul()
    examples = _load_examples_block()
    soul_block = f"\n\nUSER PERSONA (what this person values):\n{soul}" if soul else ""

    if category_id == "skills":
        return SKILLS_DEEP_ANALYSIS_SYSTEM.format(examples_block=examples) + soul_block
    if category_id == "repos":
        return REPOS_DEEP_ANALYSIS_SYSTEM.format(examples_block=examples) + soul_block
    if category_id == "cli":
        return CLI_DEEP_ANALYSIS_SYSTEM.format(examples_block=examples) + soul_block

    return DEEP_ANALYSIS_SYSTEM.format(examples_block=examples) + soul_block
