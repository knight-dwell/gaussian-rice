#!/usr/bin/env bash
# sysmon/toggle.sh [open|close|toggle]: show/hide the system monitor window.
# sysmon_open drives the data poll, so it must follow the window state.
EWW="$HOME/.local/bin/eww"
eww() { "$EWW" --no-daemonize "$@"; }   # never start a second daemon (see popup.sh)
is_open() { eww active-windows 2>/dev/null | grep -q '^sysmon:'; }
want=${1:-toggle}
[[ $want == toggle ]] && { is_open && want=close || want=open; }
if [[ $want == open ]]; then
  "$HOME/.config/eww/scripts/sysmon/sysmon.py" >/dev/null   # prime the CPU-% baseline
  eww update sysmon_open=true
  eww open sysmon --screen "$(cat "${XDG_RUNTIME_DIR:-/tmp}/eww-primary" 2>/dev/null || echo 0)"
else
  eww close sysmon 2>/dev/null
  eww update sysmon_open=false
fi
