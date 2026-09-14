#!/usr/bin/env sh
set -eu
SRC=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
TARGET_ROOT=${1:-"$HOME/.agents/skills"}
TARGET="$TARGET_ROOT/autonomous-test-fix-retest"
mkdir -p "$TARGET_ROOT"
rm -rf "$TARGET"
cp -R "$SRC" "$TARGET"
printf 'installed: %s\n' "$TARGET"
