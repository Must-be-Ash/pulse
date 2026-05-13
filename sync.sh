#!/usr/bin/env bash
# sync.sh — Deploy pulse skills to ~/.claude/skills/
# Deploys as pulse-tools and pulse-tech (not tools-pulse / tech-pulse)

set -e

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "🔧 Deploying pulse skills..."

mkdir -p ~/.claude/skills/pulse-tools
cp "$REPO_DIR/pulse-tools/SKILL.md" ~/.claude/skills/pulse-tools/SKILL.md
echo "  ✅ /pulse-tools → ~/.claude/skills/pulse-tools/SKILL.md"

mkdir -p ~/.claude/skills/pulse-tech
cp "$REPO_DIR/pulse-tech/SKILL.md" ~/.claude/skills/pulse-tech/SKILL.md
echo "  ✅ /pulse-tech  → ~/.claude/skills/pulse-tech/SKILL.md"

echo ""
echo "✅ Done. Run /pulse-tools or /pulse-tech to use the pipeline versions."
