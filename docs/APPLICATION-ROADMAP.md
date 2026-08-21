# OpenRouter Application — Final Phase Roadmap

**Status:** In progress — wrapping up the deliverable.
**Date:** 2026-08-20

---

## 1. Live Demo (DONE — live on Railway)

- **URL:** https://luke-the-duke.com/openrouter
- **Interactive dashboard** on the portfolio page:
  - Pre-baked 3-model bakeoff (Qwen 3.8-27b, Muse Glimmer 30B, Gemma 4 31B) — **no API key needed to view** (75 real API runs committed as `src/data/bakeoff.json`)
  - Session-only API key field (sessionStorage, auto-cleared on refresh, never stored server-side)
  - Live test runner against the user's own OpenRouter key
  - 4 demo cards (Deflect, Motion, Bakeoff, Caesar) with source links
- **BDH (Dragon Hatchling) research dossier** added — Pathway's post-transformer architecture, honest research-preview framing with launch-gate eval playbook (not a fake benchmark)
- **Repo:** `duketopceo/openrouter-demos` (public), README updated to note Railway hosting

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
2. You shipped a support-deflection demo with guardrails and trace replay.
3. You want the last 20% applied to OpenRouter support or GTM, not your own stack.

### Provider Ops (no harness speech)
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
