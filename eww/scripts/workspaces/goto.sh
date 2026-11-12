#!/usr/bin/env bash
# goto.sh N: switch to workspace $wsN as defined in the i3 config
# (names are glyphs, so "workspace number N" doesn't work)
name=$(i3-msg -t get_config | sed -nE "s/^\s*set\s+\\\$ws$1\s+\"(.*)\"\s*$/\1/p" | head -1)
[[ -n "$name" ]] && i3-msg -q "workspace \"$name\""
