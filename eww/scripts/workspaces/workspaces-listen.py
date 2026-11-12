#!/usr/bin/env python3
"""eww deflisten: print the state of workspaces 1-10 as one JSON line whenever
it changes. Event-driven (i3 IPC subscribe), no polling.

[{"n": 1, "name": "<i3 name>", "icon": "...", "label": "notes",
  "focused": false, "occupied": true, "urgent": false}, ...]
"""
import json
import os
import re
import time

import i3ipc

WSMAP = os.path.expanduser("~/.config/eww/generated/workspaces.json")
last = None


def i3_names(i3):
    """$ws1..$ws10 names from the live i3 config ('set $wsN "name"')."""
    names = {}
    for m in re.finditer(r'^\s*set\s+\$ws(\d+)\s+"([^"]*)"', i3.get_config().config, re.M):
        names[int(m.group(1))] = m.group(2)
    return names


def emit(i3, *_):
    global last
    names = i3_names(i3)
    try:
        wsmap = json.load(open(WSMAP))
    except (OSError, ValueError):
        wsmap = {}
    live = {w.name: w for w in i3.get_workspaces()}
    tree = i3.get_tree()
    occupied = {w.name for w in tree.workspaces() if w.leaves() or w.floating_nodes}
    out = []
    for n in range(1, 11):
        name = names.get(n, str(n))
        w = live.get(name)
        meta = wsmap.get(str(n), {})
        out.append({
            "n": n,
            "name": name,
            "icon": meta.get("icon") or name.strip() or str(n),
            "label": meta.get("label", ""),
            "focused": bool(w and w.focused),
            "occupied": name in occupied,
            "urgent": bool(w and w.urgent),
        })
    line = json.dumps(out, ensure_ascii=False)
    if line != last:  # only print real changes
        print(line, flush=True)
        last = line


def main():
    while True:
        try:
            i3 = i3ipc.Connection(auto_reconnect=True)
            emit(i3)
            i3.on(i3ipc.Event.WORKSPACE, emit)
            for ev in (i3ipc.Event.WINDOW_NEW, i3ipc.Event.WINDOW_CLOSE,
                       i3ipc.Event.WINDOW_MOVE, i3ipc.Event.WINDOW_URGENT,
                       i3ipc.Event.WINDOW_FLOATING):
                i3.on(ev, emit)
            i3.main()
        except Exception:
            pass
        time.sleep(1)  # i3 restarting: reconnect


if __name__ == "__main__":
    main()
