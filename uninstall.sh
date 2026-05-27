#!/bin/bash
set -euo pipefail

echo "Removing Pulse..."

launchctl unload "$HOME/Library/LaunchAgents/com.pulse.app.plist" 2>/dev/null || true
pkill -f "pulse-launcher" 2>/dev/null || true
pkill -f "from app.menubar import main" 2>/dev/null || true

rm -rf /Applications/Pulse.app
rm -f "$HOME/Library/LaunchAgents/com.pulse.app.plist"
rm -rf "$HOME/.pulse-env"

echo "✅ Pulse removed. Config left at ~/.config/pulse/ (delete manually if wanted)."
