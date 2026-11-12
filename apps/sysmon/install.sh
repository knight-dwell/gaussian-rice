#!/usr/bin/env bash
# install.sh: put the system monitor in place for this user (no sudo).
#   ~/.config/rice-sysmon/ (eww config + scripts)   ~/.local/bin/rice-sysmon
set -euo pipefail
cd "$(dirname "$(realpath "$0")")"
command -v eww >/dev/null || echo "missing: eww (see README step 1)"
D=~/.config/rice-sysmon
mkdir -p "$D" ~/.local/bin
install -m 644 eww.yuck eww.scss _colors.scss "$D/"
install -m 755 sysmon.py toggle.sh "$D/"
install -m 755 rice-sysmon ~/.local/bin/rice-sysmon
echo "installed. Next: add i3-snippet.conf to ~/.config/i3/config, press Super+Shift+R, then Super+M"
