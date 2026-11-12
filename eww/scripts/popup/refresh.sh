#!/usr/bin/env bash
# popup/refresh.sh NAME TOKEN: keeps the open popup's lists fresh. Started (detached)
# by popup.sh when NAME opens; exits as soon as another/no popup is current.
# Only pushes a list to eww when it actually CHANGED: eww rebuilds every row of
# a (for ...) on each update, which would steal clicks and flicker.
EWW="$HOME/.local/bin/eww"; S="$HOME/.config/eww/scripts"
CUR="${XDG_RUNTIME_DIR:-/tmp}/eww-popup-current"
name=$1 token=$2
declare -A last
is_current() { local c=""; read -r c < "$CUR" 2>/dev/null; [[ -n $c && $c == "$token" ]]; }

push() {   # push VAR VALUE: update only when changed
  [[ -n $2 && ${last[$1]} != "$2" ]] || return 0
  last[$1]=$2
  "$EWW" --no-daemonize update "$1=$2" 2>/dev/null
}

case "$name" in
  network)       every=4; tick() { local w v; { read -r w; read -r v; } < <("$S/network/network.py" lists)
                                   push wifi_list "$w"; push vpn_list "$v"; } ;;
  bluetooth)     every=4; tick() { push bt_devices "$("$S/bluetooth/bluetooth.py" devices)"; } ;;
  notifications) every=2; tick() { push notif_history "$("$S/notifications/notifications.py" history)"; } ;;
  *) exit 0 ;;
esac

# seed with what popup.sh already showed from cache, so the first tick is a no-op if equal
C="${XDG_CACHE_HOME:-$HOME/.cache}/eww"
[[ $name == network && -s $C/wifi.json ]] && last[wifi_list]=$(<"$C/wifi.json")
[[ $name == bluetooth && -s $C/bt.json ]] && last[bt_devices]=$(<"$C/bt.json")

while is_current; do
  tick
  for _ in $(seq $((every * 4))); do    # check for close 4x per second
    is_current || exit 0
    sleep 0.25
  done
done
