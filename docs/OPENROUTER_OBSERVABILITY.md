# OpenRouter observability — what you get vs transformer internals

OpenRouter is an **inference gateway**. It routes requests to upstream providers and returns API-shaped results. You do **not** get model weights, attention maps, or layer activations.

## Available from `POST /api/v1/chat/completions`

| Field | Source | Used in this repo |
|-------|--------|-------------------|
| `choices[].message.content` | Response body | Harness output / rubric checks |
| `choices[].message.tool_calls[]` | Response body | Deflect, motion, Caesar agents |
| `model` | Response (resolved slug) | Logging, bakeoff compare |
| `usage.prompt_tokens` | Response | Token context viz |
| `usage.completion_tokens` | Response | Token context viz, TPS |
| `usage.cost` | Response (when `usage.include: true`) | Cost totals, bakeoff gate |
| `id` | Response | Generation id (`ChatResponse.generation_id`) |

## Client-derived (not in raw JSON)

| Metric | How computed here |
|--------|-------------------|
| `latency_ms` | Wall clock around HTTP POST |
| `ttft_ms` | Estimated from latency × 0.25 unless streaming |
| `tokens_per_sec` | `completion_tokens / (latency_ms/1000)` |

## Not available (true transformer viz impossible via gateway)

- Attention weight matrices
- Hidden states / logits
- Per-layer KV cache
- GPU/kernel telemetry from the provider

**Practical substitute:** three gateway-level views in `/viz/` — token envelopes, bakeoff economics, tool-call routing graph.

## Streaming (optional extension)

With `stream: true`, you can measure **real TTFT** from first SSE chunk. This repo uses non-streaming completions for simpler tool-call parsing.

## Related docs

- `docs/KEYS_AND_CLI.md` — env vars, wrangler, credential surfaces
- Live dashboard: `http://localhost:8080/viz/`
