#!/usr/bin/env bash
# bluetooth/act.sh toggle MAC | power: Bluetooth popup actions with live
# feedback (bt_busy) and an immediate device-list refresh.
EWW="$HOME/.local/bin/eww"; B="$HOME/.config/eww/scripts/bluetooth/bluetooth.py"
case "$1" in
  toggle) "$EWW" update bt_busy="$2"; "$B" toggle "$2" ;;
  power)  "$EWW" update bt_busy=power; "$B" power toggle ;;
esac
"$EWW" update bt_devices="$("$B" devices)" bt_busy=""
