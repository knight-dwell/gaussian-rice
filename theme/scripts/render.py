#!/usr/bin/env python3
"""Render theme templates.

Usage: render.py <context.json> <targets.list>

context.json  flat {"name": "value"} map: palette roles + design tokens
targets.list  lines of "<template path> <output path>" ($HOME and ~ expanded)

Template syntax:
  {{primary}}               value as-is            -> #adc6ff
  {{primary|strip}}         hex without '#'        -> adc6ff
  {{primary|alpha:0.88}}    #RRGGBBAA              -> #adc6ffe0
  {{primary|rgba:0.88}}     css rgba()             -> rgba(173, 198, 255, 0.88)
  {{primary|argb}}          #AARRGGBB (Qt)         -> #ffadc6ff
  {{primary|mix:surface:0.3}}  blend 30% of surface into primary
  {{primary|vec3}}          GLSL color             -> vec3(0.678, 0.776, 1.000)
  Filter arguments may be key names: {{surface|rgba:bar_opacity}}
"""
import json
import os
import re
import sys

TOKEN = re.compile(r"\{\{\s*([a-z0-9_]+)((?:\|[a-z0-9]+(?::[^|}]+)*)*)\s*\}\}")


def rgb(hexstr):
    h = hexstr.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def to_hex(r, g, b):
    return "#{:02x}{:02x}{:02x}".format(round(r), round(g), round(b))


def apply_filter(value, name, args, ctx):
    if name == "strip":
        return value.lstrip("#")
    if name == "alpha":
        return value + "{:02x}".format(round(float(args[0]) * 255))
    if name == "rgba":
        r, g, b = rgb(value)
        return "rgba({}, {}, {}, {})".format(r, g, b, args[0])
    if name == "argb":
        return "#ff" + value.lstrip("#")
    if name == "vec3":
        return "vec3({:.3f}, {:.3f}, {:.3f})".format(*[c / 255 for c in rgb(value)])
    if name == "mix":
        other, t = rgb(args[0]), float(args[1])
        mine = rgb(value)
        return to_hex(*[a * (1 - t) + b * t for a, b in zip(mine, other)])
    raise ValueError("unknown filter: " + name)


def render(text, ctx, where):
    def sub(m):
        key, filters = m.group(1), m.group(2)
        if key not in ctx:
            raise KeyError("{}: unknown key '{}'".format(where, key))
        value = str(ctx[key])
        for f in filter(None, filters.split("|")):
            name, *args = f.split(":")
            # an argument may name another key: {{surface|rgba:bar_opacity}}
            args = [str(ctx[a]) if a in ctx else a for a in args]
            value = apply_filter(value, name, args, ctx)
        return value

    return TOKEN.sub(sub, text)


def main():
    ctx = json.load(open(sys.argv[1]))
    base = os.path.dirname(os.path.abspath(sys.argv[2]))
    for line in open(sys.argv[2]):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        src, dst = line.split()
        src = os.path.join(base, src)
        dst = os.path.expanduser(os.path.expandvars(dst))
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        out = render(open(src).read(), ctx, src)
        tmp = dst + ".tmp"
        with open(tmp, "w") as fh:
            fh.write(out)
        os.replace(tmp, dst)  # atomic, so watchers never see half a file
        print("  wrote", dst)


if __name__ == "__main__":
    main()
