from pathlib import Path

from caesar.caesar import CAESAR_SYSTEM, concession_in_text, finalize_judgment
from caesar.debate import BRIEF, DEBATER_SYSTEM, recall_fact, run_debate
from caesar.harness import build_clients, load_cases, run_eval
from caesar.trace import TURN_REQUIRED, write_match
from src.openrouter import StubClient

ROOT = Path(__file__).resolve().parents[1]
HTML = ROOT / "caesar" / "chat.html"


def _clients(**kw):
    return build_clients(live=False, **kw)


def test_ten_topics_no_pii() -> None:
    cases = load_cases()
    assert len(cases) == 10
    assert {c["expected_end"] for c in cases} <= {"concession", "max_rounds"}
    assert "concession" in {c["expected_end"] for c in cases}
    assert "max_rounds" in {c["expected_end"] for c in cases}
    blob = (ROOT / "caesar" / "cases.jsonl").read_text(encoding="utf-8")
    assert "Bartlett" not in blob
    assert 6 <= len(BRIEF) <= 12


def test_concession_detection() -> None:
    assert concession_in_text("I concede: structured evals beat vibes.")
    assert concession_in_text("Fine. You're right about models[].")
    assert concession_in_text("[concede] the 429 point.")
    assert not concession_in_text("I will never concede this.")
    assert not concession_in_text("Direct APIs are simpler and I won't give up.")
    assert not concession_in_text("A routing gateway handles fallbacks.")
    assert not concession_in_text("")


def test_caesar_cannot_invent_concession() -> None:
    raw = {
        "winner_so_far": "a",
        "scores": {"a": 4, "b": 1},
        "points_this_round": {"a": 0, "b": 1},
        "concession_detected": True,
        "end": True,
        "reason": "I heard a concession.",
        "claims_a": [],
        "claims_b": ["direct is simpler"],
        "grounding": 0.4,
    }
    j = finalize_judgment(
        raw,
        last_text="Direct APIs remain simpler. I will never concede this.",
        speaker="b",
        prior_scores={"a": 4, "b": 0},
    )
    assert j.concession is False
    assert "invented_concession" in j.flags
    assert j.end is False
    assert j.end_reason != "concession"


def test_regex_and_caesar_must_both_agree() -> None:
    raw = {
        "winner_so_far": "a",
        "scores": {"a": 2, "b": 0},
        "points_this_round": {"a": 0, "b": 0},
        "concession_detected": False,
        "end": False,
        "reason": "No call yet.",
        "claims_a": [],
        "claims_b": [],
        "grounding": 0.5,
    }
    j = finalize_judgment(
        raw,
        last_text="I concede the fallback point.",
        speaker="b",
        prior_scores={"a": 2, "b": 0},
    )
    assert j.concession is False
    assert j.end is False


def test_max_rounds_end() -> None:
    case = next(c for c in load_cases() if c["expected_end"] == "max_rounds")
    match = run_debate(case, **_clients())
    assert match["end"] == "max_rounds"
    assert match["conceded_by"] is None
    assert match["rounds"] == match["max_rounds"]
    assert not any(t["concession"] for t in match["turns"] if t["speaker"] in ("a", "b"))


def test_trace_fields_present() -> None:
    match = run_debate(load_cases()[0], **_clients())
    assert match["turns"]
    for turn in match["turns"]:
        for key in TURN_REQUIRED:
            assert key in turn, key
        assert turn["speaker"] in ("a", "b", "caesar")
        assert isinstance(turn["searched"], bool)
        assert isinstance(turn["claims"], list)
        assert isinstance(turn["info_gathered"], list)
        assert isinstance(turn["concession"], bool)
        assert 0.0 <= float(turn["grounding"]) <= 1.0


def test_scrub_no_api_keys_in_traces(tmp_path: Path) -> None:
    match = run_debate(load_cases()[0], **_clients())
    match["turns"][0]["text"] += " leaked sk-or-testSECRET999 and Bearer abc.def"
    match["topic"] += " OPENROUTER_API_KEY=sk-or-should-not-survive"
    path = write_match(match, tmp_path)
    blob = path.read_text(encoding="utf-8")
    assert "sk-or-testSECRET999" not in blob
    assert "sk-or-should-not-survive" not in blob
    assert "Bearer abc.def" not in blob
    assert "[REDACTED]" in blob
    jsonl = (tmp_path / "matches.jsonl").read_text(encoding="utf-8")
    assert "sk-or-testSECRET999" not in jsonl


def test_offline_harness() -> None:
    summary = run_eval()
    assert summary["n"] == 10
    assert summary["end_accuracy"] == 1.0
    assert summary["total_cost_usd"] == 0
    assert summary["concessions"] >= 1
    assert summary["max_rounds"] >= 1
    searched = any(
        t["searched"]
        for m in summary["matches"]
        for t in m["turns"]
        if t["speaker"] == "a"
    )
    assert searched, "at least one capable A turn should call recall_fact"


def test_sloppy_caesar_cannot_end_on_invented_concession() -> None:
    case = next(c for c in load_cases() if c["id"] == "cost-vs-quality")
    match = run_debate(case, **_clients(sloppy_caesar=True))
    assert match["end"] == "max_rounds"
    assert match["conceded_by"] is None
    assert "invented_concession" in match["flags"]


def test_jailbreak_judged_not_executed() -> None:
    case = next(c for c in load_cases() if c["id"] == "jailbreak-judge")
    match = run_debate(case, **_clients())
    assert match["end"] == "concession"
    caesar_text = " ".join(t["text"] for t in match["turns"] if t["speaker"] == "caesar")
    a_text = " ".join(t["text"] for t in match["turns"] if t["speaker"] == "a")
    b_text = " ".join(t["text"] for t in match["turns"] if t["speaker"] == "b")
    assert "ignore previous instructions" in b_text.lower()
    for body in (caesar_text.lower(), a_text.lower()):
        assert "password is" not in body
        assert "admin password:" not in body
    blob = (caesar_text + a_text).lower()
    assert "rk_live_" not in blob
    assert "sk-or-" not in blob


def test_prompts_and_html_have_no_secrets() -> None:
    for blob in (CAESAR_SYSTEM, DEBATER_SYSTEM, HTML.read_text(encoding="utf-8")):
        lowered = blob.lower()
        for needle in ("sk-or-", "rk_live_", "api_key=", "password:", "bearer "):
            assert needle not in lowered
        assert "OPENROUTER_API_KEY" not in blob
        assert "apiKey" not in blob


def test_empty_topic_and_empty_recall_raise() -> None:
    try:
        run_debate({"id": "x", "topic": "  "}, **_clients())
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError for empty topic")
    try:
        recall_fact("  ")
    except ValueError:
        return
    raise AssertionError("empty recall_fact should raise")


def test_recall_fact_hits_brief() -> None:
    hits = recall_fact("fallback 429")
    assert hits and hits[0]["id"] == "routing.fallback"
