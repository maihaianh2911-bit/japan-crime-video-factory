#!/usr/bin/env bash
# Download the fonts of the crime videos (npm packages, pinned in scripts/crime/fonts.py FAMILIES: sans, serif, mono
# and hand for the channel's language, from prompts/channel.json) into <dir>/<package> for scripts/crime/fonts.py.
# Usage: scripts/crime/get_fonts.sh <dir>
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
LANG_=$(python3 -c "import json;print(json.load(open('$HERE/../../prompts/channel.json'))['lang'])")
PKGS=$(python3 "$HERE/fonts.py" --packages "$LANG_")
mkdir -p "$1" && cd "$1"
for spec in $PKGS; do
  name=${spec%@*}; dir=${name##*/}
  [ -d "$dir/files" ] && continue
  npm pack -q "$spec" >/dev/null
  tgz=$(ls -t *.tgz | head -1)
  mkdir -p "$dir" && tar -xzf "$tgz" -C "$dir" --strip-components=1 && rm -f "$tgz"
done
ls "$1"
