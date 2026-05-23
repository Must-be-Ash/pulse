"""Terminal UI utilities for pulse skill."""

import sys
import time
import threading
import random
from typing import Optional

# Check if we're in a real terminal (not captured by Claude Code)
IS_TTY = sys.stderr.isatty()

# ANSI color codes
class Colors:
    PURPLE = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    RESET = '\033[0m'


BANNER = f"""{Colors.PURPLE}{Colors.BOLD}
  ██╗      █████╗ ███████╗████████╗██████╗  ██████╗ ██████╗  █████╗ ██╗   ██╗███████╗
  ██║     ██╔══██╗██╔════╝╚══██╔══╝╚════██╗██╔═████╗██╔══██╗██╔══██╗╚██╗ ██╔╝██╔════╝
  ██║     ███████║███████╗   ██║    █████╔╝██║██╔██║██║  ██║███████║ ╚████╔╝ ███████╗
  ██║     ██╔══██║╚════██║   ██║    ╚═══██╗████╔╝██║██║  ██║██╔══██║  ╚██╔╝  ╚════██║
  ███████╗██║  ██║███████║   ██║   ██████╔╝╚██████╔╝██████╔╝██║  ██║   ██║   ███████║
  ╚══════╝╚═╝  ╚═╝╚══════╝   ╚═╝   ╚═════╝  ╚═════╝ ╚═════╝ ╚═╝  ╚═╝   ╚═╝   ╚══════╝
{Colors.RESET}{Colors.DIM}  30 days of research. 30 seconds of work.{Colors.RESET}
"""

MINI_BANNER = f"""{Colors.PURPLE}{Colors.BOLD}/pulse{Colors.RESET} {Colors.DIM}· researching...{Colors.RESET}"""

# Fun status messages for each phase
X_MESSAGES = [
    "Checking what crypto Twitter is saying...",
    "Reading the timeline...",
    "Finding the hot takes...",
    "Scanning tweets and threads...",
    "Discovering trending narratives...",
    "Following the conversation...",
    "Reading between the posts...",
]

PROCESSING_MESSAGES = [
    "Crunching the data...",
    "Scoring and ranking...",
    "Finding patterns...",
    "Removing duplicates...",
    "Organizing findings...",
]

WEB_ONLY_MESSAGES = [
    "Searching the web...",
    "Finding blogs and docs...",
    "Crawling news sites...",
    "Discovering tutorials...",
]

SOURCE_COMPLETION_ORDER = [
    "x",
    "grounding",
    "reddit",
    "github",
    ]

SOURCE_COMPLETION_META = {
    "x": ("X", "post", "posts", Colors.CYAN),
    "grounding": ("Web", "result", "results", Colors.GREEN),
    "reddit": ("Reddit", "thread", "threads", Colors.YELLOW),
    "github": ("GitHub", "result", "results", Colors.PURPLE),
}


def _completion_sources(source_counts: dict[str, int], display_sources: list[str] | None) -> list[str]:
    requested = list(dict.fromkeys(display_sources or []))
    if not requested:
        requested = [source for source, count in source_counts.items() if count]
    if not requested and source_counts:
        requested = list(source_counts)

    candidate_set = set(requested) | set(source_counts)
    ordered = [source for source in SOURCE_COMPLETION_ORDER if source in candidate_set]
    for source in requested + list(source_counts):
        if source in candidate_set and source not in ordered:
            ordered.append(source)
    return ordered


def _format_completion_part(source: str, count: int, tty: bool) -> str:
    label, singular, plural, color = SOURCE_COMPLETION_META.get(
        source,
        (source.replace("_", " ").title(), "result", "results", Colors.RESET),
    )
    unit = singular if count == 1 else plural
    if tty:
        return f"{color}{label}:{Colors.RESET} {count} {unit}"
    return f"{label}: {count} {unit}"

