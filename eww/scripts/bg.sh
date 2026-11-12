#!/usr/bin/env bash
# bg.sh CMD ARGS...: run a click action detached and return at once.
# eww kills click commands after 200 ms; anything slower must go through here.
setsid -f "$@" >/dev/null 2>&1 </dev/null
