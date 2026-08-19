from pathlib import Path

from motion.agent import SYSTEM_PROMPT, MotionAgent
from motion.harness import load_cases, run_eval
from motion.playbook import PLAYBOOK, lookup_playbook
from src.openrouter import StubClient

ROOT = Path(__file__).resolve().parents[1]
STUB_A = ROOT / "motion" / "fixtures" / "stub_a.json"
STUB_B = ROOT / "motion" / "fixtures" / "stub_b.json"


def _stub(path: Path = STUB_A, model: str = "stub/capable") -> StubClient:
    client = StubClient.from_fixture_path(path, model=model)
    client.index_tickets(load_cases())
    return client


def test_sixteen_cases() -> None:
    cases = load_cases()
    assert len(cases) == 16
    assert {c["expected_action"] for c in cases} == {"reply", "qualify", "book", "escalate_human"}
    blob = (ROOT / "motion" / "cases.jsonl").read_text(encoding="utf-8")
    assert "Bartlett" not in blob


def test_playbook_lookup() -> None:
    assert 6 <= len(PLAYBOOK) <= 12
    hits = lookup_playbook("enterprise DPA SOC2")
    assert any(h["id"] == "enterprise" for h in hits)


def test_offline_harness() -> None:
    summary = run_eval(client=_stub())
    assert summary["n"] == 16
    assert summary["action_accuracy"] == 1.0
    assert summary["guardrail_pass_rate"] == 1.0
    assert summary["total_cost_usd"] == 0


def test_empty_note_raises() -> None:
    try:
        MotionAgent(_stub()).run(" ")
    except ValueError:
        return
    raise AssertionError("expected ValueError")


def test_no_secrets_in_prompt() -> None:
    assert "OPENROUTER_API_KEY" not in SYSTEM_PROMPT
    assert "sk-or-" not in SYSTEM_PROMPT.lower()


def test_sloppy_overbooks_get_caught() -> None:
    sloppy = run_eval(client=_stub(STUB_B, "stub/sloppy"))
    capable = run_eval(client=_stub(STUB_A, "stub/capable"))
    assert capable["action_accuracy"] > sloppy["action_accuracy"]
    assert sloppy["guardrail_pass_rate"] == 1.0
    intern = next(r for r in sloppy["cases"] if r["id"] == "qualify-intern-book-trap")
    assert intern["actual_action"] != "book"
    jail = next(r for r in sloppy["cases"] if r["id"] == "escalate-jailbreak")
    assert jail["actual_action"] == "escalate_human"
    assert jail["guardrail_ok"] is True
