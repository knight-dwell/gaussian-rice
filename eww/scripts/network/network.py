#!/usr/bin/env python3
"""NetworkManager helper for the eww bar and network popup (uses nmcli).

  network.py listen          deflisten: status JSON on every `nmcli monitor` event
                             (+ a refresh every 30 s so Wi-Fi signal stays current)
  network.py list            JSON list of Wi-Fi networks, best signal first
  network.py vpns            JSON list of NetworkManager VPN/WireGuard connections
  network.py lists           both of the above, one per line (one process for the popup refresher)
  network.py connect KEY     connect to the network whose "key" (from `list`) is KEY:
                             saved network directly; new secured network uses the password
                             stored by pwstore.sh (never on a command line)
  network.py forget-pw       delete the stored password
  network.py disconnect      disconnect the active Wi-Fi
  network.py wifi on|off|toggle
  network.py rescan
  network.py vpn KEY up|down

Network names are attacker-controlled (any nearby AP can pick its SSID), so the
eww side only ever passes hex keys; this script maps keys back to names.
"""
import hashlib
import json
import os
import select
import subprocess
import sys


CACHE = os.path.join(os.environ.get("XDG_CACHE_HOME", os.path.expanduser("~/.cache")), "eww")
PWFILE = os.path.join(os.environ.get("XDG_RUNTIME_DIR", "/tmp"), "eww-wifi-pw")


def key(name):
    return hashlib.sha1(name.encode()).hexdigest()[:12]


def lookup(kind, k):
    """Map a key back to a name using the last list we showed."""
    try:
        for item in json.load(open(os.path.join(CACHE, kind + ".json"))):
            if item["key"] == k:
                return item
    except (OSError, ValueError):
        pass
    sys.exit("network.py: unknown {} key {}".format(kind, k))


def save_cache(kind, items):
    os.makedirs(CACHE, exist_ok=True)
    with open(os.path.join(CACHE, kind + ".json"), "w") as fh:
        json.dump(items, fh)


def nmcli(*args, inp=None, check=False):
    r = subprocess.run(["nmcli", *args], capture_output=True, text=True, input=inp)
    if check and r.returncode != 0:
        raise RuntimeError(r.stderr.strip() or r.stdout.strip())
    return r.stdout


def fields(line):
    """Split one `nmcli -t` line on unescaped ':' (handles '\\:' in SSIDs)."""
    out, cur, esc = [], "", False
    for ch in line:
        if esc:
            cur += ch
            esc = False
        elif ch == "\\":
            esc = True
        elif ch == ":":
            out.append(cur)
            cur = ""
        else:
            cur += ch
    out.append(cur)
    return out


def rows(*args):
    return [fields(l) for l in nmcli("-t", *args).splitlines() if l]


def signal_level(sig):
    return 0 if sig < 20 else 1 if sig < 40 else 2 if sig < 60 else 3 if sig < 80 else 4


def ip_of(dev):
    out = nmcli("-g", "IP4.ADDRESS", "device", "show", dev).split("\n")[0]
    return out.split("/")[0]


def status():
    st = {"state": "disconnected", "ssid": "", "signal": 0, "level": 0, "ip": "",
          "device": "", "radio": nmcli("radio", "wifi").strip() == "enabled",
          "ethernet": {"present": False, "connected": False, "device": "", "ip": ""},
          "vpn": [], "running": True}
    if nmcli("-t", "-f", "RUNNING", "general").strip() != "running":
        st["running"] = False
        return st
    for dev, typ, state, con in rows("-f", "DEVICE,TYPE,STATE,CONNECTION", "device"):
        if typ == "ethernet":
            st["ethernet"]["present"] = True
            if state == "connected":
                st["ethernet"].update(connected=True, device=dev, ip=ip_of(dev))
        elif typ == "wifi" and state == "connected":
            st.update(state="wifi", ssid=con, device=dev, ip=ip_of(dev))
        elif typ in ("vpn", "wireguard", "tun") and state == "connected":
            st["vpn"].append(con)
    if st["state"] == "wifi":
        for active, ssid, sig in rows("-f", "ACTIVE,SSID,SIGNAL", "device", "wifi", "list", "--rescan", "no"):
            if active == "yes":
                st["ssid"] = ssid or st["ssid"]
                st["signal"] = int(sig or 0)
                st["level"] = signal_level(st["signal"])
                break
    if st["ethernet"]["connected"]:  # wired wins for the bar icon
        st.update(state="ethernet", device=st["ethernet"]["device"], ip=st["ethernet"]["ip"])
    for name, typ, active in rows("-f", "NAME,TYPE,ACTIVE", "connection", "show", "--active"):
        if typ in ("vpn", "wireguard") and name not in st["vpn"]:
            st["vpn"].append(name)
    return st


