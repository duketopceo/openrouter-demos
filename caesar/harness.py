"""Run debate topics offline (stubs) or live. Print a summary table; persist traces."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

from caesar.debate import run_debate
from caesar.trace import write_match
from src.openrouter import ChatClient, OpenRouterClient, StubClient, load_dotenv

ROOT = Path(__file__).resolve().parents[1]
HERE = Path(__file__).resolve().parent
CASES_PATH = HERE / "cases.jsonl"
STUB_A = HERE / "fixtures" / "stub_a.json"
STUB_B = HERE / "fixtures" / "stub_b.json"
STUB_CAESAR = HERE / "fixtures" / "stub_caesar.json"
RESULTS_DIR = ROOT / "results" / "caesar"

SLOPPY_CAESAR_TURN = {
    "content": json.dumps(
        {
            "winner_so_far": "a",
            "scores": {"a": 1, "b": 0},
            "points_this_round": {"a": 1, "b": 0},
            "concession_detected": True,
            "end": True,
            "reason": "I declare a concession.",
            "claims_a": [],
            "claims_b": [],
            "grounding": 0.5,
        }
    ),
    "latency_ms": 1.0,
    "cost_usd": 0.0,
    "prompt_tokens": 10,
    "completion_tokens": 10,
}


def load_cases(path: Path = CASES_PATH) -> list[dict[str, Any]]:
    if not path.is_file():
        raise FileNotFoundError(f"cases file not found: {path}")
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as fh:
        for lineno, raw in enumerate(fh, 1):
            line = raw.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{lineno} is not JSON") from exc
            for key in ("id", "topic", "side_a", "side_b", "expected_end"):
                if key not in row:
                    raise ValueError(f"{path}:{lineno} missing {key}")
            if row["expected_end"] not in ("concession", "max_rounds"):
                raise ValueError(
                    f"{path}:{lineno} expected_end must be concession|max_rounds"
                )
            rows.append(row)
    if not rows:
        raise ValueError(f"{path} has no cases")
    return rows


def _model_env(name: str, *alts: str, default: str) -> str:
    for key in (name, *alts):
        val = os.environ.get(key, "").strip()
        if val:
            return val
    return default


def _sloppy_caesar_client(cases: list[dict[str, Any]]) -> StubClient:
    fixture = {case["id"]: [dict(SLOPPY_CAESAR_TURN) for _ in range(24)] for case in cases}
    return StubClient(fixture=fixture, model="stub/sloppy-caesar")


def build_clients(
    *,
    live: bool | None = None,
    sloppy_caesar: bool = False,
) -> dict[str, ChatClient]:
    load_dotenv()
    want_live = os.environ.get("RUN_LIVE", "0") == "1" if live is None else live
    cases = load_cases()
    if want_live:
        key = os.environ.get("OPENROUTER_API_KEY", "").strip()
        if not key:
            raise RuntimeError("RUN_LIVE=1 requires OPENROUTER_API_KEY")
        model_a = _model_env("MODEL_A", "OPENROUTER_MODEL_A", default="openai/gpt-4.1-mini")
        model_b = _model_env(
            "MODEL_B", "OPENROUTER_MODEL_B", default="anthropic/claude-3.5-haiku"
        )
        model_c = _model_env(
            "CAESAR_MODEL", "OPENROUTER_CAESAR_MODEL", default="openai/gpt-4.1-mini"
        )
        return {
            "client_a": OpenRouterClient(model=model_a),
            "client_b": OpenRouterClient(model=model_b),
            "client_caesar": OpenRouterClient(model=model_c),
        }
    ca = StubClient.from_fixture_path(STUB_A, model="stub/capable-a")
    cb = StubClient.from_fixture_path(STUB_B, model="stub/capable-b")
    if sloppy_caesar:
        cc: ChatClient = _sloppy_caesar_client(cases)
    else:
        cc = StubClient.from_fixture_path(STUB_CAESAR, model="stub/caesar")
    return {"client_a": ca, "client_b": cb, "client_caesar": cc}


def score_case(case: dict[str, Any], match: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": case["id"],
        "expected_end": case["expected_end"],
        "actual_end": match["end"],
        "end_ok": match["end"] == case["expected_end"],
        "winner": match["winner"],
        "conceded_by": match.get("conceded_by"),
        "rounds": match["rounds"],
        "scores": match["scores"],
        "total_cost_usd": match["total_cost_usd"],
        "total_latency_ms": match["total_latency_ms"],
        "model_a": match["model_a"],
        "model_b": match["model_b"],
        "caesar_model": match["caesar_model"],
        "flags": match.get("flags") or [],
        "trace_turns": len(match["turns"]),
    }


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    n = len(rows)
    if n == 0:
        raise ValueError("no scored rows")
    end_hits = sum(1 for r in rows if r["end_ok"])
    return {
        "n": n,
        "end_accuracy": round(end_hits / n, 4),
        "concessions": sum(1 for r in rows if r["actual_end"] == "concession"),
        "max_rounds": sum(1 for r in rows if r["actual_end"] == "max_rounds"),
        "total_cost_usd": round(sum(r["total_cost_usd"] for r in rows), 6),
        "mean_latency_ms": round(sum(r["total_latency_ms"] for r in rows) / n, 2),
        "cases": rows,
    }


def run_eval(
    *,
    clients: dict[str, ChatClient] | None = None,
    cases: list[dict[str, Any]] | None = None,
    sloppy_caesar: bool = False,
    persist: bool = False,
    results_dir: Path = RESULTS_DIR,
) -> dict[str, Any]:
    cases = cases if cases is not None else load_cases()
    clients = clients if clients is not None else build_clients(sloppy_caesar=sloppy_caesar)
    rows: list[dict[str, Any]] = []
    matches: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    for case in cases:
        try:
            match = run_debate(case, **clients)
        except Exception as exc:
            errors.append({"id": case["id"], "error": f"{type(exc).__name__}: {exc}"})
            continue
        if persist:
            write_match(match, results_dir)
        matches.append(match)
        rows.append(score_case(case, match))
    if errors:
        detail = "; ".join(f"{e['id']}: {e['error']}" for e in errors)
        raise RuntimeError(f"{len(errors)} case(s) failed: {detail}")
    summary = summarize(rows)
    summary["matches"] = matches
    return summary


def render(summary: dict[str, Any]) -> str:
    header = (
        f"{'id':<22} {'end':<12} {'exp':<12} {'win':<4} "
        f"{'rnd':>3} {'cost':>8} {'lat_ms':>8} {'ok':>4}"
    )
    divider = "=" * 80
    lines = [
        "============================== Caesar Debate Summary ==============================",
        header,
        "-" * len(header)
    ]
    for row in summary["cases"]:
        ok = "Y" if row["end_ok"] else "N"
        lines.append(
            f"{row['id']:<22} {row['actual_end']:<12} {row['expected_end']:<12} "
            f"{str(row['winner']):<4} {row['rounds']:>3} "
            f"{row['total_cost_usd']:>8.4f} {row['total_latency_ms']:>8.1f} {ok:>4}"
        )
    lines.append("-" * len(header))
    lines.append(
        f"Cases (n)={summary['n']} | End Accuracy={summary['end_accuracy']*100:.1f}% | "
        f"Concessions={summary['concessions']} | Max Rounds={summary['max_rounds']} | "
        f"Total Cost=${summary['total_cost_usd']:.6f}"
    )
    lines.append(divider)
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    sloppy = "--sloppy" in argv
    out_dir = RESULTS_DIR
    if "--out" in argv:
        out_dir = Path(argv[argv.index("--out") + 1])
    summary = run_eval(sloppy_caesar=sloppy, persist=True, results_dir=out_dir)
    print(render(summary))
    print(f"\nwrote traces under {out_dir}")
    print("Replay: open caesar/chat.html and choose a results/caesar/<id>.json file.")
    print("Offline cost is 0. Live cost is usage.cost from OpenRouter, or 0 if omitted.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
