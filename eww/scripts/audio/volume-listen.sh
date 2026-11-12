#!/usr/bin/env bash
# eww deflisten: default-sink volume as JSON, one line per change.
#   {"ready":true,"level":45,"muted":false,"sink":"Stone 350 Pro"}
#
# First-login fix: Polybar only showed volume after a reload because it read
# the volume once, before PipeWire was up. This script waits (retrying) until
# the audio server answers, then follows `pactl subscribe` (event-driven),
# and if the server goes away (restart/crash) it waits again.

trap 'pkill -P $$ 2>/dev/null' EXIT

emit() {
  local out level muted sink
  if ! out=$(wpctl get-volume @DEFAULT_AUDIO_SINK@ 2>/dev/null); then
    echo '{"ready":false,"level":0,"muted":true,"sink":""}'
    return
  fi
  # out = "Volume: 0.45" or "Volume: 0.45 [MUTED]"
  level=$(awk '{printf "%d", $2 * 100 + 0.5}' <<<"$out")
  [[ $out == *MUTED* ]] && muted=true || muted=false
  sink=$(pactl -f json list sinks 2>/dev/null \
    | jq -r --arg d "$(pactl get-default-sink 2>/dev/null)" '.[] | select(.name == $d) | .description' 2>/dev/null)
  jq -cn --argjson level "$level" --argjson muted "$muted" --arg sink "$sink" \
    '{ready: true, level: $level, muted: $muted, sink: $sink}'
}

main() {
  while true; do
    # wait for PipeWire/PulseAudio (first login: the bar can start first)
    local tries=0
    until pactl info >/dev/null 2>&1; do
      (( tries++ == 0 )) && echo '{"ready":false,"level":0,"muted":true,"sink":""}'
      sleep 1
    done
    emit
    # sink = volume/mute; server = default sink changed (e.g. BT headset)
    pactl subscribe 2>/dev/null | while read -r line; do
      case "$line" in
        *" on sink "*|*" on server "*) emit ;;
      esac
    done
    sleep 1  # subscribe ended: audio server restarted, wait for it again
  done
}

# uniq drops repeated identical lines (pactl sends bursts of events)
main | stdbuf -oL uniq