def saved_wifi(conns=None):
    if conns is not None:
        return {name for name, typ in conns if typ == "802-11-wireless"}
    return {name for name, typ in rows("-f", "NAME,TYPE", "connection", "show") if typ == "802-11-wireless"}


def wifi_list(conns=None):
    saved = saved_wifi(conns)
    nets = {}
    for active, ssid, sig, sec in rows("-f", "IN-USE,SSID,SIGNAL,SECURITY", "device", "wifi", "list", "--rescan", "no"):
        if not ssid:
            continue
        sig = int(sig or 0)
        n = nets.get(ssid)
        if n is None or sig > n["signal"]:  # keep the strongest BSSID per SSID
            nets[ssid] = {"ssid": ssid, "key": key(ssid), "signal": sig, "level": signal_level(sig),
                          "secure": sec not in ("", "--"), "active": active == "*",
                          "saved": ssid in saved}
        elif active == "*":
            n["active"] = True
    # stable output (signal bars, not %, and a fixed order) so the popup only
    # re-renders when something visible changed
    out = sorted(nets.values(), key=lambda n: (not n["active"], -n["level"], n["ssid"].lower()))
    for n in out:
        del n["signal"]
    return out


def vpns(conns=None):
    if conns is None:
        conns = rows("-f", "NAME,TYPE", "connection", "show")
    vpn = [name for name, typ in conns if typ in ("vpn", "wireguard")]
    if not vpn:
        return []
    active = {r[0] for r in rows("-f", "NAME", "connection", "show", "--active")}
    return [{"name": name, "key": key(name), "active": name in active} for name in vpn]


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
        mon = subprocess.Popen(["nmcli", "monitor"], stdout=subprocess.PIPE, text=True)
        while True:
            ready, _, _ = select.select([mon.stdout], [], [], 30)
            if ready:
                if not mon.stdout.readline():
                    break  # NetworkManager restarted: start monitor again
                # drain the burst of lines that usually follows one change
                while select.select([mon.stdout], [], [], 0.3)[0]:
                    if not mon.stdout.readline():
                        break
            emit()
        mon.kill()


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "listen"
    if cmd == "listen":
        listen()
    elif cmd == "list":
        nets = wifi_list()
        save_cache("wifi", nets)
        print(json.dumps(nets))
    elif cmd == "lists":
        conns = rows("-f", "NAME,TYPE", "connection", "show")
        nets, v = wifi_list(conns), vpns(conns)
        save_cache("wifi", nets)
        save_cache("vpn", v)
        print(json.dumps(nets))
        print(json.dumps(v))
    elif cmd == "vpns":
        v = vpns()
        save_cache("vpn", v)
        print(json.dumps(v))
    elif cmd == "connect":
        net = lookup("wifi", sys.argv[2])
        ssid = net["ssid"]
        try:
            if ssid in saved_wifi():
                nmcli("connection", "up", "id", ssid, check=True)
            else:
                pw = ""
                if net["secure"]:
                    try:
                        pw = open(PWFILE).read().rstrip("\n")
                    except OSError:
                        sys.exit("network.py: no password stored")
                # --ask reads the secret from stdin, so it never shows up in `ps`
                nmcli("--ask", "device", "wifi", "connect", ssid, inp=pw + "\n", check=True)
            print("connected to " + ssid)
        except RuntimeError as e:
            print(str(e).splitlines()[-1] if str(e) else "failed")
            sys.exit(1)
        finally:
            if os.path.exists(PWFILE):
                os.remove(PWFILE)
    elif cmd == "forget-pw":
        if os.path.exists(PWFILE):
            os.remove(PWFILE)
    elif cmd == "disconnect":
        dev = status()["device"]
        if dev:
            nmcli("device", "disconnect", dev)
    elif cmd == "wifi":
        want = sys.argv[2]
        if want == "toggle":
            want = "off" if status()["radio"] else "on"
        nmcli("radio", "wifi", want)
    elif cmd == "rescan":
        nmcli("device", "wifi", "rescan")
    elif cmd == "vpn":
        if sys.argv[3] in ("up", "down"):
            nmcli("connection", sys.argv[3], "id", lookup("vpn", sys.argv[2])["name"])
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
