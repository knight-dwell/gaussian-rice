#!/usr/bin/env bash
# mic.sh status | toggle
case "$1" in
  status) wpctl get-volume @DEFAULT_AUDIO_SOURCE@ 2>/dev/null | grep -q MUTED && echo muted || echo on ;;
  toggle) wpctl set-mute @DEFAULT_AUDIO_SOURCE@ toggle
          "$HOME/.local/bin/eww" update mic="$("$0" status)" ;;
esac
