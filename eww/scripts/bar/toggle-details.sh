#!/usr/bin/env bash
# toggle-details.sh: show/hide the collapsible system-details section of the bar (Super+B)
E="$HOME/.local/bin/eww"
[[ $("$E" get expanded) == true ]] && "$E" update expanded=false || "$E" update expanded=true
