#!/usr/bin/env python3
"""eww deflisten `music`: the player the bar shows, plus every player for the
media popup (right-click the bar's music pill). One JSON line per change,
event-driven (`playerctl --follow`), no polling.

Which player the bar shows is "sticky":
  * a player that STARTS playing takes the bar;
  * pausing keeps the bar on that player (it no longer jumps to some other
    paused tab, e.g. Firefox after you pause Spotify), so you resume it there;
  * picking a player in the popup puts it in the bar (music.sh select NAME
    writes the pick and sends this process SIGUSR1);
  * only when the shown player closes does the bar fall back to another one.

Output: {"player","status","title","artist","art","source", "players":[{... "name","selected"}]}
Album art from http(s) is downloaded to ~/.cache/eww/art in the background.
(The previous bash version, music-listen.sh, is kept next to this file.)
"""
import hashlib
import json
import os
import select
import signal
import subprocess
import threading
import urllib.parse

RUN = os.environ.get("XDG_RUNTIME_DIR", "/tmp")
PICK = os.path.join(RUN, "eww-music-pick")          # written by music.sh select
PIDFILE = os.path.join(RUN, "eww-music-listen.pid")
CURRENT = os.path.join(RUN, "eww-music-current")   # survives an eww restart
ART = os.path.join(os.environ.get("XDG_CACHE_HOME", os.path.expanduser("~/.cache")), "eww", "art")
FMT = "{{status}}\x1f{{title}}\x1f{{artist}}\x1f{{mpris:artUrl}}"
EMPTY = {"player": "", "status": "Stopped", "title": "", "artist": "", "art": "", "source": "music", "players": []}

wake_r, wake_w = os.pipe()        # SIGUSR1 / finished art downloads wake the main loop
os.set_blocking(wake_w, False)
fetching = set()
state = {"cur": None, "prev": {}, "last": None}


def sh(*args):
    try:
        return subprocess.run(args, capture_output=True, text=True, timeout=3).stdout
    except (OSError, subprocess.TimeoutExpired):
        return ""


def wake(*_):
    try:
        os.write(wake_w, b".")
    except BlockingIOError:
        pass


def source_of(name):
    n = name.lower()
    if n.startswith("spotify"):
        return "spotify"
    if n.startswith("firefox"):
        return "firefox"
    if n.startswith(("chrom", "brave", "google", "microsoft", "edge")):
        return "chrome"
    return "music"


def art_for(url):
    if url.startswith("file://"):
        return urllib.parse.unquote(url[7:])
    if url.startswith(("http://", "https://")):
        f = os.path.join(ART, hashlib.md5(url.encode()).hexdigest()[:16] + ".jpg")
        if os.path.isfile(f) and os.path.getsize(f):
            return f
        if url not in fetching:
            fetching.add(url)
            threading.Thread(target=fetch, args=(url, f), daemon=True).start()
    return ""


def fetch(url, f):
    os.makedirs(ART, exist_ok=True)
    r = subprocess.run(["curl", "-fsSL", "--max-time", "10", "-o", f + ".tmp", url], capture_output=True)
    if r.returncode == 0:
        os.replace(f + ".tmp", f)
        wake()                     # re-emit with the picture


def players():
    out = []
    for name in sh("playerctl", "-l").split():
        status, title, artist, url = (sh("playerctl", "-p", name, "metadata", "--format", FMT).rstrip("\n").split("\x1f") + [""] * 4)[:4]
        if status not in ("Playing", "Paused"):
            continue                # stopped/empty sessions (closed video) are noise
        pretty = name.split(".")[0].capitalize()
        out.append({"player": name, "name": pretty, "status": status, "title": title, "artist": artist,
                    "art": art_for(url), "source": source_of(name)})
    return out


def choose(ps):
    names = {p["player"]: p["status"] for p in ps}
    cur, prev = state["cur"], state["prev"]
    pick = None
    try:
        with open(PICK) as fh:
            pick = fh.read().strip()
        os.remove(PICK)
    except OSError:
        pass
    started = [n for n, s in names.items() if s == "Playing" and prev.get(n) != "Playing"]
    if pick in names:
        cur = pick
    elif started:
        cur = started[0]
    elif cur not in names:
        playing = [n for n, s in names.items() if s == "Playing"]
        cur = (playing or list(names) or [None])[0]
    if cur != state["cur"] and cur:
        with open(CURRENT, "w") as fh:
            fh.write(cur)
    state["cur"], state["prev"] = cur, names
    return cur


def emit():
    ps = players()
    cur = choose(ps)
    for p in ps:
        p["selected"] = p["player"] == cur
    shown = next((p for p in ps if p["selected"]), None)
    data = dict(EMPTY) if shown is None else {k: shown[k] for k in ("player", "status", "title", "artist", "art", "source")}
    data["players"] = ps
    line = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    if line != state["last"]:
        state["last"] = line
        print(line, flush=True)


def main():
    with open(PIDFILE, "w") as fh:
        fh.write(str(os.getpid()))
    signal.signal(signal.SIGUSR1, wake)
    try:                        # after an eww restart, keep showing the same player
        with open(CURRENT) as fh:
            state["cur"] = fh.read().strip() or None
        state["prev"] = {p["player"]: p["status"] for p in players()}   # nothing "just started"
    except OSError:
        pass
    emit()
    while True:
        follow = subprocess.Popen(["playerctl", "-a", "--follow", "metadata", "--format", "{{playerName}}{{status}}{{title}}"],
                                  stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
        try:
            while True:
                ready, _, _ = select.select([follow.stdout, wake_r], [], [])
                if wake_r in ready:
                    os.read(wake_r, 4096)
                if follow.stdout in ready and not follow.stdout.readline():
                    break               # playerctl exited: restart it
                emit()
        finally:
            follow.kill()
        select.select([wake_r], [], [], 1)
        emit()


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, BrokenPipeError):
        pass
