# Brand assets (proposal: the owner signs off logos)

Hand-written SVG, no raster source, no stock icons, no generated imagery.

| File | Use |
|---|---|
| `logo.svg` | Mark on a dark tile (works on any background) |
| `logo-dark.svg` | Mark on a light tile, for light surfaces |
| `wordmark.svg` / `wordmark-dark.svg` | Mark plus "openrouter / demos" for light / dark pages (README uses `<picture>`) |
| `social-card.svg` | 1280x640 repository social card |

## Construction

32x32 grid, rounded tile (r=7). One input node on the left (r=2.2) feeds a line that forks at x=13 into two 2.4-wide round-capped branches ending at the top and bottom right. The top end is a solid teal node (the route that passed the gate); the bottom end is a hollow grey ring (the route that was blocked). That is the repo in one picture: route, compare, gate. Geometry is lines and circles only, so it holds at 16 px.

Colours are the DESIGN.md tokens: ink `#0E1116`, text `#D5DDE8`, signal `#3ECFB0` (dark) / `#0A7A66` (light), muted `#8D99A8` / `#55616E`.

The wordmark is live text (system sans fallback chain, bold "openrouter", regular "/ demos"), not outlined paths, so it renders with the viewer's font. Outline it before using it in print.

The app favicon is this mark inlined as a data URI in the three HTML pages.
