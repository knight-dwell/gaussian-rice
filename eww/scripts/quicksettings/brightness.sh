#!/usr/bin/env bash
# brightness.sh get | set N   (percent)
case "$1" in
  get) brightnessctl -m | awk -F, '{gsub("%","",$4); print $4}' ;;
  set) brightnessctl -q set "$(printf '%d' "${2%.*}")%" ;;
esac
