from pathlib import Path

from bakeoff.runner import compare, launch_gate, load_cases, render, run_cases, score_output
from src.openrouter import StubClient

ROOT = Path(__file__).resolve().parents[1]
STUB_A = ROOT / "bakeoff" / "fixtures" / "stub_a.json"
STUB_B = ROOT / "bakeoff" / "fixtures" / "stub_b.json"


def test_twelve_quality_prompts() -> None:
    cases = load_cases()
    assert len(cases) == 12
    blob = (ROOT / "bakeoff" / "cases.jsonl").read_text(encoding="utf-8")
    assert "Bartlett" not in blob


def test_rubric_is_not_full_string_match() -> None:
    rubric = {
        "expect_json": True,
        "required_keys": ["action"],
        "expected_fields": {"action": "escalate"},
    }
    a = score_output('{"action": "escalate", "extra": "noise is fine"}', rubric)
    b = score_output('{"action": "deflect"}', rubric)
    assert a["score"] == 1.0
    assert b["checks"]["expected_fields"] is False


def test_offline_capable_passes_gate() -> None:
    payload = compare()
    assert payload["live"] is False
    assert payload["a"]["gate"]["pass"] is True
    assert payload["a"]["quality"] >= 0.9
    assert payload["a"]["total_cost_usd"] == 0
    assert payload["b"]["gate"]["pass"] is False
    assert payload["a"]["quality"] > payload["b"]["quality"]
    table = render(payload)
    assert "PASS" in table and "FAIL" in table


def test_sloppy_jailbreak_fails_quality() -> None:
    cases = load_cases()
    client = StubClient.from_fixture_path(STUB_B, model="stub/sloppy")
    client.index_tickets(cases)
    summary = run_cases(client, [c for c in cases if c["id"] == "jailbreak-refuse"])
    assert summary["quality"] < 1.0


def test_launch_gate_reasons() -> None:
    gate = launch_gate(
        {"quality": 0.2, "mean_latency_ms": 10, "total_cost_usd": 0},
        {"min_quality": 0.9, "max_mean_latency_ms": 15000, "quality_epsilon": 0.05},
    )
    assert gate["pass"] is False
    assert gate["reasons"]
