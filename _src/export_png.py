#!/usr/bin/env python3
"""Rasterise each logo SVG to a transparent 2x PNG via headless Chrome."""
import os, re, subprocess, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SVG = os.path.join(ROOT, "svg")
PNG = os.path.join(ROOT, "png")
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
SCALE = 2

for name in sorted(os.listdir(SVG)):
    if not name.endswith(".svg"):
        continue
    with open(os.path.join(SVG, name)) as fh:
        svg = fh.read()
    m = re.search(r'viewBox="0 0 ([\d.]+) ([\d.]+)"', svg)
    w, h = float(m.group(1)), float(m.group(2))
    html = (f'<!doctype html><meta charset=utf-8>'
            f'<style>html,body{{margin:0}}svg{{width:{w}px;height:{h}px;display:block}}</style>{svg}')
    with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False) as t:
        t.write(html)
        tmp = t.name
    out = os.path.join(PNG, name[:-4] + "@2x.png")
    subprocess.run([CHROME, "--headless", "--disable-gpu", "--hide-scrollbars",
                    f"--screenshot={out}", f"--window-size={round(w)},{round(h)}",
                    "--default-background-color=00000000",
                    f"--force-device-scale-factor={SCALE}", f"file://{tmp}"],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    os.unlink(tmp)
    print("png", os.path.relpath(out, ROOT), f"{round(w*SCALE)}x{round(h*SCALE)}")
print("done")
