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
                    "label": "just_released",
                    "search_query": "just released open source",
                    "ranking_query": "What open-source projects were just released?",
                    "sources": ["x", "github"],
                    "weight": 1.0,
                },
                {
                    "label": "introducing_oss",
                    "search_query": "introducing open source",
                    "ranking_query": "What open-source projects are being introduced or announced?",
                    "sources": ["x"],
                    "weight": 1.0,
                },
                {
                    "label": "just_shipped",
                    "search_query": "just shipped GitHub",
                    "ranking_query": "What projects have builders just shipped and shared on GitHub?",
                    "sources": ["x"],
                    "weight": 0.9,
                },
                {
                    "label": "show_hn",
                    "search_query": "Show HN",
                    "ranking_query": "What new projects are being shared on Show HN?",
                    "sources": ["hackernews"],
                    "weight": 0.9,
                },
                {
                    "label": "built_open_source",
                    "search_query": "built open source",
                    "ranking_query": "What have builders recently built and open-sourced?",
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
                    "label": "check_out_repo",
                    "search_query": "check out repo",
                    "ranking_query": "What repos are builders recommending others check out?",
                    "sources": ["x"],
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
                    "label": "introducing_cli",
                    "search_query": "introducing CLI",
                    "ranking_query": "What new CLI tools are being introduced or announced by builders?",
                    "sources": ["x", "github"],
                    "weight": 1.0,
                },
                {
                    "label": "shipped_cli",
                    "search_query": "shipped CLI terminal",
                    "ranking_query": "What CLI or terminal tools have builders just shipped?",
                    "sources": ["x"],
                    "weight": 1.0,
                },
                {
                    "label": "built_cli",
                    "search_query": "built CLI",
                    "ranking_query": "What CLI tools have builders recently built and shared?",
                    "sources": ["x", "github"],
                    "weight": 0.9,
                },
                {
                    "label": "show_hn_cli",
                    "search_query": "Show HN CLI",
                    "ranking_query": "What CLI tools are being shared on Show HN?",
                    "sources": ["hackernews"],
                    "weight": 0.9,
                },
                {
                    "label": "command_line_oss",
                    "search_query": "command line open source",
                    "ranking_query": "What command-line tools are being open-sourced?",
                    "sources": ["x", "github", "hackernews"],
                    "weight": 0.8,
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
                    "label": "introducing_mcp",
                    "search_query": "introducing MCP",
                    "ranking_query": "What MCP servers or agent tools are being introduced or announced?",
                    "sources": ["x"],
                    "weight": 1.0,
                },
                {
                    "label": "built_mcp",
                    "search_query": "built MCP server",
                    "ranking_query": "What MCP servers have builders recently built and shared?",
                    "sources": ["x", "github"],
                    "weight": 1.0,
                },
                {
                    "label": "shipped_mcp",
                    "search_query": "shipped MCP",
                    "ranking_query": "What MCP servers or skills have builders just shipped?",
                    "sources": ["x"],
                    "weight": 0.9,
                },
                {
                    "label": "mcp_open_source",
                    "search_query": "MCP open source",
                    "ranking_query": "What MCP servers or agent tools have been open-sourced?",
                    "sources": ["x", "github", "grounding"],
                    "weight": 1.0,
                },
                {
                    "label": "claude_code_skills",
                    "search_query": "Claude Code",
                    "ranking_query": "What Claude Code skills, workflows, or integrations are builders sharing?",
                    "sources": ["x"],
                    "weight": 0.9,
                },
                {
                    "label": "show_hn_mcp",
                    "search_query": "Show HN MCP",
                    "ranking_query": "What MCP servers or agent tools are being shared on Show HN?",
                    "sources": ["hackernews"],
                    "weight": 0.9,
                },
                {
                    "label": "agent_harness",
                    "search_query": "agent harness open source",
                    "ranking_query": "What agent harnesses or frameworks are being open-sourced?",
                    "sources": ["x", "github", "hackernews", "grounding"],
                    "weight": 0.8,
                },
                {
                    "label": "check_out_mcp",
                    "search_query": "check out MCP",
                    "ranking_query": "What MCP servers or skills are builders recommending others check out?",
                    "sources": ["x"],
                    "weight": 0.8,
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
        lookback_days=1,
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
