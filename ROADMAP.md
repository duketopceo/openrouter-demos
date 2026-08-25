# OpenRouter Demos — Roadmap

**Repo:** [duketopceo/openrouter-demos](https://github.com/duketopceo/openrouter-demos)  
**Purpose:** RouteKit hiring harnesses on OpenRouter — support deflection, GTM motion, provider bakeoff, guardrail probe, Caesar debate. RouteKit is a synthetic stand-in, not OpenRouter.  
**Last updated:** 2026-08-25

---

## Status at a glance

| Phase | Scope | Status |
|-------|--------|--------|
| 0 | Repo scaffold + harnesses | ✅ Done |
| 1 | Local dashboard (`dev_server.py`) | ✅ Done |
| 2 | Offline fixtures + pytest | ✅ Done |
| 3 | Metrics (est. TTFT, TPS, cost, SQLite logger) | ✅ Done |
| 4 | Caesar trace replay viewer | ✅ Done |
| 5 | CI + bootstrap + bugfixes | ✅ Done |
| 6 | Harden + ship (streaming, baked demo, model catalog) | ✅ Done |
| 7 | Portfolio hub integration (luke-the-duke.com) | ✅ Done (2026-08-20) |
| 8 | Live OpenRouter run + bakeoff sign-off | 🔳 Pending — needs a blessed live run + filled `launch_note.md` |
| 9 | Submission polish (walkthrough redo, launch note) | 🔳 Partial (README link + topics done) |

---

## Phase 0–4 — Built (shipped on `main`)

### Harnesses (Provider Ops first)

1. **Support Deflection** (`deflect/`) — 20 synthetic tickets → classify → deflect / draft / escalate with FAQ + guardrails.
2. **GTM Motion** (`motion/`) — inbound lead qualification → structured next action (not prose scoring).
3. **Provider Ops Bakeoff** (`bakeoff/`) — head-to-head quality, latency, **estimated TTFT**, TPS, cost; gate vs `baseline.json`.
4. **Guardrail Probe** (`probe/`) — fail-on-purpose: upstream blocks vs refusals vs leaks on jailbreak prompts.
5. **Caesar Debate** (`caesar/`) — two models debate; Caesar judges; JSON traces replay in `caesar/chat.html` (secondary showcase).

### Shared infrastructure

- `src/openrouter.py` — live HTTP client + offline stub replay (tool calls supported).
- `src/guardrails.py` — policy checks (jailbreak, invented policy, exploit language).
- `src/db.py` — SQLite run log at `results/runs.db` with two-sentence summaries.
- `src/models.json` — 32 curated + 415 all OpenRouter slugs for the dashboard picker.

### Entry points

```bash
./bin/setup.sh          # venv + deps + offline smoke
python3 dev_server.py   # dashboard at http://localhost:8080
pytest                  # offline only (RUN_LIVE=0)
```

---

## Phase 5 — Wrap-up (2026-08-19)

Completed in this session:

- [x] Clone to `~/Documents/Dev/github/duketopceo/openrouter-demos`
- [x] Fix `/api/caesar-traces` crash (`import time` missing in `dev_server.py`)
- [x] Add `bin/setup.sh` one-command bootstrap
- [x] Add GitHub Actions CI (offline pytest on push/PR)
- [x] Add `tests/test_dev_server.py` for API smoke
- [x] Document roadmap (this file)

---

## Phase 6 — Harden + ship (2026-08-19 → 2026-08-20)

Post-build polish shipped on `main` (PRs #1–#3 + follow-on commits):

- [x] README rewrite for local dashboard (PR #1)
- [x] Stream harness progress + live Caesar debate follow-along (PR #2)
- [x] Baked full offline demo — one-click, no API key (PR #3); `POST /api/run-baked-stream` wired
- [x] Curated Heavy Hitters model catalog toggle (32 top slugs vs ~415 all)
- [x] Automatic trace loader + dropdown selector in Caesar Debate UI
- [x] SQLite run logger (`src/db.py`) + fast AI 2-sentence run summaries
- [x] Standardized pretty-print table rendering across all harnesses
- [x] Explicit error reasons + failure details in logs and bakeoff output
- [x] Native grouped HTML select dropdowns on all model menus; default `nvidia/nemotron-3.5-lightning`

---

## Phase 7 — Portfolio hub integration (2026-08-20)

`openrouter-demos` is a curated, featured project on **[luke-the-duke.com](https://luke-the-duke.com)** (the `duketopceo/portfolio-hub` Next.js site):

- [x] Entry added to `portfolio-hub/src/data/projects.ts` — slug `openrouter-demos`, category `ai`, `featured: true`
- [x] Public repo (`duketopceo/openrouter-demos`) enriches live via GitHub API — stars, language, README
- [x] Walkthrough video wired as `demoVideoUrl` → Cloudflare R2 (`openrouter-demos-walkthrough.mp4`)
- [x] Dossier page renders at `luke-the-duke.com/projects/openrouter-demos`
- [x] Separate baked viewer at `luke-the-duke.com/openrouter` — replays committed offline artifacts; **not** this repo’s `dev_server.py`

The portfolio page is a static/baked replay surface. The **local dashboard** remains `python3 dev_server.py` → `http://localhost:8080`.

---

## Phase 8 — Live demo run + bakeoff sign-off

**Status: 🔳 Pending.** Offline stubs pass the gate in CI; a **blessed live bakeoff** with real API numbers has not been committed to `bakeoff/launch_note.md`.

Requires `OPENROUTER_API_KEY` and `RUN_LIVE=1`.

### Checklist

1. **Bootstrap**
   ```bash
   cd ~/Documents/Dev/github/duketopceo/openrouter-demos
   ./bin/setup.sh
   cp .env.example .env
   # paste key into .env or use dashboard Save Settings
   ```

2. **Start local dashboard**
   ```bash
   python3 dev_server.py
   ```
   Open http://localhost:8080

3. **Run harnesses live** — click **Run All Live Demos** or run individually:
   ```bash
   RUN_LIVE=1 python -m deflect.harness
   RUN_LIVE=1 python -m motion.harness
   RUN_LIVE=1 python -m bakeoff.runner
   RUN_LIVE=1 python -m probe.harness
   RUN_LIVE=1 python -m caesar.harness
   ```

4. **Bakeoff gate** — read `results/bakeoff.json`:
   - `gate.pass` must be `true` for promotion
   - Gate checks `min_quality`, `max_mean_latency_ms`, and `max_total_cost_usd` from `bakeoff/baseline.json`
   - If fail: adjust model slugs or update baseline with documented rationale

5. **Fill launch note** — copy numbers from `results/bakeoff.json` into `bakeoff/launch_note.md` (template below; do not invent values).

6. **Caesar replay** — open `/caesar/chat.html`, pick a trace from dropdown or upload JSON.

### Default models

| Role | Slug |
|------|------|
| Primary / Caesar judge | `nvidia/nemotron-3.5-lightning` |
| Bakeoff / debate B | `openai/gpt-4o-mini` |

Swap via dashboard or `.env` (`OPENROUTER_MODEL`, `OPENROUTER_MODEL_A`, `OPENROUTER_MODEL_B`).

---

## Phase 9 — Submission polish

For OpenRouter hiring / portfolio handoff:

- [x] Screen recording shipped to Cloudflare R2 + wired into portfolio hub (`openrouter-demos-walkthrough.mp4`, offline ~20s)
- [x] README links to ROADMAP (2026-08-20)
- [x] GitHub topics pinned: `openrouter`, `llm-evals`, `tool-calling` (2026-08-20)
- [x] Sanitized `demo/baked/results/` JSON committed for reviewers who skip live API
- [ ] **Redo walkthrough** — extend into a full live run recording (local dashboard → run live → results → Caesar replay); logged as a follow-up, not started
- [ ] **Launch note** — fill after Phase 8 live bakeoff

---

## Out of scope (intentional)

- Real PII or Bartlett data (synthetic cases only)
- Auth / multi-tenant (single-operator dev tool)
- Model fine-tuning or training pipelines
- Claiming measured TTFT without streaming (this repo uses `latency_ms × 0.25` as an estimate on non-streaming completions)

---

## File map

```
deflect/   motion/   bakeoff/   probe/   caesar/   # harnesses + cases + fixtures
src/       openrouter.py, db.py, guardrails.py, models.json
tests/     offline pytest (no network)
dev_server.py                              # local dashboard :8080
bin/setup.sh                               # bootstrap script
results/   gitignored outputs + runs.db
bakeoff/launch_note.md                     # fill after live sign-off
ROADMAP.md                                 # this file
```

---

## Quick health check

```bash
./bin/setup.sh && pytest -q && curl -s http://localhost:8080/api/models | head -c 80
# (start dev_server in another terminal for curl)
```

All green = ready for live API key and submission recording.
