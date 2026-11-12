#!/usr/bin/env bash
# music.sh toggle|next|prev [PLAYER]: control the player the bar shows.
# PLAYER comes from the music listener; MPRIS names are [A-Za-z0-9_.-] only,
# anything else is ignored (eww pastes values into the shell unquoted).
p=$2
if [[ ! $p =~ ^[A-Za-z0-9_.-]+$ ]]; then
  p=$(playerctl -l 2>/dev/null | while read -r x; do
        [[ $(playerctl -p "$x" status 2>/dev/null) == Playing ]] && { echo "$x"; break; }
      done)
  [[ -z $p ]] && p=$(playerctl -l 2>/dev/null | head -1)
fi
[[ -z $p ]] && exit 0
case "$1" in
  toggle) playerctl -p "$p" play-pause ;;
  next)   playerctl -p "$p" next ;;
  prev)   playerctl -p "$p" previous ;;
esac
