#!/usr/bin/env bash
# Upload demo video to Cloudflare R2 (remote).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUCKET="${R2_BUCKET:-openrouter-demos}"
KEY="${R2_KEY:-demos/openrouter-demos-walkthrough.mp4}"
VIDEO="${1:-$ROOT/demo/openrouter-demos-walkthrough.mp4}"

if [[ ! -f "$VIDEO" ]]; then
  echo "Video not found: $VIDEO" >&2
  echo "Run: python3 scripts/record_demo.py" >&2
  exit 1
fi

log() { echo "[r2] $*"; }

log "Uploading $VIDEO -> $BUCKET/$KEY"
npx --yes wrangler@latest r2 object put "$BUCKET/$KEY" \
  --file="$VIDEO" \
  --content-type=video/mp4 \
  --remote

DEV_URL="$(npx --yes wrangler@latest r2 bucket dev-url get "$BUCKET" 2>&1 | rg -o 'https://pub-[a-f0-9]+\\.r2\\.dev' | head -1)"
if [[ -n "$DEV_URL" ]]; then
  log "Public URL: ${DEV_URL}/${KEY}"
else
  log "Upload complete. Enable public access: wrangler r2 bucket dev-url enable $BUCKET"
fi
