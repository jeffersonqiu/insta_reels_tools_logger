#!/usr/bin/env bash
# Record a short Playwright session (video) and convert to GIF for docs/screenshots/demo.gif
# Requires: ffmpeg (brew install ffmpeg)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/frontend"
npm install
npx playwright install chromium
npm run record:demo
VIDEO="$(find "$ROOT/frontend/test-results" -name "*.webm" -type f 2>/dev/null | head -n 1)"
OUT="$ROOT/docs/screenshots/demo.gif"
if [[ -z "${VIDEO:-}" ]]; then
  echo "No .webm found under frontend/test-results. Run npm run record:demo manually."
  exit 1
fi
if ! command -v ffmpeg >/dev/null 2>&1; then
  echo "ffmpeg not installed; video saved at: $VIDEO"
  echo "Install ffmpeg and re-run, or: ffmpeg -i \"$VIDEO\" -vf fps=10,scale=720:-1 \"$OUT\""
  exit 0
fi
mkdir -p "$(dirname "$OUT")"
ffmpeg -y -i "$VIDEO" -vf "fps=10,scale=720:-1:flags=lanczos,split[s0][s1];[s0]palettegen=max_colors=128[p];[s1][p]paletteuse" "$OUT"
echo "Wrote $OUT"
