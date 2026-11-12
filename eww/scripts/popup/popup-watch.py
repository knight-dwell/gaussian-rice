#!/usr/bin/env python3
"""eww deflisten (prints nothing useful; eww owns its lifecycle). Watches i3:

1. "Click outside": closes eww popups when focus moves to a non-eww window
   because of a mouse click or a key binding. Focus that moves only because
   the pointer HOVERED another window (i3 focus_follows_mouse, e.g. crossing
   the gap between bar and popup) does not close it.
2. Fullscreen: the bar is an override-redirect window, so it would sit on top
   of fullscreen video. While the focused workspace has a fullscreen window
   the bar is unmapped (no click-blocking strip, no blur), then mapped again.
"""
import os
import subprocess
import threading
import time

import i3ipc
from Xlib import X, display

POPUP = os.path.expanduser("~/.config/eww/scripts/popup/popup.sh")
state = {"mode": "default", "hidden": None, "last_binding": 0.0, "away": False}
BUTTONS = X.Button1Mask | X.Button2Mask | X.Button3Mask
dpy = display.Display()


def bar_windows():
    """Top-level X windows titled 'Eww - bar' (override-redirect, so they are
    direct children of the root window). Cached; re-scanned if eww restarted."""
    cached = state.get("bars") or []
    try:
        if cached and all(w.get_wm_name() == "Eww - bar" for w in cached):
            return cached
    except Exception:
        pass
    found = []
    for w in dpy.screen().root.query_tree().children:
        try:
            if w.get_wm_name() == "Eww - bar":
                found.append(w)
        except Exception:
            pass
    state["bars"] = found
    return found


def set_bar_hidden(hidden):
    if state["hidden"] == hidden:
        return
    for w in bar_windows():
        w.unmap() if hidden else w.map()
    dpy.flush()
    state["hidden"] = hidden


def check_fullscreen(i3, *_):
    ws = i3.get_tree().find_focused()
    ws = ws.workspace() if ws else None
    full = bool(ws) and any(c.fullscreen_mode == 1 for c in ws.descendants())
    set_bar_hidden(full)


def on_mode(i3, e):
    state["mode"] = e.change
    if e.change != "eww-popup":
        state["away"] = False


def on_binding(i3, e):
    state["last_binding"] = time.monotonic()


def deliberate():
    """True if the current focus change came from a click or a key binding."""
    if time.monotonic() - state["last_binding"] < 0.5:
        return True
    try:
        return bool(dpy.screen().root.query_pointer().mask & BUTTONS)
    except Exception:
        return True


def close_popup():
    state["away"] = False
    subprocess.Popen([POPUP, "close"])


def watch_clicks(i3):
    """Focus hovered away from the popup: there will be no new focus event if
    the user now clicks that same window, so watch the mouse buttons (20x/s,
    only in this state) and close on a press outside the popup and the bar."""
    d = display.Display()   # own X connection (this runs in a thread)
    root = d.screen().root
    try:
        while state["away"] and state["mode"] == "eww-popup":
            p = root.query_pointer()
            if p.mask & BUTTONS and p.root_y > 52:   # below the bar
                pops = [c.rect for c in i3.get_tree().leaves() if (c.name or "").startswith("Eww - ")]
                if not any(r.x <= p.root_x < r.x + r.width and r.y <= p.root_y < r.y + r.height for r in pops):
                    close_popup()
                    break
            time.sleep(0.05)
    finally:
        d.close()


def on_focus(i3, e):
    title = e.container.name or ""
    if title.startswith("Eww - "):
        state["away"] = False
    elif state["mode"] == "eww-popup":
        if deliberate():
            close_popup()
        elif not state["away"]:
            state["away"] = True
            threading.Thread(target=watch_clicks, args=(i3ipc.Connection(),), daemon=True).start()
    check_fullscreen(i3)


def on_workspace(i3, e):
    if state["mode"] == "eww-popup":   # switched workspace: popup goes away
        close_popup()
    check_fullscreen(i3)


def on_close(i3, e):
    # system monitor closed by i3 (e.g. Super+Q): stop its data poll too
    if (e.container.name or "") == "Eww - sysmon":
        subprocess.Popen([os.path.expanduser("~/.config/eww/scripts/sysmon/toggle.sh"), "close"])
    check_fullscreen(i3)


def main():
    print("", flush=True)
    while True:
        try:
            i3 = i3ipc.Connection(auto_reconnect=True)
            state["hidden"] = None
            check_fullscreen(i3)
            i3.on(i3ipc.Event.MODE, on_mode)
            i3.on(i3ipc.Event.WINDOW_FOCUS, on_focus)
            i3.on(i3ipc.Event.BINDING, on_binding)
            i3.on(i3ipc.Event.WORKSPACE_FOCUS, on_workspace)
            i3.on(i3ipc.Event.WINDOW_CLOSE, on_close)
            i3.on(i3ipc.Event.WINDOW_FULLSCREEN_MODE, check_fullscreen)
            i3.main()
        except Exception:
            pass
        time.sleep(1)


if __name__ == "__main__":
    main()
