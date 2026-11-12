#!/usr/bin/env python3
"""Bluetooth helper for the eww bar and popup (BlueZ via bluetoothctl).

  bluetooth.py listen            deflisten: status JSON whenever BlueZ changes
                                 (watches BlueZ D-Bus signals, no polling)
  bluetooth.py devices           JSON list of paired devices with connected flag
  bluetooth.py power on|off|toggle
  bluetooth.py connect MAC | disconnect MAC | toggle MAC
"""
import json
import os
import re
import select
import subprocess
import sys


def btctl(*args, timeout=8):
    try:
        return subprocess.run(["bluetoothctl", *args], capture_output=True, text=True,
                              timeout=timeout).stdout
    except subprocess.TimeoutExpired:
        return ""


def devices(kind):
    """[(mac, name)] from `bluetoothctl devices Paired|Connected`."""
    out = []
    for line in btctl("devices", kind).splitlines():
        m = re.match(r"Device ([0-9A-F:]{17}) (.*)", line.strip())
        if m:
            out.append((m.group(1), m.group(2)))
    return out


def status():
    show = btctl("show")
    if not show.strip() or "No default controller" in show:
        return {"available": False, "powered": False, "connected": [], "count": 0}
    powered = bool(re.search(r"^\s*Powered: yes", show, re.M))
    connected = [name for _, name in devices("Connected")] if powered else []
    return {"available": True, "powered": powered, "connected": connected, "count": len(connected)}


def device_list():
    connected = {mac for mac, _ in devices("Connected")}
    out = []
    for mac, name in devices("Paired"):
        info = btctl("info", mac)
        icon = re.search(r"^\s*Icon: (\S+)", info, re.M)
        batt = re.search(r"Battery Percentage: 0x[0-9a-f]+ \((\d+)\)", info)
        out.append({"mac": mac, "name": name, "connected": mac in connected,
                    "icon": icon.group(1) if icon else "",
                    "battery": int(batt.group(1)) if batt else -1})
    return sorted(out, key=lambda d: (not d["connected"], d["name"].lower()))


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
            ["dbus-monitor", "--system",
             "type='signal',sender='org.bluez',interface='org.freedesktop.DBus.Properties'",
             "type='signal',sender='org.bluez',interface='org.freedesktop.DBus.ObjectManager'"],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
        while True:
            ready, _, _ = select.select([mon.stdout], [], [], 300)
            if ready:
                if not mon.stdout.readline():
                    break
                # coalesce the burst of signals one change produces
                while select.select([mon.stdout], [], [], 0.4)[0]:
                    if not mon.stdout.readline():
                        break
            emit()
        mon.kill()


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "listen"
    if cmd == "listen":
        listen()
    elif cmd == "devices":
        devs = json.dumps(device_list())
        cache = os.path.join(os.environ.get("XDG_CACHE_HOME", os.path.expanduser("~/.cache")), "eww")
        os.makedirs(cache, exist_ok=True)
        with open(os.path.join(cache, "bt.json"), "w") as fh:  # popup shows this instantly next time
            fh.write(devs)
        print(devs)
    elif cmd == "power":
        want = sys.argv[2]
        if want == "toggle":
            want = "off" if status()["powered"] else "on"
        btctl("power", want)
    elif cmd in ("connect", "disconnect", "toggle"):
        mac = sys.argv[2].upper()
        if not re.fullmatch(r"([0-9A-F]{2}:){5}[0-9A-F]{2}", mac):  # only MACs reach bluetoothctl
            sys.exit("bluetooth.py: bad MAC")
        if cmd != "toggle":
            btctl(cmd, mac, timeout=20)
            return
        connected = {m for m, _ in devices("Connected")}
        btctl("disconnect" if mac in connected else "connect", mac, timeout=20)
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
