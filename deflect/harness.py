"""Run labeled tickets through the agent. Score structured fields, not reply text."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

from deflect.agent import Agent, AgentResult
from src.guardrails import guardrail_violation_for_eval
from src.openrouter import ChatClient, OpenRouterClient, StubClient, load_dotenv

ROOT = Path(__file__).resolve().parents[1]
CASES_PATH = Path(__file__).resolve().parent / "cases.jsonl"
STUB_A = Path(__file__).resolve().parent / "fixtures" / "stub_a.json"
RESULTS_PATH = ROOT / "results" / "deflect.json"


def load_cases(path: Path = CASES_PATH) -> list[dict[str, Any]]:
    if not path.is_file():
        raise FileNotFoundError(f"cases file not found: {path}")
    cases: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as fh:
        for lineno, raw in enumerate(fh, 1):
            line = raw.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{lineno} is not JSON") from exc
            for key in ("id", "ticket", "expected_action", "expected_category"):
                if key not in row:
                    raise ValueError(f"{path}:{lineno} missing {key}")
            cases.append(row)
    if not cases:
        raise ValueError(f"{path} has no cases")
    return cases


def build_client(*, live: bool | None = None, model: str | None = None) -> ChatClient:
    load_dotenv()
    want_live = os.environ.get("RUN_LIVE", "0") == "1" if live is None else live
    key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if want_live:
        if not key:
            raise RuntimeError("RUN_LIVE=1 requires OPENROUTER_API_KEY")
        return OpenRouterClient(model=model)
    stub = StubClient.from_fixture_path(STUB_A, model=model or "stub/capable")
    stub.index_tickets(load_cases())
    return stub


def score_case(case: dict[str, Any], result: AgentResult) -> dict[str, Any]:
    action_ok = result.action == case["expected_action"]
    category_ok = result.category == case["expected_category"]
    violated = guardrail_violation_for_eval(
        ticket=case["ticket"],
        final_action=result.action,
        final_reply=result.reply,
        must_not_deflect=bool(case.get("must_not_deflect")),
    )
    return {
        "id": case["id"],
        "expected_action": case["expected_action"],
        "actual_action": result.action,
        "proposed_action": result.proposed_action,
        "expected_category": case["expected_category"],
        "actual_category": result.category,
        "action_ok": action_ok,
        "category_ok": category_ok,
        "guardrail_ok": not violated,
        "overridden": result.overridden,
        "flags": result.guardrail_flags,
        "faq_hits": result.faq_hits,
        "cost_usd": result.cost_usd,
        "latency_ms": result.latency_ms,
        "model": result.model,
        "reason": result.reason,
    }


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    n = len(rows)
    if n == 0:
        raise ValueError("no scored rows")
    action_hits = sum(1 for r in rows if r["action_ok"])
    category_hits = sum(1 for r in rows if r["category_ok"])
    guardrail_hits = sum(1 for r in rows if r["guardrail_ok"])
    return {
        "n": n,
        "action_accuracy": round(action_hits / n, 4),
        "category_accuracy": round(category_hits / n, 4),
        "guardrail_pass_rate": round(guardrail_hits / n, 4),
        "total_cost_usd": round(sum(r["cost_usd"] for r in rows), 6),
        "mean_latency_ms": round(sum(r["latency_ms"] for r in rows) / n, 2),
        "overrides": sum(1 for r in rows if r["overridden"]),
        "model": rows[0].get("model"),
        "cases": rows,
    }


def run_eval(
    *,
    client: ChatClient | None = None,
    cases: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    cases = cases if cases is not None else load_cases()
    client = client if client is not None else build_client()
    agent = Agent(client)
    rows: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    for case in cases:
        try:
            result = agent.run(case["ticket"], case_id=case["id"])
        except Exception as exc:
            errors.append({"id": case["id"], "error": f"{type(exc).__name__}: {exc}"})
            continue
        rows.append(score_case(case, result))
    if errors:
        # Fail loud: a crashed case is not a silent 0.0 accuracy.
        detail = "; ".join(f"{e['id']}: {e['error']}" for e in errors)
        raise RuntimeError(f"{len(errors)} case(s) failed: {detail}")
    return summarize(rows)


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    out_path = RESULTS_PATH
    if "--out" in argv:
        i = argv.index("--out")
        out_path = Path(argv[i + 1])
    summary = run_eval()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {k: v for k, v in summary.items() if k != "cases"}
    payload["cases"] = [
        {k: v for k, v in row.items() if k != "reason"} | {"reason": row["reason"]}
        for row in summary["cases"]
    ]
    out_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    header = f"{'metric':<22} {'value':<16}"
    divider = "-" * 40
    lines = [
        "=================== Support Deflection Summary ===================",
        header,
        divider,
        f"{'Model':<22} {summary['model']:<16}",
        f"{'Cases (n)':<22} {summary['n']:<16}",
        f"{'Action Accuracy':<22} {summary['action_accuracy']*100:.1f}%",
        f"{'Category Accuracy':<22} {summary['category_accuracy']*100:.1f}%",
        f"{'Guardrail Pass Rate':<22} {summary['guardrail_pass_rate']*100:.1f}%",
        f"{'Mean Latency':<22} {summary['mean_latency_ms']:.1f} ms",
        f"{'Total Cost':<22} ${summary['total_cost_usd']:.6f}",
        f"{'Policy Overrides':<22} {summary['overrides']:<16}",
        divider,
        f"Wrote results: {out_path}",
        "=================================================================="
    ]
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
