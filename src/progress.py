"""Real ASCII progress bars for eval harness case loops (stderr)."""

from __future__ import annotations

import json
import os
import sys
import time


def _progress_enabled(enabled: bool | None) -> bool:
    if enabled is not None:
        return enabled
    if os.environ.get("NO_PROGRESS", "0") == "1":
        return False
    if os.environ.get("PROGRESS", "0") == "1":
        return True
    if os.environ.get("PYTEST_CURRENT_TEST") is not None:
        return False
    return sys.stderr.isatty()


class EvalProgress:
    """Updates as each case finishes — tied to real work, not timers."""

    def __init__(
        self,
        label: str,
        total: int,
        *,
        width: int = 32,
        enabled: bool | None = None,
    ) -> None:
        self.label = label
        self.total = max(total, 1)
        self.width = width
        self.done = 0
        self._started = time.perf_counter()
        self.enabled = _progress_enabled(enabled)
        self.line_mode = self.enabled and not sys.stderr.isatty()
        if self.enabled:
            self._render(prefix="")

    def advance(self, case_id: str, *, ok: bool = True) -> None:
        self.done += 1
        if self.enabled:
            mark = "ok" if ok else "FAIL"
            self._render(suffix=f" {case_id[:28]} {mark}")
            if os.environ.get("PROGRESS_JSON", "0") == "1":
                payload = {
                    "event": "progress",
                    "label": self.label,
                    "done": self.done,
                    "total": self.total,
                    "case_id": case_id,
                    "ok": ok,
                    "pct": int(min(100, round(100 * self.done / self.total))),
                }
                print(json.dumps(payload), flush=True)

    def finish(self, *, note: str = "") -> None:
        if not self.enabled:
            return
        elapsed = time.perf_counter() - self._started
        self._render(suffix=f" done {self.done}/{self.total} · {elapsed:.1f}s {note}")
        sys.stderr.write("\n")
        sys.stderr.flush()
        if os.environ.get("PROGRESS_JSON", "0") == "1":
            print(
                json.dumps(
                    {
                        "event": "progress_done",
                        "label": self.label,
                        "done": self.done,
                        "total": self.total,
                        "elapsed_s": round(elapsed, 2),
                    }
                ),
                flush=True,
            )

    def _render(self, *, prefix: str = "", suffix: str = "") -> None:
        ratio = min(1.0, self.done / self.total)
        filled = int(round(ratio * self.width))
        bar = "█" * filled + "░" * (self.width - filled)
        pct = int(ratio * 100)
        line = f"{prefix}{self.label:<14} [{bar}] {pct:3d}% ({self.done}/{self.total}){suffix}"
        if self.line_mode:
            sys.stderr.write(line[:120] + "\n")
        else:
            sys.stderr.write("\r" + line[:120].ljust(120))
        sys.stderr.flush()
