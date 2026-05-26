"""Environment and API key management for pulse skill."""

from __future__ import annotations

import base64
import binascii
import json
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

# Allow override via environment variable for testing
# Set LAST30DAYS_CONFIG_DIR="" for clean/no-config mode
# Set LAST30DAYS_CONFIG_DIR="/path/to/dir" for custom config location
_config_override = os.environ.get('LAST30DAYS_CONFIG_DIR')
if _config_override == "":
    # Empty string = no config file (clean mode)
    CONFIG_DIR = None
    CONFIG_FILE = None
elif _config_override:
    CONFIG_DIR = Path(_config_override)
    CONFIG_FILE = CONFIG_DIR / ".env"
else:
    CONFIG_DIR = Path.home() / ".config" / "pulse"
    CONFIG_FILE = CONFIG_DIR / ".env"

CODEX_AUTH_FILE = Path(os.environ.get("CODEX_AUTH_FILE", str(Path.home() / ".codex" / "auth.json")))

AuthSource = Literal["api_key", "codex", "none"]
AuthStatus = Literal["ok", "missing", "expired", "missing_account_id"]

AUTH_SOURCE_API_KEY: AuthSource = "api_key"
AUTH_SOURCE_CODEX: AuthSource = "codex"
AUTH_SOURCE_NONE: AuthSource = "none"

AUTH_STATUS_OK: AuthStatus = "ok"
AUTH_STATUS_MISSING: AuthStatus = "missing"
AUTH_STATUS_EXPIRED: AuthStatus = "expired"
AUTH_STATUS_MISSING_ACCOUNT_ID: AuthStatus = "missing_account_id"


@dataclass(frozen=True)
class OpenAIAuth:
    token: str | None
    source: AuthSource
    status: AuthStatus
    account_id: str | None
    codex_auth_file: str


def _check_file_permissions(path: Path) -> None:
    """Warn to stderr if a secrets file has overly permissive permissions."""
    try:
        mode = path.stat().st_mode
        # Check if group or other can read (bits 0o044)
        if mode & 0o044:
            sys.stderr.write(
                f"[pulse] WARNING: {path} is readable by other users. "
                f"Run: chmod 600 {path}\n"
            )
            sys.stderr.flush()
    except OSError as exc:
        sys.stderr.write(f"[pulse] WARNING: could not stat {path}: {exc}\n")
        sys.stderr.flush()


