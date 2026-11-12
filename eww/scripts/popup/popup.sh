#!/usr/bin/env bash
# popup.sh toggle NAME | close   (always called through bg.sh from the bar)
# One popup at a time (quicksettings, network, bluetooth, notifications).
# While a popup is open i3 is in mode "eww-popup", where Escape closes it;
# popup-watch.py closes it when focus moves to another window.
EWW="$HOME/.local/bin/eww"
# --no-daemonize: if the daemon is slow to answer, `eww open` would otherwise
# start a SECOND daemon (and steal its socket), leaving popups that never close
eww() { "$EWW" --no-daemonize "$@"; }
POPUPS="quicksettings network bluetooth notifications calendar"

# one popup.sh at a time (the watcher's async close can race a toggle)
exec 9>"${XDG_RUNTIME_DIR:-/tmp}/eww-popup.lock"
flock -w 2 9 || exit 0

# leave the popup mode FIRST: closing a popup moves focus back to an app
# window, and popup-watch.py must not treat that as a "click outside"
i3-msg -q mode default

open=" $(eww active-windows 2>/dev/null | cut -d: -f1 | tr '\n' ' ') "
was_open() { [[ $open == *" $1 "* ]]; }

for w in $POPUPS; do was_open "$w" && eww close "$w"; done
rm -f "${XDG_RUNTIME_DIR:-/tmp}/eww-wifi-pw"
CUR="${XDG_RUNTIME_DIR:-/tmp}/eww-popup-current"   # refresh.sh runs while this names its popup

target=""
if [[ $1 == toggle ]] && ! was_open "$2"; then target=$2; fi

# a unique token per opening, so a refresher from an earlier opening always stops
token="$target:$EPOCHREALTIME"
: > "$CUR"; [[ -n $target ]] && echo "$token" > "$CUR"

flag() { [[ $target == "$1" ]] && echo true || echo false; }
# last known lists (from cache) go in the same single eww call, so the popup
# opens already filled; refresh.sh keeps them current while it is open
C="${XDG_CACHE_HOME:-$HOME/.cache}/eww"; lists=()
[[ $target == network && -s $C/wifi.json ]] && lists+=("wifi_list=$(<"$C/wifi.json")")
[[ $target == bluetooth && -s $C/bt.json ]] && lists+=("bt_devices=$(<"$C/bt.json")")
if [[ $target == calendar ]]; then   # always open on today
  lists+=(cal_sel="$(date +%F)" cal_label="$(date '+%A, %d %B')" rem_msg=""
          cal_d="$(date +%-d)" cal_m="$(date +%-m)" cal_y="$(date +%Y)")
fi
eww update qs_open="$(flag quicksettings)" net_open="$(flag network)" \
  bt_open="$(flag bluetooth)" notif_open="$(flag notifications)" cal_open="$(flag calendar)" \
  power_confirm="" pw_key="" net_msg="" net_busy="" bt_busy="" "${lists[@]}" 2>/dev/null

if [[ -n $target ]]; then
  [[ $target == network ]] && ( nmcli device wifi rescan >/dev/null 2>&1 9>&- & )
  primary=$(cat "${XDG_RUNTIME_DIR:-/tmp}/eww-primary" 2>/dev/null)
  eww open "$target" --screen "${primary:-0}" 9>&- ||
    { sleep 0.2; eww open "$target" --screen "${primary:-0}" 9>&-; }
  i3-msg -q mode eww-popup
  setsid -f "$HOME/.config/eww/scripts/popup/refresh.sh" "$target" "$token" >/dev/null 2>&1 </dev/null 9>&-
fi
