#!/usr/bin/env bash
# powerprofile.sh get | cycle   (power-profiles-daemon)
case "$1" in
  get) powerprofilesctl get 2>/dev/null || echo unavailable ;;
  cycle)
    case "$(powerprofilesctl get)" in
      power-saver) next=balanced ;;
      balanced)    next=performance ;;
      *)           next=power-saver ;;
    esac
    # performance may be unavailable on some hardware: fall back to power-saver
    powerprofilesctl set "$next" 2>/dev/null || powerprofilesctl set power-saver
    "$HOME/.local/bin/eww" update pprofile="$(powerprofilesctl get)" ;;
esac
