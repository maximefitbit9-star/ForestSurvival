"""In-game HUD: survival bars, day counter, campfire fuel, prompts and warnings."""
from panda3d.core import TextNode
from direct.gui import DirectGuiGlobals
from direct.gui.DirectFrame import DirectFrame
from direct.gui.DirectLabel import DirectLabel

from .widgets import THEME, make_label, make_progress_bar, set_bar


class HUD:
    def __init__(self, base, gm, renderer):
        self.base = base
        self.gm = gm
        self.renderer = renderer
        self.root = DirectFrame(frameColor=(0, 0, 0, 0))
        self.root.hide()
        self._build()

    def _build(self):
        self.day_label = make_label("Day 1", self.root, (-1.55, 0, 0.94), scale=0.06, colour=THEME["text"])
        self.phase_label = make_label("Daytime", self.root, (-1.55, 0, 0.87), scale=0.045,
                                      colour=(0.8, 0.85, 0.8, 1))
        self.wood_label = make_label("", self.root, (-1.55, 0, 0.80), scale=0.04, colour=(0.8, 0.85, 0.8, 1))

        self.health_bg, self.health_fill = make_progress_bar(self.root, (-1.55, 0, 0.72), width=0.8)
        self.health_fill["frameColor"] = (0.85, 0.25, 0.25, 1)
        self.hunger_bg, self.hunger_fill = make_progress_bar(self.root, (-1.55, 0, 0.64), width=0.8)
        self.hunger_fill["frameColor"] = (0.85, 0.7, 0.25, 1)
        self.stamina_bg, self.stamina_fill = make_progress_bar(self.root, (-1.55, 0, 0.56), width=0.8)
        self.stamina_fill["frameColor"] = (0.3, 0.7, 0.9, 1)

        self.fire_label = make_label("Campfire", self.root, (1.2, 0, 0.94), scale=0.05, colour=THEME["text"])
        self.fire_bg, self.fire_fill = make_progress_bar(self.root, (1.2, 0, 0.86), width=0.8)
        self.fire_level_label = make_label("Level 1", self.root, (1.2, 0, 0.78), scale=0.04,
                                           colour=(0.9, 0.7, 0.4, 1))

        self.prompt = make_label("", self.root, (0, 0, -0.6), scale=0.05, colour=(0.95, 0.95, 0.85, 1))
        self.prompt["text_align"] = TextNode.ACenter
        self.warning = make_label("", self.root, (0, 0, 0.6), scale=0.06, colour=THEME["danger"])
        self.warning["text_align"] = TextNode.ACenter
        self.warning_timer = 0.0
        self.crosshair = make_label("+", self.root, (0, 0, 0), scale=0.05, colour=(1, 1, 1, 0.7))

    def show_warning(self, text, duration=3.0):
        self.warning["text"] = text
        self.warning_timer = duration

    def set_prompt(self, text):
        self.prompt["text"] = text

    def update(self, dt):
        gm = self.gm
        self.day_label["text"] = "Day %d / 99" % gm.day_night.day
        self.phase_label["text"] = ("Night %d - stay in the light" % gm.day_night.day
                                    if gm.day_night.is_night() else
                                    "Daytime - %d:%02d until night" % self._until_night())
        wood = gm.inventory.count("log")
        self.wood_label["text"] = "Logs: %d  Wood: %d" % (wood, gm.inventory.count("wood"))
        set_bar(self.health_fill, gm.player.health / gm.player.max_health, width=0.8)
        set_bar(self.hunger_fill, gm.player.hunger / gm.player.max_hunger, width=0.8)
        set_bar(self.stamina_fill, gm.player.stamina / gm.player.max_stamina, width=0.8)
        set_bar(self.fire_fill, gm.campfire.fuel_fraction(), width=0.8)
        color = (0.9, 0.5, 0.2, 1) if gm.campfire.fuel_fraction() > 0.35 else THEME["danger"]
        self.fire_fill["frameColor"] = color
        self.fire_level_label["text"] = "Level %d - safe zone %dm" % (gm.campfire.level, gm.campfire.safe_radius)
        if self.warning_timer > 0:
            self.warning_timer -= dt
            if self.warning_timer <= 0:
                self.warning["text"] = ""

    def _until_night(self):
        secs = self.gm.day_night.seconds_until_night()
        return int(secs // 60), int(secs % 60)

    def show(self):
        self.root.show()

    def hide(self):
        self.root.hide()
