#!/usr/bin/env python3
"""autotiling: alternate splits automatically, like a spiral/dwindle layout.

Whenever a tiled window gets focus, the split direction for the NEXT window is
set from its shape: wider than tall -> split horizontally (side by side),
taller than wide -> split vertically (stacked). So opening windows one after
another alternates the splits on its own.

Leaves alone: floating and fullscreen windows, tabbed/stacked containers.
Your own $mod+Shift+b / $mod+Shift+v still work (they apply until the next
focus change). Turn it off without editing configs: touch ~/.config/i3/autotiling.off
Started from the i3 config with exec_always; a pidfile keeps one copy running.
"""
import os
import signal

import i3ipc

PIDFILE = os.path.join(os.environ.get("XDG_RUNTIME_DIR", "/tmp"), "i3-autotiling.pid")
OFF = os.path.expanduser("~/.config/i3/autotiling.off")


def single_instance():
    try:
        old = int(open(PIDFILE).read())
        if old != os.getpid() and b"autotiling" in open(f"/proc/{old}/cmdline", "rb").read():
            os.kill(old, signal.SIGTERM)
    except (OSError, ValueError):
        pass
    with open(PIDFILE, "w") as fh:
        fh.write(str(os.getpid()))


def on_focus(i3, event):
    if os.path.exists(OFF):
        return
    con = i3.get_tree().find_focused()
    if (not con or con.type != "con" or con.floating in ("user_on", "auto_on")
            or con.fullscreen_mode == 1 or (con.parent and con.parent.layout in ("tabbed", "stacked"))):
        return
    want = "splitv" if con.rect.height > con.rect.width else "splith"
    if con.parent and con.parent.layout != want:
        i3.command("split v" if want == "splitv" else "split h")


def main():
    single_instance()
    i3 = i3ipc.Connection()
    i3.on(i3ipc.Event.WINDOW_FOCUS, on_focus)
    i3.main()


if __name__ == "__main__":
    main()
