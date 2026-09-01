#!/usr/bin/env python3
"""Build presentable HTML from the canvas artboard sources.

The slides are authored as Design Component files in `src/` so they can be
re-seeded into the editable canvas. Those files are not directly viewable —
they carry an `<x-dc>` wrapper and a `<helmet>` block the canvas runtime
consumes. This lifts the markup out of each one and emits two standalone
pages that open in any browser with no dependencies:

    index.html        the deck, arrow keys to advance, one slide per print page
    cheat-sheet.html  the two Letter reference pages, print-ready

Run from this directory:  python3 build.py
"""

from __future__ import annotations

import re
from pathlib import Path

HERE = Path(__file__).parent
SRC = HERE / "src"

SLIDES = [
    ("Main.dc.html", "Title"),
    ("Role.dc.html", "Role & skill"),
    ("Pipeline.dc.html", "Pipeline"),
    ("Results.dc.html", "Measured results"),
    ("ErrorAnalysis.dc.html", "Error analysis"),
    ("Next.dc.html", "What's next"),
]
SHEETS = [
    ("CheatSheet.dc.html", "Stack & numbers"),
    ("CheatSheetQA.dc.html", "Likely questions"),
]

FONTS = (
    '<link rel="preconnect" href="https://fonts.googleapis.com">\n'
    '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
    '<link rel="stylesheet" href="https://fonts.googleapis.com/css2'
    '?family=Archivo:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500&display=swap">'
)


def split_artboard(path: Path) -> tuple[str, str]:
    """Return (css, markup) for one artboard file."""
    text = path.read_text(encoding="utf-8")

    body = re.search(r"<x-dc>(.*)</x-dc>", text, re.S)
    if not body:
        raise SystemExit(f"{path.name}: no <x-dc> block found")
    inner = body.group(1)

    css_blocks = re.findall(r"<style>(.*?)</style>", inner, re.S)
    markup = re.sub(r"<helmet>.*?</helmet>", "", inner, flags=re.S).strip()

    # `body { ... }` inside an artboard styles that artboard's own document;
    # hoisting it into a shared page would restyle every slide at once.
    css = "\n".join(css_blocks)
    css = re.sub(r"\bbody\s*\{[^}]*\}", "", css)
    return css.strip(), markup


RULE = re.compile(r"[^{}]+\{[^{}]*\}", re.S)


def collect(entries):
    """Merge each artboard's styles, de-duplicating whole rules.

    De-duplicating by LINE looks equivalent and is not: two rules can share
    an identical continuation line (several here end with the same
    `font-family: ...; }`), and dropping the second as a duplicate leaves
    the first rule unterminated, swallowing everything after it.
    """
    seen, css_out, markup = set(), [], []
    for filename, label in entries:
        css, html = split_artboard(SRC / filename)
        for rule in RULE.findall(css):
            normalised = " ".join(rule.split())
            if normalised not in seen:
                seen.add(normalised)
                css_out.append("  " + normalised)
        markup.append((label, html))
    return "\n".join(css_out), markup


