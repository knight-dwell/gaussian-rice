#!/usr/bin/env bash
# calendar/act.sh add DATE | delete ID | clear-done: reminder actions from the
# calendar popup, with the result shown in the popup (rem_msg).
EWW="$HOME/.local/bin/eww"; R="$HOME/.config/eww/scripts/calendar/reminders.py"
case "$1" in
  add)
    if msg=$("$R" add "$2" 2>&1); then
      "$EWW" update rem_msg="$msg" rem_clear="$EPOCHREALTIME"   # empties the input fields
    else
      "$EWW" update rem_msg="$(tail -1 <<< "$msg")"
    fi ;;
  delete)     "$R" delete "$2" ;;
  clear-done) "$R" clear-done ;;
esac
