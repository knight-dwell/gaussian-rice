#!/usr/bin/env bash
# ~/.config/lockscreen/idle.sh: apply the idle/suspend settings from lock.conf.
# Run by i3 on every start/restart (exec_always); run it by hand after editing
# lock.conf (from a terminal it re-launches itself through i3, see below).
# Keeps exactly one xss-lock running.
#   IDLE_MINUTES      -> X screensaver timeout; xss-lock locks when it fires
#   SCREEN_OFF_AFTER  -> DPMS turns the screen off this long after the lock
#   LOCK_ON_SUSPEND   -> xss-lock locks before sleep (and delays sleep until locked)
# xss-lock must live inside the login session to hear "lock"/"suspend" from
# logind. Programs started from a terminal (kitty) are outside it, so when run
# by hand, hand ourselves to i3, which starts us inside the session.
if ! busctl call org.freedesktop.login1 /org/freedesktop/login1 org.freedesktop.login1.Manager \
     GetSessionByPID u $$ >/dev/null 2>&1; then
  exec i3-msg -q exec "$0"
fi

source "$HOME/.config/lockscreen/lock.conf"
LOCK="$HOME/.config/lockscreen/lock.sh"

pkill -xu "$EUID" xss-lock

if (( IDLE_MINUTES > 0 )); then
  xset s $(( IDLE_MINUTES * 60 )) $(( IDLE_MINUTES * 60 ))
else
  xset s off
fi
if (( SCREEN_OFF_AFTER > 0 && IDLE_MINUTES > 0 )); then
  off=$(( (IDLE_MINUTES + SCREEN_OFF_AFTER) * 60 ))
  xset +dpms dpms 0 0 "$off"
else
  xset -dpms
fi

if [[ $LOCK_ON_SUSPEND == yes ]]; then
  sleep_opt=(--transfer-sleep-lock)
else
  sleep_opt=(--ignore-sleep)
fi
setsid -f xss-lock "${sleep_opt[@]}" -- "$LOCK" >/dev/null 2>&1 </dev/null
