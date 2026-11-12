#!/usr/bin/env python3
"""border-random: give every window a random border color, red or blue.

i3 can only draw one border color for all windows (blue, from the theme). This
listener tags each new window with the X property _RICE_BORDER (1 = red,
0 = blue); picom's rules repaint the border of the red ones with a shader
(see ~/.config/picom/picom.conf, "random red/blue borders").

Windows without a border (eww popups/bar, border none) are left alone.
Started from the i3 config with exec_always; a pidfile keeps one copy running.
"""
import os
import random
import signal

import i3ipc
from Xlib import Xatom, display

PIDFILE = os.path.join(os.environ.get("XDG_RUNTIME_DIR", "/tmp"), "i3-border-random.pid")
RED_SHARE = 0.5          # chance that a window gets a red border
SKIP_CLASSES = {"RiceDock"}   # borderless windows (i3 "border none")

dpy = display.Display()
ATOM = dpy.intern_atom("_RICE_BORDER")


def single_instance():
    try:
        old = int(open(PIDFILE).read())
        if old != os.getpid():
            os.kill(old, signal.SIGTERM)
    except (OSError, ValueError):
        pass
    with open(PIDFILE, "w") as fh:
        fh.write(str(os.getpid()))


def tag(con, keep=False):
    """Set _RICE_BORDER on the window's X client (keep=True: only if unset)."""
    if (not con.window or (con.name or "").startswith("Eww - ")
            or con.window_class in SKIP_CLASSES or con.border == "none"):
        return
    try:
        win = dpy.create_resource_object("window", con.window)
        if keep and win.get_full_property(ATOM, Xatom.CARDINAL) is not None:
            return
        win.change_property(ATOM, Xatom.CARDINAL, 32, [1 if random.random() < RED_SHARE else 0])
        dpy.flush()
    except Exception:
        pass   # window vanished meanwhile


def main():
    single_instance()
    i3 = i3ipc.Connection()
    for con in i3.get_tree().leaves():     # windows that existed before we started
        tag(con, keep=True)
    i3.on(i3ipc.Event.WINDOW_NEW, lambda i3, e: tag(e.container))
    i3.main()


if __name__ == "__main__":
    main()
