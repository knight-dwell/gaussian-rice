#!/usr/bin/env python3
"""make-braille.py MASK.svg WIDTH_PX OUT.txt: turn the bat-signal mask into
braille-dot art for fastfetch (white = dot). Each character holds 2x4 dots,
so WIDTH_PX 80 -> 40 columns. "$1" marks the logo color for fastfetch.
Regenerate everything:  python3 make-svg.py && for w in 80 56 40 ...
"""
import subprocess
import sys
import tempfile

from PIL import Image

svg, width, out = sys.argv[1], int(sys.argv[2]), sys.argv[3]
with tempfile.NamedTemporaryFile(suffix=".png") as tmp:
    subprocess.run(["rsvg-convert", "-w", str(width), svg, "-o", tmp.name], check=True)
    im = Image.open(tmp.name).convert("L")
w, h = im.size
lit = lambda x, y: x < w and y < h and im.getpixel((x, y)) > 140
BITS = [(0, 0, 0x01), (0, 1, 0x02), (0, 2, 0x04), (1, 0, 0x08), (1, 1, 0x10), (1, 2, 0x20), (0, 3, 0x40), (1, 3, 0x80)]
lines = []
for cy in range(0, h, 4):
    row = ""
    for cx in range(0, w, 2):
        v = sum(b for dx, dy, b in BITS if lit(cx + dx, cy + dy))
        row += chr(0x2800 + v) if v else " "
    lines.append(row.rstrip())
while lines and not lines[-1].strip():
    lines.pop()
with open(out, "w") as fh:
    fh.write("$1" + "\n".join(lines) + "\n")
print(out, max(map(len, lines)), "x", len(lines))
