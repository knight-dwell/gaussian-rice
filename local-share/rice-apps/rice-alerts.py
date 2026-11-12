#!/usr/bin/env python3
"""rice-alerts: battery-low and high-CPU-temperature notifications (dunst).

  rice-alerts                    run (started by i3; one copy runs)
  rice-alerts --test BAT TEMP    one check with fake values, e.g. --test 8 96,
                                 to see the notifications; real state untouched

Thresholds: ~/.config/rice-alerts/alerts.conf (re-read on every check).
"""
import glob
import os
import signal
import subprocess
import sys
import time

CONF = os.path.expanduser("~/.config/rice-alerts/alerts.conf")
PIDFILE = os.path.join(os.environ.get("XDG_RUNTIME_DIR", "/tmp"), "rice-alerts.pid")
DEFAULTS = {"CHECK_EVERY": 30, "BATTERY_LOW": 20, "BATTERY_CRITICAL": 10, "TEMP_HIGH": 85, "TEMP_CRITICAL": 95}
HYSTERESIS = 5


def conf():
    c = dict(DEFAULTS)
    try:
        for line in open(CONF):
            line = line.split("#", 1)[0].strip()
            if "=" in line:
                k, v = (x.strip() for x in line.split("=", 1))
                if k in c and v.lstrip("-").isdigit():
                    c[k] = int(v)
    except OSError:
        pass
    return c


def read(path, default=""):
    try:
        return open(path).read().strip()
    except OSError:
        return default


def battery():
    b = "/sys/class/power_supply/BAT0"
    if not os.path.isdir(b):
        return None, ""
    return int(read(b + "/capacity", "100")), read(b + "/status")


def cpu_temp():
    for hw in glob.glob("/sys/class/hwmon/hwmon*"):
        if read(hw + "/name") in ("k10temp", "coretemp", "zenpower"):
            vals = [int(read(t, "0")) / 1000 for t in glob.glob(hw + "/temp*_input")]
            if vals:
                return max(vals)
    return None


def notify(urgency, icon, title, body):
    subprocess.run(["notify-send", "-a", "System", "-u", urgency, "-i", icon, title, body])


class Alerts:
    def __init__(self):
        self.bat_level = 0      # 0 none, 1 low sent, 2 critical sent (this discharge)
        self.temp_level = 0     # 0 none, 1 high sent, 2 critical sent

    def check(self, cap, status, temp, c):
        if cap is not None:
            if status in ("Charging", "Full", "Not charging"):
                self.bat_level = 0
            elif cap <= c["BATTERY_CRITICAL"] and self.bat_level < 2:
                self.bat_level = 2
                notify("critical", "battery-caution", f"Battery critical: {cap}%",
                       "Plug in the charger now; the laptop will shut down soon.")
            elif cap <= c["BATTERY_LOW"] and self.bat_level < 1:
                self.bat_level = 1
                notify("normal", "battery-low", f"Battery low: {cap}%", "Consider plugging in the charger.")
        if temp is not None:
            if temp >= c["TEMP_CRITICAL"] and self.temp_level < 2:
                self.temp_level = 2
                notify("critical", "dialog-warning", f"CPU very hot: {temp:.0f} °C",
                       "Close heavy programs and check the fan / air vents.")
            elif temp >= c["TEMP_HIGH"] and self.temp_level < 1:
                self.temp_level = 1
                notify("normal", "dialog-warning", f"CPU hot: {temp:.0f} °C", "Something is working the CPU hard.")
            elif temp < c["TEMP_HIGH"] - HYSTERESIS:
                self.temp_level = 0


def main():
    if len(sys.argv) == 4 and sys.argv[1] == "--test":
        cap, temp = int(sys.argv[2]), float(sys.argv[3])
        Alerts().check(cap, "Discharging", temp, conf())
        return
    try:
        old = int(open(PIDFILE).read())
        if old != os.getpid() and b"rice-alerts" in open(f"/proc/{old}/cmdline", "rb").read():
            os.kill(old, signal.SIGTERM)
    except (OSError, ValueError):
        pass
    with open(PIDFILE, "w") as fh:
        fh.write(str(os.getpid()))
    a = Alerts()
    while True:
        c = conf()
        cap, status = battery()
        a.check(cap, status, cpu_temp(), c)
        time.sleep(max(5, c["CHECK_EVERY"]))


if __name__ == "__main__":
    main()
