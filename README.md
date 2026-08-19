# RouteKit demos for OpenRouter

Hiring artifact for **Luke Kimball** — three working demos, one repo. Synthetic product is **RouteKit**, a fake OpenAI-compatible LLM gateway. No real customers, no PII, no production metrics.

The last 20% is the point: structured actions, deterministic guardrails, evals that do not brittle-match full replies, and a launch gate you can run without an API key.

| Demo | Job | What it actually does |
| --- | --- | --- |
| `deflect/` | Applied AI Engineer — **support seat** | Ticket → `deflect` / `draft` / `escalate` via OpenRouter tool calls. FAQ grounding. Guardrails block invented refunds/account changes and false-deflect of angry/legal/jailbreak. |
| `motion/` | Applied AI Engineer — **GTM seat** | Inbound note → `reply` / `qualify` / `book` / `escalate_human`. Playbook grounding. Cannot mint discounts, credits, or calendar holds. |
| `bakeoff/` | **AI Provider Operations** | Same 12 quality prompts on MODEL_A vs MODEL_B. Scores latency, cost, structured quality. Launch gate vs `bakeoff/baseline.json`. |

Shared: `src/openrouter.py` (POST `https://openrouter.ai/api/v1/chat/completions`) and `src/guardrails.py`.

This is a demonstrated artifact, not a deployed system. There are no invented deflection rates, token volumes, or live accuracy numbers here.

## Run

`OPENROUTER_API_KEY` is required for live calls. **`pytest` still runs against fixtures** when the key is missing.

```bash
cd openrouter-demos
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

pytest
python -m deflect.harness
python -m motion.harness
python -m bakeoff.runner
```

Live (optional):

```bash
export OPENROUTER_API_KEY=sk-or-...
export RUN_LIVE=1
python -m deflect.harness
python -m motion.harness
python -m bakeoff.runner          # OPENROUTER_MODEL_A / OPENROUTER_MODEL_B
```

Results land in `results/` (gitignored). Offline `total_cost_usd` is 0. Live cost is whatever OpenRouter returns on `usage.cost`, or 0 if omitted — we do not estimate token prices.

## Design choices

- **Tools, not prose.** Agents must call allowlisted tools. Freeform text is untrusted and still goes through policy.
- **Policy only upgrades severity** (support) or **un-books / escalates** (GTM). A sloppy model that over-escalates how-tos hurts accuracy (human load). A sloppy model that under-deflects legal/angry tickets gets overridden.
- **Scoring is structured.** Action/category/rubric fields — not full-string match of the customer reply.
- **Provider Ops bakeoff** is the onboarding loop: compare two slugs, fail the gate on quality regression vs `bakeoff/baseline.json`, fill `bakeoff/launch_note.md` by hand with *measured* numbers.
- **Offline CI.** Two stub “models” (`stub/capable`, `stub/sloppy`) so every harness works without a key.

## Layout

```
src/openrouter.py src/guardrails.py
deflect/   agent.py faq.py cases.jsonl harness.py
motion/    agent.py playbook.py cases.jsonl harness.py
bakeoff/   runner.py cases.jsonl baseline.json launch_note.md
tests/
```
