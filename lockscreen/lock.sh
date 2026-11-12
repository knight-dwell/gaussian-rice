#!/usr/bin/env bash
# ~/.config/lockscreen/lock.sh: minimal themed lock screen (i3lock-color).
#
#   lock.sh             lock now
#   lock.sh --preview   only render the lock image and print its path (no lock)
#
# Settings: ~/.config/lockscreen/lock.conf. Colors: ~/.config/theme.
# i3lock-color draws the live clock + date; music, CPU and RAM (captured at
# lock time) are drawn onto the blurred wallpaper with ImageMagick first.
# If it ever gets stuck: Ctrl+Alt+F3, log in, `pkill -x i3lock-color`.

DIR="$HOME/.config/lockscreen"
CACHE="${XDG_CACHE_HOME:-$HOME/.cache}/lockscreen"
RUN="${XDG_RUNTIME_DIR:-/tmp}"
LOCKER="$HOME/.local/bin/i3lock-color"
LOG="${XDG_CACHE_HOME:-$HOME/.cache}/lockscreen/lock.log"   # locker errors end up here
PREVIEW=no; [[ $1 == --preview ]] && PREVIEW=yes

# only one lock at a time (idle, suspend and the key can fire together): the
# first caller holds this lock until the screen is unlocked, the rest exit
if [[ $PREVIEW == no ]]; then
  exec 8>"$RUN/lockscreen.lock"
  flock -n 8 || exit 0
  pgrep -xu "$EUID" i3lock-color >/dev/null && exit 0
fi

source "$DIR/lock.conf"
source "$HOME/.config/theme/generated/lock-colors.sh" 2>/dev/null
[[ -x $LOCKER ]] || LOCKER=i3lock-color

