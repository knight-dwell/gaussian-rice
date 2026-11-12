#!/usr/bin/env bash
# volume.sh up|down|mute|set N : change the default sink (the listener updates the bar)
case "$1" in
  up)   wpctl set-volume -l 2.0 @DEFAULT_AUDIO_SINK@ 5%+ ;;   # cap 200%: never lowers a boosted volume
  down) wpctl set-volume @DEFAULT_AUDIO_SINK@ 5%- ;;
  mute) wpctl set-mute @DEFAULT_AUDIO_SINK@ toggle ;;
  set)  wpctl set-volume -l 1.0 @DEFAULT_AUDIO_SINK@ "$(printf '%d' "${2%.*}")%" ;;
  *)    echo "usage: $0 up|down|mute|set N" >&2; exit 2 ;;
esac
