#!/usr/bin/env python3
"""Rice Dock: a small floating app launcher.

  * drag it anywhere by the grip (⠿) at the top; it remembers where it was
  * the chevron collapses it into a slim tab on the nearest screen side;
    click the tab to bring it back
  * click an app to start it; right-click for Edit / Move / Remove
  * "+" adds an app: pick an installed one, or type any command or zsh alias
    (e.g. `vim`, `minecraft`) and choose whether it runs in a terminal
  * the chart icon opens the system monitor (full CPU / RAM / disk details)

Apps:  ~/.config/rice-dock/apps.json  (editable by hand too)
State: ~/.config/rice-dock/state.json (position, collapsed)
Running `rice-dock` again while it runs toggles collapsed/expanded.
"""
import json
import os
import shlex
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
import ricetheme  # noqa: E402  (also selects GTK 3)

from gi.repository import Gdk, GdkPixbuf, Gio, GLib, Gtk  # noqa: E402

CONF_DIR = os.path.expanduser("~/.config/rice-dock")
APPS = os.path.join(CONF_DIR, "apps.json")
STATE = os.path.join(CONF_DIR, "state.json")
ICON = 30            # app icon size (px)
TAB_W = 14           # width of the collapsed tab (px)

DEFAULT_APPS = [
    {"name": "Terminal", "icon": "~/.config/terminal-greeter/art/batsignal.png", "command": "kitty", "terminal": False},
    {"name": "Terminal Studio (customize the terminal)", "icon": "preferences-desktop-theme", "command": "terminal-studio", "terminal": False},
    {"name": "Neovim (vim)", "icon": "lvim", "command": "vim", "terminal": True},
    {"name": "Files", "icon": "org.xfce.thunar", "command": "thunar", "terminal": False},
    {"name": "Firefox", "icon": "firefox", "command": "firefox", "terminal": False},
    {"name": "Brave", "icon": "brave-browser", "command": "brave-browser", "terminal": False},
    {"name": "VS Code", "icon": "com.visualstudio.code", "command": "code", "terminal": False},
    {"name": "Spotify", "icon": "spotify", "command": "spotify", "terminal": False},
    {"name": "Telegram", "icon": "telegram", "command": "telegram-desktop", "terminal": False},
    {"name": "Discord", "icon": "com.discordapp.Discord", "command": "flatpak run com.discordapp.Discord", "terminal": False},
    {"name": "Minecraft", "icon": "minecraft", "command": "minecraft", "terminal": False},
]

CSS = """
.dock {
  background-color: alpha($surface_container, 0.92);
  border-radius: ${radius}px;
  border: 1px solid $outline_variant;
  padding: 6px;
}
.grip { color: $outline; padding: 2px 0; border-radius: ${radius_sm}px; }
.grip:hover { color: $primary; background-color: $surface_container_high; }
.dock button {
  background: transparent; border: none; box-shadow: none;
  border-radius: ${radius_sm}px; padding: 6px; min-width: 0; min-height: 0;
  transition: background-color 160ms ease, padding 160ms ease;
}
.dock button:hover { background-color: $surface_container_highest; padding: 4px 6px 8px 6px; }
.dock button:active { background-color: $primary_container; }
.dock .add { color: $primary; font-size: 18px; font-weight: bold; }
.dock .add:hover { background-color: $primary_container; color: $on_primary_container; }
.dock .glyph { font-family: "$font_family"; font-size: 18px; color: $on_surface_variant; }
.dock separator { background-color: $outline_variant; margin: 4px 6px; min-height: 1px; }
.tab {
  min-width: 0; min-height: 0; padding: 0;
  background-color: $primary;
  color: $on_primary;
  border-radius: ${radius_sm}px;
  font-weight: bold;
}
.tab:hover { background-color: $primary_container; color: $on_primary_container; }
window.rice-dialog { background-color: $surface_container; color: $on_surface; font-family: "$font_family"; }
.rice-dialog .hint { color: $on_surface_variant; font-size: 0.9em; }
.rice-dialog .title { font-size: 1.3em; font-weight: bold; color: $primary; }
.rice-dialog button.suggested-action { background: $primary; color: $on_primary; border: none; border-radius: 999px; padding: 4px 16px; }
"""