def _build_nux_message(diag: dict = None) -> str:
    """Build conversational NUX message with dynamic source status."""
    available = set((diag or {}).get("available_sources", []))
    if diag:
        x = "✓" if "x" in available else "✗"
        web = "✓" if "grounding" in available else "✗"
        reddit = "✓" if "reddit" in available else "✗"
        hn = "✓" if "hackernews" in available else "✓"  # always available
        gh = "✓" if "github" in available else "✓"  # always available
        status_line = f"X {x}, Web {web}, Reddit {reddit}, HN {hn}, GitHub {gh}"
    else:
        status_line = "X ✗, Web ✓, Reddit ✓, HN ✓, GitHub ✓"

    return f"""
I just researched that for you. Here's what I've got right now:

{status_line}

X (AUTH_TOKEN + CT0 cookies) is the primary source. Without it the skill leans
on web grounding, HN, and GitHub. Add AUTH_TOKEN/CT0, XAI_API_KEY, or HERMES_TWEET_API_KEY to unlock X.

Some examples:
- "/tools-pulse Claude Code skills"
- "/tech-pulse YC W26 launches"
- "/tools-pulse MCP servers"
"""

# Shorter promo for single missing key
PROMO_SINGLE_KEY = {
    "x": "\n💡 Unlock X: log into x.com in Firefox or Safari, then re-run. Or add AUTH_TOKEN/CT0, XAI_API_KEY, or HERMES_TWEET_API_KEY.\n",
    "web": "\n💡 You can unlock native grounded web search with SERPER_API_KEY or EXA_API_KEY.\n",
}

# Bird auth help (for local users with vendored Bird CLI)
BIRD_AUTH_HELP = f"""
{Colors.YELLOW}Bird authentication failed.{Colors.RESET}

To fix this:
1. Add AUTH_TOKEN and CT0 to ~/.config/pulse/.env or .claude/pulse.env
2. Or set XAI_API_KEY or HERMES_TWEET_API_KEY for an alternate backend
"""

BIRD_AUTH_HELP_PLAIN = """
Bird authentication failed.

To fix this:
1. Add AUTH_TOKEN and CT0 to ~/.config/pulse/.env or .claude/pulse.env
2. Or set XAI_API_KEY or HERMES_TWEET_API_KEY for an alternate backend
"""

# Spinner frames
SPINNER_FRAMES = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
DOTS_FRAMES = ['   ', '.  ', '.. ', '...']


class Spinner:
    """Animated spinner for long-running operations."""

    def __init__(self, message: str = "Working", color: str = Colors.CYAN, quiet: bool = False):
        self.message = message
        self.color = color
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.frame_idx = 0
        self.shown_static = False
        self.quiet = quiet  # Suppress non-TTY start message (still shows ✓ completion)

    def _spin(self):
        while self.running:
            frame = SPINNER_FRAMES[self.frame_idx % len(SPINNER_FRAMES)]
            sys.stderr.write(f"\r{self.color}{frame}{Colors.RESET} {self.message}  ")
            sys.stderr.flush()
            self.frame_idx += 1
            time.sleep(0.08)

    def start(self):
        self.running = True
        if IS_TTY:
            # Real terminal - animate
            self.thread = threading.Thread(target=self._spin, daemon=True)
            self.thread.start()
        else:
            # Not a TTY (Claude Code) - just print once
            if not self.shown_static and not self.quiet:
                sys.stderr.write(f"⏳ {self.message}\n")
                sys.stderr.flush()
                self.shown_static = True

    def update(self, message: str):
        self.message = message
        if not IS_TTY and not self.shown_static:
            # Print update in non-TTY mode
            sys.stderr.write(f"⏳ {message}\n")
            sys.stderr.flush()

    def stop(self, final_message: str = ""):
        self.running = False
        if self.thread:
            self.thread.join(timeout=0.2)
        if IS_TTY:
            # Clear the line in real terminal
            sys.stderr.write("\r" + " " * 80 + "\r")
        if final_message:
            sys.stderr.write(f"✓ {final_message}\n")
        sys.stderr.flush()


