# OpenRouter keys & CLI map

## Environment variables (this repo)

| Variable | Purpose | Required |
|----------|---------|----------|
| `OPENROUTER_API_KEY` | Bearer token for live API | Live only |
| `OPENROUTER_MODEL` | Primary model slug | Optional |
| `OPENROUTER_MODEL_A` / `MODEL_A` | Bakeoff / debate A | Optional |
| `OPENROUTER_MODEL_B` / `MODEL_B` | Bakeoff / debate B | Optional |
| `CAESAR_MODEL` | Judge model | Optional |
| `RUN_LIVE` | `1` = network, `0` = stubs | Default `0` |
| `OPENROUTER_HTTP_REFERER` | Attribution header | Recommended |
| `OPENROUTER_TITLE` | Attribution header | Recommended |

Copy `.env.example` → `.env`. Dashboard **Save Settings** writes the same file (never commit `.env`).

## Where keys might already live

| Location | How to check | Notes |
|----------|--------------|-------|
| Repo `.env` | `test -f .env && echo set` | Local only |
| `~/.env` | Dev server fallback reader | Shared homelab pattern |
| 1Password | Personal vault items tagged Cloudflare/OpenRouter | Use locally, never in video |
| Dashboard UI | `/api/key` returns masked key only | Safe for demos |
| GitHub Actions | Repo secrets `OPENROUTER_API_KEY` | CI live jobs only |
| Wrangler secrets | `wrangler secret list` on Workers projects | Unrelated to this Python repo |

## CLI entry points

```bash
./bin/setup.sh                    # venv + offline smoke
python3 dev_server.py             # dashboard :8080
python3 scripts/record_demo.py    # demo video
./scripts/upload_demo_r2.sh       # R2 publish
pytest                            # offline (no key)
RUN_LIVE=1 python -m deflect.harness   # live (key required)
```

## OpenRouter platform CLI (external)

OpenRouter does not ship a first-party `openrouter` shell CLI. Typical integrations:

- **curl / httpx** — direct REST
- **OpenAI SDK** — base URL `https://openrouter.ai/api/v1`
- **LiteLLM** — provider alias `openrouter/...`
- **Management API** — keys, credits, usage (separate from chat completions)

## Management key (spending / usage) — future hook

For a spending dashboard (Khan-style), store a **management** or **provisioning** key separately from inference keys. This repo only uses inference keys for harness runs.
