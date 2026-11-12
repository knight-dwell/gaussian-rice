#!/usr/bin/env bash
# apply-theme.sh: build the palette from theme.conf and re-render every app's
# color/token file, then nudge running apps to reload.
#
#   apply-theme.sh                  use theme.conf as-is
#   apply-theme.sh --wallpaper F    set WALLPAPER=F in theme.conf first
#   apply-theme.sh --no-reload      render files only
#
# Output: ~/.config/theme/generated/palette.json (+ every file in targets.list)

set -euo pipefail

THEME_DIR="$HOME/.config/theme"
CONF="$THEME_DIR/theme.conf"
GEN="$THEME_DIR/generated"
RELOAD=1

while (( $# )); do
  case "$1" in
    --wallpaper)
      wp="$(realpath "$2")"; shift
      # rewrite the WALLPAPER= line in place (keeps comments and everything else)
      python3 - "$CONF" "$wp" <<'EOF'
import re, sys
path, wp = sys.argv[1], sys.argv[2]
text = open(path).read()
text = re.sub(r'^WALLPAPER=.*$', 'WALLPAPER="%s"' % wp.replace('"', '\\"'), text, flags=re.M)
open(path, 'w').write(text)
EOF
      ;;
    --no-reload) RELOAD=0 ;;
    *) echo "unknown option: $1" >&2; exit 2 ;;
  esac
  shift
done

# shellcheck source=/dev/null
source "$CONF"
mkdir -p "$GEN"

# ── 1. Palette ──────────────────────────────────────────────────────────────
roles="$GEN/.roles.json"
source_used="$COLOR_MODE"
if [[ "$COLOR_MODE" == "wallpaper" ]]; then
  if ! matugen image "$WALLPAPER" -m dark -t "$MATUGEN_SCHEME" --prefer "$MATUGEN_PREFER" \
        --dry-run --old-json-output --json hex 2>/dev/null \
      | jq '.colors | map_values(.dark)' > "$roles" || [[ ! -s "$roles" ]]; then
    echo "apply-theme: matugen failed on '$WALLPAPER', falling back to fixed palette" >&2
    source_used="fixed (fallback)"
    cp "$FIXED_PALETTE" "$roles"
  fi
else
  cp "$FIXED_PALETTE" "$roles"
fi

# ── 2. Context = palette roles + ANSI colors + design tokens ───────────────
jq -n \
  --slurpfile roles "$roles" \
  --slurpfile ansi "$THEME_DIR/palettes/ansi.json" \
  --arg color_source "$source_used" \
  --arg wallpaper "$WALLPAPER" \
  --arg font_family "$FONT_FAMILY" --arg font_size "$FONT_SIZE" \
  --arg font_size_term "$FONT_SIZE_TERM" --arg icon_font "$ICON_FONT" \
  --arg radius "$RADIUS" \
  --arg space_xs "$SPACE_XS" --arg space_sm "$SPACE_SM" --arg space_md "$SPACE_MD" \
  --arg space_lg "$SPACE_LG" --arg space_xl "$SPACE_XL" \
  --arg bar_opacity "$BAR_OPACITY" --arg term_opacity "$TERM_OPACITY" \
  --arg border_terminal "$BORDER_TERMINAL" --arg border_window "$BORDER_WINDOW" \
  --arg border_width "$BORDER_WIDTH" \
  --arg gtk_theme "$GTK_THEME" --arg icon_theme "$ICON_THEME" \
  --arg cursor_theme "$CURSOR_THEME" --arg cursor_size "$CURSOR_SIZE" \
  '$roles[0] + ($ansi[0] | del(._comment)) + ($ARGS.named)' > "$GEN/palette.json"
rm -f "$roles"

echo "apply-theme: colors from $source_used, primary=$(jq -r .primary "$GEN/palette.json")"

# ── 3. Render every template listed in targets.list ────────────────────────
python3 "$THEME_DIR/scripts/render.py" "$GEN/palette.json" "$THEME_DIR/templates/targets.list"

# ── 4. Tell running apps (each step is skipped if the app isn't running) ───
(( RELOAD )) || exit 0
# kitty re-reads its config on SIGUSR1
pkill -USR1 -x kitty 2>/dev/null || true
# dunst drop-in colors
pgrep -x dunst >/dev/null && dunstctl reload 2>/dev/null || true
# i3 border colors (generated/i3-colors.conf is included from the i3 config)
pgrep -x i3 >/dev/null && i3-msg -q reload 2>/dev/null || true
# eww watches its config dir and reloads _colors.scss by itself
# GTK/Qt: new windows pick the colors up; running apps need a restart
exit 0