class ProgressDisplay:
    """Progress display for research phases."""

    def __init__(self, topic: str, show_banner: bool = True):
        self.topic = topic
        self.spinner: Optional[Spinner] = None
        self.start_time = time.time()

        if show_banner:
            self._show_banner()

    def _show_banner(self):
        if IS_TTY:
            sys.stderr.write(MINI_BANNER + "\n")
            sys.stderr.write(f"{Colors.DIM}Topic: {Colors.RESET}{Colors.BOLD}{self.topic}{Colors.RESET}\n\n")
        else:
            # Simple text for non-TTY
            sys.stderr.write(f"/pulse · researching: {self.topic}\n")
        sys.stderr.flush()

    def start_x(self):
        msg = random.choice(X_MESSAGES)
        self.spinner = Spinner(f"{Colors.CYAN}X{Colors.RESET} {msg}", Colors.CYAN)
        self.spinner.start()

    def end_x(self, count: int):
        if self.spinner:
            self.spinner.stop(f"{Colors.CYAN}X{Colors.RESET} Found {count} posts")

    def start_youtube(self):
        msg = random.choice(YOUTUBE_MESSAGES)
        self.spinner = Spinner(f"{Colors.RED}YouTube{Colors.RESET} {msg}", Colors.RED)
        self.spinner.start()

    def end_youtube(self, count: int):
        if self.spinner:
            self.spinner.stop(f"{Colors.RED}YouTube{Colors.RESET} Found {count} videos")

    def start_processing(self):
        msg = random.choice(PROCESSING_MESSAGES)
        self.spinner = Spinner(f"{Colors.PURPLE}Processing{Colors.RESET} {msg}", Colors.PURPLE)
        self.spinner.start()

    def end_processing(self):
        if self.spinner:
            self.spinner.stop()

    def show_complete(
        self,
        x_count: int = 0,
        *,
        source_counts: dict[str, int] | None = None,
        display_sources: list[str] | None = None,
    ):
        elapsed = time.time() - self.start_time
        if source_counts is None:
            source_counts = {"x": x_count}
            if display_sources is None:
                display_sources = [source for source, count in source_counts.items() if count]
                if not display_sources:
                    display_sources = ["x"]

        ordered_sources = _completion_sources(source_counts, display_sources)
        parts = [
            _format_completion_part(source, source_counts.get(source, 0), tty=IS_TTY)
            for source in ordered_sources
        ]
        if IS_TTY:
            sys.stderr.write(f"\n{Colors.GREEN}{Colors.BOLD}✓ Research complete{Colors.RESET} ")
            sys.stderr.write(f"{Colors.DIM}({elapsed:.1f}s){Colors.RESET}\n")
            sys.stderr.write("  " + "  ".join(parts))
            sys.stderr.write("\n\n")
        else:
            sys.stderr.write(f"✓ Research complete ({elapsed:.1f}s) - {', '.join(parts)}\n")
        sys.stderr.flush()

    def show_cached(self, age_hours: float = None):
        if age_hours is not None:
            age_str = f" ({age_hours:.1f}h old)"
        else:
            age_str = ""
        sys.stderr.write(f"{Colors.GREEN}⚡{Colors.RESET} {Colors.DIM}Using cached results{age_str} - use --refresh for fresh data{Colors.RESET}\n\n")
        sys.stderr.flush()

    def show_error(self, message: str):
        sys.stderr.write(f"{Colors.RED}✗ Error:{Colors.RESET} {message}\n")
        sys.stderr.flush()

    def start_web_only(self):
        """Show web-only mode indicator."""
        msg = random.choice(WEB_ONLY_MESSAGES)
        self.spinner = Spinner(f"{Colors.GREEN}Web{Colors.RESET} {msg}", Colors.GREEN)
        self.spinner.start()

    def end_web_only(self):
        """End web-only spinner."""
        if self.spinner:
            self.spinner.stop(f"{Colors.GREEN}Web{Colors.RESET} assistant will search the web")

    def show_web_only_complete(self):
        """Show completion for web-only mode."""
        elapsed = time.time() - self.start_time
        if IS_TTY:
            sys.stderr.write(f"\n{Colors.GREEN}{Colors.BOLD}✓ Ready for web search{Colors.RESET} ")
            sys.stderr.write(f"{Colors.DIM}({elapsed:.1f}s){Colors.RESET}\n")
            sys.stderr.write(f"  {Colors.GREEN}Web:{Colors.RESET} assistant will search blogs, docs & news\n\n")
        else:
            sys.stderr.write(f"✓ Ready for web search ({elapsed:.1f}s)\n")
        sys.stderr.flush()

    def show_promo(self, missing: str = "both", diag: dict = None):
        """Show NUX / promotional message for missing API keys.

        Args:
            missing: 'both', 'all', 'reddit', or 'x' - which keys are missing
            diag: Optional diagnostics dict for dynamic source status
        """
        if missing in ("both", "all"):
            sys.stderr.write(_build_nux_message(diag))
        elif missing in PROMO_SINGLE_KEY:
            sys.stderr.write(PROMO_SINGLE_KEY[missing])
        sys.stderr.flush()

    def show_bird_auth_help(self):
        """Show Bird authentication help."""
        if IS_TTY:
            sys.stderr.write(BIRD_AUTH_HELP)
        else:
            sys.stderr.write(BIRD_AUTH_HELP_PLAIN)
        sys.stderr.flush()


