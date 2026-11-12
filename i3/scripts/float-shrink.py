#!/usr/bin/env python3
"""float-shrink: when you float a window by hand (Super+Shift+Space), shrink it
to a centered, comfortable size. picom's "geometry" animation makes the
resize/move smooth. Windows that float on their own (dialogs, popups) are
left alone, and so is the keybinding itself.

Started from the i3 config with exec_always; a pidfile makes sure only one copy
runs (a new start replaces the old one).
"""
import os
import signal
import time

import i3ipc

# size of a freshly floated window, in percent of the screen
WIDTH_PPT = 60
HEIGHT_PPT = 65

# only react to floating that a key binding just caused (for_window rules also
# report "user_on", and those windows choose their own size)
last_float_binding = [0.0]

PIDFILE = os.path.join(os.environ.get("XDG_RUNTIME_DIR", "/tmp"), "i3-float-shrink.pid")


def single_instance():
    try:
        old = int(open(PIDFILE).read())
        if old != os.getpid():
            os.kill(old, signal.SIGTERM)
    except (OSError, ValueError):
        pass
    with open(PIDFILE, "w") as fh:
        fh.write(str(os.getpid()))


def on_binding(i3, event):
    if "floating" in (event.binding.command or ""):
        last_float_binding[0] = time.monotonic()


def on_floating(i3, event):
    con = event.container
    if time.monotonic() - last_float_binding[0] > 1.0:
        return
    # "user_on" = floated by the user; "auto_on" = dialogs etc. (skip)
    if con.floating != "user_on":
        return
    # eww popups are floated by an i3 rule; they size themselves
    if (con.name or "").startswith("Eww - "):
        return
    i3.command(
        "[con_id={}] resize set {} ppt {} ppt, move position center".format(
            con.id, WIDTH_PPT, HEIGHT_PPT
        )
    )


def main():
    single_instance()
    i3 = i3ipc.Connection()
    i3.on(i3ipc.Event.BINDING, on_binding)
    i3.on(i3ipc.Event.WINDOW_FLOATING, on_floating)
    i3.main()  # returns when i3 exits or restarts; exec_always starts us again


if __name__ == "__main__":
    main()
