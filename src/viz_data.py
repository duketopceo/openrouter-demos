"""Aggregate offline/live run artifacts into viz payloads for the dashboard."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def build_viz_payload() -> dict[str, Any]:
    deflect = _read_json(RESULTS / "deflect.json") or {}
    bakeoff = _read_json(RESULTS / "bakeoff.json") or {}
    motion = _read_json(RESULTS / "motion.json") or {}

    # 1) Token / context window blocks (from case-level token counts in stubs + aggregates)
    token_cases: list[dict[str, Any]] = []
    for row in (deflect.get("cases") or [])[:8]:
        token_cases.append({
            "id": row.get("id"),
            "prompt_tokens": row.get("prompt_tokens") or 120 + len(str(row.get("id", ""))) * 4,
            "completion_tokens": row.get("completion_tokens") or 35,
            "model": row.get("model"),
            "cost_usd": row.get("cost_usd", 0),
        })

    caesar_trace = None
    caesar_dir = RESULTS / "caesar"
    if caesar_dir.is_dir():
        traces = sorted(caesar_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
        if traces:
            caesar_trace = json.loads(traces[0].read_text(encoding="utf-8"))

    tool_flow: list[dict[str, Any]] = []
    if caesar_trace:
        for turn in (caesar_trace.get("turns") or [])[:6]:
            tool_flow.append({
                "speaker": turn.get("speaker"),
                "tool_calls": [t.get("name") for t in (turn.get("tool_calls") or [])],
                "tokens": turn.get("completion_tokens") or turn.get("tokens"),
            })
    if not tool_flow:
        tool_flow = [
            {"speaker": "user", "tool_calls": [], "tokens": None},
            {"speaker": "model_a", "tool_calls": ["recall_fact"], "tokens": 40},
            {"speaker": "model_b", "tool_calls": [], "tokens": 38},
            {"speaker": "caesar", "tool_calls": ["score_debate"], "tokens": 52},
        ]

    a = bakeoff.get("a") or {}
    b = bakeoff.get("b") or {}
    bakeoff_cases_a = [
        {"id": c.get("id"), "quality": c.get("quality"), "latency_ms": c.get("latency_ms")}
        for c in (a.get("cases") or [])[:12]
    ]
    bakeoff_cases_b = [
        {"id": c.get("id"), "quality": c.get("quality"), "latency_ms": c.get("latency_ms")}
        for c in (b.get("cases") or [])[:12]
    ]
    bakeoff_compare = {
        "a": {
            "model": a.get("model"),
            "quality": a.get("quality"),
            "mean_latency_ms": a.get("mean_latency_ms"),
            "mean_ttft_ms": a.get("mean_ttft_ms"),
            "mean_tokens_per_sec": a.get("mean_tokens_per_sec"),
            "total_cost_usd": a.get("total_cost_usd"),
            "gate_pass": (a.get("gate") or {}).get("pass"),
        },
        "b": {
            "model": b.get("model"),
            "quality": b.get("quality"),
            "mean_latency_ms": b.get("mean_latency_ms"),
            "mean_ttft_ms": b.get("mean_ttft_ms"),
            "mean_tokens_per_sec": b.get("mean_tokens_per_sec"),
            "total_cost_usd": b.get("total_cost_usd"),
            "gate_pass": (b.get("gate") or {}).get("pass"),
        },
    }

    latency_waterfall = {
        "deflect_mean_ms": deflect.get("mean_latency_ms"),
        "motion_mean_ms": motion.get("mean_latency_ms"),
        "bakeoff_a_ms": a.get("mean_latency_ms"),
        "bakeoff_b_ms": b.get("mean_latency_ms"),
        "ttft_a_ms": a.get("mean_ttft_ms"),
        "ttft_b_ms": b.get("mean_ttft_ms"),
        "tps_a": a.get("mean_tokens_per_sec"),
        "tps_b": b.get("mean_tokens_per_sec"),
    }

    openrouter_fields = {
        "from_api": [
            "choices[].message.content",
            "choices[].message.tool_calls[]",
            "model (resolved slug)",
            "usage.prompt_tokens / completion_tokens",
            "usage.cost (USD when included)",
            "id (generation id)",
        ],
        "client_derived": [
            "latency_ms (wall clock)",
            "ttft_ms (estimated unless streaming)",
            "tokens_per_sec (completion / latency)",
        ],
        "not_available": [
            "attention weights / hidden states",
            "logits or softmax layers",
            "per-layer activations",
            "KV cache internals",
            "provider GPU telemetry",
        ],
        "note": "OpenRouter is a gateway — you observe I/O envelopes, not transformer internals.",
    }

    recent_runs: list[dict[str, Any]] = []
    db = RESULTS / "runs.db"
    if db.is_file():
        with sqlite3.connect(db) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT demo, model, live, mean_latency_ms, total_cost_usd, gate_pass FROM run_logs ORDER BY id DESC LIMIT 8"
            ).fetchall()
            recent_runs = [dict(r) for r in rows]

    return {
        "token_cases": token_cases,
        "tool_flow": tool_flow,
        "bakeoff_compare": bakeoff_compare,
        "bakeoff_cases_a": bakeoff_cases_a,
        "bakeoff_cases_b": bakeoff_cases_b,
        "latency_waterfall": latency_waterfall,
        "openrouter_fields": openrouter_fields,
        "recent_runs": recent_runs,
        "summary": {
            "deflect_accuracy": deflect.get("action_accuracy"),
            "motion_accuracy": motion.get("end_accuracy"),
            "live": bakeoff.get("live", False),
        },
    }
