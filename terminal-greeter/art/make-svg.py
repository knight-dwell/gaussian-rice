#!/usr/bin/env python3
"""make-svg.py: draws the bat-signal emblem (batsignal.svg, the icon) and the
mask used for the braille terminal logo (batsignal-mask.svg). Edit RIGHT to
reshape the bat; the left half is mirrored."""
import sys
# right half of the bat, from the dip between the ears, clockwise, to the tail tip.
# ("L",(x,y)) line, ("Q",(cx,cy),(x,y)) quad curve. x: 0..100 right, y: down.
RIGHT = [
    ("L", (5, -2)),            # ear tip
    ("L", (9, 15)),            # ear base
    ("Q", (15, 19), (22, 13)), # shoulder
    ("C", (40, -1), (72, -4), (100, 6)),   # top edge sweeping up to the wing tip
    ("Q", (88, 18), (90, 38)), # outer edge down
    ("Q", (80, 28), (70, 34)), # scallop 1
    ("Q", (68, 44), (60, 52)), # down
    ("Q", (50, 42), (38, 46)), # scallop 2
    ("Q", (18, 50), (0, 70)),  # down to the tail
]
START = (0, 16)

def fmt(p, cx, cy, s): return f"{cx + p[0]*s:.1f},{cy + p[1]*s:.1f}"

def path(cx, cy, s):
    d = ["M" + fmt(START, cx, cy, s)]
    for seg in RIGHT:
        d.append(seg[0] + " ".join(fmt(p, cx, cy, s) for p in seg[1:]))
    # left half: walk the right half backwards, mirrored
    pts = [START] + [seg[-1] for seg in RIGHT]
    for i in range(len(RIGHT) - 1, -1, -1):
        seg = RIGHT[i]
        prev_end = pts[i]
        ctrl = [(-x, y) for x, y in seg[1:-1]][::-1]
        end = (-prev_end[0], prev_end[1])
        d.append(seg[0] + " ".join(fmt(p, cx, cy, s) for p in ctrl + [end]))
    return " ".join(d) + " Z"

def emblem(bat_d):
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="256" height="256" viewBox="0 0 256 256">
  <defs><radialGradient id="glow" cx="50%" cy="45%" r="55%">
    <stop offset="0%" stop-color="#fff7c2"/><stop offset="65%" stop-color="#ffd84a"/><stop offset="100%" stop-color="#eaa800"/>
  </radialGradient></defs>
  <rect x="8" y="8" width="240" height="240" rx="52" fill="#111318"/>
  <ellipse cx="128" cy="128" rx="114" ry="76" fill="url(#glow)"/>
  <ellipse cx="128" cy="128" rx="114" ry="76" fill="none" stroke="#1e88e5" stroke-width="5"/>
  <path d="{bat_d}" fill="#111318"/>
</svg>'''

def mask(bat_d):
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="256" height="160" viewBox="4 46 248 164">
  <rect x="0" y="0" width="256" height="256" fill="black"/>
  <ellipse cx="128" cy="128" rx="120" ry="80" fill="white"/>
  <path d="{bat_d}" fill="black"/>
</svg>'''

d = path(128, 92, 0.98)
open("batsignal.svg", "w").write(emblem(d))
open("batsignal-mask.svg", "w").write(mask(path(128, 80, 1.14)))
