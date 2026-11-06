#!/usr/bin/env bash
# praxis-kit installer — copies profiles into ~/.claude with a manifest.
#
# Default: install all profiles globally (~/.claude/).
# Override: pass profile names as args, e.g. ./install.sh minimal security
#
# Per-project install: use `just install-project DIR PROFILE [PROFILE...]` instead.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

command -v uv >/dev/null || { echo "ERROR: uv not found; install it from https://docs.astral.sh/uv/" >&2; exit 1; }

echo "=== praxis-kit installer ==="
echo ""
echo "Target: Claude Code (~/.claude/)"
echo ""

# ── Claude Code: profile-driven install ───────────────────────
echo "Installing Claude Code profiles..."
uv run --no-dev --project "$SCRIPT_DIR" hugin profiles --root "$SCRIPT_DIR" install "$@"
echo ""

echo ""
echo "=== Installation complete ==="
echo ""
echo "Claude Code (~/.claude):"
ls -d ~/.claude/skills/*/ 2>/dev/null | wc -l | xargs -I{} echo "  {} skills"
ls ~/.claude/agents/*.md 2>/dev/null | wc -l | xargs -I{} echo "  {} agents"
ls ~/.claude/commands/*.md 2>/dev/null | wc -l | xargs -I{} echo "  {} commands"
echo ""
echo "Next steps:"
echo "  - Inspect with: just doctor"
echo "  - List profiles: just list-profiles"
echo "  - Per-project: just install-project /path/to/project security team-delivery"
echo "  - Validate: just validate"
