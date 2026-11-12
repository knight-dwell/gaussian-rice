#!/usr/bin/env bash
# install.sh: put rice-clip in place for this user (no sudo).
#   ~/.local/share/rice-apps/rice-clip.py  (the program)
#   ~/.local/bin/rice-clip                 (the command)
set -euo pipefail
cd "$(dirname "$(realpath "$0")")"
for need in xclip rofi; do command -v "$need" >/dev/null || echo "missing: $need (see README)"; done
python3 -c 'import Xlib' 2>/dev/null || echo "missing: python3-xlib (see README)"
mkdir -p ~/.local/share/rice-apps ~/.local/bin
install -m 755 rice-clip.py ~/.local/share/rice-apps/rice-clip.py
install -m 755 rice-clip    ~/.local/bin/rice-clip
echo "installed. Next: add i3-snippet.conf to ~/.config/i3/config and press Super+Shift+R"
