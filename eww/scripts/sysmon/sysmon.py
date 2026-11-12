#!/usr/bin/env python3
"""System monitor data for the eww "sysmon" window (defpoll, every 2 s while open).

Prints one JSON object: CPU model/frequency/load/uptime, memory + swap, GPU,
temperatures, disks, battery, network speed and the top processes by CPU.
Per-core usage and the graphs use eww's own EWW_CPU / EWW_RAM.

Process CPU % is measured between two runs (state in $XDG_RUNTIME_DIR), not
the since-start average that `ps` reports.
"""
import glob
import json
import os
import time

RUN = os.environ.get("XDG_RUNTIME_DIR", "/tmp")
STATE = os.path.join(RUN, "eww-sysmon-state.json")
HZ = os.sysconf("SC_CLK_TCK")
PAGE = os.sysconf("SC_PAGE_SIZE")
GIB = 1024 ** 3


def read(path, default=""):
    try:
        with open(path) as fh:
            return fh.read().strip()
    except OSError:
        return default


def cpu_info():
    model, threads = "", 0
    for line in read("/proc/cpuinfo").splitlines():
        if line.startswith("model name") and not model:
            model = line.split(":", 1)[1].strip()
        elif line.startswith("processor"):
            threads += 1
    cores = len({read(p) for p in glob.glob("/sys/devices/system/cpu/cpu*/topology/core_id")}) or threads
    freqs = [int(read(p, "0")) for p in glob.glob("/sys/devices/system/cpu/cpu*/cpufreq/scaling_cur_freq")]
    fmax = int(read("/sys/devices/system/cpu/cpu0/cpufreq/cpuinfo_max_freq", "0"))
    load = read("/proc/loadavg").split()[:3]
    up = float(read("/proc/uptime", "0").split()[0])
    d, rem = divmod(int(up), 86400)
    h, m = rem // 3600, rem % 3600 // 60
    return {
        "model": model.replace("with Radeon Graphics", "").strip(),
        "cores": cores, "threads": threads,
        "freq": round(sum(freqs) / len(freqs) / 1e6, 2) if freqs else 0,
        "freq_max": round(fmax / 1e6, 2),
        "governor": read("/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor", "?"),
        "load": load, "uptime": (f"{d}d " if d else "") + f"{h}h {m}m",
        "procs": len([p for p in os.listdir("/proc") if p.isdigit()]),
    }


def mem_info():
    mi = {}
    for line in read("/proc/meminfo").splitlines():
        k, v = line.split(":", 1)
        mi[k] = int(v.split()[0]) * 1024
    total, avail = mi["MemTotal"], mi["MemAvailable"]
    cached = mi.get("Cached", 0) + mi.get("Buffers", 0) + mi.get("SReclaimable", 0)
    st, sf = mi.get("SwapTotal", 0), mi.get("SwapFree", 0)
    g = lambda b: round(b / GIB, 1)
    return {"total": g(total), "used": g(total - avail), "avail": g(avail), "cached": g(cached),
            "perc": round(100 * (total - avail) / total), "swap_total": g(st), "swap_used": g(st - sf),
            "swap_perc": round(100 * (st - sf) / st) if st else 0}


def gpu_info():
    for dev in glob.glob("/sys/class/drm/card*/device"):
        busy = read(dev + "/gpu_busy_percent")
        if busy:
            vt, vu = int(read(dev + "/mem_info_vram_total", "0")), int(read(dev + "/mem_info_vram_used", "0"))
            return {"present": True, "busy": int(busy), "vram_used": round(vu / GIB, 2),
                    "vram_total": round(vt / GIB, 2), "vram_perc": round(100 * vu / vt) if vt else 0}
    return {"present": False, "busy": 0, "vram_used": 0, "vram_total": 0, "vram_perc": 0}


