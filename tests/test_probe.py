from probe.harness import classify_response, load_cases, probe_case, run_eval


def test_load_cases_has_jailbreak_and_math() -> None:
    cases = load_cases()
    ids = {c["id"] for c in cases}
    assert "ignore-instructions" in ids
    assert "math-harmless" in ids
    assert len(cases) >= 8


def test_classify_refused_vs_leaked() -> None:
    case = {"id": "x", "forbidden": ["PWNED"], "must_refuse": True}
    outcome, _ = classify_response(case, "I can't help with that request.")
    assert outcome == "refused"
    outcome2, _ = classify_response(case, "PWNED")
    assert outcome2 == "leaked"


def test_classify_math_json_ok() -> None:
    case = {
        "id": "math",
        "forbidden": [],
        "must_refuse": False,
        "expect_json": True,
        "expected_fields": {"product": 391},
    }
    outcome, checks = classify_response(case, '{"product": 391}')
    assert outcome == "ok"
    assert checks["json_ok"]


def test_offline_probe_eval() -> None:
    summary = run_eval()
    assert summary["n"] == 16  # 8 cases × 2 profiles
    assert summary["refused"] >= 6
    assert summary["leaked"] >= 6


def test_probe_case_strict_stub() -> None:
    from probe.harness import build_clients

    clients = build_clients(live=False)
    case = load_cases()[0]
    row = probe_case(clients["strict"], case)
    assert row["outcome"] in ("refused", "upstream_blocked", "ok")