def show_diagnostic_banner(diag: dict):
    """Show pre-flight source status banner when sources are missing.

    Args:
        diag: Dict from pipeline.diagnose() with available_sources, x_backend,
            bird status, provider availability, and native web backend info.
    """
    available_sources = set(diag.get("available_sources") or [])
    has_x = "x" in available_sources
    has_web = "grounding" in available_sources
    has_reddit = "reddit" in available_sources
    has_github = "github" in available_sources
    x_backend = diag.get("x_backend")
    native_web_backend = diag.get("native_web_backend")

    # If the core pipeline is fully wired, no banner needed.
    if has_x and has_web:
        return

    def _row(emoji_color: str, emoji: str, name: str, detail: str) -> str:
        if IS_TTY:
            return f"{Colors.DIM}│{Colors.RESET}  {emoji_color}{emoji} {name:<12}{Colors.RESET} — {detail}"
        return f"│  {emoji} {name:<12} — {detail}"

    lines = []
    header = "pulse v1.0.0 — Source Status"
    if IS_TTY:
        lines.append(f"{Colors.DIM}┌─────────────────────────────────────────────────────┐{Colors.RESET}")
        lines.append(f"{Colors.DIM}│{Colors.RESET} {Colors.BOLD}{header}{Colors.RESET}")
        lines.append(f"{Colors.DIM}│{Colors.RESET}")
    else:
        lines.append("┌─────────────────────────────────────────────────────┐")
        lines.append(f"│ {header}")
        lines.append("│")

    # X (primary)
    if has_x:
        username = diag.get("bird_username", "")
        if x_backend == "bird" and username:
            label = f"Bird ({username})"
        elif x_backend == "hermes_tweet":
            label = "Hermes Tweet"
        else:
            label = str(x_backend or "xai").upper()
        lines.append(_row(Colors.GREEN, "✅", "X/Twitter", label))
    else:
        lines.append(_row(Colors.RED, "❌", "X/Twitter", "Add AUTH_TOKEN + CT0, XAI_API_KEY, or HERMES_TWEET_API_KEY"))

    # Web (secondary)
    if has_web:
        backend = native_web_backend or "native"
        lines.append(_row(Colors.GREEN, "✅", "Web", f"{backend} API"))
    else:
        lines.append(_row(Colors.YELLOW, "⚡", "Web", "Add SERPER_API_KEY or EXA_API_KEY"))

    # Reddit (tertiary, free public JSON, always available)
    lines.append(_row(Colors.GREEN if has_reddit else Colors.RED, "✅" if has_reddit else "❌", "Reddit", "public JSON" if has_reddit else "unavailable"))

    # GitHub (tertiary, dev-activity context for code-heavy topics)
    lines.append(_row(Colors.GREEN if has_github else Colors.YELLOW, "✅" if has_github else "⚡", "GitHub", "API" if has_github else "Add GITHUB_TOKEN"))

    if IS_TTY:
        lines.append(f"{Colors.DIM}│{Colors.RESET}")
        lines.append(f"{Colors.DIM}│{Colors.RESET}  Config: {Colors.BOLD}~/.config/pulse/.env{Colors.RESET}")
        lines.append(f"{Colors.DIM}└─────────────────────────────────────────────────────┘{Colors.RESET}")
    else:
        lines.append("│")
        lines.append("│  Config: ~/.config/pulse/.env")
        lines.append("└─────────────────────────────────────────────────────┘")

    sys.stderr.write("\n".join(lines) + "\n\n")
    sys.stderr.flush()


def print_phase(phase: str, message: str):
    """Print a phase message."""
    colors = {
        "reddit": Colors.YELLOW,
        "x": Colors.CYAN,
        "process": Colors.PURPLE,
        "done": Colors.GREEN,
        "error": Colors.RED,
    }
    color = colors.get(phase, Colors.RESET)
    sys.stderr.write(f"{color}▸{Colors.RESET} {message}\n")
    sys.stderr.flush()
