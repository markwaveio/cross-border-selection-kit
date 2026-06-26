#!/usr/bin/env bash
# Source this to load pipeline.config into the environment (expanding ~).
#   source "$(dirname "$0")/load_config.sh"
# Looks for pipeline.config next to this script's parent /config dir, or at
# $PIPELINE_CONFIG if set. Exports every KEY=VALUE as an env var.
set -euo pipefail

_find_config() {
  if [[ -n "${PIPELINE_CONFIG:-}" && -f "${PIPELINE_CONFIG}" ]]; then
    echo "${PIPELINE_CONFIG}"; return 0
  fi
  local here; here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  for cand in "$here/../config/pipeline.config" "$here/../pipeline.config" "$HOME/.cross-border-selection/pipeline.config"; do
    [[ -f "$cand" ]] && { echo "$cand"; return 0; }
  done
  return 1
}

CONFIG_FILE="$(_find_config)" || {
  echo "❌ 找不到 pipeline.config。先复制模板并填写:" >&2
  echo "   cp config/pipeline.config.example config/pipeline.config" >&2
  return 1 2>/dev/null || exit 1
}

while IFS='=' read -r key val; do
  [[ -z "$key" || "$key" == \#* ]] && continue
  key="$(echo "$key" | xargs)"            # trim
  val="${val%%#*}"                         # strip inline comment
  val="$(echo "$val" | xargs)"             # trim
  val="${val/#\~/$HOME}"                   # expand leading ~
  [[ -z "$key" ]] && continue
  export "$key"="$val"
done < "$CONFIG_FILE"

export PIPELINE_CONFIG="$CONFIG_FILE"
