#!/usr/bin/env bash
# power.sh lock|logout|suspend|reboot|shutdown  (the popup asks for a 2nd click first)
"$HOME/.config/eww/scripts/popup/popup.sh" close
case "$1" in
  # lock)     ~/scripts/lock.sh ;;
  lock)     ~/.config/lockscreen/lock.sh ;;   # Phase 5 lock screen
  logout)   i3-msg exit ;;
  suspend)  systemctl suspend ;;
  reboot)   systemctl reboot ;;
  shutdown) systemctl poweroff ;;
esac
