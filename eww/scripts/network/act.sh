#!/usr/bin/env bash
# network/act.sh ACTION [KEY]: network popup actions with live feedback.
#   disconnect | connect KEY | wifi-toggle | rescan | vpn KEY up|down
# Shows progress via eww vars (net_busy, net_msg) and refreshes the list at once.
EWW="$HOME/.local/bin/eww"; N="$HOME/.config/eww/scripts/network/network.py"
refresh() { local w v; { read -r w; read -r v; } < <("$N" lists); "$EWW" update wifi_list="$w" vpn_list="$v"; }
case "$1" in
  disconnect)
    "$EWW" update net_busy=disconnect net_msg="Disconnecting…"
    "$N" disconnect; "$EWW" update net_busy="" net_msg="" ;;
  connect)
    "$EWW" update net_busy="$2" pw_key="" net_msg="Connecting…"
    msg=$("$N" connect "$2" 2>&1 | tail -1)
    "$EWW" update net_busy="" net_msg="$msg" ;;
  wifi-toggle) "$N" wifi toggle ;;
  rescan)
    "$EWW" update net_busy=rescan net_msg="Scanning…"
    nmcli device wifi rescan >/dev/null 2>&1; sleep 2
    "$EWW" update net_busy="" net_msg="" ;;
  vpn) "$EWW" update net_busy="$2"; "$N" vpn "$2" "$3"; "$EWW" update net_busy="" ;;
esac
refresh
