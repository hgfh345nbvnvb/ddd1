#!/usr/bin/env bash
# Run Blender jobs strictly one after another (two EEVEE processes overrun an 8 GB sandbox).
#   tools/render_queue.sh <project>:<mode> [<project>:<mode> ...]     e.g. gagarin-7-facts:preview messi-vs-ronaldo:full
set -u
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
for job in "$@"; do
  proj="${job%%:*}"
  mode="${job##*:}"
  cd "$ROOT/shorts/$proj" || continue
  [ "$mode" = preview ] && rm -rf preview
  log="$mode.log"
  blender --background --python build.py -- . "$mode" > "$log" 2>&1
  echo "EXIT $?" >> "$log"
done
