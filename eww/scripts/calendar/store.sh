#!/usr/bin/env bash
# calendar/store.sh time|text: save what is typed in a reminder field (stdin)
# to a private runtime file; reminders.py add reads it. Typed text is never
# put on a command line (eww would paste it raw into sh).
[[ $1 == time || $1 == text ]] || exit 1
umask 077
cat > "${XDG_RUNTIME_DIR:-/tmp}/eww-rem-$1"
