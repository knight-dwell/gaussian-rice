#!/usr/bin/env bash
# nightlight.sh status | toggle | restore   (gammastep)
#   modes: off -> auto -> on -> off ...   (the quick-settings tile cycles them)
#   auto: gammastep runs as a daemon with the dusk/dawn schedule in
#         ~/.config/gammastep/config.ini (smooth fade in the evening/morning)
#   on:   warm all the time (NIGHT_TEMP)
#   restore: re-apply the saved mode (run by i3 at login)
NIGHT_TEMP=4200
STATE="${XDG_CACHE_HOME:-$HOME/.cache}/eww/nightlight"   # contains: auto | on (missing = off)
mkdir -p "$(dirname "$STATE")"
mode() { [[ -s $STATE ]] && cat "$STATE" || echo off; }

apply() {
  pkill -xu "$EUID" gammastep
  sleep 0.1
  case "$1" in
    auto) setsid -f gammastep >/dev/null 2>&1 ;;                          # schedule from config.ini
    on)   gammastep -P -O "$NIGHT_TEMP" >/dev/null 2>&1 ;;                # one-shot, stays set
    off)  gammastep -x >/dev/null 2>&1 ;;                                 # back to neutral
  esac
}

case "$1" in
  status) mode ;;
  toggle)
    case "$(mode)" in off) next=auto ;; auto) next=on ;; *) next=off ;; esac
    [[ $next == off ]] && rm -f "$STATE" || echo "$next" > "$STATE"
    apply "$next"
    "$HOME/.local/bin/eww" update nightlight="$next" ;;
  restore) [[ $(mode) != off ]] && apply "$(mode)" ;;
esac
