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
        query_plan={
            "intent": "product",
            "freshness_mode": "strict_recent",
            "cluster_mode": "none",
            "subqueries": [
                {
                    "label": "github_trending",
                    "search_query": "trending open source repo builders starring forking",
                    "ranking_query": "What open-source repositories are builders actively starring, forking, and using this week? Look for repos with genuine organic traction from independent developers.",
                    "sources": ["github", "hackernews", "grounding"],
                    "weight": 1.0,
                },
                {
                    "label": "show_hn_repos",
                    "search_query": "Show HN open source new repo released project",
                    "ranking_query": "What new open-source projects have been shared on Show HN recently by individual builders? Look for genuinely useful repos, not corporate launches.",
                    "sources": ["hackernews", "github"],
                    "weight": 0.9,
                },
                {
                    "label": "builder_recommendations",
                    "search_query": "open source repo recommend using shipped built tool",
                    "ranking_query": "What open-source repos are builders recommending to each other on X? Look for organic sharing from individual developer accounts.",
                    "sources": ["x", "hackernews"],
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
        query_plan={
            "intent": "product",
            "freshness_mode": "strict_recent",
            "cluster_mode": "none",
            "subqueries": [
                {
                    "label": "new_cli_tools",
                    "search_query": "new CLI tool terminal utility command line released",
                    "ranking_query": "What new CLI tools, terminal utilities, or command-line developer tools have been released recently by individual builders?",
                    "sources": ["x", "hackernews", "github"],
                    "weight": 1.0,
                },
                {
                    "label": "cli_trending",
                    "search_query": "CLI tool trending developer terminal popular",
                    "ranking_query": "What CLI tools or terminal utilities are trending among developers? What are they actively installing and recommending?",
                    "sources": ["hackernews", "github", "grounding"],
                    "weight": 0.9,
                },
                {
                    "label": "cli_recommendations",
                    "search_query": "best CLI tool developer recommend replaced switched using",
                    "ranking_query": "What CLI tools are builders switching to or recommending as replacements for existing tools? What terminal utilities are getting organic buzz?",
                    "sources": ["x", "hackernews"],
                    "weight": 0.7,
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
        description="What builders are actually adopting and excited about today",
        topic="developer tools AI agent building startup trend adoption",
        lookback_days=3,
        depth="exhaustive",
        x_list_ids=[
            "1953536336675365173",
            "1539497752140206080",
            "2058775422171803800",
        ],
        fetch_home_timeline=True,
        query_plan={
            "intent": "breaking_news",
            "freshness_mode": "strict_recent",
            "cluster_mode": "story",
            "subqueries": [
                # -- X-native keyword searches (short, specific, diverse) --
                {
                    "label": "just_shipped",
                    "search_query": "just shipped AI",
                    "ranking_query": "What AI tools, products, or features did builders just ship or launch?",
                    "sources": ["x"],
                    "weight": 1.0,
                },
                {
                    "label": "just_launched",
                    "search_query": "just launched AI tool",
                    "ranking_query": "What new AI tools or products just launched?",
                    "sources": ["x"],
                    "weight": 1.0,
                },
                {
                    "label": "open_sourced",
                    "search_query": "open sourced AI",
                    "ranking_query": "What AI projects or tools were just open-sourced?",
                    "sources": ["x", "github"],
                    "weight": 1.0,
                },
                {
                    "label": "ai_agent",
                    "search_query": "AI agent",
                    "ranking_query": "What's happening with AI agents — new frameworks, tools, launches, discussions?",
                    "sources": ["x", "hackernews"],
                    "weight": 0.9,
                },
                {
                    "label": "mcp_server",
                    "search_query": "MCP server",
                    "ranking_query": "What new MCP servers or MCP tools are being built and shared?",
                    "sources": ["x", "github"],
                    "weight": 0.9,
                },
                {
                    "label": "claude_code",
                    "search_query": "Claude Code",
                    "ranking_query": "What are builders doing with Claude Code? New skills, workflows, tips?",
                    "sources": ["x", "hackernews"],
                    "weight": 0.9,
                },
                {
                    "label": "cursor_ai",
                    "search_query": "Cursor AI",
                    "ranking_query": "What's new with Cursor? Updates, tips, workflows builders are sharing?",
                    "sources": ["x"],
                    "weight": 0.8,
                },
                {
                    "label": "ai_coding",
                    "search_query": "AI coding tool",
                    "ranking_query": "What AI coding tools are builders discussing, comparing, or switching to?",
                    "sources": ["x", "hackernews"],
                    "weight": 0.8,
                },
                {
                    "label": "dev_tool_launch",
                    "search_query": "developer tool launched",
                    "ranking_query": "What developer tools just launched or were announced?",
                    "sources": ["x", "grounding"],
                    "weight": 0.8,
                },
                {
                    "label": "cli_new",
                    "search_query": "CLI tool released",
                    "ranking_query": "What new CLI tools were just released?",
                    "sources": ["x", "github"],
                    "weight": 0.7,
                },
                {
                    "label": "show_hn",
                    "search_query": "Show HN AI",
                    "ranking_query": "What AI projects are being shared on Show HN?",
                    "sources": ["hackernews"],
                    "weight": 1.0,
                },
                {
                    "label": "show_hn_tools",
                    "search_query": "Show HN tool",
                    "ranking_query": "What new tools are being shared on Show HN?",
                    "sources": ["hackernews"],
                    "weight": 0.9,
                },
                {
                    "label": "ai_app_built",
                    "search_query": "built with AI",
                    "ranking_query": "What are people building with AI? What apps and tools are being created?",
                    "sources": ["x"],
                    "weight": 0.7,
                },
                {
                    "label": "yc_launch",
                    "search_query": "YC launch AI",
                    "ranking_query": "What YC startups launched recently in AI or developer tools?",
                    "sources": ["x", "hackernews", "grounding"],
                    "weight": 0.8,
                },
                {
                    "label": "github_trending",
                    "search_query": "trending GitHub AI",
                    "ranking_query": "What AI repos are trending on GitHub?",
                    "sources": ["github", "x"],
                    "weight": 0.8,
                },
                {
                    "label": "ai_workflow",
                    "search_query": "AI workflow automation",
                    "ranking_query": "What AI-powered workflows or automation tools are builders adopting?",
                    "sources": ["x", "grounding"],
                    "weight": 0.7,
                },
                # -- Grounding/web for broader coverage --
                {
                    "label": "ai_news_web",
                    "search_query": "AI developer tools news today",
                    "ranking_query": "What are the biggest AI and developer tools news stories today?",
                    "sources": ["grounding"],
                    "weight": 0.9,
                },
                {
                    "label": "ai_startup_news",
                    "search_query": "AI startup launch funding announcement",
                    "ranking_query": "What AI startups announced funding or product launches?",
                    "sources": ["grounding"],
                    "weight": 0.7,
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
