#!/usr/bin/env bash
# sync.sh — Deploy pulse skills to ~/.claude/skills/
# Run this after any changes to tools-pulse/SKILL.md or tech-pulse/SKILL.md

set -e

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "🔧 Deploying pulse skills..."

# Deploy tools-pulse
mkdir -p ~/.claude/skills/tools-pulse
cp "$REPO_DIR/tools-pulse/SKILL.md" ~/.claude/skills/tools-pulse/SKILL.md
echo "  ✅ /tools-pulse → ~/.claude/skills/tools-pulse/SKILL.md"

# Deploy tech-pulse
mkdir -p ~/.claude/skills/tech-pulse
cp "$REPO_DIR/tech-pulse/SKILL.md" ~/.claude/skills/tech-pulse/SKILL.md
echo "  ✅ /tech-pulse  → ~/.claude/skills/tech-pulse/SKILL.md"

echo ""
echo "✅ Done. Start a new Claude Code session to pick up changes."
echo "   Run /tools-pulse or /tech-pulse to verify."
