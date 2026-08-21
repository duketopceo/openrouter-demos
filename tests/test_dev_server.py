"""Smoke tests for dev_server helpers (no socket)."""

from __future__ import annotations

import json

import dev_server


def test_dashboard_meta_counts_harnesses() -> None:
    meta = dev_server.build_dashboard_meta()
    assert len(meta["harnesses"]) == 5
    ids = {h["id"] for h in meta["harnesses"]}
    assert ids == {"deflect", "motion", "bakeoff", "caesar", "probe"}
    caesar = next(h for h in meta["harnesses"] if h["id"] == "caesar")
    assert caesar["cases"] == 10
    assert meta["math_presets"] >= 6


def test_run_env_from_request_offline() -> None:
    env = dev_server._run_env_from_request({"mode": "offline"}, {"RUN_LIVE": "1"})
    assert env["RUN_LIVE"] == "0"


def test_models_catalog_has_curated_and_all() -> None:
    models_path = dev_server.REPO_DIR / "src" / "models.json"
    data = json.loads(models_path.read_text(encoding="utf-8"))
    assert len(data["curated"]) >= 10
    assert len(data["all"]) >= 100
    assert len(data.get("probe_picks", [])) >= 4
