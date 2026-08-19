# OpenRouter Demos

Four RouteKit demos for OpenRouter in one repo — support deflection, GTM motion, provider bakeoff, and Caesar model debate. Run everything from a **local dashboard** at `http://localhost:8080`, or from the CLI.

| Demo | Directory | What it does |
|------|-----------|--------------|
| **Support Deflection** | `deflect/` | Classify support tickets and route them (deflect / draft / escalate) with policy guardrails |
| **GTM Motion** | `motion/` | Qualify inbound leads and pick the next GTM action (structured, not prose scoring) |
| **Provider Ops Bakeoff** | `bakeoff/` | Head-to-head quality, latency, TTFT, TPS, and cost comparison between two models |
| **Caesar Debate** | `caesar/` | Two models debate; Caesar judges. Traces replay in an interactive viewer |

## Quick Start — Local Dashboard

```bash
uv venv --clear .venv
source .venv/bin/activate
uv pip install -r requirements.txt

python3 dev_server.py
```

Open **`http://localhost:8080`**.

The dashboard (`dev_server.py`) is the primary interface. From it you can:

- Run any of the four harnesses and stream logs in the browser
- Run the offline pytest suite (`RUN_LIVE=0`)
- Inspect JSON results under `results/`
- Pick models from **Curated Heavy Hitters (32)** or **All Models (~415)** via `src/models.json`
- Save `OPENROUTER_API_KEY`, model slugs, and `RUN_LIVE=1` to `.env`
- Replay Caesar debate traces in the embedded viewer (`caesar/chat.html`)

There is no hosted deployment in this repo — start the dev server locally.

## Offline vs Live

| Mode | How | API key |
|------|-----|---------|
| **Offline (default)** | `RUN_LIVE=0` — pytest and harnesses use recorded stub fixtures per demo | Not required |
| **Live** | Set `OPENROUTER_API_KEY` and `RUN_LIVE=1` (or save both from the dashboard) | Required |

Copy `.env.example` to `.env` and fill in values as needed:

```bash
cp .env.example .env
```

Default primary model: **`nvidia/nemotron-3.5-lightning`**. Bakeoff / debate model B defaults to `openai/gpt-4o-mini`.

## CLI

```bash
# Offline tests (stub fixtures, no network)
pytest

# Individual harnesses (respect RUN_LIVE / OPENROUTER_API_KEY from .env)
python -m deflect.harness
python -m motion.harness
python -m bakeoff.runner
python -m caesar.harness
```

Results land in `results/`:

- `deflect.json`, `motion.json`, `bakeoff.json` — eval summaries
- `caesar/<id>.json` — debate traces for replay
- `runs.db` — SQLite run log (see below)

## Metrics & Run Logger

Live and offline runs record latency, **TTFT** (time to first token), **TPS** (tokens per second), cost, accuracy, and guardrail pass rate via `src/db.py`.

Each run is persisted to **`results/runs.db`** with a two-sentence summary (template offline; `gpt-4o-mini` when live with a key). Metrics are sourced from `src/openrouter.py` and aggregated in each harness.

## Caesar Trace Viewer

After `python -m caesar.harness`, open **`http://localhost:8080/caesar/chat.html`** (or use **Open Replay** on the dashboard).

The viewer loads traces from:

- A dropdown of recent runs (`/api/caesar-traces` → `results/caesar/*.json`)
- Local JSON upload or drag-and-drop

Turn-by-turn debate text and a stats drawer (latency, cost, grounding, claims) — no API key in the page.

## Project Layout

```
deflect/   motion/   bakeoff/   caesar/   # demo harnesses + cases + offline fixtures
src/       openrouter.py, db.py, models.json, guardrails.py
tests/     pytest against stub fixtures (no live API)
dev_server.py                              # local dashboard on :8080
results/   JSON outputs + runs.db (gitignored)
```

## Requirements

- Python 3.11+
- Dependencies: `httpx`, `pytest` (see `requirements.txt` / `pyproject.toml`)
