"""Run bakeoff cases once per model — for multi-model comparison sweeps."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

from bakeoff.runner import (
    BASELINE_PATH,
    CASES_PATH,
    RESULTS_PATH,
    launch_gate,
    load_baseline,
    load_cases,
    run_cases,
)
from src.openrouter import OpenRouterClient, StubClient, load_dotenv

ROOT = Path(__file__).resolve().parents[1]
STUB_A = Path(__file__).resolve().parent / "fixtures" / "stub_a.json"
SWEEP_RESULTS = ROOT / "results" / "bakeoff_sweep.json"


def _parse_models(raw: str | None) -> list[str]:
    if not raw or not raw.strip():
        return []
    return [m.strip() for m in raw.split(",") if m.strip()]


def _client_for_model(model_id: str, *, live: bool, cases: list[dict[str, Any]]) -> tuple[str, Any]:
    if live:
        key = os.environ.get("OPENROUTER_API_KEY", "").strip()
        if not key:
            raise RuntimeError("RUN_LIVE=1 requires OPENROUTER_API_KEY")
        return model_id, OpenRouterClient(model=model_id)
    client = StubClient.from_fixture_path(STUB_A, model=model_id)
    client.index_tickets(cases)
    return model_id, client


def run_sweep(models: list[str] | None = None) -> dict[str, Any]:
    load_dotenv()
    live = os.environ.get("RUN_LIVE", "0") == "1"
    models = models or _parse_models(os.environ.get("BAKEOFF_SWEEP_MODELS", ""))
    if not models:
        models = [
            os.environ.get("OPENROUTER_MODEL_A", "nvidia/nemotron-3.5-lightning").strip(),
        ]

    cases = load_cases(CASES_PATH)
    baseline = load_baseline(BASELINE_PATH)
    rows: list[dict[str, Any]] = []

    for model_id in models:
        name, client = _client_for_model(model_id, live=live, cases=cases)
        summary = run_cases(client, cases, label=f"sweep-{name}")
        gate = launch_gate(summary, baseline)
        row = {
            "model": name,
            "live": live,
            "gate": gate,
            **summary,
        }
        rows.append(row)

    payload = {
        "live": live,
        "baseline": baseline,
        "n_models": len(rows),
        "models": rows,
    }

    SWEEP_RESULTS.parent.mkdir(parents=True, exist_ok=True)
    SWEEP_RESULTS.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    try:
        from src.db import log_run

        for row in rows:
            log_run("bakeoff_sweep", row)
    except Exception:
        pass

    return payload


def main() -> int:
    payload = run_sweep()
    print(f"Bakeoff sweep: {payload['n_models']} model(s)")
    for row in payload["models"]:
        gate = "PASS" if row["gate"]["pass"] else "FAIL"
        print(
            f"  {row['model']:<40} quality={row['quality']:.3f} "
            f"lat={row['mean_latency_ms']:.0f}ms cost=${row['total_cost_usd']:.4f} {gate}"
        )
    print(f"Wrote {SWEEP_RESULTS}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
