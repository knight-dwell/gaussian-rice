#!/usr/bin/env python3
"""Terminal Studio: point-and-click settings for kitty, the prompt and the
startup art. Changes apply live to every open kitty window.

Writes only these files (your own kitty.conf / .zshrc are never rewritten):
  ~/.config/kitty/studio.conf             kitty settings (included last by kitty.conf)
  ~/.config/terminal-studio/settings.json what the app shows when reopened
  ~/.config/terminal-studio/zsh-theme     prompt style (read by .zshrc)
  ~/.config/terminal-studio/no-fetch      exists = no startup art (read by .zshrc)
  ~/.config/fastfetch/config.jsonc        only the logo ("source") and the Welcome name
  ~/.config/terminal-greeter/greeter.json system info / quote on-off (read by bat-greeter)

"Reset" empties studio.conf, so kitty falls back to kitty.conf + the desktop theme.
"""
import glob
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
import ricetheme  # noqa: E402  (also selects GTK 3)

from gi.repository import GLib, Gtk, Pango  # noqa: E402

HOME = os.path.expanduser("~")
KITTY_DIR = os.path.join(HOME, ".config/kitty")
STUDIO_CONF = os.path.join(KITTY_DIR, "studio.conf")
APP_DIR = os.path.join(HOME, ".config/terminal-studio")
SETTINGS = os.path.join(APP_DIR, "settings.json")
ZSH_THEME_FILE = os.path.join(APP_DIR, "zsh-theme")
NO_FETCH = os.path.join(APP_DIR, "no-fetch")
FASTFETCH = os.path.join(HOME, ".config/fastfetch/config.jsonc")
SCHEMES = sorted(os.path.basename(p)[:-5] for p in glob.glob(os.path.join(KITTY_DIR, "kitty-themes/themes/*.conf")))
CUSTOM_PROMPTS = sorted(os.path.basename(p)[:-10] for p in glob.glob(os.path.join(HOME, ".oh-my-zsh/custom/themes/*.zsh-theme"))
                        if not p.endswith("example.zsh-theme"))
PROMPTS = CUSTOM_PROMPTS + sorted(os.path.basename(p)[:-10] for p in glob.glob(os.path.join(HOME, ".oh-my-zsh/themes/*.zsh-theme")))
GREETER_DIR = os.path.join(HOME, ".config/terminal-greeter")
GREETER = os.path.join(GREETER_DIR, "greeter.json")
BAT_LOGO = "~/.config/terminal-greeter/art/batsignal.txt"
LOGOS = [BAT_LOGO, "Fedora_small", "Fedora", "Fedora2_small", "Fedora_old", "none"]
LOGO_NAMES = ["Bat signal", "Fedora (small)", "Fedora", "Fedora 2 (small)", "Fedora (old)", "No logo"]

DEFAULTS = {
    "font_family": "JetBrainsMono Nerd Font", "font_size": 13.5, "cell_height": 100,
    "opacity": 0.90, "padding": 14, "cursor_shape": "block", "cursor_blink": True,
    "scheme": "", "bg": "", "fg": "", "fetch": True, "logo": BAT_LOGO, "prompt": "ket",
    "name": "gaussian_knight", "sysinfo": True, "quotes": True,
}

CSS = """
window, .studio { background-color: $surface_container; color: $on_surface; font-family: "$font_family"; }
headerbar { background: $surface_container_high; border: none; box-shadow: none; padding: 4px 8px; }
headerbar .title { font-weight: bold; }
stacksidebar, stacksidebar list { background-color: $surface_container_high; border: none; }
stacksidebar row { padding: 10px 16px; border-radius: ${radius_sm}px; margin: 2px 6px; }
stacksidebar row:selected { background-color: $primary_container; color: $on_primary_container; }
.page { padding: 18px 22px; }
.page-title { font-size: 1.4em; font-weight: bold; color: $primary; margin-bottom: 6px; }
.hint { color: $on_surface_variant; font-size: 0.9em; }
.setting { background-color: $surface_container_high; border-radius: ${radius}px; padding: 10px 14px; }
.setting-label { font-weight: bold; }
button.suggested-action { background: $primary; color: $on_primary; border-radius: 999px; padding: 4px 14px; border: none; }
button.pill { border-radius: 999px; padding: 4px 14px; }
.preview { background-color: $surface; border-radius: ${radius}px; padding: 14px; font-family: monospace; }
"""