# ── settings → values ───────────────────────────────────────────────────────
accent=${ACCENT/theme/${TH_PRIMARY:0:6}};        accent=${accent#\#}
text=${TEXT/theme/${TH_ON_SURFACE:0:6}};         text=${text#\#}
dimtext=${TH_ON_SURFACE_VARIANT:0:6};            dimtext=${dimtext:-c4c6d0}
error=${TH_ERROR:0:6};                           error=${error:-ffb4ab}
family=${FONT/theme/${TH_FONT:-JetBrainsMono Nerd Font}}
font_file=$(fc-match -f '%{file}' "$family:style=Regular")
read -r W H < <(xrandr --current | awk '/current/{gsub(",","",$10); print $8, $10; exit}')
W=${W:-1920}; H=${H:-1080}

wallpaper=$LOCK_WALLPAPER
if [[ $wallpaper == desktop || -z $wallpaper ]]; then
  wallpaper=$(sed -n 's/^file=//p' "$HOME/.config/nitrogen/bg-saved.cfg" 2>/dev/null | head -1)
fi
wallpaper=${wallpaper/#\~/$HOME}

# ── background: blurred + dimmed wallpaper, cached (blur is the slow part) ──
mkdir -p "$CACHE"
if [[ -f $wallpaper ]]; then
  key=$(printf '%s|%s|%s|%s|%sx%s' "$wallpaper" "$(stat -c %Y "$wallpaper")" "$BLUR" "$DIM" "$W" "$H" | sha1sum | cut -c1-16)
  bg="$CACHE/bg-$key.png"
  if [[ ! -f $bg ]]; then
    rm -f "$CACHE"/bg-*.png
    # blur at quarter size, then scale up: same look, ~10x faster
    magick "$wallpaper" -resize "${W}x${H}^" -gravity center -extent "${W}x${H}" \
      -resize 25% -blur "0x$(( BLUR > 0 ? (BLUR + 3) / 4 : 0 ))" -resize "${W}x${H}!" \
      -fill black -colorize "${DIM}%" "$bg"
  fi
else
  bg="$CACHE/bg-plain.png"
  magick -size "${W}x${H}" "xc:#${TH_SURFACE:0:6}" "$bg"
fi

# ── info captured now: music, CPU, RAM ──────────────────────────────────────
info=()
if [[ $SHOW_MUSIC == yes ]] && command -v playerctl >/dev/null; then
  status=$(playerctl status 2>/dev/null)
  if [[ $status == Playing || $status == Paused ]]; then
    artist=$(playerctl metadata artist 2>/dev/null); title=$(playerctl metadata title 2>/dev/null)
    if [[ -n $title ]]; then
      icon=$([[ $status == Playing ]] && echo $'\U000f075a' || echo $'\U000f03e4')   # md-music / md-pause
      info+=("$icon  ${artist:+$artist – }$title")
    fi
  fi
fi
sys=""
if [[ $SHOW_CPU == yes ]]; then
  read -r _ a b c d e f g _ < /proc/stat; t1=$((a+b+c+d+e+f+g)); i1=$((d+e))
  sleep 0.25
  read -r _ a b c d e f g _ < /proc/stat; t2=$((a+b+c+d+e+f+g)); i2=$((d+e))
  sys+=$'\uf4bc'"  CPU $(( 100 * ((t2-t1) - (i2-i1)) / (t2-t1 > 0 ? t2-t1 : 1) ))%"
fi
if [[ $SHOW_RAM == yes ]]; then
  ram=$(awk '/MemTotal/{t=$2} /MemAvailable/{a=$2} END{printf "%.1f / %.1f GB", (t-a)/1048576, t/1048576}' /proc/meminfo)
  sys+="${sys:+       }"$'\uefc5'"  RAM $ram"
fi
[[ -n $sys ]] && info+=("$sys")

# ── compose the lock image ──────────────────────────────────────────────────
img="$RUN/lockscreen.png"
args=(-font "$font_file" -gravity center -pointsize "$INFO_SIZE" -fill "#$dimtext")
y=$(( 120 ))                       # first info line: this far below the screen center
for line in "${info[@]}"; do
  line=${line//%/%%}               # ImageMagick treats % as an escape
  args+=(-annotate "+0+$y" "$line")
  y=$(( y + INFO_SIZE + 18 ))
done
magick "$bg" "${args[@]}" "$img" 2>/dev/null || cp "$bg" "$img"

if [[ $PREVIEW == yes ]]; then
  echo "$img"
  exit 0
fi

# ── lock ────────────────────────────────────────────────────────────────────
greeter=""; [[ $SHOW_USER == yes ]] && greeter="Locked · $USER"
opts=(
  -i "$img" --ignore-empty-password --show-failed-attempts
  --pass-media-keys --pass-volume-keys --pass-screen-keys
  --clock --force-clock
  --time-str="$CLOCK_FORMAT" --date-str="$DATE_FORMAT"
  --time-font="$family" --date-font="$family" --greeter-font="$family"
  --verif-font="$family" --wrong-font="$family" --layout-font="$family"
  --time-size="$CLOCK_SIZE" --date-size="$DATE_SIZE" --greeter-size=16
  --time-color="${accent}ff" --date-color="${text}ff" --greeter-color="${dimtext}cc"
  --time-pos="w/2:h/2-40" --date-pos="tx:ty+52"
  --indicator --radius=26 --ring-width=5 --ind-pos="w/2:h-150"
  --greeter-text="$greeter" --greeter-pos="ix:iy+62"
  --inside-color=00000000 --insidever-color=00000000 --insidewrong-color=00000000
  --ring-color="${dimtext}55" --ringver-color="${accent}ff" --ringwrong-color="${error}ff"
  --line-color=00000000 --separator-color=00000000
  --keyhl-color="${accent}ff" --bshl-color="${error}ff"
  --verif-text="" --wrong-text="" --noinput-text="" --lock-text="" --lockfailed-text="lock failed"
  --modif-color="${dimtext}cc" --wrong-color="${error}ff"
)

# xss-lock hands us a "sleep lock" fd when locking before suspend. The system
# waits for us to close it, so: start the locker WITHOUT that fd, close ours
# once the screen is locked (suspend continues), then wait for the unlock.
if [[ -e /dev/fd/${XSS_SLEEP_LOCK_FD:--1} ]]; then
  kill_locker() { pkill -xu "$EUID" "$@" i3lock-color; }
  trap kill_locker TERM INT
  "$LOCKER" "${opts[@]}" {XSS_SLEEP_LOCK_FD}<&- 8>&- 2>>"$LOG"
  exec {XSS_SLEEP_LOCK_FD}<&-
  while kill_locker -0; do sleep 0.5; done
else
  trap 'kill %% 2>/dev/null' TERM INT
  start=$SECONDS
  "$LOCKER" --nofork "${opts[@]}" 8>&- 2>>"$LOG" &
  wait $!
  rc=$?
  # only a locker that FAILED TO START (error exit within 3 s, e.g. keyboard
  # still grabbed) is retried, once. Unlocking (0) or being killed (>128)
  # never re-locks.
  if (( rc >= 1 && rc < 128 && SECONDS - start < 3 )); then
    echo "$(date '+%F %T') i3lock-color failed to start (exit $rc), retrying once" >> "$LOG"
    sleep 0.5
    "$LOCKER" --nofork "${opts[@]}" 8>&- 2>>"$LOG" &
    wait $!
  fi
fi
