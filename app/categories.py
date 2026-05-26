"""Preset research categories with pre-baked query plans."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Category:
    id: str
    name: str
    emoji: str
    description: str
    topic: str
    lookback_days: int
    query_plan: dict
    depth: str = "deep"
    subreddits: list[str] = field(default_factory=list)
    x_list_ids: list[str] = field(default_factory=list)
    fetch_home_timeline: bool = False


CATEGORIES: list[Category] = [
    Category(
        id="repos",
        name="Open-Source Repos",
        emoji="\U0001f4e6",  # 📦
        description="Trending repos, new projects builders are starring and shipping",
        topic="trending open source repos new projects builders are using shipped",
        lookback_days=14,
        depth="exhaustive",
        x_list_ids=[
            "1953536336675365173",
            "1539497752140206080",
            "1526716323316875265",
            "89817980",
            "15526",
            "2058775422171803800",
        ],
        query_plan={
            "intent": "product",
            "freshness_mode": "strict_recent",
            "cluster_mode": "none",
            "subqueries": [
                {
                    "label": "open_sourced",
                    "search_query": "open sourced",
                    "ranking_query": "What projects were just open-sourced by builders?",
                    "sources": ["x", "github"],
                    "weight": 1.0,
                },
                {
                    "label": "github_repo_new",
                    "search_query": "new GitHub repo",
                    "ranking_query": "What new GitHub repositories are builders sharing and starring?",
                    "sources": ["x", "github"],
                    "weight": 1.0,
                },
                {
                    "label": "show_hn",
                    "search_query": "Show HN",
                    "ranking_query": "What new projects are being shared on Show HN?",
                    "sources": ["hackernews"],
                    "weight": 0.9,
                },
                {
                    "label": "just_released",
                    "search_query": "just released open source",
                    "ranking_query": "What open-source projects were just released?",
                    "sources": ["x", "github"],
                    "weight": 0.9,
                },
                {
                    "label": "ai_repo",
                    "search_query": "AI open source repo",
                    "ranking_query": "What AI-related open-source repositories are getting attention?",
                    "sources": ["github", "hackernews", "grounding"],
                    "weight": 0.8,
                },
                {
                    "label": "developer_tool_repo",
                    "search_query": "developer tool open source",
                    "ranking_query": "What developer tools are being open-sourced or gaining traction on GitHub?",
                    "sources": ["github", "grounding"],
                    "weight": 0.8,
                },
            ],
        },
    ),
    Category(
        id="cli",
        name="CLI Tools",
        emoji="\U0001f527",  # 🔧
        description="New CLI tools, terminal utilities, developer command-line tools",
        topic="new CLI tools terminal utilities developer command line tools",
        lookback_days=14,
        depth="exhaustive",
        x_list_ids=[
            "1953536336675365173",
            "1539497752140206080",
            "1526716323316875265",
            "89817980",
            "15526",
            "2058775422171803800",
        ],
        query_plan={
            "intent": "product",
            "freshness_mode": "strict_recent",
            "cluster_mode": "none",
            "subqueries": [
                {
                    "label": "cli_new",
                    "search_query": "CLI tool",
                    "ranking_query": "What new CLI tools or terminal utilities have been released recently?",
                    "sources": ["x", "github", "hackernews"],
                    "weight": 1.0,
                },
                {
                    "label": "terminal_tool",
                    "search_query": "terminal tool",
                    "ranking_query": "What terminal tools and utilities are builders using or recommending?",
                    "sources": ["x", "github"],
                    "weight": 0.9,
                },
                {
                    "label": "command_line",
                    "search_query": "command line tool",
                    "ranking_query": "What command-line tools are getting traction among developers?",
                    "sources": ["x", "github", "hackernews"],
                    "weight": 0.8,
                },
                {
                    "label": "show_hn_cli",
                    "search_query": "Show HN CLI",
                    "ranking_query": "What CLI tools are being shared on Show HN?",
                    "sources": ["hackernews"],
                    "weight": 0.9,
                },
                {
                    "label": "dev_cli",
                    "search_query": "developer CLI shipped",
                    "ranking_query": "What developer CLI tools were just shipped or released?",
                    "sources": ["x", "github"],
                    "weight": 0.8,
                },
            ],
        },
    ),
    Category(
        id="skills",
        name="Skills & MCP Servers",
        emoji="\u2b50",  # ⭐
        description="Claude Code skills, MCP servers, agent tools and harnesses",
        topic="Claude Code skill MCP server agent tool harness plugin",
        lookback_days=14,
        depth="exhaustive",
        x_list_ids=[
            "1953536336675365173",
            "1539497752140206080",
            "1526716323316875265",
            "89817980",
            "15526",
            "2058775422171803800",
        ],
        subreddits=["LocalLLaMA", "ClaudeAI", "AIAgents", "SideProject", "selfhosted"],
        query_plan={
            "intent": "product",
            "freshness_mode": "strict_recent",
            "cluster_mode": "none",
            "subqueries": [
                {
                    "label": "show_hn_new",
                    "search_query": "Show HN Claude Code skill MCP server open source released new",
                    "ranking_query": "What open-source tools, repos, MCP servers, Claude Code skills, or agent harnesses have been newly released or shared on Hacker News Show HN in the last 2 weeks by individual builders?",
                    "sources": ["x", "hackernews", "github"],
                    "weight": 1.0,
                },
                {
                    "label": "builder_x_shares",
                    "search_query": "built released open source MCP skill CLI agent tool",
                    "ranking_query": "What have individual builders or makers recently released — MCP servers, Claude Code skills, agent tools, or harnesses? Prefer posts from individual developers over corporate accounts.",
                    "sources": ["x", "hackernews"],
                    "weight": 0.9,
                },
                {
                    "label": "github_fresh",
                    "search_query": "MCP server Claude skill agent harness open source",
                    "ranking_query": "What new GitHub repos for MCP servers, Claude Code skills, or agent harnesses have been created recently by individual developers or small teams?",
                    "sources": ["github", "grounding"],
                    "weight": 0.7,
                },
                {
                    "label": "skills_fresh",
                    "search_query": "Claude Code skill agent skill MCP plugin open source new",
                    "ranking_query": "What Claude Code skills, agent skills, MCP servers, or skill harnesses have been released recently by individual builders?",
                    "sources": ["x", "hackernews", "github"],
                    "weight": 1.0,
                },
            ],
        },
    ),
    Category(
        id="tech",
        name="Tech & AI Trends",
        emoji="\U0001f4e1",  # 📡
        description="Narratives, debates, and zeitgeist — where the tech/AI space is heading",
        topic="AI technology trends narrative debate zeitgeist builder community",
        lookback_days=3,
        depth="exhaustive",
        x_list_ids=[
            "1953536336675365173",
            "1539497752140206080",
            "1526716323316875265",
            "89817980",
            "15526",
            "2058775422171803800",
        ],
        fetch_home_timeline=True,
        # No keyword search subqueries — trends pipeline pulls lists/timeline directly.
        # The query_plan is a stub; _run_trends_pipeline skips pipeline.run() entirely.
        query_plan={
            "intent": "breaking_news",
            "freshness_mode": "strict_recent",
            "cluster_mode": "story",
            "subqueries": [],
        },
    ),
    Category(
        id="news",
        name="World News",
        emoji="\U0001f30d",  # 🌍
        description="Science, space, health breakthroughs + high-impact economy + major events",
        topic="science discovery breakthrough space health economy disaster major event",
        lookback_days=1,
        depth="deep",
        query_plan={
            "intent": "breaking_news",
            "freshness_mode": "strict_recent",
            "cluster_mode": "story",
            "subqueries": [
                {
                    "label": "science_space",
                    "search_query": "science discovery breakthrough research space",
                    "ranking_query": "What scientific discoveries, space missions, or research breakthroughs were announced today? Look for genuinely significant findings published in major outlets.",
                    "sources": ["grounding"],
                    "weight": 1.0,
                },
                {
                    "label": "health_medicine",
                    "search_query": "health medicine breakthrough drug treatment",
                    "ranking_query": "What health or medical breakthroughs were announced today? Drug approvals, treatment advances, disease research findings.",
                    "sources": ["grounding"],
                    "weight": 1.0,
                },
                {
                    "label": "economy_business",
                    "search_query": "economy central bank recession market crash major",
                    "ranking_query": "What major economic events happened today? Central bank decisions, recession signals, market crashes, major corporate failures affecting large populations.",
                    "sources": ["grounding"],
                    "weight": 0.8,
                },
                {
                    "label": "disasters_events",
                    "search_query": "earthquake disaster explosion major accident casualties",
                    "ranking_query": "What major disasters or unmissable events happened today? Only events with significant casualties or global significance.",
                    "sources": ["grounding"],
                    "weight": 0.6,
                },
                {
                    "label": "technology_breakthroughs",
                    "search_query": "technology breakthrough innovation scientific progress",
                    "ranking_query": "What genuine technology breakthroughs represent real scientific progress today? Not product launches — actual advances in capability.",
                    "sources": ["grounding"],
                    "weight": 0.9,
                },
            ],
        },
    ),
]


def all_categories() -> list[Category]:
    return CATEGORIES


def get_category(category_id: str) -> Category | None:
    for cat in CATEGORIES:
        if cat.id == category_id:
            return cat
    return None
