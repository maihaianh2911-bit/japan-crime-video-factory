#!/usr/bin/env bash
# Download the fonts of the crime videos (npm packages, pinned) into <dir>/<package> for scripts/crime/fonts.py:
# Japanese channel: @fontsource-variable/noto-sans-jp; German channel: @fontsource/anton (captions, title) and
# @fontsource-variable/source-sans-3 (label, credit). The channel comes from prompts/channel.json.
# Usage: scripts/crime/get_fonts.sh <dir>
set -euo pipefail
LANG_=$(python3 -c "import json;print(json.load(open('prompts/channel.json'))['lang'])")
mkdir -p "$1" && cd "$1"
if [ "$LANG_" = ja ]; then PKGS="@fontsource-variable/noto-sans-jp@5.3.1"; else PKGS="@fontsource/anton@5.2.7 @fontsource-variable/source-sans-3@5.3.1"; fi
for spec in $PKGS; do
  name=${spec%@*}; dir=${name##*/}
  [ -f "$dir/index.css" ] && continue
  npm pack -q "$spec" >/dev/null
  tgz=$(ls -t *.tgz | head -1)
  mkdir -p "$dir" && tar -xzf "$tgz" -C "$dir" --strip-components=1 && rm -f "$tgz"
done
ls "$1"
