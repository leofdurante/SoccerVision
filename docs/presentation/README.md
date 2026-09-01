# Hackathon presentation

Six-slide deck and a two-page judge cheat sheet for SoccerVision, framed
around the job posting the project was built against: **SumerSports —
Sports Computer Vision Engineer**.

## Presenting

Open **`index.html`** in any browser. No build step, no server, no
dependencies.

| Key | |
|---|---|
| <kbd>&rarr;</kbd> <kbd>space</kbd> <kbd>click</kbd> | next slide |
| <kbd>&larr;</kbd> | previous |
| <kbd>Home</kbd> / <kbd>End</kbd> | first / last |
| <kbd>F</kbd> | fullscreen |

The slide number is in the URL hash, so `index.html#4` opens on slide 4 —
useful if you need to jump back mid-demo. Printing gives one slide per page.

**`cheat-sheet.html`** is the reference for Q&A: stack, pipeline with real
module paths, every number with its source, and the questions a CV-literate
judge is most likely to ask. It is laid out at US Letter and prints to two
pages.

## Timing

Five minutes is roughly 50 seconds a slide. Slides 2 (the role and the skill)
and 5 (error analysis) are the ones that distinguish the project — give them
the most air and move quickly through 1 and 3.

## Editing

`index.html` and `cheat-sheet.html` are **generated**. Edit the artboard
sources in `src/` and rebuild:

```bash
python3 build.py
```

Each file in `src/` is one slide or one sheet, authored as a Design Component
so the same sources can be re-seeded into an editable canvas. `canvas.json`
holds the canvas layout (two pages: slides, cheat sheet).

`[TEAM NAMES]` is a placeholder on slides 1 and 6 — replace it before
presenting.

## A note on fonts

Both pages load Archivo and IBM Plex Mono from Google Fonts, matching the
app's own typography. They fall back to `system-ui` offline, which shifts
the metrics slightly but does not break any layout.
