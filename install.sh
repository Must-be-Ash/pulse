#!/bin/bash
set -euo pipefail

# Pulse — one-command installer for macOS
# Creates a menu bar app at /Applications/Pulse.app that auto-starts on login.

PULSE_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$HOME/.pulse-env"
APP_DIR="/Applications/Pulse.app"
PLIST="$HOME/Library/LaunchAgents/com.pulse.app.plist"
CONFIG_DIR="$HOME/.config/pulse"

echo "📡 Installing Pulse..."

# ── 1. Python venv ──────────────────────────────────────────────────
echo "  → Setting up Python environment..."
python3 -m venv "$VENV_DIR" 2>/dev/null || python3.12 -m venv "$VENV_DIR"
"$VENV_DIR/bin/pip" install --quiet --upgrade pip
"$VENV_DIR/bin/pip" install --quiet -e "$PULSE_DIR[app]"

# ── 2. Config directory ─────────────────────────────────────────────
mkdir -p "$CONFIG_DIR"
if [ ! -f "$CONFIG_DIR/.env" ]; then
    cat > "$CONFIG_DIR/.env" << 'ENVEOF'
# ── Pulse config ─────────────────────────────────────────────────
# Minimum: AUTH_TOKEN + CT0 + CLAUDE_API_KEY

# X/Twitter cookies (F12 > Application > Cookies on x.com)
LAST30DAYS_X_BACKEND=bird
AUTH_TOKEN=
CT0=

# LLM (required — powers the signal agent)
CLAUDE_API_KEY=

# Optional — improves results
TWITTER_BEARER_TOKEN=
EXA_API_KEY=
SERPER_API_KEY=
XAI_API_KEY=
GITHUB_TOKEN=
FIRECRAWL_API_KEY=
ELEVENLABS_API_KEY=

SETUP_COMPLETE=true
ENVEOF
    echo "  → Created config at $CONFIG_DIR/.env — add your API keys there."
else
    echo "  → Config already exists at $CONFIG_DIR/.env"
fi

# ── 3. Kill existing Pulse if running ────────────────────────────
launchctl bootout "gui/$(id -u)/com.pulse.app" 2>/dev/null || true
launchctl unload "$PLIST" 2>/dev/null || true
pkill -f "pulse-launcher" 2>/dev/null || true
pkill -f "from app.menubar import main" 2>/dev/null || true
sleep 1

# ── 4. Create Pulse.app bundle ───────────────────────────────────
echo "  → Creating Pulse.app..."
rm -rf "$APP_DIR"
mkdir -p "$APP_DIR/Contents/MacOS" "$APP_DIR/Contents/Resources"

cat > "$APP_DIR/Contents/Info.plist" << 'PLISTEOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleName</key>
    <string>Pulse</string>
    <key>CFBundleDisplayName</key>
    <string>Pulse</string>
    <key>CFBundleIdentifier</key>
    <string>com.pulse.app</string>
    <key>CFBundleVersion</key>
    <string>1.0.0</string>
    <key>CFBundleShortVersionString</key>
    <string>1.0.0</string>
    <key>CFBundleExecutable</key>
    <string>pulse-launcher</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>LSUIElement</key>
    <true/>
    <key>LSMinimumSystemVersion</key>
    <string>13.0</string>
</dict>
</plist>
PLISTEOF

cat > "$APP_DIR/Contents/MacOS/pulse-launcher" << LAUNCHEOF
#!/bin/bash
exec "$VENV_DIR/bin/python" -c "
import sys
sys.path.insert(0, '$PULSE_DIR')
sys.path.insert(0, '$PULSE_DIR/scripts')
from app.menubar import main
main()
"
LAUNCHEOF
chmod +x "$APP_DIR/Contents/MacOS/pulse-launcher"

# ── 5. Launch agent (auto-start on login) ────────────────────────
echo "  → Setting up auto-start..."
mkdir -p "$(dirname "$PLIST")"

cat > "$PLIST" << AGENTEOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.pulse.app</string>
    <key>ProgramArguments</key>
    <array>
        <string>$VENV_DIR/bin/python</string>
        <string>-c</string>
        <string>import sys; sys.path.insert(0, '$PULSE_DIR'); sys.path.insert(0, '$PULSE_DIR/scripts'); from app.menubar import main; main()</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <false/>
    <key>StandardOutPath</key>
    <string>/tmp/pulse-app.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/pulse-app.err</string>
</dict>
</plist>
AGENTEOF

launchctl load "$PLIST" 2>/dev/null || launchctl bootstrap "gui/$(id -u)" "$PLIST" 2>/dev/null || true

# ── 6. Launch ────────────────────────────────────────────────────
echo "  → Launching Pulse..."
open -a "$APP_DIR"

echo ""
echo "✅ Pulse installed! Look for 📡 in your menu bar."
echo ""
echo "Next: add your API keys to $CONFIG_DIR/.env"
echo "  Minimum: AUTH_TOKEN + CT0 + CLAUDE_API_KEY"
echo ""
echo "To uninstall: bash $PULSE_DIR/uninstall.sh"
