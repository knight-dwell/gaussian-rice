"""ricetheme: shared look for the rice's GTK apps (Terminal Studio, Rice Dock).

Reads the central palette (~/.config/theme/generated/palette.json, written by
apply-theme.sh) and turns a CSS template with $token placeholders into GTK
CSS. Watches the palette file, so the apps recolor live when the theme changes.
"""
import json
import os
from string import Template

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gdk, Gio, Gtk  # noqa: E402

PALETTE = os.path.expanduser("~/.config/theme/generated/palette.json")

# used if the palette can't be read (Material dark, blue seed)
FALLBACK = {
    "primary": "#adc6ff", "on_primary": "#102f60", "primary_container": "#2b4678",
    "on_primary_container": "#d8e2ff", "surface": "#111318", "surface_container": "#1e1f25",
    "surface_container_high": "#282a2f", "surface_container_highest": "#33353a",
    "on_surface": "#e2e2e9", "on_surface_variant": "#c4c6d0", "outline": "#8e9099",
    "outline_variant": "#44474f", "error": "#ffb4ab", "tertiary": "#debcdf",
    "border_terminal": "#e53935", "border_window": "#1e88e5",
    "font_family": "JetBrainsMono Nerd Font", "radius": 12,
}


def palette():
    p = dict(FALLBACK)
    try:
        with open(PALETTE) as fh:
            data = json.load(fh)
        p.update({k: v for k, v in data.items() if isinstance(v, (str, int, float))})
    except (OSError, ValueError):
        pass
    return p


class Theme:
    """Apply `css_template` ($primary, $surface, ... from the palette) to the screen and
    re-apply it whenever the palette changes."""

    def __init__(self, css_template):
        self.template = css_template
        self.provider = Gtk.CssProvider()
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(), self.provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        self.apply()
        self.monitor = Gio.File.new_for_path(PALETTE).monitor_file(Gio.FileMonitorFlags.NONE, None)
        self.monitor.connect("changed", lambda *a: self.apply())

    def apply(self):
        p = palette()
        p["radius_sm"] = max(int(p.get("radius", 12)) - 4, 2)
        try:
            self.provider.load_from_data(Template(self.template).safe_substitute(p).encode())
        except Exception as e:   # a bad template must not kill the app
            print("ricetheme:", e)
