#!/usr/bin/env bash
# calendar/select.sh DAY MONTH0 YEAR: a day was clicked in the calendar
# (GTK months are 0-based). Shows that day's reminders.
[[ $1 =~ ^[0-9]+$ && $2 =~ ^[0-9]+$ && $3 =~ ^[0-9]+$ ]] || exit 1
d=$(printf '%04d-%02d-%02d' "$3" $(( $2 + 1 )) "$1")
"$HOME/.local/bin/eww" update cal_sel="$d" cal_label="$(date -d "$d" '+%A, %d %B')" rem_msg=""
