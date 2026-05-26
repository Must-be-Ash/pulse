"""Pulse menu bar app — macOS status bar briefing tool."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

# Ensure scripts/ is on sys.path before any lib imports
_SCRIPTS_DIR = Path(__file__).parent.parent / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

import rumps

from . import categories as cat_mod
from . import runner

# Categories that get audio narration
_AUDIO_CATEGORIES = {"tech", "news"}


class PulseApp(rumps.App):
    def __init__(self):
        super().__init__("\U0001f4e1", quit_button=None)  # 📡
        self._run_items: dict[str, rumps.MenuItem] = {}
        self._view_items: dict[str, rumps.MenuItem] = {}
        self._audio_items: dict[str, rumps.MenuItem] = {}
        self._stop_audio_item: rumps.MenuItem | None = None
        self._category_menus: dict[str, rumps.MenuItem] = {}
        self._notified_runs: set[str] = set()
        self._audio_process: subprocess.Popen | None = None
        self._build_menu()

        # Poll for run completion every 2 seconds
        self._poll_timer = rumps.Timer(self._poll_run_state, 2)
        self._poll_timer.start()

    def _build_menu(self) -> None:
        run_all = rumps.MenuItem("Run All", callback=self._on_run_all)

        category_items = []
        for cat in cat_mod.all_categories():
            cat_menu = rumps.MenuItem(f"{cat.emoji} {cat.name}")

            run_item = rumps.MenuItem("Run Now")
            run_item.set_callback(self._make_run_callback(cat))
            self._run_items[cat.id] = run_item

            view_item = rumps.MenuItem("View Latest Report")

            # Restore from disk if a previous run exists
            existing = runner.get_latest_run(cat.id)
            if existing and existing.report_html_path:
                view_item.set_callback(self._make_view_callback(existing.report_html_path))
                self._notified_runs.add(existing.run_id)
            else:
                view_item.set_callback(None)

            self._view_items[cat.id] = view_item

            cat_menu[run_item.title] = run_item
            cat_menu[view_item.title] = view_item

            # Only Tech & AI gets audio
            if cat.id in _AUDIO_CATEGORIES:
                audio_item = rumps.MenuItem("Play Audio")
                stop_item = rumps.MenuItem("Stop Audio")

                if existing and existing.audio_path:
                    audio_item.set_callback(self._make_audio_callback(existing.audio_path))
                    self._notified_runs.add(existing.run_id)
                else:
                    audio_item.set_callback(None)

                stop_item.set_callback(self._on_stop_audio)
                self._audio_items[cat.id] = audio_item
                self._stop_audio_item = stop_item

                cat_menu[audio_item.title] = audio_item
                cat_menu[stop_item.title] = stop_item

            category_items.append(cat_menu)
            self._category_menus[cat.id] = cat_menu

        quit_item = rumps.MenuItem("Quit", callback=self._on_quit)

        self.menu = [run_all, None] + category_items + [None, quit_item]

    def _make_run_callback(self, category: cat_mod.Category):
        def callback(sender):
            self._start_run(category)
        return callback

    def _make_view_callback(self, html_path: str):
        def callback(sender):
            subprocess.Popen(["open", html_path])
        return callback

    def _make_audio_callback(self, audio_path: str):
        def callback(sender):
            # Stop any currently playing audio first
            self._kill_audio()
            self._audio_process = subprocess.Popen(["afplay", audio_path])
        return callback

    def _on_stop_audio(self, sender) -> None:
        self._kill_audio()

    def _kill_audio(self) -> None:
        """Kill any running afplay process."""
        if self._audio_process and self._audio_process.poll() is None:
            self._audio_process.terminate()
            self._audio_process = None
        # Also kill any stray afplay processes we might have spawned
        try:
            subprocess.run(["pkill", "-f", "afplay.*Pulse"], capture_output=True, timeout=3)
        except Exception:
            pass

    def _start_run(self, category: cat_mod.Category) -> None:
        if runner.is_running():
            rumps.notification(
                "Pulse",
                "Already running",
                "Wait for the current briefing to finish.",
                sound=False,
            )
            return

        result = runner.start_run(category)
        if result is None:
            return

        # Update UI to show running state
        self.title = "\u23f3"  # ⏳
        for cat_id, item in self._run_items.items():
            if cat_id == category.id:
                item.title = "Running..."
                item.set_callback(None)
            else:
                item.set_callback(None)  # Disable others

        rumps.notification(
            "Pulse",
            f"{category.emoji} {category.name}",
            "Briefing started...",
            sound=False,
        )

    def _on_run_all(self, sender) -> None:
        if runner.is_running():
            rumps.notification(
                "Pulse",
                "Already running",
                "Wait for the current briefing to finish.",
                sound=False,
            )
            return

        self.title = "\u23f3"  # ⏳

        # Disable all run buttons
        for item in self._run_items.values():
            item.set_callback(None)

        runner.queue_all()

        rumps.notification(
            "Pulse",
            "Running all briefings",
            "All 4 categories queued. You'll be notified as each completes.",
            sound=False,
        )

    def _poll_run_state(self, timer) -> None:
        """Polled every 2 seconds to check for run completion."""
        current = runner.get_current_run()

        if current and current.status == "running":
            cat_id = current.category.id
            run_item = self._run_items.get(cat_id)
            if run_item and current.progress_messages:
                last_msg = current.progress_messages[-1]
                if len(last_msg) > 40:
                    last_msg = last_msg[:37] + "..."
                run_item.title = f"Running: {last_msg}"
            return

        # Check if any category just completed
        for cat in cat_mod.all_categories():
            latest = runner.get_latest_run(cat.id)
            if not latest or latest.status != "completed":
                continue
            if latest.run_id in self._notified_runs:
                continue

            self._notified_runs.add(latest.run_id)
            view_item = self._view_items[cat.id]

            if latest.report_html_path:
                view_item.set_callback(self._make_view_callback(latest.report_html_path))

            # Update audio only for Tech & AI
            if cat.id in _AUDIO_CATEGORIES and latest.audio_path:
                audio_item = self._audio_items.get(cat.id)
                if audio_item:
                    audio_item.set_callback(self._make_audio_callback(latest.audio_path))

            rumps.notification(
                "Pulse",
                f"{cat.emoji} {cat.name}",
                "Briefing ready! Click to view.",
                sound=True,
            )

        # If nothing is running, restore UI
        if not runner.is_running():
            self.title = "\U0001f4e1"  # 📡
            for cat in cat_mod.all_categories():
                run_item = self._run_items[cat.id]
                run_item.title = "Run Now"
                run_item.set_callback(self._make_run_callback(cat))

    def _on_quit(self, sender) -> None:
        self._kill_audio()
        rumps.quit_application()


def main():
    PulseApp().run()


if __name__ == "__main__":
    main()
