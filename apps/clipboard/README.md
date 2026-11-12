# Clipboard history (rice-clip)

A small clipboard manager for X11 (i3 or any other window manager). It remembers the last 50 things you copied.
Press **Super+V** to pick one, then **Ctrl+V** to paste it.

- Text only. Copies bigger than 64 KB are skipped.
- Copies from password managers (KeePassXC, Bitwarden, 1Password, …) are **never** stored.
- History is kept in `~/.cache/rice-clip/history.json`, readable only by you. `rice-clip clear` forgets everything,
  and so does the last entry in the picker.

## Files

| File | What it is |
|---|---|
| `rice-clip.py` | the program, with its **settings at the top**: `MAX_ITEMS`, `MAX_BYTES`, `BLOCKED_CLASSES` |
| `rice-clip` | the command: `rice-clip daemon` / `pick` / `clear` |
| `i3-snippet.conf` | the two i3 lines: start the daemon, and Super+V |
| `install.sh` | copies the two files into place (no sudo) |

## Install

```sh
# needs: python3-xlib, xclip, rofi
#   Fedora:  sudo dnf install python3-xlib xclip rofi
#   Ubuntu:  sudo apt install python3-xlib xclip rofi
#   Arch:    sudo pacman -S python-xlib xclip rofi
./install.sh
```

Then add the lines from `i3-snippet.conf` to `~/.config/i3/config`, check that Super+V isn't already used there,
and reload i3 with Super+Shift+R. If you use another window manager, run `rice-clip daemon &` at login and bind a key to `rice-clip pick`.