def load_env_file(path: Path) -> dict[str, str]:
    """Load environment variables from a file."""
    env = {}
    if not path or not path.exists():
        return env
    _check_file_permissions(path)

    with open(path, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '=' in line:
                key, _, value = line.partition('=')
                key = key.strip()
                value = value.strip()
                # Remove quotes if present
                if value and value[0] in ('"', "'") and value[-1] == value[0]:
                    value = value[1:-1]
                if key and value:
                    env[key] = value
    return env


def _decode_jwt_payload(token: str) -> dict[str, Any] | None:
    """Decode JWT payload without verification."""
    try:
        parts = token.split(".")
        if len(parts) < 2:
            return None
        payload_b64 = parts[1]
        pad = "=" * (-len(payload_b64) % 4)
        decoded = base64.urlsafe_b64decode(payload_b64 + pad)
        return json.loads(decoded.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError, binascii.Error, IndexError) as exc:
        sys.stderr.write(f"[pulse] WARNING: malformed JWT token: {exc}\n")
        sys.stderr.flush()
        return None


def _token_expired(token: str, leeway_seconds: int = 60) -> bool:
    """Check if JWT token is expired."""
    payload = _decode_jwt_payload(token)
    if not payload:
        return False
    exp = payload.get("exp")
    if not exp:
        return False
    return exp <= (time.time() + leeway_seconds)


def extract_chatgpt_account_id(access_token: str) -> str | None:
    """Extract chatgpt_account_id from JWT token."""
    payload = _decode_jwt_payload(access_token)
    if not payload:
        return None
    auth_claim = payload.get("https://api.openai.com/auth", {})
    if isinstance(auth_claim, dict):
        return auth_claim.get("chatgpt_account_id")
    return None


def load_codex_auth(path: Path = CODEX_AUTH_FILE) -> dict[str, Any]:
    """Load Codex auth JSON."""
    if not path.exists():
        return {}
    try:
        with open(path, "r") as f:
            return json.load(f)
    except json.JSONDecodeError:
        sys.stderr.write(
            f"[pulse] WARNING: {path} exists but contains invalid JSON -- ignoring\n"
        )
        sys.stderr.flush()
        return {}


def get_codex_access_token() -> tuple[str | None, str]:
    """Get Codex access token from auth.json.

    Returns:
        (token, status) where status is 'ok', 'missing', or 'expired'
    """
    auth = load_codex_auth()
    token = None
    if isinstance(auth, dict):
        tokens = auth.get("tokens") or {}
        if isinstance(tokens, dict):
            token = tokens.get("access_token")
        if not token:
            token = auth.get("access_token")
    if not token:
        return None, AUTH_STATUS_MISSING
    if _token_expired(token):
        return None, AUTH_STATUS_EXPIRED
    return token, AUTH_STATUS_OK


def get_openai_auth(file_env: dict[str, str]) -> OpenAIAuth:
    """Resolve OpenAI auth from API key or Codex login."""
    api_key = os.environ.get('OPENAI_API_KEY') or file_env.get('OPENAI_API_KEY')
    if api_key:
        return OpenAIAuth(
            token=api_key,
            source=AUTH_SOURCE_API_KEY,
            status=AUTH_STATUS_OK,
            account_id=None,
            codex_auth_file=str(CODEX_AUTH_FILE),
        )

    # Codex auth (chatgpt.com backend) intentionally skipped.
    # The endpoint is unstable and causes crashes when the token expires.
    # Users who want OpenAI should set OPENAI_API_KEY explicitly.

    return OpenAIAuth(
        token=None,
        source=AUTH_SOURCE_NONE,
        status=AUTH_STATUS_MISSING,
        account_id=None,
        codex_auth_file=str(CODEX_AUTH_FILE),
    )


def _find_project_env() -> Path | None:
    """Find per-project .env by walking up from cwd.

    Searches for .claude/pulse.env in each parent directory,
    stopping at the user's home directory or filesystem root.
    """
    cwd = Path.cwd()
    for parent in [cwd, *cwd.parents]:
        candidate = parent / '.claude' / 'pulse.env'
        if candidate.exists():
            return candidate
        # Stop at filesystem root or home
        if parent == Path.home() or parent == parent.parent:
            break
    return None


def get_config() -> dict[str, Any]:
    """Load configuration from multiple sources.

    Priority (highest wins):
      1. Environment variables (os.environ)
      2. .claude/pulse.env (per-project config)
      3. ~/.config/pulse/.env (global config)
    """
    # Load from global config file
    file_env = load_env_file(CONFIG_FILE) if CONFIG_FILE else {}

    # Load from per-project config (overrides global)
    project_env_path = _find_project_env()
    project_env = load_env_file(project_env_path) if project_env_path else {}

    # Merge: project overrides global
    merged_env = {**file_env, **project_env}

    openai_auth = get_openai_auth(merged_env)

    # Build config: Codex/OpenAI auth + process.env > project .env > global .env
    config = {
        'OPENAI_API_KEY': openai_auth.token,
        'OPENAI_AUTH_SOURCE': openai_auth.source,
        'OPENAI_AUTH_STATUS': openai_auth.status,
        'OPENAI_CHATGPT_ACCOUNT_ID': openai_auth.account_id,
        'CODEX_AUTH_FILE': openai_auth.codex_auth_file,
    }

    keys = [
        # Reasoning / planner / rerank providers
        ('XAI_API_KEY', None),
        ('GOOGLE_API_KEY', None),
        ('GEMINI_API_KEY', None),
        ('GOOGLE_GENAI_API_KEY', None),
        ('OPENROUTER_API_KEY', None),
        ('LAST30DAYS_REASONING_PROVIDER', 'auto'),
        ('LAST30DAYS_PLANNER_MODEL', None),
        ('LAST30DAYS_RERANK_MODEL', None),
        ('LAST30DAYS_X_MODEL', None),
        ('LAST30DAYS_X_BACKEND', None),
        ('OPENAI_MODEL_PIN', None),
        ('XAI_MODEL_PIN', None),
        # X / Twitter auth
        ('AUTH_TOKEN', None),
        ('CT0', None),
        # Web search backends
        ('BRAVE_API_KEY', None),
        ('EXA_API_KEY', None),
        ('SERPER_API_KEY', None),
        ('PARALLEL_API_KEY', None),
        ('FIRECRAWL_API_KEY', None),
        # GitHub
        ('GITHUB_TOKEN', None),
        # Twitter API v2
        ('TWITTER_API_KEY', None),
        ('TWITTER_API_SECRET', None),
        ('TWITTER_BEARER_TOKEN', None),
        # Claude / Anthropic
        ('CLAUDE_API_KEY', None),
        # ElevenLabs TTS
        ('ELEVENLABS_API_KEY', None),
        # Misc
        ('FROM_BROWSER', None),
        ('SETUP_COMPLETE', None),
        ('INCLUDE_SOURCES', None),
        ('BROWSER_CONSENT', None),
    ]

    for key, default in keys:
        config[key] = os.environ.get(key) or merged_env.get(key, default)

    # Track which config source was used
    if project_env_path:
        config['_CONFIG_SOURCE'] = f'project:{project_env_path}'
    elif CONFIG_FILE and CONFIG_FILE.exists():
        config['_CONFIG_SOURCE'] = f'global:{CONFIG_FILE}'
    else:
        config['_CONFIG_SOURCE'] = 'env_only'

    # Extract browser credentials if configured
    browser_creds = extract_browser_credentials(config)
    for key, value in browser_creds.items():
        if not config.get(key):
            config[key] = value
            config[f"_{key}_SOURCE"] = "browser"

    return config


# ---------------------------------------------------------------------------
# Browser cookie extraction
# ---------------------------------------------------------------------------

COOKIE_DOMAINS: dict[str, dict[str, Any]] = {
    "x": {
        "domain": ".x.com",
        "cookies": ["auth_token", "ct0"],
        "mapping": {"auth_token": "AUTH_TOKEN", "ct0": "CT0"},
    },
}


def extract_browser_credentials(config: dict[str, Any]) -> dict[str, str]:
    """Extract auth cookies from local browsers.

    Default behavior (FROM_BROWSER unset): tries Firefox and Safari only.
    These read local files silently with no system dialogs.  Chrome is
    skipped because ``security find-generic-password`` triggers a macOS
    Keychain prompt that cannot be reliably suppressed.

    Set ``FROM_BROWSER=auto`` to also try Chrome (accepts the dialog),
    or ``FROM_BROWSER=off`` to disable extraction entirely.
    """
    from_browser = (config.get("FROM_BROWSER") or "").strip().lower()
    if from_browser == "off":
        return {}
    try:
        from . import cookie_extract
    except ImportError:
        return {}
    # Determine which browsers to try
    if from_browser in ("firefox", "chrome", "safari"):
        browsers = [from_browser]
    elif from_browser == "auto":
        browsers = ["firefox", "safari", "chrome"]
    else:
        # Default: silent browsers only (no Keychain dialog)
        browsers = ["firefox", "safari"]
    extracted: dict[str, str] = {}
    for _service, spec in COOKIE_DOMAINS.items():
        if all(config.get(env_key) for env_key in spec["mapping"].values()):
            continue
        for browser in browsers:
            try:
                cookies = cookie_extract.extract_cookies(browser, spec["domain"], spec["cookies"])
            except Exception:
                continue
            if cookies:
                for cookie_name, env_key in spec["mapping"].items():
                    if cookie_name in cookies and not config.get(env_key):
                        extracted[env_key] = cookies[cookie_name]
                break  # Found cookies for this service, stop trying browsers
    return extracted


def get_x_source_with_method(config: dict[str, Any]) -> tuple[str | None, str]:
    """Return (source, method) for X search, where method describes the auth origin."""
    if config.get("XAI_API_KEY"):
        return "xai", "xai"
    if config.get("AUTH_TOKEN") and config.get("CT0"):
        method = config.get("_AUTH_TOKEN_SOURCE", "env")
        return "bird", method
    return None, "none"


def config_exists() -> bool:
    """Check if any configuration source exists."""
    if _find_project_env():
        return True
    if CONFIG_FILE:
        return CONFIG_FILE.exists()
    return False


def is_reddit_available(config: dict[str, Any]) -> bool:
    """Reddit public JSON works without any API key — always available."""
    return True


def get_x_source(config: dict[str, Any]) -> str | None:
    """Determine the best available explicit X/Twitter source.

    Priority: explicit backend pin, then xAI, then Bird with explicit cookies.

    Browser-cookie probing is intentionally not used here. Automatic Keychain
    access causes popups during normal pipeline runs. Bird is only considered
    available when AUTH_TOKEN and CT0 are present explicitly.

    Args:
        config: Configuration dict from get_config()

    Returns:
        'bird' if Bird is installed and explicit cookies are configured,
        'xai' if XAI_API_KEY is configured,
        None if no X source available.
    """
    # Import here to avoid circular dependency
    from . import bird_x

    preferred = (config.get('LAST30DAYS_X_BACKEND') or '').lower()
    has_bird_creds = bool(config.get('AUTH_TOKEN') and config.get('CT0'))
    if has_bird_creds:
        bird_x.set_credentials(config.get('AUTH_TOKEN'), config.get('CT0'))

    if preferred == 'xai':
        return 'xai' if config.get('XAI_API_KEY') else None
    if preferred == 'bird':
        return 'bird' if has_bird_creds and bird_x.is_bird_installed() else None

    if config.get('XAI_API_KEY'):
        return 'xai'
    if has_bird_creds and bird_x.is_bird_installed():
        return 'bird'

    return None




# ---------------------------------------------------------------------------
# Crypto data API accessors
# ---------------------------------------------------------------------------

def get_coingecko_key(config: dict[str, Any]) -> str | None:
    return None  # removed: not used in pulse


def get_messari_key(config: dict[str, Any]) -> str | None:
    return None  # removed: not used in pulse


def get_lunarcrush_key(config: dict[str, Any]) -> str | None:
    return None  # removed: not used in pulse


def get_firecrawl_key(config: dict[str, Any]) -> str | None:
    """Return the Firecrawl API key, if configured."""
    return config.get('FIRECRAWL_API_KEY') or None


def is_coingecko_available(config: dict[str, Any]) -> bool:
    return bool(get_coingecko_key(config))


def is_messari_available(config: dict[str, Any]) -> bool:
    return bool(get_messari_key(config))


def is_lunarcrush_available(config: dict[str, Any]) -> bool:
    return bool(get_lunarcrush_key(config))


def is_firecrawl_available(config: dict[str, Any]) -> bool:
    return bool(get_firecrawl_key(config))


def _parse_include_sources(config: dict[str, Any]) -> set[str]:
    """Parse INCLUDE_SOURCES config value into a set of lowercase source names."""
    raw = config.get('INCLUDE_SOURCES') or ''
    return {s.strip().lower() for s in raw.split(',') if s.strip()}


def get_x_source_status(config: dict[str, Any]) -> dict[str, Any]:
    """Get detailed X source status for UI decisions.

    Returns:
        Dict with keys: source, bird_installed, bird_authenticated,
        bird_username, xai_available, can_install_bird
    """
    from . import bird_x

    bird_status = bird_x.get_bird_status()
    xai_available = bool(config.get('XAI_API_KEY'))

    # Determine active source
    if bird_status["authenticated"]:
        source = 'bird'
    elif xai_available:
        source = 'xai'
    else:
        source = None

    return {
        "source": source,
        "bird_installed": bird_status["installed"],
        "bird_authenticated": bird_status["authenticated"],
        "bird_username": bird_status["username"],
        "xai_available": xai_available,
        "can_install_bird": bird_status["can_install"],
    }


