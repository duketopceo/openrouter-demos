#!/usr/bin/env python3
"""Record a walkthrough video of the OpenRouter Demos local dashboard (offline mode)."""

from __future__ import annotations

import shutil
import sys
import time
from pathlib import Path

from playwright.sync_api import TimeoutError as PlaywrightTimeout
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "demo"
BASE_URL = "http://localhost:8080"


def wait_for_log(page, text: str, timeout_ms: int = 90_000) -> None:
    page.locator("#output").get_by_text(text, exact=False).wait_for(timeout=timeout_ms)


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    video_tmp = OUT_DIR / "_video_tmp"
    if video_tmp.exists():
        shutil.rmtree(video_tmp)
    video_tmp.mkdir()

    final_path = OUT_DIR / "openrouter-demos-walkthrough.mp4"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            record_video_dir=str(video_tmp),
            record_video_size={"width": 1280, "height": 800},
            viewport={"width": 1280, "height": 800},
            color_scheme="dark",
        )
        page = context.new_page()

        page.goto(BASE_URL, wait_until="networkidle")
        page.wait_for_timeout(2000)

        page.goto(f"{BASE_URL}/viz/", wait_until="networkidle")
        page.wait_for_timeout(3500)

        page.goto(BASE_URL, wait_until="networkidle")
        page.wait_for_timeout(1000)

        page.get_by_role("button", name="Run Pytest Suite (Offline)").click()
        wait_for_log(page, "Pytest passed")
        page.wait_for_timeout(1500)

        cards = page.locator(".card")
        cards.nth(0).get_by_role("button", name="Run Harness").click()
        wait_for_log(page, "finished successfully")
        page.wait_for_timeout(1200)

        cards.nth(0).get_by_role("button", name="Results").click()
        page.wait_for_timeout(2000)

        cards.nth(2).get_by_role("button", name="Run Bakeoff").click()
        try:
            wait_for_log(page, "wrote", timeout_ms=60_000)
        except PlaywrightTimeout:
            wait_for_log(page, "bakeoff", timeout_ms=15_000)
        page.wait_for_timeout(1200)

        cards.nth(3).get_by_role("button", name="Run Debate").click()
        try:
            wait_for_log(page, "wrote traces", timeout_ms=60_000)
        except PlaywrightTimeout:
            wait_for_log(page, "caesar", timeout_ms=15_000)
        page.wait_for_timeout(1500)

        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        page.wait_for_timeout(2500)

        with context.expect_page() as new_page_info:
            cards.nth(3).get_by_role("link", name="Open Replay").click()
        replay = new_page_info.value
        replay.wait_for_load_state("networkidle")
        replay.wait_for_timeout(3500)

        context.close()
        browser.close()

        webm_files = list(video_tmp.glob("*.webm"))
        if not webm_files:
            print("No video file recorded", file=sys.stderr)
            return 1

        raw = webm_files[0]
        shutil.copy(raw, OUT_DIR / "openrouter-demos-walkthrough.webm")

        import subprocess

        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-i",
                str(raw),
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                "-movflags",
                "+faststart",
                str(final_path),
            ],
            check=True,
            capture_output=True,
        )
        shutil.rmtree(video_tmp)

    size_mb = final_path.stat().st_size / (1024 * 1024)
    print(f"Wrote {final_path} ({size_mb:.1f} MB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
