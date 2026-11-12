#!/usr/bin/env bash
# tube.sh: YouTube window (Super+Shift+Enter). It tiles next to your other
# windows like a new kitty terminal does (resize it like any tiled window:
# drag the border with the mouse, or Super+R then the arrow keys).
#   not running              → start Rice Tube here
#   on this workspace        → hide it (scratchpad); the video keeps playing
#   hidden / other workspace → bring it here, tiled again, focused
C='[class="^RiceTube$"]'
tree=$(i3-msg -t get_tree)
id=$(jq -r '.. | objects | select(.window_properties?.class? == "RiceTube") | .id' <<<"$tree" | head -1)
if [[ -z $id ]]; then
  setsid -f "$HOME/.local/bin/rice-tube" >/dev/null 2>&1
  exit 0
fi
# the workspace that contains the window (scratchpad = "__i3_scratch")
ws=$(jq -r --argjson id "$id" '.. | objects | select(.type? == "workspace") | select([.. | objects | .id?] | index($id)) | .name' <<<"$tree" | head -1)
cur=$(i3-msg -t get_workspaces | jq -r '.[] | select(.focused) | .name')
if [[ $ws == "$cur" ]]; then
  i3-msg -q "$C move scratchpad"
elif [[ $ws == __i3_scratch ]]; then
  i3-msg -q "$C scratchpad show, floating disable, focus"
else
  i3-msg -q "$C move container to workspace current, focus"
fi
