#!/usr/bin/env bash
# pwstore.sh: store the Wi-Fi password typed in the eww popup, read from stdin,
# in a private file (tmpfs, mode 600). network.py connect reads and deletes it.
umask 077
cat > "${XDG_RUNTIME_DIR:-/tmp}/eww-wifi-pw"
