# Apps you can install on your own machine

Each folder has everything it needs: the program, a README, an `install.sh` (no sudo; copies into `~/.local`/`~/.config`)
and an `i3-snippet.conf` with the i3 lines to add.

| Folder | What it is | Key |
|---|---|---|
| [`clipboard/`](clipboard) | clipboard history with a rofi picker; skips password managers | Super+V |
| [`dock/`](dock) | floating, collapsible app launcher with ＋ to add apps or aliases | Super+O |
| [`sysmon/`](sysmon) | full system monitor window (CPU, threads, RAM, GPU, disks, temps, processes) | Super+M |

Fetch only one folder without cloning everything:

```sh
git clone --filter=blob:none --sparse https://github.com/knight-dwell/config-dump
cd config-dump && git sparse-checkout set apps/dock      # or apps/sysmon, apps/clipboard, apps
cd apps/dock && ./install.sh
```

Before adding the i3 lines, check that the keys aren't already used in your config.
