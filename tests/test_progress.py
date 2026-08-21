"""Tests for eval progress bar."""

from __future__ import annotations

import io
import sys
from unittest.mock import patch

from src.progress import EvalProgress, _progress_enabled


def test_progress_disabled_does_not_write() -> None:
    p = EvalProgress("test", 3, enabled=False)
    with patch.object(sys.stderr, "write") as mock_write:
        p.advance("a")
        p.finish()
    mock_write.assert_not_called()


def test_progress_line_mode_when_forced_non_tty() -> None:
    buf = io.StringIO()
    with patch.object(sys.stderr, "isatty", return_value=False), patch.dict(
        "os.environ", {"PROGRESS": "1", "PYTEST_CURRENT_TEST": ""}, clear=False
    ):
        p = EvalProgress("bakeoff", 2)
        assert p.line_mode is True
        with patch.object(sys.stderr, "write", side_effect=lambda s: buf.write(s)):
            with patch.object(sys.stderr, "flush"):
                p.advance("case-1", ok=True)
                p.advance("case-2", ok=True)
                p.finish()
    out = buf.getvalue()
    assert "bakeoff" in out
    assert "case-1" in out
    assert "50%" in out or "100%" in out
    assert out.count("\n") >= 2


def test_progress_respects_no_progress_env() -> None:
    with patch.dict("os.environ", {"NO_PROGRESS": "1"}, clear=False):
        assert _progress_enabled(None) is False
