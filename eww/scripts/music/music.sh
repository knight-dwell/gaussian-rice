#!/usr/bin/env bash
# music.sh toggle|next|prev|select|pip [PLAYER]: control a media player.
#   toggle/next/prev  the player the bar (or the media popup) shows
#   select            show PLAYER in the bar (media popup → click a player)
#   pip               pop the YouTube video out of Firefox (Picture-in-Picture)
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
RUN=${XDG_RUNTIME_DIR:-/tmp}
case "$1" in
  toggle) playerctl -p "$p" play-pause ;;
  next)   playerctl -p "$p" next ;;
  prev)   playerctl -p "$p" previous ;;
  select) echo "$p" > "$RUN/eww-music-pick"
          kill -USR1 "$(cat "$RUN/eww-music-listen.pid" 2>/dev/null)" 2>/dev/null ;;
  pip)    # Firefox's Picture-in-Picture shortcut (Ctrl+Shift+]) on the window whose
          # active tab plays YouTube; the floating mini player is styled by i3 + picom
          "$HOME/.config/eww/scripts/popup/popup.sh" close
          w=$(xdotool search --onlyvisible --class firefox 2>/dev/null | while read -r id; do
                [[ $(xdotool getwindowname "$id" 2>/dev/null) == *YouTube* ]] && { echo "$id"; break; }
              done)
          [[ -z $w ]] && { notify-send -a Music "Picture-in-Picture" "Open the YouTube video's tab in Firefox first."; exit 0; }
          xdotool windowactivate --sync "$w" key --clearmodifiers ctrl+shift+bracketright ;;
esac
