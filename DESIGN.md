# Design direction: Gateway Ledger

A calm, dark-first operations console for people who read numbers: ink background, one signal colour (route teal), tabular figures, no gradients, no glass. It should feel like a ledger of what a gateway decided, not a SaaS landing page.

## Surfaces

| Surface | File | Notes |
|---|---|---|
| Run Center (served at `/`) | `dashboard/run_center.html` | Primary. Fully tokenised in this pass. |
| Observability viz | `viz/index.html` | Deliberate neon-on-black line charts; only focus ring, favicon and a contrast fix applied. |
| Caesar replay | `caesar/chat.html` | Deliberate serif transcript; focus ring and favicon only. |
| Terminal tables | `src/terminal_viz.py` | Plain text; unchanged. |
| README / social card | `README.md`, `assets/brand/` | Logo, wordmark, social card. |

## Reference lock and decision ledger

The refero-design skill was not run (it needs live research tooling and this is a small internal console). Direction was chosen by hand from the repo's own constraints; no external references are claimed.

| Decision | Why |
|---|---|
| Dark default, light via `prefers-color-scheme` | Existing UI is dark; light added for README-adjacent viewing |
| One accent (teal) | The product is pass/fail; colour should mean state, not decoration |
| Semantic colours kept distinct from accent | ok / err / warn / info are state only |
| System font stack, Inter first | No webfont download; the baked demo runs offline |
| Tabular numerals on tables and legends | Numbers are the content |
| Empty states say what to press | Log panes were blank black boxes |
| Keep viz and Caesar looks | They are different jobs (charts, reading); share chrome only |

## Tokens (WCAG contrast measured against panel)

| Token | Dark | Contrast | Light | Contrast |
|---|---|---|---|---|
| bg | `#0E1116` | | `#F5F6F3` | |
| panel | `#151B23` | | `#FFFFFF` | |
| text | `#D5DDE8` | 12.6 | `#1C232B` | 15.9 |
| muted | `#8D99A8` | 6.0 | `#55616E` | 6.3 |
| accent | `#3ECFB0` | 8.9 | `#0A7A66` | 5.3 |
| ok | `#4ADE80` | 9.9 | `#1A7F37` | 5.1 |
| err | `#FF7B72` | 6.9 | `#B42318` | 6.6 |
| warn | `#E3B341` | 8.9 | `#8A5A00` | 5.9 |
| button text on accent | `#0E1116` | 9.7 | `#FFFFFF` | 5.3 |

All pairs pass AA (4.5:1). Ratios computed with the WCAG relative-luminance formula. Light theme is contrast-verified but was not visually screenshot-verified in this pass.

## Type

Inter, then system UI stack. 18 px page title, 13 px body, 11-13 px labels (uppercase, 0.06em tracking, muted). Mono (`ui-monospace`) for logs and slugs. Tabular numerals for tables.

## Icons and glyphs

Geometric line style from the logo: 2.4 px strokes on a 32 grid, round caps and joins, circles for nodes. A hollow ring means blocked/failed, a solid dot means passed. No icon fonts.

## Motion

Only functional: progress fill width (0.2 s ease) and bar hover. Everything is disabled under `prefers-reduced-motion`. No entrance animation.

## Focus and keyboard

`:focus-visible` shows a 2 px accent outline, 2 px offset, on every control in all three pages. Native controls only, so the existing keyboard paths are unchanged.

## Open items

- Hover tooltip and chart bars rely on the mouse (existing behaviour; not changed here).
- Logo is a proposal; owner signs off.
