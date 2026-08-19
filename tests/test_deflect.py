from pathlib import Path

from deflect.agent import SYSTEM_PROMPT, Agent
from deflect.faq import FAQ, search_faq
from deflect.harness import load_cases, run_eval
from src.openrouter import StubClient

ROOT = Path(__file__).resolve().parents[1]
STUB_A = ROOT / "deflect" / "fixtures" / "stub_a.json"
STUB_B = ROOT / "deflect" / "fixtures" / "stub_b.json"


def _stub(path: Path = STUB_A, model: str = "stub/capable") -> StubClient:
    client = StubClient.from_fixture_path(path, model=model)
    client.index_tickets(load_cases())
    return client


def test_twenty_cases_no_real_pii() -> None:
    cases = load_cases()
    assert len(cases) == 20
    assert {c["expected_action"] for c in cases} == {"deflect", "draft", "escalate"}
    blob = (ROOT / "deflect" / "cases.jsonl").read_text(encoding="utf-8")
    assert "Bartlett" not in blob


def test_faq_bounds_and_search() -> None:
    assert 8 <= len(FAQ) <= 12
    hits = search_faq("fallback model")
    assert hits and hits[0]["id"] == "routing.fallback"
    try:
        search_faq("  ")
    except ValueError:
        return
    raise AssertionError("empty query should raise")


def test_offline_harness() -> None:
    summary = run_eval(client=_stub())
    assert summary["n"] == 20
    assert summary["action_accuracy"] == 1.0
    assert summary["category_accuracy"] == 1.0
    assert summary["guardrail_pass_rate"] == 1.0
    assert summary["total_cost_usd"] == 0


def test_empty_ticket_raises() -> None:
    try:
        Agent(_stub()).run("  ")
    except ValueError as exc:
        assert "non-empty" in str(exc)
        return
    raise AssertionError("expected ValueError")


def test_system_prompt_has_no_secrets() -> None:
    lowered = SYSTEM_PROMPT.lower()
    for needle in ("sk-or-", "rk_live_", "api_key=", "password:", "bearer "):
        assert needle not in lowered
    assert "OPENROUTER_API_KEY" not in SYSTEM_PROMPT


def test_sloppy_stub_is_worse_but_guardrails_hold() -> None:
    capable = run_eval(client=_stub(STUB_A, "stub/capable"))
    sloppy = run_eval(client=_stub(STUB_B, "stub/sloppy"))
    assert capable["action_accuracy"] > sloppy["action_accuracy"]
    assert capable["category_accuracy"] > sloppy["category_accuracy"]
    assert sloppy["guardrail_pass_rate"] == 1.0
    assert sloppy["overrides"] > capable["overrides"]
