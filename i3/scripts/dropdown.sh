#!/usr/bin/env bash
# dropdown.sh: Quake-style terminal (Super+T). First press starts it, then each
# press shows/hides the same window, so whatever runs in it keeps running.
# Placement/size come from the for_window rule in the i3 config.
if i3-msg -t get_tree | jq -e '[.. | objects | select(.window_properties?.class? == "dropdown")] | length > 0' >/dev/null; then
  i3-msg -q '[class="^dropdown$"] scratchpad show, move position 10 ppt 56 px'
else
  # RICE_NO_FETCH: no startup art in this quick terminal
  RICE_NO_FETCH=1 setsid -f kitty --class dropdown --title "dropdown" >/dev/null 2>&1
fi
