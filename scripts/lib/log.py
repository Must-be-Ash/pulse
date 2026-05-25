"""Shared logging utilities for last30days-crypto skill."""

import os
import sys

DEBUG = os.environ.get("LAST30DAYS_DEBUG", "").lower() in ("1", "true", "yes")


def debug(msg: str) -> None:
    """Log debug message to stderr (only when LAST30DAYS_DEBUG is set)."""
    if DEBUG:
        sys.stderr.write(f"[DEBUG] {msg}\n")
        sys.stderr.flush()


def source_log(prefix: str, msg: str, *, tty_only: bool = False) -> None:
    """Log a source module message to stderr.

    Args:
        prefix: Source label (e.g. "Reddit", "Bird").
        msg: Message text.
        tty_only: If True, only log when stderr is a TTY. Default False
                  so logs are always visible (including LaunchAgent runs).
    """
    if tty_only and not sys.stderr.isatty():
        return
    sys.stderr.write(f"[{prefix}] {msg}\n")
    sys.stderr.flush()
