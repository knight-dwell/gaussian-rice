#!/usr/bin/env python3
"""rice-clip: small clipboard history with a rofi picker (text only).

  rice-clip daemon   watch the CLIPBOARD and remember what was copied
                     (started by i3; one copy runs, a new start replaces it)
  rice-clip pick     rofi list of recent copies; the chosen one goes back on
                     the clipboard, ready for Ctrl+V (Super+V)
  rice-clip clear    forget everything

History: ~/.cache/rice-clip/history.json (only you can read it, newest first,
MAX_ITEMS entries). Copies from password managers (BLOCKED_CLASSES) and very
large copies are never stored.
"""
import json
import os
import signal
import subprocess
import sys
import time

CACHE = os.path.join(os.environ.get("XDG_CACHE_HOME", os.path.expanduser("~/.cache")), "rice-clip")
HISTORY = os.path.join(CACHE, "history.json")
PIDFILE = os.path.join(os.environ.get("XDG_RUNTIME_DIR", "/tmp"), "rice-clip.pid")
MAX_ITEMS = 50
MAX_BYTES = 64 * 1024
BLOCKED_CLASSES = {"keepassxc", "keepass2", "bitwarden", "1password", "seahorse", "kwalletmanager5"}


def load():
    try:
        with open(HISTORY) as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return []


def save(items):
    os.makedirs(CACHE, mode=0o700, exist_ok=True)
    tmp = HISTORY + ".tmp"
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as fh:
        json.dump(items, fh)
    os.replace(tmp, HISTORY)


def read_clipboard():
    try:
        r = subprocess.run(["xclip", "-o", "-selection", "clipboard", "-t", "UTF8_STRING"],
                           capture_output=True, timeout=2)
    except subprocess.TimeoutExpired:
        return None
    if r.returncode != 0 or len(r.stdout) > MAX_BYTES:
        return None
    try:
        return r.stdout.decode("utf-8")
    except UnicodeDecodeError:
        return None


def owner_class(dpy, atom):
    """WM_CLASS of the window that owns the clipboard (or of its toplevel)."""
    try:
        w = dpy.get_selection_owner(atom)
        for _ in range(4):
            if not w:
                return ""
            cls = w.get_wm_class()
            if cls:
                return cls[1].lower()
            w = w.query_tree().parent
    except Exception:
        pass
    return ""


def remember(text):
    if text is None or not text.strip():
        return
    items = [i for i in load() if i != text]
    items.insert(0, text)
    save(items[:MAX_ITEMS])


def daemon():
    from Xlib import display
    from Xlib.ext import xfixes

    # replace a running copy, but only if that PID really is rice-clip
    # (a stale pidfile may point at an unrelated process by now)
    try:
        old = int(open(PIDFILE).read())
        if old != os.getpid() and b"rice-clip" in open(f"/proc/{old}/cmdline", "rb").read():
            os.kill(old, signal.SIGTERM)
    except (OSError, ValueError):
        pass
    with open(PIDFILE, "w") as fh:
        fh.write(str(os.getpid()))

    dpy = display.Display()
    if not dpy.has_extension("XFIXES"):
        sys.exit("rice-clip: XFIXES extension missing")
    dpy.xfixes_query_version()
    clip = dpy.intern_atom("CLIPBOARD")
    root = dpy.screen().root
    dpy.xfixes_select_selection_input(root, clip, xfixes.XFixesSetSelectionOwnerNotifyMask)
    dpy.flush()
    while True:
        ev = dpy.next_event()
        # python-xlib builds the event class per connection, so match on the
        # event's fields rather than isinstance()
        if getattr(ev, "selection", None) != clip or not hasattr(ev, "owner"):
            continue
        if owner_class(dpy, clip) in BLOCKED_CLASSES:
            continue
        time.sleep(0.05)              # let the owner finish setting up
        remember(read_clipboard())


def preview(text, width=90):
    one = " ".join(text.split())
    return one if len(one) <= width else one[:width - 1] + "…"


def pick():
    items = load()
    if not items:
        subprocess.run(["notify-send", "-a", "Clipboard", "Clipboard history is empty",
                        "Copy something first (Ctrl+C)."])
        return
    menu = "\n".join(f"{preview(t)}" for t in items) + "\n󰆴  Clear history"
    r = subprocess.run(["rofi", "-dmenu", "-i", "-format", "i", "-p", "Clipboard",
                        "-mesg", "Enter = put it back on the clipboard, then paste with Ctrl+V",
                        "-theme-str", "window { width: 760px; } listview { lines: 12; }"],
                       input=menu, capture_output=True, text=True)
    if r.returncode != 0 or not r.stdout.strip().isdigit():
        return
    idx = int(r.stdout.strip())
    if idx == len(items):            # "Clear history"
        clear()
        return
    _serve(items[idx])


def _serve(text):
    """Own the clipboard with this text. xclip forks into the background and
    serves it until something else is copied (the daemon then also moves it
    to the top of the history)."""
    p = subprocess.Popen(["xclip", "-selection", "clipboard", "-i"], stdin=subprocess.PIPE,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    p.stdin.write(text.encode())
    p.stdin.close()


def clear():
    save([])
    subprocess.run(["notify-send", "-a", "Clipboard", "Clipboard history cleared"])


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "pick"
    {"daemon": daemon, "pick": pick, "clear": clear}.get(cmd, lambda: sys.exit(__doc__))()
