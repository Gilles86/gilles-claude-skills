#!/usr/bin/env bash
# Symlink every skill in skills/ into ~/.claude/skills/ (or $CLAUDE_SKILLS_DIR).
# Idempotent: re-running refreshes existing symlinks; non-symlink entries are
# left alone (with a warning) so this never clobbers a real directory.

set -eo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
SKILLS_SRC="$REPO_DIR/skills"
SKILLS_DST="${CLAUDE_SKILLS_DIR:-$HOME/.claude/skills}"

mkdir -p "$SKILLS_DST"

linked=0
refreshed=0
skipped=0

for src in "$SKILLS_SRC"/*/; do
    [ -f "$src/SKILL.md" ] || continue
    name="$(basename "$src")"
    src="${src%/}"
    dst="$SKILLS_DST/$name"

    if [ -L "$dst" ]; then
        if [ "$(readlink "$dst")" = "$src" ]; then
            echo "  ok    $name"
        else
            ln -sfn "$src" "$dst"
            echo "  refresh $name (was -> $(readlink "$dst"))"
            refreshed=$((refreshed + 1))
        fi
    elif [ -e "$dst" ]; then
        echo "  SKIP  $name — $dst exists and is not a symlink" >&2
        skipped=$((skipped + 1))
    else
        ln -s "$src" "$dst"
        echo "  link  $name"
        linked=$((linked + 1))
    fi
done

echo
echo "Done. $linked new, $refreshed refreshed, $skipped skipped."
echo "Target: $SKILLS_DST"
