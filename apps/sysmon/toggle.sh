#!/usr/bin/env bash
# toggle.sh [open|close|toggle]: show/hide the system monitor window.
# It is its own eww instance (config ~/.config/rice-sysmon), separate from any bar.
# sysmon_open drives the data poll, so it must follow the window state.
CFG="$HOME/.config/rice-sysmon"
eww() { command eww -c "$CFG" "$@"; }
is_open() { eww active-windows 2>/dev/null | grep -q '^sysmon:'; }
want=${1:-toggle}
[[ $want == toggle ]] && { is_open && want=close || want=open; }
if [[ $want == open ]]; then
  "$CFG/sysmon.py" >/dev/null       # prime the CPU-% baseline
  eww ping >/dev/null 2>&1 || { eww daemon; sleep 0.5; }
  eww update sysmon_open=true
  eww open sysmon
else
  eww close sysmon 2>/dev/null
  eww update sysmon_open=false
fi
