#!/usr/bin/env python3
"""Reminders for the eww calendar popup.

  reminders.py listen       deflisten: JSON state on start and on every change;
                            also fires due reminders as desktop notifications
                            (missed ones, e.g. while suspended, fire on wake-up)
  reminders.py add DATE     add a reminder on DATE (YYYY-MM-DD); time and text
                            are read from the files written by store.sh (the
                            typed text never goes through a command line)
  reminders.py delete ID    remove one reminder
  reminders.py clear-done   remove reminders that already fired

Data: ~/gaussian_keep/reminders.json (shared with the gaussian_keep app)
  [{"id": "a1b2c3d4", "date": "2026-11-12", "time": "14:30", "text": "...", "fired": false}]
"""
import datetime as dt
import json
import os
import re
import secrets
import signal
import subprocess
import sys

# shared with the gaussian_keep app (Reminders tab), so they sync with it.
# The old location is migrated once and left in place as a backup.
DATA = os.path.expanduser("~/gaussian_keep/reminders.json")
OLD_DATA = os.path.join(os.environ.get("XDG_DATA_HOME", os.path.expanduser("~/.local/share")),
                        "reminders", "reminders.json")
RUN = os.environ.get("XDG_RUNTIME_DIR", "/tmp")
PIDFILE = os.path.join(RUN, "eww-reminders.pid")
INPUT = os.path.join(RUN, "eww-rem-{}")          # store.sh writes eww-rem-time / eww-rem-text


def load():
    if not os.path.exists(DATA) and os.path.exists(OLD_DATA):
        os.makedirs(os.path.dirname(DATA), exist_ok=True)
        with open(OLD_DATA) as src, open(DATA, "w") as dst:
            dst.write(src.read())
    try:
        with open(DATA) as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return []


def save(items):
    os.makedirs(os.path.dirname(DATA), exist_ok=True)
    tmp = DATA + ".tmp"
    with open(tmp, "w") as fh:
        json.dump(items, fh, indent=1)
    os.replace(tmp, DATA)        # atomic: the listener never reads half a file


def when(r):
    return dt.datetime.strptime(r["date"] + " " + r["time"], "%Y-%m-%d %H:%M")


def poke():
    """Wake the listener so the popup updates at once."""
    try:
        os.kill(int(open(PIDFILE).read()), signal.SIGUSR1)
    except (OSError, ValueError):
        pass


def state(items, now):
    items = sorted(items, key=when)
    by_date = {}
    for r in items:
        d = dict(r, past=r["fired"] or when(r) <= now,
                 label=when(r).strftime("%a %d %b"))
        by_date.setdefault(r["date"], []).append(d)
    upcoming = [dict(r, label=when(r).strftime("%a %d %b")) for r in items if not r["fired"]][:6]
    today = now.strftime("%Y-%m-%d")
    return {"by_date": by_date, "upcoming": upcoming,
            "today": sum(1 for r in items if r["date"] == today and not r["fired"]),
            "count": len(items)}


def fire(r):
    subprocess.run(["notify-send", "-a", "Reminder", "-u", "critical", "-i", "appointment-soon",
                    "Reminder · " + r["time"], r["text"]])


def listen():
    # one listener only: a leftover from an earlier eww run would fire every
    # reminder twice, so replace it (only if that PID really is this script)
    try:
        old = int(open(PIDFILE).read())
        if old != os.getpid() and b"reminders.py" in open(f"/proc/{old}/cmdline", "rb").read():
            os.kill(old, signal.SIGTERM)
    except (OSError, ValueError):
        pass
    signal.pthread_sigmask(signal.SIG_BLOCK, [signal.SIGUSR1])
    with open(PIDFILE, "w") as fh:
        fh.write(str(os.getpid()))
    last = None
    while True:
        now = dt.datetime.now()
        items = load()
        due = [r for r in items if not r["fired"] and when(r) <= now]
        if due:
            for r in due:
                fire(r)
                r["fired"] = True
            save(items)
        line = json.dumps(state(items, now))
        if line != last:
            print(line, flush=True)
            last = line
        # sleep until the next reminder or the next minute (date/"past" flags
        # change), whichever is first; add/delete wake us with SIGUSR1
        nxt = [(when(r) - now).total_seconds() for r in items if not r["fired"]]
        to_minute = 60 - now.second - now.microsecond / 1e6
        signal.sigtimedwait([signal.SIGUSR1], max(0.2, min(nxt + [to_minute])))


def read_input(name):
    try:
        with open(INPUT.format(name)) as fh:
            return fh.read().strip()
    except OSError:
        return ""


def add(date):
    try:
        dt.datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        sys.exit("Invalid date")
    t = read_input("time") or "09:00"
    m = re.fullmatch(r"(\d{1,2})[:.]?(\d{2})?\s*([aApP][mM])?", t)
    if not m:
        sys.exit("Time must look like 14:30 or 2:30pm")
    h, mi = int(m.group(1)), int(m.group(2) or 0)
    if m.group(3):
        h = h % 12 + (12 if m.group(3).lower() == "pm" else 0)
    if h > 23 or mi > 59:
        sys.exit("Time must look like 14:30 or 2:30pm")
    text = " ".join(read_input("text").split())[:200]
    if not text:
        sys.exit("Type what to remind you about")
    r = {"id": secrets.token_hex(4), "date": date, "time": "{:02d}:{:02d}".format(h, mi),
         "text": text, "fired": False}
    r["fired"] = when(r) <= dt.datetime.now() - dt.timedelta(minutes=1)   # no alarm for the past
    items = load()
    items.append(r)
    save(items)
    for name in ("time", "text"):
        try:
            os.remove(INPUT.format(name))
        except OSError:
            pass
    poke()
    print("Reminder set for {} {}".format(when(r).strftime("%a %d %b"), r["time"]))


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "listen"
    if cmd == "listen":
        listen()
    elif cmd == "add" and len(sys.argv) == 3:
        add(sys.argv[2])
    elif cmd == "delete" and len(sys.argv) == 3 and re.fullmatch(r"[0-9a-f]{8}", sys.argv[2]):
        save([r for r in load() if r["id"] != sys.argv[2]])
        poke()
    elif cmd == "clear-done":
        save([r for r in load() if not r["fired"]])
        poke()
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
