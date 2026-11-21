#!/bin/sh
# Install one style skill from this repository into Codex's skills directory.
# Running it again updates the installed copy; files removed here are removed there.
#
# Run from a public checkout with rsync installed. The script also copies
# local content under skills/<name>/ if run in a maintainer checkout.
# Codex-specific settings, including the display name and implicit
# invocation, live in scripts/codex/<name>/agents/ and are added to
# the installed copy.
#
# Usage: sh scripts/install_codex.sh explainer-guide
# Undo:  rm -r "${CODEX_HOME:-$HOME/.codex}/skills/explainer-guide"
set -eu

NAME="${1:?usage: sh scripts/install_codex.sh <skill-name>}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SRC="$ROOT/skills/$NAME/"
CODEX_AGENTS="$ROOT/scripts/codex/$NAME/agents/"
DEST="${CODEX_HOME:-$HOME/.codex}/skills/$NAME/"

[ -f "$SRC/SKILL.md" ] || { echo "no such skill: $NAME" >&2; exit 1; }

mkdir -p "$DEST"
# Copy the content, leaving agents/ alone; then fill agents/ if this skill has Codex settings.
rsync -a --delete --exclude '.DS_Store' --exclude '/agents/' "$SRC" "$DEST"
[ -d "$CODEX_AGENTS" ] && rsync -a --delete --exclude '.DS_Store' "$CODEX_AGENTS" "$DEST/agents/"
echo "installed $NAME into the Codex skills directory"
