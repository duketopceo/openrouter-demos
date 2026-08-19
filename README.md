# OpenRouter Demos

RouteKit demos for OpenRouter — four working demos in one repository.

- `deflect/` — Support Deflection
- `motion/` — GTM Motion
- `bakeoff/` — Provider Ops Bakeoff
- `caesar/` — Caesar Model Debate & Replay

## Quick Start (Local Dev Server)

Run the unified local dashboard server:

```bash
python3 dev_server.py
```

Then open **`http://localhost:8080`** in your browser.

From the web UI, you can:
- Trigger any of the 4 demo harnesses (`deflect`, `motion`, `bakeoff`, `caesar`)
- Run pytest suites and view live terminal outputs
- Inspect JSON evaluation results
- Replay Caesar model debates in the interactive trace viewer
- Toggle between Offline (stub models) and Live mode (`OPENROUTER_API_KEY`)

## CLI Usage

```bash
uv venv --clear .venv
source .venv/bin/activate
uv pip install -r requirements.txt

pytest
python -m deflect.harness
python -m motion.harness
python -m bakeoff.runner
python -m caesar.harness
```
