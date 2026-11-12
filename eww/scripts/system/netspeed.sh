#!/usr/bin/env bash
# netspeed.sh DEV: KiB/s down/up since the previous call, from the kernel's
# byte counters. Used by a defpoll that only runs while the bar details are
# expanded (eww's EWW_NET stays at 0 on this build).
dev=${1:-$(ip route show default 2>/dev/null | awk '{print $5; exit}')}
f="/sys/class/net/$dev/statistics"
[[ -r $f/rx_bytes ]] || { echo '{"down":0,"up":0}'; exit 0; }
state="${XDG_RUNTIME_DIR:-/tmp}/eww-netspeed-$dev"
now=$(date +%s%N); rx=$(<"$f/rx_bytes"); tx=$(<"$f/tx_bytes")
if read -r t0 rx0 tx0 < "$state" 2>/dev/null && (( now > t0 )); then
  dt=$(( now - t0 ))
  printf '{"down":%d,"up":%d}\n' $(( (rx - rx0) * 1000000000 / dt / 1024 )) $(( (tx - tx0) * 1000000000 / dt / 1024 ))
else
  echo '{"down":0,"up":0}'
fi
echo "$now $rx $tx" > "$state"
