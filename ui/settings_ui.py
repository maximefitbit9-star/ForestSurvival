"""Settings screen: graphics presets and individual options, sound and music."""
from direct.gui.DirectFrame import DirectFrame
from direct.gui.DirectButton import DirectButton
from direct.gui.DirectLabel import DirectLabel

from .widgets import THEME, make_label, make_panel


class SettingsUI:
    def __init__(self, base, app):
        self.base = base
        self.app = app
        self.visible = False
        self.root = DirectFrame(frameColor=(0, 0, 0, 0.6))
        self.root.set_transparency(True)
        self.root.hide()
        self.panel = make_panel(self.root, (0, 0, 0), (-0.8, 0.8, -0.85, 0.85))
        self.title = make_label("Settings", self.panel, (0, 0, 0.75), scale=0.07)
        self.rows = []
        self._build()

    def _add_button(self, text, command, pos, width=10):
        return DirectButton(parent=self.panel, pos=pos, scale=0.05, text=text,
                            text_fg=THEME["text"], frameColor=(0.15, 0.2, 0.15, 0.95),
                            frameSize=(-width / 2, width / 2, -0.8, 1.0),
                            command=command)

    def _build(self):
        presets = self.app.gamedata.settings["graphics_presets"]
        x = -0.6
        for name in presets:
            btn = self._add_button(name.title(), self.app.apply_preset, (x, 0, 0.55), width=8)
            btn.setPythonTag("preset", name)
            x += 0.35
        self.preset_label = make_label("", self.panel, (0, 0, 0.45), scale=0.04)
        self._add_button("Toggle Fullscreen", self.app.toggle_fullscreen, (-0.35, 0, 0.3), width=14)
        self._add_button("Toggle VSync", self.app.toggle_vsync, (0.35, 0, 0.3), width=10)
        self._add_button("Render Distance +", self.app.increase_render_distance, (-0.35, 0, 0.15), width=14)
        self._add_button("Toggle Shadows", self.app.toggle_shadows, (0.35, 0, 0.15), width=10)
        self._add_button("Sound Volume +", self.app.increase_sound, (-0.35, 0, 0.0), width=14)
        self._add_button("Music Volume +", self.app.increase_music, (0.35, 0, 0.0), width=12)
        self.values_label = make_label("", self.panel, (0, 0, -0.15), scale=0.04)
        self.close = self._add_button("Back", self.hide, (0, 0, -0.6), width=10)

    def refresh(self):
        s = self.app.user_settings
        self.preset_label["text"] = "Current preset: %s" % s.get("preset", "custom")
        self.values_label["text"] = (
            "Resolution: %dx%d | Fullscreen: %s | VSync: %s\n"
            "Render distance: %dm | Shadows: %s\n"
            "Sound: %d%% | Music: %d%%" % (
                s["resolution"][0], s["resolution"][1], "yes" if s["fullscreen"] else "no",
                "yes" if s["vsync"] else "no", s["render_distance"],
                "yes" if s["shadows"] else "no", int(s["sound_volume"] * 100),
                int(s["music_volume"] * 100)))

    def show(self):
        self.visible = True
        self.refresh()
        self.root.show()

    def hide(self):
        self.visible = False
        self.app.save_settings()
        self.root.hide()
