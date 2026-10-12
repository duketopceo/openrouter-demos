---
title: "OpenRouter Demos: program roadmap"
type: program-plan
status: active
date: 2026-10-11
---

# OpenRouter Demos: program roadmap

Written directly (not through the ce-plan pipeline) following the repo-program brief fields: stable U-IDs, status, evidence, dependencies, verification, plus Difficulty, Feasibility and Simpler alternative per unit. Research: `docs/research/2026-10-10-landscape.md`.

## State today (evidence)

- Phases 0-7 shipped; 8-9 are optional (PR #9 marks them so). `RUN_LIVE=0 pytest -q` exits 0.
- `dev_server.py` is 1655 lines; lines 94-1288 are `HTML_TEMPLATE`, a fallback page that is never served while `dashboard/run_center.html` exists (`do_GET`, line ~1305).
- TTFT is an estimate (`latency_ms x 0.25`).
- CI smokes four harnesses; `probe.harness` is not in `.github/workflows/ci.yml`.
- Three UI surfaces (`dashboard/run_center.html`, `viz/index.html`, `caesar/chat.html`) with three unrelated palettes. Token and chrome unification started in this PR (see U9).

## Now

### U1. Delete the dead `HTML_TEMPLATE` fallback
- Status: not started. Evidence: `dev_server.py` 94-1288, referenced once at ~1314.
- Difficulty: easy. About 1200 lines, one reference; tests in `tests/test_dev_server.py` show what is covered.
- Feasibility: none. Check no test imports `HTML_TEMPLATE` first.
- Simpler alternative: this is the simplification. If the fallback must stay, replace with a 5-line "run_center.html missing" message.
- Depends on: none. Verification: `pytest -q`, GET `/` returns run_center.

### U2. Measured TTFT via streaming
- Status: not started. Evidence: README "Metrics" section; `src/openrouter.py`.
- Difficulty: medium. Streaming path in `src/openrouter.py` plus stub fixtures that carry a first-token timestamp.
- Feasibility: needs a live key to validate against real providers (costs a few cents); offline path can be tested with fixtures. OpenRouter streaming is documented.
- Simpler alternative: keep the estimate and say so (already done). Cheapest real version: stream only in bakeoff, not in the other harnesses.
- Depends on: none. Verification: offline test for stub streaming; one blessed live run recorded in `bakeoff/launch_note.md`.

### U3. Add the probe harness to CI and a lint step
- Status: not started. Evidence: `ci.yml` runs deflect, motion, bakeoff, caesar only.
- Difficulty: easy. Two workflow lines plus `ruff` config.
- Feasibility: public repo, hosted CI works. Avoid editing the same lines as PR #7 (AGENTS.md only).
- Simpler alternative: fold the harness smokes into one `pytest` marker so CI and local share one command (`bin/setup.sh` already runs the same four smokes).
- Verification: CI green.

## Next

### U4. Refresh `src/models.json` from the OpenRouter models endpoint
- Status: not started. Evidence: static 32 curated + ~415 all; the README says "~415".
- Difficulty: easy. A script under `scripts/` that writes the file.
- Feasibility: the public models list needs no key and no spend; the curated list stays hand-edited. Slugs drift, so a refresh also needs a stale-slug check in tests.
- Simpler alternative: stop shipping the "All Models" list; fetch it at dashboard load.
- Verification: `tests/test_dev_server.py` model endpoint test still passes.

### U5. Gate with variance, not one pass
- Status: not started. Evidence: `bakeoff/baseline.json` thresholds on a single run.
- Difficulty: medium. Repeat each case N times, gate on mean and spread; schema change in `results/bakeoff.json` and `src/db.py`.
- Feasibility: live repeats multiply cost by N; offline stubs are deterministic so the feature is only meaningful live.
- Simpler alternative: report spread only (no gate change).
- Depends on: U2 (same runner). Verification: `tests/test_bakeoff.py` with a noisy stub.

### U6. Split `dev_server.py` by route group
- Status: not started. After U1 it is about 460 lines; split only if it grows.
- Difficulty: medium. Risk is handler state shared across routes.
- Feasibility: none external.
- Simpler alternative: skip. After U1 the file is small enough; do not split for its own sake.

### U7. Export results as JSONL for promptfoo / Inspect
- Status: not started. Evidence: landscape doc, "export" expectation.
- Difficulty: medium. Mapping each harness result to a neutral row schema.
- Feasibility: target schemas change upstream; pin to a documented one.
- Simpler alternative: one flat `results/all.jsonl` with documented columns; let users adapt.

### U8. Share one CSS token file across the three web surfaces
- Status: partly done here (tokens in `run_center.html` only).
- Difficulty: easy. Serve `/assets/tokens.css` (the server already serves static files).
- Feasibility: `caesar/chat.html` is deliberately a serif transcript; share colour tokens only.
- Simpler alternative: leave the viz and Caesar pages on their own palettes (current state) and only keep focus and favicon in sync.

## Later

### U9. Blessed live run and launch note (optional, cost)
- Status: optional per PR #9. Difficulty: easy to execute, needs a key and about a dollar of spend.
- Feasibility: spend rules: use the cheap default model only.
- Simpler alternative: link the committed baked run as the evidence (current state).

### U10. Use OpenRouter-reported cost instead of local price tables
- Status: not started; check `docs/OPENROUTER_OBSERVABILITY.md` for what is already read.
- Difficulty: medium. Feasibility: depends on the usage fields OpenRouter returns for each provider; verify before relying.
- Simpler alternative: keep the current table.

## Overlap with open PRs

- PR #9 (draft, `docs/close-application-roadmap`) edits `ROADMAP.md` (the Last-updated line, the phase 8-9 rows and sections) and `docs/APPLICATION-ROADMAP.md`. This PR adds a section at the top of `ROADMAP.md` and leaves the rest alone; a small textual conflict near the top of `ROADMAP.md` is possible and trivial to resolve. This plan treats phases 8-9 as optional, matching #9.
- PR #7 touches `AGENTS.md` only; no overlap.
