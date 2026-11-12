#!/usr/bin/env bash
# launch.sh: (re)start the eww bar. Run by i3 with exec_always.
# Guarantees exactly one daemon, one bar and one copy of every listener,
# no matter how often i3 is restarted.
export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
EWW="$HOME/.local/bin/eww"

"$EWW" close-all >/dev/null 2>&1
"$EWW" kill >/dev/null 2>&1
# any stray daemon (e.g. one auto-started by a client) must go too
pkill -x eww 2>/dev/null; sleep 0.2
# listeners left behind by a crashed daemon. Patterns are anchored to the
# exact "interpreter script" command line so nothing else can match.
D="$HOME/.config/eww/scripts"
pkill -f "^(bash|python3) $D/[a-z]+/[a-z]+-(listen|watch)\.(sh|py)$" 2>/dev/null
pkill -f "^python3 $D/(network|bluetooth|notifications|calendar)/[a-z]+\.py listen$" 2>/dev/null
i3-msg -q mode default 2>/dev/null

"$HOME/.config/eww/scripts/gen-icons.py" >/dev/null
"$EWW" daemon
for _ in $(seq 50); do "$EWW" ping >/dev/null 2>&1 && break; sleep 0.1; done

# bar on the primary monitor only (see ~/.config/eww/README for other monitors)
primary=$(xrandr --query | awk '/ connected primary/{print $1; exit}')
echo "$primary" > "${XDG_RUNTIME_DIR:-/tmp}/eww-primary"   # popups open here too
"$EWW" --no-daemonize open bar --screen "${primary:-0}"
