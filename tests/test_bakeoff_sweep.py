from bakeoff.sweep import run_sweep


def test_offline_sweep_two_models() -> None:
    payload = run_sweep(["stub/model-a", "stub/model-b"])
    assert payload["n_models"] == 2
    assert len(payload["models"]) == 2
    for row in payload["models"]:
        assert "quality" in row
        assert "gate" in row
        assert row["n"] >= 1


def test_sweep_logs_to_db(tmp_path, monkeypatch) -> None:
    import src.db as db_mod

    db_path = tmp_path / "runs.db"
    monkeypatch.setattr(db_mod, "DB_PATH", db_path)
    run_sweep(["stub/alpha", "stub/beta"])
    rows = db_mod.get_runs_for_chart(demo="bakeoff_sweep", db_path=db_path)
    assert len(rows) == 2
    assert rows[0]["model"] == "stub/alpha"