def temps():
    out = []
    for hw in sorted(glob.glob("/sys/class/hwmon/hwmon*")):
        name = read(hw + "/name")
        for t in sorted(glob.glob(hw + "/temp*_input")):
            label = read(t.replace("_input", "_label")) or name
            val = int(read(t, "0")) / 1000
            if val > 0:
                nice = {"k10temp": "CPU", "amdgpu": "GPU", "nvme": "SSD", "mt7921_phy0": "Wi-Fi",
                        "acpitz": "Board"}.get(name, name)
                if "Sensor" in label:
                    continue          # duplicate SSD sensors
                if label not in (name, "Tctl", "edge", "Composite"):
                    nice += " " + label
                out.append({"name": nice, "value": round(val), "hot": val >= 80})
    seen, uniq = set(), []
    for t in out:
        if t["name"] not in seen:
            seen.add(t["name"])
            uniq.append(t)
    return uniq[:6]


def disks():
    out, seen = [], set()
    for line in read("/proc/mounts").splitlines():
        dev, mnt, fs = line.split()[:3]
        if not dev.startswith("/dev/") or fs in ("squashfs", "iso9660") or dev in seen or "/snap/" in mnt:
            continue
        seen.add(dev)
        try:
            st = os.statvfs(mnt)
        except OSError:
            continue
        total, free = st.f_blocks * st.f_frsize, st.f_bavail * st.f_frsize
        if total < GIB:
            continue
        out.append({"mount": mnt, "used": round((total - free) / GIB), "total": round(total / GIB),
                    "perc": round(100 * (total - free) / total)})
    return out[:4]


def battery():
    b = "/sys/class/power_supply/BAT0"
    if not os.path.isdir(b):
        return {"present": False}
    full, design = int(read(b + "/energy_full", "0")), int(read(b + "/energy_full_design", "0"))
    return {"present": True, "capacity": int(read(b + "/capacity", "0")), "status": read(b + "/status"),
            "power": round(int(read(b + "/power_now", "0")) / 1e6, 1),
            "health": round(100 * full / design) if design else 0}


def procs_and_net(state, now):
    # processes: CPU time delta since the previous run
    ticks, info = {}, []
    for pid in filter(str.isdigit, os.listdir("/proc")):
        st = read(f"/proc/{pid}/stat")
        if not st:
            continue
        name = st[st.find("(") + 1:st.rfind(")")]
        f = st[st.rfind(")") + 2:].split()
        ticks[pid] = int(f[11]) + int(f[12])
        info.append((pid, name, int(f[21]) * PAGE))
    prev, dt = state.get("ticks", {}), max(now - state.get("time", now - 2), 0.5)
    rows = []
    for pid, name, rss in info:
        cpu = (ticks[pid] - prev.get(pid, ticks[pid])) / HZ / dt * 100
        rows.append({"pid": int(pid), "name": name, "cpu": round(cpu, 1), "mem": round(rss / 1024 ** 2)})
    rows.sort(key=lambda r: (-r["cpu"], -r["mem"]))
    # network: bytes delta on the default-route interface
    iface = ""
    for line in read("/proc/net/route").splitlines()[1:]:
        p = line.split()
        if p[1] == "00000000":
            iface = p[0]
            break
    rx = int(read(f"/sys/class/net/{iface}/statistics/rx_bytes", "0")) if iface else 0
    tx = int(read(f"/sys/class/net/{iface}/statistics/tx_bytes", "0")) if iface else 0
    pr, pt = state.get("rx", rx), state.get("tx", tx)
    net = {"iface": iface or "offline", "down": round(max(rx - pr, 0) / dt / 1024), "up": round(max(tx - pt, 0) / dt / 1024)}
    state.update(ticks=ticks, time=now, rx=rx, tx=tx)
    return rows[:8], net


def main():
    now = time.monotonic()
    try:
        state = json.load(open(STATE))
    except (OSError, ValueError):
        state = {}
    procs, net = procs_and_net(state, now)
    with open(STATE, "w") as fh:
        json.dump(state, fh)
    print(json.dumps({"cpu": cpu_info(), "mem": mem_info(), "gpu": gpu_info(), "temps": temps(),
                      "disks": disks(), "bat": battery(), "net": net, "procs": procs}))


if __name__ == "__main__":
    main()