def build_deck() -> None:
    css, slides = collect(SLIDES)
    sections = "\n".join(
        f'<section class="slide" data-label="{label}" aria-label="Slide {i}: {label}">\n{html}\n</section>'
        for i, (label, html) in enumerate(slides, 1)
    )

    (HERE / "index.html").write_text(f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>SoccerVision — hackathon deck</title>
{FONTS}
<style>
  *, *::before, *::after {{ box-sizing: border-box; }}
  html, body {{ margin: 0; height: 100%; background: oklch(0.128 0.010 150);
                font-family: Archivo, system-ui, "Helvetica Neue", sans-serif; }}
  #stage {{ position: fixed; inset: 0; display: grid; place-items: center; overflow: hidden; }}
  .slide {{ width: 1280px; height: 720px; flex: none; display: none;
            transform-origin: center center; box-shadow: 0 24px 80px -30px rgb(0 0 0 / 0.8); }}
  .slide.current {{ display: block; }}
  #hud {{ position: fixed; left: 0; right: 0; bottom: 0; display: flex; align-items: center;
          justify-content: space-between; gap: 16px; padding: 10px 18px;
          font-size: 12px; color: oklch(0.55 0.014 145); pointer-events: none; }}
  #hud kbd {{ font-family: 'IBM Plex Mono', ui-monospace, monospace; font-size: 11px;
              border: 1px solid oklch(0.32 0.016 150); border-radius: 4px; padding: 1px 5px; }}
  #count {{ font-family: 'IBM Plex Mono', ui-monospace, monospace; }}
{css}
  @media print {{
    @page {{ size: 1280px 720px; margin: 0; }}
    html, body {{ height: auto; background: #fff; }}
    #stage {{ position: static; display: block; overflow: visible; }}
    #hud {{ display: none; }}
    .slide {{ display: block !important; transform: none !important;
              break-after: page; box-shadow: none; }}
    .slide:last-child {{ break-after: auto; }}
  }}
</style>
</head>
<body>
<div id="stage">
{sections}
</div>
<div id="hud">
  <span><kbd>&larr;</kbd> <kbd>&rarr;</kbd> to navigate &middot; <kbd>F</kbd> fullscreen</span>
  <span id="count"></span>
</div>
<script>
  const slides = [...document.querySelectorAll('.slide')];
  const count = document.getElementById('count');
  let at = 0;

  function show(next) {{
    at = Math.max(0, Math.min(slides.length - 1, next));
    slides.forEach((s, i) => s.classList.toggle('current', i === at));
    count.textContent = `${{at + 1}} / ${{slides.length}}`;
    location.hash = at + 1;
  }}

  // Scale the fixed 1280x720 slide to whatever the window is, without
  // reflowing anything — the layout is designed at exactly that size.
  function fit() {{
    const scale = Math.min(innerWidth / 1280, (innerHeight - 34) / 720);
    slides.forEach(s => s.style.transform = `scale(${{scale}})`);
  }}

  addEventListener('resize', fit);
  addEventListener('keydown', e => {{
    if (e.key === 'ArrowRight' || e.key === 'PageDown' || e.key === ' ') {{ e.preventDefault(); show(at + 1); }}
    else if (e.key === 'ArrowLeft' || e.key === 'PageUp') {{ e.preventDefault(); show(at - 1); }}
    else if (e.key === 'Home') show(0);
    else if (e.key === 'End') show(slides.length - 1);
    else if (e.key === 'f' || e.key === 'F') {{
      document.fullscreenElement ? document.exitFullscreen() : document.documentElement.requestFullscreen();
    }}
  }});
  addEventListener('click', e => {{ if (!e.target.closest('a')) show(at + 1); }});

  fit();
  show(Math.max(0, (parseInt(location.hash.slice(1), 10) || 1) - 1));
</script>
</body>
</html>
""", encoding="utf-8")


def build_sheets() -> None:
    css, sheets = collect(SHEETS)
    pages = "\n".join(
        f'<section class="sheet" aria-label="{label}">\n{html}\n</section>'
        for label, html in sheets
    )
    (HERE / "cheat-sheet.html").write_text(f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>SoccerVision — judge cheat sheet</title>
{FONTS}
<style>
  *, *::before, *::after {{ box-sizing: border-box; }}
  html, body {{ margin: 0; background: oklch(0.92 0.006 110);
                font-family: Archivo, system-ui, "Helvetica Neue", sans-serif; }}
  #sheets {{ display: flex; flex-direction: column; align-items: center;
             gap: 24px; padding: 24px; }}
  .sheet {{ box-shadow: 0 8px 30px -12px rgb(0 0 0 / 0.35); }}
{css}
  @media print {{
    @page {{ size: letter; margin: 0; }}
    html, body {{ background: #fff; }}
    #sheets {{ display: block; padding: 0; gap: 0; }}
    .sheet {{ box-shadow: none; break-after: page; }}
    .sheet:last-child {{ break-after: auto; }}
  }}
</style>
</head>
<body>
<div id="sheets">
{pages}
</div>
</body>
</html>
""", encoding="utf-8")


if __name__ == "__main__":
    build_deck()
    build_sheets()
    print("built index.html and cheat-sheet.html from src/")
