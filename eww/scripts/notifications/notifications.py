#!/usr/bin/env python3
"""dunst helper for the eww bell and notification-history popup.

  notifications.py listen     deflisten: {"count": N, "paused": bool, "waiting": N}
                              on every notification / close / dunstctl command (D-Bus, no polling)
  notifications.py history    JSON list of past notifications, newest first
  notifications.py dnd        toggle do-not-disturb (dunst "paused")
  notifications.py clear      clear the history
"""
import json
import select
import subprocess
import sys
import time


def dunstctl(*args):
    try:
        return subprocess.run(["dunstctl", *args], capture_output=True, text=True, timeout=3).stdout.strip()
    except subprocess.TimeoutExpired:
        return ""


def status():
    def num(s):
        try:
            return int(s)
        except ValueError:
            return 0
    return {"count": num(dunstctl("count", "history")),
            "paused": dunstctl("is-paused") == "true",
            "waiting": num(dunstctl("count", "waiting"))}


def history():
    try:
        data = json.loads(dunstctl("history") or "{}")
    except ValueError:
        return []
    out = []
    for n in data.get("data", [[]])[0]:
        val = lambda k: n.get(k, {}).get("data", "")
        out.append({"id": val("id"), "app": val("appname"), "summary": val("summary"),
                    "body": val("body"), "icon": val("icon_path"),
                    # timestamp is monotonic microseconds; show relative age
                    "age": age(val("timestamp"))})
    return out


def age(ts_us):
    try:
        secs = time.clock_gettime(time.CLOCK_MONOTONIC) - int(ts_us) / 1e6
    except (TypeError, ValueError):
        return ""
    if secs < 60:
        return "now"
    if secs < 3600:
        return "{}m".format(int(secs // 60))
    if secs < 86400:
        return "{}h".format(int(secs // 3600))
    return "{}d".format(int(secs // 86400))


def listen():
    last = None

    def emit():
        nonlocal last
        line = json.dumps(status())
        if line != last:
            print(line, flush=True)
            last = line

    while True:
        emit()
        mon = subprocess.Popen(
            ["dbus-monitor", "--session",
             "type='method_call',interface='org.freedesktop.Notifications',member='Notify'",
             "type='signal',interface='org.freedesktop.Notifications',member='NotificationClosed'",
             "type='method_call',interface='org.dunstproject.cmd0'",
             "type='method_call',interface='org.freedesktop.DBus.Properties',path='/org/freedesktop/Notifications'"],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
        while True:
            ready, _, _ = select.select([mon.stdout], [], [], 600)
            if ready:
                if not mon.stdout.readline():
                    break
                while select.select([mon.stdout], [], [], 0.3)[0]:
                    if not mon.stdout.readline():
                        break
                time.sleep(0.2)  # let dunst move the notification into history
            emit()
        mon.kill()
        time.sleep(1)


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "listen"
    if cmd == "listen":
        listen()
    elif cmd == "history":
        print(json.dumps(history()))
    elif cmd == "dnd":
        dunstctl("set-paused", "toggle")
    elif cmd == "clear":
        dunstctl("history-clear")
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
