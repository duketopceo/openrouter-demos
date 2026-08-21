#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

log() { echo "[setup] $*"; }

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 is required (3.11+)" >&2
  exit 1
fi

log "Creating venv at .venv ..."
python3 -m venv .venv
# shellcheck disable=SC1091
source .venv/bin/activate

log "Installing dependencies ..."
pip install -q -r requirements.txt

log "Running offline pytest ..."
RUN_LIVE=0 pytest -q

log "Running offline harness smoke ..."
RUN_LIVE=0 python -m deflect.harness >/dev/null
RUN_LIVE=0 python -m motion.harness >/dev/null
RUN_LIVE=0 python -m bakeoff.runner >/dev/null
RUN_LIVE=0 python -m caesar.harness >/dev/null

log "Done. Next steps:"
echo "  cp .env.example .env   # add OPENROUTER_API_KEY for live runs"
echo "  python3 dev_server.py  # open http://localhost:8080"
