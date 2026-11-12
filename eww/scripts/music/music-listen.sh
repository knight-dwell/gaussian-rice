#!/usr/bin/env bash
# eww deflisten: the "current" media player as JSON, one line per change.
# Event-driven: `playerctl --follow` wakes us on any player/track/status change.
#   {"player":"spotify","status":"Playing","title":"..","artist":"..",
#    "art":"/home/../.cache/eww/art/<hash>.jpg","source":"spotify"}
# Picks the first Playing player, else the first Paused one, else nothing.
# Works for Spotify, Firefox, Chrome/Chromium/Brave (any MPRIS player).

ART_DIR="${XDG_CACHE_HOME:-$HOME/.cache}/eww/art"
mkdir -p "$ART_DIR"
trap 'pkill -P $$ 2>/dev/null' EXIT

pick_player() {
  local p s paused=""
  for p in $(playerctl -l 2>/dev/null); do
    s=$(playerctl -p "$p" status 2>/dev/null)
    [[ $s == Playing ]] && { echo "$p"; return; }
    [[ $s == Paused && -z $paused ]] && paused=$p
  done
  echo "$paused"
}

art_for() {  # artUrl -> local file (downloads http(s) art in the background)
  local url=$1 f
  case "$url" in
    file://*) printf '%s' "${url#file://}" | sed 's/%20/ /g' ;;
    http*://*)
      f="$ART_DIR/$(printf '%s' "$url" | md5sum | cut -c1-16).jpg"
      if [[ -s $f ]]; then echo "$f"
      else
        # fetch in the background; the main loop re-emits once the file exists
        echo "$f" > "$ART_DIR/.pending"
        ( curl -fsSL --max-time 10 -o "$f.tmp" "$url" && mv "$f.tmp" "$f" ) >/dev/null 2>&1 &
        echo ""
      fi ;;
    *) echo "" ;;
  esac
}

emit() {
  local p meta status title artist url source
  p=$(pick_player)
  if [[ -z $p ]]; then
    echo '{"player":"","status":"Stopped","title":"","artist":"","art":"","source":"music"}'
    return
  fi
  meta=$(playerctl -p "$p" metadata --format $'{{status}}\x1f{{title}}\x1f{{artist}}\x1f{{mpris:artUrl}}' 2>/dev/null)
  IFS=$'\x1f' read -r status title artist url <<<"$meta"
  case "$p" in
    spotify*) source=spotify ;;
    firefox*) source=firefox ;;
    chrom*|brave*|google*|microsoft*|edge*) source=chrome ;;
    *) source=music ;;
  esac
  jq -cn --arg player "$p" --arg status "${status:-Stopped}" --arg title "$title" \
    --arg artist "$artist" --arg art "$(art_for "$url")" --arg source "$source" \
    '{player: $player, status: $status, title: $title, artist: $artist, art: $art, source: $source}'
}

main() {
  emit
  while true; do
    playerctl -a --follow metadata --format '{{playerName}}{{status}}{{title}}' 2>/dev/null \
      | while true; do
          read -r -t 2 _; rc=$?
          (( rc == 1 )) && break                 # playerctl exited
          if (( rc == 0 )); then emit            # player event
          elif [[ -s $ART_DIR/.pending ]] && [[ -s $(<"$ART_DIR/.pending") ]]; then
            rm -f "$ART_DIR/.pending"; emit      # album art just finished downloading
          fi
        done
    sleep 1
  done
}

main | stdbuf -oL uniq
