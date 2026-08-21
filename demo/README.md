# Demo video

**File:** `openrouter-demos-walkthrough.mp4` (~20s, 1280×800)

Recorded in **offline mode** — no API key on screen. Shows:

1. Local dashboard at `http://localhost:8080`
2. Offline pytest suite from the UI
3. Support Deflection harness + results JSON
4. Provider Ops bakeoff (stub fixtures)
5. Caesar debate harness
6. Caesar trace replay viewer (new tab)

## Public URL (Cloudflare R2)

Bucket: **`openrouter-demos`** (WNAM, account `duketopceo@gmail.com`)

**Video:** https://pub-9e45e5f7be6f4c9989852b4989e83a23.r2.dev/demos/openrouter-demos-walkthrough.mp4

Upload / refresh:

```bash
./scripts/upload_demo_r2.sh
# or: R2_KEY=demos/my-cut.mp4 ./scripts/upload_demo_r2.sh path/to/video.mp4
```

Requires `wrangler` auth (`npx wrangler whoami`). Uses `--remote` so objects land in Cloudflare, not local simulation.

## Regenerate

```bash
./bin/setup.sh
python3 dev_server.py   # terminal 1
python3 scripts/record_demo.py   # terminal 2
```

Requires: `playwright`, `ffmpeg`, dev server on port 8080.

Outputs:

- `demo/openrouter-demos-walkthrough.mp4` — share this
- `demo/openrouter-demos-walkthrough.webm` — raw Playwright capture (optional)

## Live version

For a live-API recording, set `OPENROUTER_API_KEY` in `.env` via the dashboard **before** recording, but do not type the key on camera. Extend `scripts/record_demo.py` to click **Run All Live Demos** if needed.
