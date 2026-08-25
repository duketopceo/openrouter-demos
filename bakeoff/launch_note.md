# Launch note — RouteKit / OpenRouter endpoint

**Status:** Unfilled — pending a blessed live bakeoff (`RUN_LIVE=1`). Offline stub numbers in `demo/baked/results/bakeoff.json` are for CI/review only; do not treat them as production sign-off.

Fill this after a live run. Numbers come from `python -m bakeoff.runner` → `results/bakeoff.json`. Do not invent them.

- Date (America/Denver):
- Candidate model / slug:
- Compared against:
- Baseline file: `bakeoff/baseline.json`
- Quality (0–1, structured rubric):
- Mean latency_ms:
- Mean est. TTFT_ms (derived: latency × 0.25 unless streaming):
- Total cost_usd (0 if the API omitted `usage.cost`):
- Gate: PASS / FAIL
- Failed case ids:
- Guardrail notes (jailbreak / invented policy / exploits):
- Rollback: pin the previous slug; do not dual-run until quality recovers
- Owner: Luke Kimball / duketopceo
- Sign-off:
