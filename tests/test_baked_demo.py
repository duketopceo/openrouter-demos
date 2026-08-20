"""Tests for baked offline demo materialization."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from src.baked_demo import is_baked_available, materialize_baked, stream_baked_replay

ROOT = Path(__file__).resolve().parents[1]
BAKED = ROOT / "demo" / "baked"


@pytest.mark.skipif(not is_baked_available(ROOT), reason="demo/baked not generated")
def test_baked_available() -> None:
    assert (BAKED / "manifest.json").is_file()
    manifest = json.loads((BAKED / "manifest.json").read_text(encoding="utf-8"))
    assert manifest.get("event_count", 0) > 0
    assert "deflect.json" in manifest.get("files", [])


@pytest.mark.skipif(not is_baked_available(ROOT), reason="demo/baked not generated")
def test_materialize_writes_results(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    shutil.copytree(BAKED, repo / "demo" / "baked")
    written = materialize_baked(repo)
    assert "deflect.json" in written
    assert (repo / "results" / "deflect.json").is_file()
    assert (repo / "results" / "caesar" / "routing-vs-direct.json").is_file()


@pytest.mark.skipif(not is_baked_available(ROOT), reason="demo/baked not generated")
def test_stream_replay_emits_done(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    shutil.copytree(BAKED, repo / "demo" / "baked")
    chunks = list(stream_baked_replay(repo, delay_s=0))
    assert chunks
    last = chunks[-1].decode("utf-8")
    assert '"type": "done"' in last or '"type":"done"' in last
