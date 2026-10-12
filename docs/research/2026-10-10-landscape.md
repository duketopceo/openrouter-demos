# Landscape: who else does this

Scope: offline-first eval harnesses and a run dashboard for gateway-style LLM work (routing, bakeoffs, guardrail probes), built against OpenRouter. Read on 2026-10-11 from each project's GitHub README or docs page (linked). Claims about this repo come from its code and README.

## Comparable projects

| Project | What it is | Better than this repo | Worse / different |
|---|---|---|---|
| [promptfoo](https://github.com/promptfoo/promptfoo) (MIT) | CLI and library for evals and red teaming; side-by-side model comparison across providers | Declarative configs, many providers, real red-team suites, caching | General purpose: no bundled support/GTM/provider-ops cases, no launch-gate baseline file |
| [Inspect AI](https://github.com/UKGovernmentBEIS/inspect_ai) (MIT, UK AISI) | Eval framework with 200+ pre-built evals, tool use, multi-turn, model-graded scoring | Rigor, ecosystem, scorers | Heavier; not a small readable demo; no gateway-ops framing |
| [LiteLLM](https://github.com/BerriAI/litellm) | Open-source gateway to 100+ providers; router with retries and fallbacks; per-user spend tracking | Production routing, budgets, virtual keys | It is the gateway, not an eval harness; enterprise features under a commercial licence |
| [Helicone](https://github.com/Helicone/helicone) (Apache-2.0) | AI gateway plus observability: traces, sessions, cost, latency | Real traces and analytics over live traffic | Hosted/self-hosted service; no offline fixtures or gate |
| [Langfuse](https://github.com/langfuse/langfuse) (MIT, `ee` excluded) | Observability, prompt management, datasets, LLM-as-judge evals | Datasets, judge evals, UI maturity | Needs a running service; not a one-command offline replay |
| [OpenRouter provider routing](https://openrouter.ai/docs/features/provider-routing) | The platform itself: provider order, fallbacks, sort by price/throughput/latency | Actual routing | Does not give you a pass/fail launch gate for a model; that gap is what `bakeoff/` demos |

## What users expect

- Offline-reproducible runs with no key (promptfoo caching, Inspect fixtures). This repo has it: `RUN_LIVE=0` stub fixtures plus a committed baked run in `demo/baked/`.
- Measured latency, TTFT and cost, not estimates. This repo's TTFT is `latency_ms x 0.25` on non-streaming calls and is labelled as an estimate (README, `docs/OPENROUTER_OBSERVABILITY.md`). That is honest but is the weakest metric.
- Fallbacks and routing visible in results. Not covered yet.
- Export to common formats (JSONL, other tools). Results are repo-specific JSON plus SQLite.

## What is unique here

1. A compact, readable set of five cases tied to a hiring story (support deflection, GTM next-action, provider bakeoff with a gate, guardrail probe that fails on purpose, Caesar debate trace replay).
2. Everything runs with no key, tests included (CI runs offline pytest and four harness smokes).
3. A committed baked run that a reviewer can replay in one click.

## Implications for the roadmap

- Measure TTFT with streaming before anything else; it is the visible credibility gap.
- Do not compete on breadth with promptfoo or Inspect; export to them instead of reimplementing scorers.
- Keep the dashboard small: it is a demo surface, not Langfuse.