def load_json(path, default):
    try:
        with open(path) as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return default


def save_json(path, data):
    os.makedirs(CONF_DIR, exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w") as fh:
        json.dump(data, fh, indent=1)
    os.replace(tmp, path)


def icon_widget(name, size=ICON):
    """Gtk.Image from an icon-theme name or an image file; generic fallback."""
    if name and os.path.isfile(os.path.expanduser(name)):
        try:
            pb = GdkPixbuf.Pixbuf.new_from_file_at_scale(os.path.expanduser(name), size, size, True)
            return Gtk.Image.new_from_pixbuf(pb)
        except GLib.Error:
            pass
    theme = Gtk.IconTheme.get_default()
    for n in (name, "application-x-executable"):
        if n and theme.has_icon(n):
            img = Gtk.Image.new_from_icon_name(n, Gtk.IconSize.DND)
            img.set_pixel_size(size)
            return img
    return Gtk.Image.new_from_icon_name("application-x-executable", Gtk.IconSize.DND)


def launch(app):
    """Run through an interactive zsh so aliases (vim, minecraft, ...) work.
    RICE_NO_FETCH=1 skips the startup art in those shells."""
    env = dict(os.environ, RICE_NO_FETCH="1")
    cmd = app["command"]
    argv = (["kitty", "--title", app["name"], "zsh", "-ic", cmd] if app.get("terminal")
            else ["zsh", "-ic", cmd])
    subprocess.Popen(argv, env=env, cwd=os.path.expanduser("~"), start_new_session=True,
                     stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def zsh_aliases():
    try:
        out = subprocess.run(["zsh", "-ic", "alias"], capture_output=True, text=True, timeout=5,
                             env=dict(os.environ, RICE_NO_FETCH="1"), cwd=os.path.expanduser("~")).stdout
    except (OSError, subprocess.TimeoutExpired):
        return []
    names = []
    for line in out.splitlines():
        if "=" in line and not line.startswith(("\x1b", " ")):
            names.append(line.split("=", 1)[0].strip("'"))
    return sorted(set(names))


class AppDialog(Gtk.Window):
    """Add or edit one dock entry."""

    def __init__(self, dock, app=None, index=None):
        super().__init__(title="Add to dock" if app is None else "Edit dock item")
        self.set_wmclass("rice-dock-dialog", "RiceDockDialog")
        self.get_style_context().add_class("rice-dialog")
        self.dock, self.index = dock, index
        self.set_default_size(520, -1)
        self.set_border_width(18)
        app = app or {"name": "", "icon": "", "command": "", "terminal": False}

        v = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.add(v)
        t = Gtk.Label(label=self.get_title(), xalign=0)
        t.get_style_context().add_class("title")
        v.pack_start(t, False, False, 0)

        # installed apps (fills the fields below)
        self.apps = sorted((a for a in Gio.AppInfo.get_all() if a.should_show()),
                           key=lambda a: a.get_display_name().lower())
        pick = Gtk.ComboBoxText.new_with_entry()
        pick.append_text("— choose an installed app (optional) —")
        for a in self.apps:
            pick.append_text(a.get_display_name())
        pick.set_active(0)
        comp = Gtk.EntryCompletion(model=pick.get_model(), text_column=0, inline_completion=True)
        comp.set_match_func(lambda c, key, it: key.lower() in (c.get_model()[it][0] or "").lower())
        pick.get_child().set_completion(comp)
        pick.connect("changed", self.on_pick)
        v.pack_start(self.labeled("Installed app", pick, "type to search, or skip and fill in a command below"), False, False, 0)

        self.name = Gtk.Entry(text=app["name"])
        v.pack_start(self.labeled("Name", self.name), False, False, 0)

        self.command = Gtk.Entry(text=app["command"])
        store = Gtk.ListStore(str)
        for a in zsh_aliases():
            store.append([a])
        c2 = Gtk.EntryCompletion(model=store, text_column=0, inline_completion=True)
        self.command.set_completion(c2)
        v.pack_start(self.labeled("Command or alias", self.command,
                                  "anything you'd type in the terminal: vim, minecraft, firefox, ~/scripts/x.sh"), False, False, 0)

        ib = Gtk.Box(spacing=6)
        self.icon = Gtk.Entry(text=app["icon"], hexpand=True)
        self.preview = Gtk.Box()
        browse = Gtk.Button(label="Image…")
        browse.connect("clicked", self.on_browse)
        ib.pack_start(self.preview, False, False, 0)
        ib.pack_start(self.icon, True, True, 0)
        ib.pack_start(browse, False, False, 0)
        self.icon.connect("changed", lambda *_: self.update_preview())
        v.pack_start(self.labeled("Icon", ib, "icon name (e.g. nvim, minecraft, firefox) or an image file"), False, False, 0)

        self.terminal = Gtk.CheckButton(label="Open in a terminal (for terminal programs like vim, htop)")
        self.terminal.set_active(bool(app.get("terminal")))
        v.pack_start(self.terminal, False, False, 0)

        bb = Gtk.Box(spacing=8, halign=Gtk.Align.END)
        cancel = Gtk.Button(label="Cancel")
        cancel.connect("clicked", lambda *_: self.destroy())
        save = Gtk.Button(label="Save")
        save.get_style_context().add_class("suggested-action")
        save.connect("clicked", self.on_save)
        bb.pack_start(cancel, False, False, 0)
        bb.pack_start(save, False, False, 0)
        v.pack_start(bb, False, False, 6)
        self.update_preview()
        self.show_all()

    def labeled(self, text, widget, hint=None):
        b = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
        b.pack_start(Gtk.Label(label=text, xalign=0), False, False, 0)
        b.pack_start(widget, False, False, 0)
        if hint:
            h = Gtk.Label(label=hint, xalign=0)
            h.get_style_context().add_class("hint")
            b.pack_start(h, False, False, 0)
        return b

    def update_preview(self):
        for c in self.preview.get_children():
            c.destroy()
        self.preview.pack_start(icon_widget(self.icon.get_text().strip(), 24), False, False, 0)
        self.preview.show_all()

    def on_pick(self, combo):
        name = combo.get_active_text()
        app = next((a for a in self.apps if a.get_display_name() == name), None)
        if not app:
            return
        self.name.set_text(app.get_display_name())
        exe = app.get_commandline() or app.get_executable() or ""
        exe = " ".join(w for w in shlex.split(exe) if not w.startswith("%"))   # drop %U etc.
        self.command.set_text(exe)
        icon = app.get_icon()
        if isinstance(icon, Gio.ThemedIcon):
            self.icon.set_text(icon.get_names()[0])
        elif isinstance(icon, Gio.FileIcon):
            self.icon.set_text(icon.get_file().get_path())
        self.terminal.set_active(bool(app.get_boolean("Terminal")) if hasattr(app, "get_boolean") else False)

    def on_browse(self, *_):
        d = Gtk.FileChooserDialog(title="Choose an icon image", parent=self, action=Gtk.FileChooserAction.OPEN)
        d.add_buttons("Cancel", Gtk.ResponseType.CANCEL, "Choose", Gtk.ResponseType.OK)
        f = Gtk.FileFilter()
        f.set_name("Images")
        f.add_pixbuf_formats()
        d.add_filter(f)
        if d.run() == Gtk.ResponseType.OK:
            self.icon.set_text(d.get_filename())
        d.destroy()

    def on_save(self, *_):
        app = {"name": self.name.get_text().strip(), "icon": self.icon.get_text().strip(),
               "command": self.command.get_text().strip(), "terminal": self.terminal.get_active()}
        if not app["command"]:
            self.command.grab_focus()
            return
        app["name"] = app["name"] or app["command"].split()[0]
        if self.index is None:
            self.dock.apps.append(app)
        else:
            self.dock.apps[self.index] = app
        self.dock.save_and_rebuild()
        self.destroy()


class Dock(Gtk.ApplicationWindow):
    def __init__(self, application):
        super().__init__(application=application, title="Rice Dock")
        self.set_wmclass("rice-dock", "RiceDock")
        self.set_decorated(False)
        self.set_type_hint(Gdk.WindowTypeHint.UTILITY)
        self.set_skip_taskbar_hint(True)
        self.set_keep_above(True)
        self.set_resizable(False)
        self.set_accept_focus(False)       # clicking the dock never steals keyboard focus
        screen = self.get_screen()
        if screen.get_rgba_visual():
            self.set_visual(screen.get_rgba_visual())
        self.set_app_paintable(True)

        self.apps = load_json(APPS, None)
        if self.apps is None:
            self.apps = [dict(a) for a in DEFAULT_APPS]
            save_json(APPS, self.apps)
        self.state = load_json(STATE, {"x": 12, "y": 220, "collapsed": False, "side": "left"})
        self.save_pending = None
        self.placed = False      # ignore i3's initial centering until restore_place ran

        self.stack = Gtk.Stack(transition_type=Gtk.StackTransitionType.CROSSFADE, transition_duration=160)
        self.stack.set_hhomogeneous(False)   # the collapsed tab is much smaller than the dock
        self.stack.set_vhomogeneous(False)
        self.add(self.stack)
        self.body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        self.body.get_style_context().add_class("dock")
        self.stack.add_named(self.body, "open")
        tab = Gtk.Button(label="›")
        tab.get_style_context().add_class("tab")
        tab.set_size_request(TAB_W, 72)
        tab.set_tooltip_text("Show dock")
        tab.connect("clicked", lambda *_: self.set_collapsed(False))
        self.tab = tab
        self.stack.add_named(tab, "tab")

        self.rebuild()
        self.connect("configure-event", self.on_configure)
        self.show_all()
        # i3 centers new floating windows; restore our place once it's mapped
        GLib.timeout_add(250, self.restore_place)

    def restore_place(self):
        self.placed = True
        if self.state.get("collapsed"):
            self.set_collapsed(True, remember=False)
        else:
            self.move(self.state["x"], self.state["y"])
        return False

    # ── content ─────────────────────────────────────────────────────────────
    def rebuild(self):
        for c in self.body.get_children():
            c.destroy()
        top = Gtk.Box(spacing=0)
        grip = Gtk.EventBox()
        gl = Gtk.Label(label="⠿")
        gl.get_style_context().add_class("grip")
        grip.add(gl)
        grip.set_tooltip_text("Drag to move")
        grip.connect("button-press-event", self.on_grip)
        grip.connect("realize", lambda w: w.get_window().set_cursor(Gdk.Cursor.new_from_name(w.get_display(), "grab")))
        top.pack_start(grip, True, True, 0)
        col = Gtk.Button(label="‹")
        col.set_tooltip_text("Collapse to the side")
        col.connect("clicked", lambda *_: self.set_collapsed(True))
        top.pack_end(col, False, False, 0)
        self.body.pack_start(top, False, False, 0)

        for i, app in enumerate(self.apps):
            b = Gtk.Button()
            b.add(icon_widget(app.get("icon")))
            b.set_tooltip_text(app.get("name") or app["command"])
            b.connect("clicked", lambda w, a=app: launch(a))
            b.connect("button-press-event", self.on_item_press, i)
            self.body.pack_start(b, False, False, 0)

        self.body.pack_start(Gtk.Separator(), False, False, 0)
        mon = Gtk.Button()
        mon.add(icon_widget("utilities-system-monitor"))
        mon.set_tooltip_text("System monitor (CPU, RAM, disks, temperatures)")
        mon.connect("clicked", lambda *_: subprocess.Popen(
            [os.path.expanduser("~/.local/bin/rice-sysmon")], start_new_session=True))
        self.body.pack_start(mon, False, False, 0)
        add = Gtk.Button(label="+")
        add.get_style_context().add_class("add")
        add.set_tooltip_text("Add an app or alias")
        add.connect("clicked", lambda *_: AppDialog(self))
        self.body.pack_start(add, False, False, 0)
        self.body.show_all()
        self.resize(1, 1)    # shrink to fit after items were removed

    def save_and_rebuild(self):
        save_json(APPS, self.apps)
        self.rebuild()

    def on_item_press(self, button, event, index):
        if event.button != 3:
            return False
        menu = Gtk.Menu()
        for label, fn in (("Edit…", lambda *_: AppDialog(self, dict(self.apps[index]), index)),
                          ("Move up", lambda *_: self.move_item(index, -1)),
                          ("Move down", lambda *_: self.move_item(index, 1)),
                          ("Remove", lambda *_: self.remove_item(index))):
            it = Gtk.MenuItem(label=label)
            it.connect("activate", fn)
            menu.append(it)
        menu.show_all()
        menu.popup_at_pointer(event)
        return True

    def move_item(self, i, d):
        j = i + d
        if 0 <= j < len(self.apps):
            self.apps[i], self.apps[j] = self.apps[j], self.apps[i]
            self.save_and_rebuild()

    def remove_item(self, i):
        del self.apps[i]
        self.save_and_rebuild()

    # ── moving / collapsing ─────────────────────────────────────────────────
    def on_grip(self, widget, event):
        if event.button == 1:
            self.begin_move_drag(event.button, int(event.x_root), int(event.y_root), event.time)
        return True

    def monitor_geometry(self):
        display = self.get_display()
        mon = display.get_monitor_at_window(self.get_window()) or display.get_primary_monitor()
        return mon.get_geometry()

    def on_configure(self, *_):
        if self.placed and not self.state.get("collapsed"):
            x, y = self.get_position()
            self.state.update(x=x, y=y)
            if self.save_pending:
                GLib.source_remove(self.save_pending)
            self.save_pending = GLib.timeout_add(400, self.save_state)
        return False

    def save_state(self):
        self.save_pending = None
        save_json(STATE, self.state)
        return False

    def set_collapsed(self, collapsed, remember=True):
        geo = self.monitor_geometry()
        if collapsed:
            if remember:      # where to come back to, and which side to stick to
                x, y = self.get_position()
                w, _ = self.get_size()
                self.state.update(x=x, y=y, side="left" if x + w / 2 < geo.x + geo.width / 2 else "right")
            self.state["collapsed"] = True
            side, y = self.state.get("side", "left"), self.state["y"]
            self.tab.set_label("›" if side == "left" else "‹")
            self.stack.set_visible_child_name("tab")
            self.resize(TAB_W, 72)
            tx = geo.x if side == "left" else geo.x + geo.width - TAB_W
            self.move(tx, y)
        else:
            self.state["collapsed"] = False
            self.stack.set_visible_child_name("open")
            self.resize(1, 1)
            self.move(self.state["x"], self.state["y"])
        self.save_state()
        return False


class DockApp(Gtk.Application):
    def __init__(self):
        super().__init__(application_id="dev.rice.Dock", flags=Gio.ApplicationFlags.FLAGS_NONE)
        self.win = None

    def do_activate(self):
        if self.win:          # launched again: toggle collapsed/expanded
            self.win.set_collapsed(not self.win.state.get("collapsed"))
            return
        ricetheme.Theme(CSS)
        self.win = Dock(self)


if __name__ == "__main__":
    GLib.set_prgname("rice-dock")
    sys.exit(DockApp().run(sys.argv[:1]))