def load_settings():
    s = dict(DEFAULTS)
    try:
        with open(SETTINGS) as fh:
            s.update(json.load(fh))
    except (OSError, ValueError):
        pass
    return s


class Studio(Gtk.Window):
    def __init__(self):
        super().__init__(title="Terminal Studio")
        self.set_wmclass("terminal-studio", "TerminalStudio")
        self.set_default_size(820, 560)
        self.s = load_settings()
        self.pending = None
        self.loading = True

        hb = Gtk.HeaderBar(title="Terminal Studio", subtitle="changes apply live to every kitty window")
        hb.set_show_close_button(True)
        self.set_titlebar(hb)
        reset = Gtk.Button(label="Reset")
        reset.set_tooltip_text("Back to kitty.conf + desktop theme")
        reset.get_style_context().add_class("pill")
        reset.connect("clicked", self.on_reset)
        hb.pack_start(reset)
        test = Gtk.Button(label="Open test terminal")
        test.get_style_context().add_class("suggested-action")
        test.connect("clicked", lambda *_: subprocess.Popen(["kitty"], start_new_session=True))
        hb.pack_end(test)

        stack = Gtk.Stack(transition_type=Gtk.StackTransitionType.SLIDE_UP_DOWN, transition_duration=180)
        side = Gtk.StackSidebar(stack=stack)
        side.set_size_request(170, -1)
        box = Gtk.Box()
        box.get_style_context().add_class("studio")
        box.pack_start(side, False, False, 0)
        box.pack_start(stack, True, True, 0)
        self.add(box)

        stack.add_titled(self.page_font(), "font", "  Font")
        stack.add_titled(self.page_window(), "window", "  Window")
        stack.add_titled(self.page_colors(), "colors", "  Colors")
        stack.add_titled(self.page_art(), "art", "  Startup art")
        stack.add_titled(self.page_prompt(), "prompt", "  Prompt")
        self.loading = False

    # ── layout helpers ──────────────────────────────────────────────────────
    def page(self, title, hint):
        v = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        v.get_style_context().add_class("page")
        t = Gtk.Label(label=title, xalign=0)
        t.get_style_context().add_class("page-title")
        h = Gtk.Label(label=hint, xalign=0, wrap=True)
        h.get_style_context().add_class("hint")
        v.pack_start(t, False, False, 0)
        v.pack_start(h, False, False, 0)
        sw = Gtk.ScrolledWindow(hscrollbar_policy=Gtk.PolicyType.NEVER)
        sw.add(v)
        sw.inner = v
        return sw

    def row(self, page, label, widget, hint=None):
        r = Gtk.Box(spacing=12)
        r.get_style_context().add_class("setting")
        lv = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        lab = Gtk.Label(label=label, xalign=0)
        lab.get_style_context().add_class("setting-label")
        lv.pack_start(lab, False, False, 0)
        if hint:
            h = Gtk.Label(label=hint, xalign=0, wrap=True, max_width_chars=40)
            h.get_style_context().add_class("hint")
            lv.pack_start(h, False, False, 0)
        r.pack_start(lv, True, True, 0)
        widget.set_valign(Gtk.Align.CENTER)
        r.pack_end(widget, False, False, 0)
        page.inner.pack_start(r, False, False, 0)
        return r

    def slider(self, key, lo, hi, step, digits, width=260):
        sc = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, lo, hi, step)
        sc.set_digits(digits)
        sc.set_value(self.s[key])
        sc.set_size_request(width, -1)
        sc.set_value_pos(Gtk.PositionType.RIGHT)
        sc.connect("value-changed", lambda w: self.set(key, round(w.get_value(), digits) if digits else int(w.get_value())))
        return sc

    def combo(self, key, items, labels=None):
        c = Gtk.ComboBoxText()
        for i, it in enumerate(items):
            c.append(it, (labels or items)[i])
        c.set_active_id(self.s[key] if self.s[key] in items else items[0])
        c.connect("changed", lambda w: self.set(key, w.get_active_id()))
        return c

    def switch(self, key):
        sw = Gtk.Switch(active=bool(self.s[key]))
        sw.connect("notify::active", lambda w, _: self.set(key, w.get_active()))
        return sw

    # ── pages ───────────────────────────────────────────────────────────────
    def page_font(self):
        p = self.page("Font", "Pick a monospace font. Nerd Fonts show the icons used by the prompt, eza and fastfetch.")
        fb = Gtk.FontButton()
        fb.set_filter_func(lambda fam, face: fam.is_monospace())
        fb.set_level(Gtk.FontChooserLevel.FAMILY)
        fb.set_font(self.s["font_family"])
        fb.connect("font-set", lambda w: self.set("font_family", w.get_font_family().get_name()))
        self.row(p, "Font family", fb)
        self.row(p, "Size", self.slider("font_size", 8, 24, 0.5, 1))
        self.row(p, "Line height", self.slider("cell_height", 80, 160, 5, 0), "percent of the normal height")
        return p

    def page_window(self):
        p = self.page("Window", "How the terminal window itself looks.")
        self.row(p, "Opacity", self.slider("opacity", 0.5, 1.0, 0.01, 2), "1.00 = solid, lower = see the wallpaper")
        self.row(p, "Padding", self.slider("padding", 0, 40, 1, 0), "space between the border and the text (px)")
        self.row(p, "Cursor shape", self.combo("cursor_shape", ["block", "beam", "underline"], ["Block █", "Beam ▏", "Underline ▁"]))
        self.row(p, "Blinking cursor", self.switch("cursor_blink"))
        return p

    def page_colors(self):
        p = self.page("Colors", "\"Desktop theme\" follows the rice palette (currently blue) and changes with it. "
                                "Or pick one of your kitty-themes.")
        self.row(p, "Color scheme", self.combo("scheme", [""] + SCHEMES, ["Desktop theme (follows rice)"] + [x.replace("_", " ") for x in SCHEMES]))
        for key, label in (("bg", "Background override"), ("fg", "Text color override")):
            box = Gtk.Box(spacing=6)
            cb = Gtk.ColorButton()
            if self.s[key]:
                from gi.repository import Gdk
                rgba = Gdk.RGBA()
                rgba.parse(self.s[key])
                cb.set_rgba(rgba)
            cb.connect("color-set", lambda w, k=key: self.set(k, "#%02x%02x%02x" % tuple(int(c * 255) for c in (w.get_rgba().red, w.get_rgba().green, w.get_rgba().blue))))
            clear = Gtk.Button(label="Clear")
            clear.get_style_context().add_class("pill")
            clear.connect("clicked", lambda w, k=key: self.set(k, ""))
            box.pack_start(cb, False, False, 0)
            box.pack_start(clear, False, False, 0)
            self.row(p, label, box, "optional; Clear = use the scheme's color")
        return p

    def page_art(self):
        p = self.page("Startup art", "What a new terminal greets you with: the bat signal with system info, "
                                     "then a random quote, joke or short story about a scientist or philosopher.")
        self.row(p, "Show at startup", self.switch("fetch"), "off = plain prompt, nothing printed")
        name = Gtk.Entry(text=self.s["name"], width_chars=20)
        name.connect("changed", lambda w: self.set("name", w.get_text().strip()))
        self.row(p, "Welcome name", name, "shown as \"🦇 Welcome, <name>\"")
        self.row(p, "Logo", self.combo("logo", LOGOS, LOGO_NAMES))
        self.row(p, "System info", self.switch("sysinfo"), "logo + OS, CPU, RAM, disk, battery")
        self.row(p, "Quote / story", self.switch("quotes"), "one random entry per terminal, never repeating recent ones")
        lib = Gtk.Button(label="Open library folder")
        lib.get_style_context().add_class("pill")
        lib.connect("clicked", lambda *_: subprocess.Popen(["xdg-open", os.path.join(GREETER_DIR, "library")], start_new_session=True))
        self.row(p, "Your own quotes & stories", lib, "add .txt files or entries there (format in README.txt)")
        prev = Gtk.Button(label="Show a sample")
        prev.get_style_context().add_class("pill")
        self.fetch_view = Gtk.Label(xalign=0, selectable=True, wrap=True)
        self.fetch_view.get_style_context().add_class("preview")
        prev.connect("clicked", self.preview_fetch)
        self.row(p, "Preview", prev, "plain text (in the terminal it's in color and italics)")
        p.inner.pack_start(self.fetch_view, False, False, 0)
        return p

    def page_prompt(self):
        p = self.page("Prompt", "oh-my-zsh prompt style. Applies to NEW terminals (or run `exec zsh`).")
        items = [""] + PROMPTS
        labels = ["Keep .zshrc (sunrise)"] + [("ket   Ĥ|ψ⟩  (operator on a ket)" if x == "ket" else x) for x in PROMPTS]
        self.row(p, "Prompt theme", self.combo("prompt", items, labels),
                 "good ones from your .zshrc notes: norm, af-magic, bureau, clean, crunch")
        return p

    # ── apply ───────────────────────────────────────────────────────────────
    def set(self, key, value):
        if self.loading:
            return
        self.s[key] = value
        if self.pending:
            GLib.source_remove(self.pending)
        self.pending = GLib.timeout_add(250, self.apply)   # debounce slider drags

    def apply(self):
        self.pending = None
        s = self.s
        os.makedirs(APP_DIR, exist_ok=True)
        with open(SETTINGS, "w") as fh:
            json.dump(s, fh, indent=1)
        lines = ["# GENERATED by Terminal Studio. Change these in the app (terminal-studio).",
                 "font_family %s" % s["font_family"],
                 "font_size %s" % s["font_size"],
                 "modify_font cell_height %d%%" % s["cell_height"],
                 "background_opacity %.2f" % s["opacity"],
                 "window_padding_width %d" % s["padding"],
                 "cursor_shape %s" % s["cursor_shape"],
                 "cursor_blink_interval %s" % ("-1" if s["cursor_blink"] else "0")]
        if s["scheme"] in SCHEMES:
            lines.append("include kitty-themes/themes/%s.conf" % s["scheme"])
        for key, opt in (("bg", "background"), ("fg", "foreground")):
            if re.fullmatch(r"#[0-9a-fA-F]{6}", s[key] or ""):
                lines.append("%s %s" % (opt, s[key]))
        with open(STUDIO_CONF, "w") as fh:
            fh.write("\n".join(lines) + "\n")
        # startup art + prompt (read by .zshrc)
        if s["fetch"]:
            if os.path.exists(NO_FETCH):
                os.remove(NO_FETCH)
        else:
            open(NO_FETCH, "w").close()
        if s["prompt"] in PROMPTS:
            with open(ZSH_THEME_FILE, "w") as fh:
                fh.write(s["prompt"] + "\n")
        elif os.path.exists(ZSH_THEME_FILE):
            os.remove(ZSH_THEME_FILE)
        self.set_logo(s["logo"])
        self.set_welcome(s["name"] or "friend")
        os.makedirs(GREETER_DIR, exist_ok=True)
        with open(GREETER, "w") as fh:
            json.dump({"fetch": s["sysinfo"], "quotes": s["quotes"]}, fh)
        subprocess.run(["pkill", "-USR1", "-x", "kitty"])   # kitty reloads its config
        return False

    def set_welcome(self, name):
        name = re.sub(r'[^\w .\-]', "", name)[:30]      # keep the JSON valid
        try:
            txt = open(FASTFETCH).read()
            new = re.sub(r'(Welcome, \\u001b\[1;34m)[^"]*"', lambda m: m.group(1) + name + '"', txt, count=1)
            if new != txt:
                with open(FASTFETCH, "w") as fh:
                    fh.write(new)
        except OSError:
            pass

    def set_logo(self, logo):
        try:
            txt = open(FASTFETCH).read()
            new = re.sub(r'"source": "[^"]*"', '"source": "%s"' % logo, txt, count=1)
            if new != txt:
                with open(FASTFETCH, "w") as fh:
                    fh.write(new)
        except OSError:
            pass

    def preview_fetch(self, *_):
        self.apply()
        ff = subprocess.run(["fastfetch", "--pipe", "true"], capture_output=True, text=True).stdout if self.s["sysinfo"] else ""
        q = subprocess.run(["bat-greeter", "--quote"], capture_output=True, text=True).stdout if self.s["quotes"] else ""
        q = re.sub(r"\x1b\[[0-9;]*m", "", q)
        self.fetch_view.set_text((ff.strip("\n") + "\n\n" + q).strip("\n"))

    def on_reset(self, *_):
        open(STUDIO_CONF, "w").close()
        for f in (SETTINGS, ZSH_THEME_FILE, NO_FETCH, GREETER):
            if os.path.exists(f):
                os.remove(f)
        self.set_logo(DEFAULTS["logo"])
        self.set_welcome(DEFAULTS["name"])
        with open(ZSH_THEME_FILE, "w") as fh:     # default prompt: the ket
            fh.write(DEFAULTS["prompt"] + "\n")
        subprocess.run(["pkill", "-USR1", "-x", "kitty"])
        os.execv(sys.executable, [sys.executable] + sys.argv)   # reopen showing the defaults


def main():
    GLib.set_prgname("terminal-studio")
    ricetheme.Theme(CSS)
    win = Studio()
    win.connect("destroy", Gtk.main_quit)
    win.show_all()
    Gtk.main()


if __name__ == "__main__":
    main()
