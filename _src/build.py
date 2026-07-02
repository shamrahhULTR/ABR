#!/usr/bin/env python3
"""Another Beautiful Roof — logo build. Outlines the wordmark to vector paths
and assembles the mark + lockups as self-contained SVG files."""
import os
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SVG = os.path.join(ROOT, "svg")

INK    = "#0B0E14"
PAPER  = "#F4F5F7"
SIGNAL = "#A31621"

# ---- load + instance the wordmark cut: expanded, bold ----
def cut(wght, wdth):
    f = TTFont(os.path.join(HERE, "Archivo.ttf"))
    instantiateVariableFont(f, {"wght": wght, "wdth": wdth}, inplace=True)
    return f

WORD = cut(680, 112)   # refined expanded bold — engineered, institutional
_upm = WORD["head"].unitsPerEm
_cap = WORD["OS/2"].sCapHeight
_cmap = WORD.getBestCmap()
_gs = WORD.getGlyphSet()
_hmtx = WORD["hmtx"]

def wordmark_path(text, cap_px, tracking_em=0.0, x0=0.0, baseline=0.0):
    """Return (path_d, advance_width_px). Baseline at y=baseline, caps rise above."""
    scale = cap_px / _cap
    ls = tracking_em * cap_px
    pen = SVGPathPen(_gs)
    x = x0
    for ch in text:
        g = _cmap.get(ord(ch))
        if g is None:
            g = ".notdef"
        adv = _hmtx[g][0]
        tp = TransformPen(pen, (scale, 0, 0, -scale, x, baseline))
        _gs[g].draw(tp)
        x += adv * scale + ls
    width = (x - x0 - ls) if text else 0.0
    return pen.getCommands(), width

# ---- the mark: v3 "Quiet Flight" — solid twin-spike A, blade slit,
# ---- inner peak restated in negative space at the base
MARK_D = "M8 92 L41 14 L27 60 L33 63 L48 16 L57 5 L92 92 L69 92 L51 48 L33 92 Z"

def mark(color):
    return f'<path d="{MARK_D}" fill="{color}"/>'

def write(name, body):
    p = os.path.join(SVG, name)
    with open(p, "w") as fh:
        fh.write(body)
    print("wrote", os.path.relpath(p, ROOT))

# 1. standalone mark, tight viewBox to content (y 7..89, x 7..93)
def mark_file(name, color):
    b = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" '
         f'role="img" aria-label="Another Beautiful Roof mark">{mark(color)}</svg>')
    write(name, b)

mark_file("mark-ink.svg", INK)
mark_file("mark-reverse.svg", PAPER)

# 2. app icon / favicon: ink rounded tile, paper mark inset
def icon_file(name, tile, glyph):
    inner = 60.0            # mark drawn in a 60-unit box, centered in 100 tile
    off = (100 - inner) / 2
    s = inner / 100.0
    b = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" '
         f'role="img" aria-label="Another Beautiful Roof icon">'
         f'<rect width="100" height="100" rx="22" fill="{tile}"/>'
         f'<g transform="translate({off},{off}) scale({s})">{mark(glyph)}</g></svg>')
    write(name, b)

icon_file("app-icon.svg", INK, PAPER)
icon_file("app-icon-signal.svg", SIGNAL, INK)

# 3. horizontal lockup: mark left + 3-line stacked wordmark, left-aligned
def horizontal(name, ink, wm_color):
    pad = 16.0
    mark_h = 98.0
    gap = 38.0
    cap = 32.0
    lead = cap * 1.2
    lines = ["ANOTHER", "BEAUTIFUL", "ROOF"]
    tracking = 0.02
    wm_x = pad + mark_h + gap
    paths, widths = [], []
    top = pad + 2.0                       # top of first cap
    for i, ln in enumerate(lines):
        base = top + cap + i * lead
        d, w = wordmark_path(ln, cap, tracking, x0=wm_x, baseline=base)
        paths.append(f'<path d="{d}" fill="{wm_color}"/>')
        widths.append(w)
    block_h = cap + (len(lines) - 1) * lead
    total_w = wm_x + max(widths) + pad
    total_h = pad + block_h + pad
    # vertically center mark against the text block
    mark_scale = mark_h / 100.0
    mark_y = pad + (block_h - mark_h) / 2 + 2.0
    body = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {total_w:.1f} {total_h:.1f}" '
        f'role="img" aria-label="Another Beautiful Roof">'
        f'<g transform="translate({pad},{mark_y:.1f}) scale({mark_scale})">{mark(ink)}</g>'
        + "".join(paths) + '</svg>'
    )
    write(name, body)

horizontal("logo-horizontal-ink.svg", INK, INK)
horizontal("logo-horizontal-reverse.svg", PAPER, PAPER)

# 4. stacked emblem: mark centered on top, wordmark centered below (2 lines)
def stacked(name, ink, wm_color):
    pad = 18.0
    mark_h = 106.0
    cap = 27.0
    lead = cap * 1.22
    lines = ["ANOTHER", "BEAUTIFUL", "ROOF"]
    tracking = 0.05
    measured = [wordmark_path(ln, cap, tracking, 0, 0) for ln in lines]
    max_w = max(w for _, w in measured)
    total_w = max(max_w, mark_h) + 2 * pad
    cx = total_w / 2
    gap = 26.0
    top = pad
    mark_scale = mark_h / 100.0
    parts = [f'<g transform="translate({cx - mark_h/2:.1f},{top:.1f}) scale({mark_scale})">{mark(ink)}</g>']
    wm_top = top + mark_h + gap
    for i, ln in enumerate(lines):
        base = wm_top + cap + i * lead
        _, w = measured[i]
        d, _w = wordmark_path(ln, cap, tracking, x0=cx - w / 2, baseline=base)
        parts.append(f'<path d="{d}" fill="{wm_color}"/>')
    total_h = wm_top + cap + (len(lines) - 1) * lead + pad
    body = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {total_w:.1f} {total_h:.1f}" '
            f'role="img" aria-label="Another Beautiful Roof">' + "".join(parts) + '</svg>')
    write(name, body)

stacked("logo-stacked-ink.svg", INK, INK)
stacked("logo-stacked-reverse.svg", PAPER, PAPER)

# 5. one-line wordmark only (no mark), for tight horizontal contexts
def wordline(name, color):
    pad = 14.0
    cap = 40.0
    d, w = wordmark_path("ANOTHER BEAUTIFUL ROOF", cap, 0.03, x0=pad, baseline=pad + cap)
    total_w = w + 2 * pad
    total_h = cap + 2 * pad
    body = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {total_w:.1f} {total_h:.1f}" '
            f'role="img" aria-label="Another Beautiful Roof"><path d="{d}" fill="{color}"/></svg>')
    write(name, body)

wordline("wordmark-ink.svg", INK)
wordline("wordmark-reverse.svg", PAPER)
print("done")
