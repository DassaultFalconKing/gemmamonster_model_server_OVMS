#!/usr/bin/env sh
set -eu
SRC=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
TARGET_ROOT=${1:-"$HOME/.agents/skills"}
TARGET="$TARGET_ROOT/making-skills-portable"
mkdir -p "$TARGET_ROOT"
rm -rf "$TARGET"
cp -R "$SRC" "$TARGET"
printf 'installed: %s\n' "$TARGET"
