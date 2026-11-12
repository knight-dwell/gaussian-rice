#!/usr/bin/env python3
"""Rice Tube: YouTube in its own small window, not a Firefox tab.

  * tiles next to your windows like a new kitty terminal: no tabs, no address
    bar, just YouTube under a slim Material bar. Resize it like any tiled window
    (drag its border, or Super+R + arrows); Super+Shift+Space floats it, and then
    you can drag it by the bar
  * Super+Shift+Enter shows/hides it (the video keeps playing while hidden)
  * stays signed in: cookies and settings live in ~/.local/share/rice-tube
  * only YouTube (and Google sign-in) opens inside; any other link opens in
    your normal browser
  * bar buttons: back · home · reload · open this page in your browser · hide
  * video fullscreen (YouTube's ⛶ button or f) hides the bar
"""
import os
import subprocess
import sys
from urllib.parse import urlparse

sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
import ricetheme  # noqa: E402  (also selects GTK 3)

import gi  # noqa: E402

gi.require_version("WebKit2", "4.1")
from gi.repository import Gdk, GLib, Gtk, WebKit2  # noqa: E402

HOME_URL = "https://www.youtube.com/"
DATA = os.path.join(GLib.get_user_data_dir(), "rice-tube")      # cookies, sign-in, settings
CACHE = os.path.join(GLib.get_user_cache_dir(), "rice-tube")
# hosts that stay inside the window (YouTube itself + Google sign-in); the rest → browser
INSIDE = ("youtube.com", "youtu.be", "youtube-nocookie.com", "accounts.google.com", "accounts.youtube.com",
          "google.com", "gstatic.com", "googleusercontent.com", "ytimg.com", "googlevideo.com")

ICON = {"back": "\U000f004d", "home": "\U000f02dc", "reload": "\U000f0450", "browser": "\U000f03cc",
        "hide": "\U000f05b0", "logo": "\U000f05c3"}

CSS = """
window.rice-tube { background-color: $surface_container; }
.tube-bar {
  background-color: $surface_container;
  color: $on_surface;
  padding: 4px 6px;
  font-family: "$font_family";
}
.tube-bar .logo { color: #ff4e45; font-size: 18px; padding: 0 6px 0 4px; }
.tube-bar .title { color: $on_surface_variant; font-size: 12px; }
.tube-bar button {
  background: transparent; border: none; box-shadow: none; min-width: 0; min-height: 0;
  padding: 3px 8px; border-radius: ${radius_sm}px; color: $on_surface_variant;
  font-family: "$font_family"; font-size: 16px;
  transition: background-color 160ms ease, color 160ms ease;
}
.tube-bar button:hover { background-color: $surface_container_highest; color: $on_surface; }
.tube-bar button:active { background-color: $primary_container; color: $on_primary_container; }
.tube-bar button.hide:hover { background-color: $primary; color: $on_primary; }
"""


def inside(uri):
    host = (urlparse(uri).hostname or "").lower()
    return any(host == h or host.endswith("." + h) for h in INSIDE)


