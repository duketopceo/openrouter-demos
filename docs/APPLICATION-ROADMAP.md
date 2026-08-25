# OpenRouter Application — Final Phase Roadmap

**Status:** In progress — wrapping up the deliverable.
**Date:** 2026-08-20

---

## 1. Portfolio baked viewer (separate from local dashboard)

- **Portfolio URL:** https://luke-the-duke.com/openrouter — replays committed offline artifacts from `duketopceo/openrouter-demos`; **not** `dev_server.py`
- **Local dashboard:** `python3 dev_server.py` → http://localhost:8080 — run harnesses, pytest, and live API tests from this repo
- Portfolio page shows pre-baked stub/offline bakeoff JSON for reviewers without an API key
- Session-only API key on the portfolio site (if present) is separate from this Python server
- **Repo:** `duketopceo/openrouter-demos` (public)

## 2. Two Resumes (DONE)

### Resume A — Applied AI Engineer (support/GTM) ✅
- 1-page, titled **Applied AI** (support OR GTM, not both)
- Open with **live demo URL** (`luke-the-duke.com/openrouter`)
- Then Khan, Kurultai, Bartlett helpdesk (support/GTM proof)
- **Pace demoted** to a single line in projects
- **Measured impact** line: "Helpdesk dashboard replaced follow-up spreadsheets — manual reporting dropped from daily to weekly"
- File: `luke-kimball-applied-ai.docx/.pdf`

### Resume B — Provider Operations & Support Engineer ✅
- Second resume, same facts, new order
- **Headline:** AI Provider Operations — Model Onboarding & Eval Engineering
- Harness speech = **one line**
- Opens with provider bakeoff demo (latency, cost, quality, launch gate, deprecation)
- BDH (Dragon Hatchling) launch-gate playbook prominent
- File: `luke-kimball-provider-ops.docx/.pdf`

## 3. Cover Notes (TODO)

### Applied AI (3 sentences)
1. You build internal tools instead of buying them.
2. You shipped a support-deflection demo with guardrails, probe failures, and trace replay.
3. You want the last 20% applied to OpenRouter support or GTM, not your own stack.

### Provider Ops (no harness speech)
- Lead with Deflect, Motion, Bakeoff, and Probe — not Caesar debate.
- You already debug OpenRouter providers with keys, logs, and token usage.
- You want to turn that into launch playbooks and internal evals.

## 4. Demo Walkthrough (TODO)

- **Fail on purpose:** show a blocked tool call, an RLS halt, a bad classification caught by a guardrail.
- Green-path demos look like the first 80% — the failures are the job.

## 5. Take-Home Standard (Provider Ops)

30-minute playbook:
1. New model
2. cURL against Chat Completions
3. Fixture eval
4. Pass/fail gate
5. Changelog

## 6. Application Order

- **Apply to Provider Ops first** for the interview.
- **Apply to Applied AI only after** the demo shows a failed gate and a measured support or GTM motion.

---

## Key Decisions
- Two separate packets, never one merged resume.
- BDH shown as honest research dossier, not a fake benchmark.
- Session-only key for the public demo — operator key never powers the public page.

## Files
- Resumes: `~/Documents/Resumes/luke-kimball-openrouter.docx/.pdf` (Applied AI) + Provider Ops variant (to create)
- Demo repo: `~/workspace/openrouter-demos`
- Portfolio: `~/workspace/portfolio-hub` (`src/app/openrouter/`, `src/data/bakeoff.json`)
