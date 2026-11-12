#!/usr/bin/env bash
# install.sh: put Rice Dock in place for this user (no sudo).
#   ~/.local/share/rice-apps/{rice-dock.py,ricetheme.py}   ~/.local/bin/rice-dock
set -euo pipefail
cd "$(dirname "$(realpath "$0")")"
python3 -c 'import gi; gi.require_version("Gtk", "3.0"); from gi.repository import Gtk' 2>/dev/null \
  || echo "missing: python3-gobject / GTK 3 (see README)"
command -v kitty >/dev/null || echo "note: kitty not found (needed only for apps that run in a terminal)"
mkdir -p ~/.local/share/rice-apps ~/.local/bin
install -m 755 rice-dock.py ~/.local/share/rice-apps/rice-dock.py
install -m 644 ricetheme.py ~/.local/share/rice-apps/ricetheme.py
install -m 755 rice-dock    ~/.local/bin/rice-dock
echo "installed. Next: add i3-snippet.conf to ~/.config/i3/config and press Super+Shift+R (or run: rice-dock &)"
