#!/usr/bin/env bash
# miniterm.sh: quarter-screen floating terminal (Super+Shift+Enter), like the
# YouTube mini player: borderless card on every workspace. First press starts
# it, then each press shows/hides the same window (what runs in it keeps
# running). Drag it anywhere: it reappears where you left it.
# First size/place: the for_window rule in the i3 config.
if i3-msg -t get_tree | jq -e '[.. | objects | select(.window_properties?.class? == "miniterm")] | length > 0' >/dev/null; then
  i3-msg -q '[class="^miniterm$"] scratchpad show'
else
  # RICE_NO_FETCH: no startup art (it would fill the small window)
  RICE_NO_FETCH=1 setsid -f kitty --class miniterm --title "mini terminal" >/dev/null 2>&1
fi