def open_in_browser(uri):
    subprocess.Popen(["xdg-open", uri], start_new_session=True,
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


class Tube(Gtk.Window):
    def __init__(self):
        super().__init__(title="YouTube")
        self.set_wmclass("rice-tube", "RiceTube")
        self.get_style_context().add_class("rice-tube")
        self.set_default_size(960, 540)
        self.connect("destroy", Gtk.main_quit)

        data = WebKit2.WebsiteDataManager(base_data_directory=os.path.join(DATA, "data"),
                                          base_cache_directory=CACHE)
        data.get_cookie_manager().set_persistent_storage(os.path.join(DATA, "cookies.sqlite"),
                                                         WebKit2.CookiePersistentStorage.SQLITE)
        context = WebKit2.WebContext.new_with_website_data_manager(data)
        self.view = WebKit2.WebView(web_context=context)
        s = self.view.get_settings()
        s.set_hardware_acceleration_policy(WebKit2.HardwareAccelerationPolicy.ALWAYS)
        s.set_enable_smooth_scrolling(True)
        s.set_media_playback_requires_user_gesture(False)
        self.view.connect("decide-policy", self.on_policy)
        self.view.connect("notify::title", lambda v, _p: self.on_title())
        self.view.connect("enter-fullscreen", lambda *_: self.bar.hide() or False)
        self.view.connect("leave-fullscreen", lambda *_: self.bar.show() or False)

        # slim bar: drag the window by it (anywhere except the buttons)
        self.bar = Gtk.EventBox()
        self.bar.get_style_context().add_class("tube-bar")
        self.bar.connect("button-press-event", self.on_drag)
        row = Gtk.Box(spacing=2)
        self.bar.add(row)
        logo = Gtk.Label(label=ICON["logo"])
        logo.get_style_context().add_class("logo")
        row.pack_start(logo, False, False, 0)
        self.title = Gtk.Label(label="YouTube", xalign=0, ellipsize=3)   # 3 = END
        self.title.get_style_context().add_class("title")
        row.pack_start(self.title, True, True, 0)
        for key, tip, cb in (("back", "Back (Alt+←)", lambda *_: self.view.go_back()),
                             ("home", "YouTube home", lambda *_: self.view.load_uri(HOME_URL)),
                             ("reload", "Reload (F5)", lambda *_: self.view.reload()),
                             ("browser", "Open this page in your browser",
                              lambda *_: open_in_browser(self.view.get_uri() or HOME_URL)),
                             ("hide", "Hide (Super+Shift+Enter brings it back here)", lambda *_: self.hide_to_scratchpad())):
            b = Gtk.Button(label=ICON[key], tooltip_text=tip, relief=Gtk.ReliefStyle.NONE)
            b.get_style_context().add_class(key)
            b.connect("clicked", cb)
            row.pack_start(b, False, False, 0)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        box.pack_start(self.bar, False, False, 0)
        box.pack_start(self.view, True, True, 0)
        self.add(box)
        self.connect("key-press-event", self.on_key)
        self.view.load_uri(HOME_URL)

    def on_title(self):
        t = (self.view.get_title() or "YouTube").removesuffix(" - YouTube")
        self.title.set_text(t)
        self.set_title(t)

    def on_drag(self, _w, ev):
        if ev.button == 1 and ev.type == Gdk.EventType.BUTTON_PRESS:
            self.begin_move_drag(ev.button, int(ev.x_root), int(ev.y_root), ev.time)
        return False

    def on_key(self, _w, ev):
        alt = ev.state & Gdk.ModifierType.MOD1_MASK
        if alt and ev.keyval == Gdk.KEY_Left:
            self.view.go_back()
        elif ev.keyval == Gdk.KEY_F5:
            self.view.reload()
        else:
            return False
        return True

    def hide_to_scratchpad(self):
        subprocess.run(["i3-msg", "-q", '[class="^RiceTube$"] move scratchpad'])

    def on_policy(self, _view, decision, kind):
        """Keep YouTube inside; send every other link to the normal browser."""
        if kind in (WebKit2.PolicyDecisionType.NAVIGATION_ACTION, WebKit2.PolicyDecisionType.NEW_WINDOW_ACTION):
            action = decision.get_navigation_action()
            uri = action.get_request().get_uri()
            if not uri.startswith(("http://", "https://")):
                return False
            user_click = action.get_navigation_type() == WebKit2.NavigationType.LINK_CLICKED
            if kind == WebKit2.PolicyDecisionType.NEW_WINDOW_ACTION or (user_click and not inside(uri)):
                decision.ignore()
                if inside(uri):
                    self.view.load_uri(uri)       # target=_blank YouTube link: same window
                else:
                    open_in_browser(uri)
                return True
        return False


def main():
    GLib.set_prgname("rice-tube")
    os.makedirs(DATA, mode=0o700, exist_ok=True)
    win = Tube()
    ricetheme.Theme(CSS)
    win.show_all()
    Gtk.main()


if __name__ == "__main__":
    main()
