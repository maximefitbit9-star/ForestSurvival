"""Main menu with an atmospheric forest background scene."""
from panda3d.core import TextNode
from direct.gui import DirectGuiGlobals
from direct.gui.DirectFrame import DirectFrame
from direct.gui.DirectButton import DirectButton
from direct.gui.DirectLabel import DirectLabel

from .widgets import THEME, make_button, make_label

TITLE = "NINETY-NINE NIGHTS IN THE WILDWOOD"
SUBTITLE = "An original forest survival game inspired by the systems of 99 Nights in the Forest"


class MainMenu:
    def __init__(self, base, app_callbacks):
        self.base = base
        self.cb = app_callbacks
        self.root = DirectFrame(frameColor=(0, 0, 0, 0))
        self.root.hide()
        self._build()

    def _build(self):
        vignette = DirectFrame(parent=self.root, frameColor=(0, 0, 0, 0.55), frameSize=(-2, 2, -1.2, 1.2))
        vignette.set_transparency(True)
        title = make_label(TITLE, self.root, (0, 0, 0.82), scale=0.09, colour=THEME["text"])
        title["text_align"] = TextNode.ACenter
        subtitle = make_label(SUBTITLE, self.root, (0, 0, 0.68), scale=0.035,
                               colour=(0.7, 0.8, 0.7, 1))
        subtitle["text_align"] = TextNode.ACenter
        buttons = [
            ("Continue", self.cb.get("continue", lambda: None)),
            ("New Game", self.cb.get("new_game", lambda: None)),
            ("Load Game", self.cb.get("load_game", lambda: None)),
            ("Class Selection", self.cb.get("classes", lambda: None)),
            ("Settings", self.cb.get("settings", lambda: None)),
            ("Credits", self.cb.get("credits", lambda: None)),
            ("Exit", self.cb.get("exit", lambda: None)),
        ]
        y = 0.45
        for label, cmd in buttons:
            btn = make_button(label, cmd, self.root, (0, 0, y), width=16)
            btn.set_transparency(True)
            y -= 0.13
        self.hint = make_label("WASD move | Mouse look | E interact | I inventory | C craft | M map | Esc pause",
                               self.root, (0, 0, -0.85), scale=0.03, colour=(0.6, 0.7, 0.6, 1))
        self.hint["text_align"] = TextNode.ACenter

    def show(self, can_continue=True):
        self.root.show()

    def hide(self):
        self.root.hide()


class CreditsScreen:
    def __init__(self, base):
        self.root = DirectFrame(frameColor=THEME["bg"])
        self.root.hide()
        lines = [
            ("Ninety-Nine Nights in the Wildwood", 0.75, 0.07),
            ("An original single-player survival game.", 0.6, 0.045),
            ("Inspired by the gameplay systems of 99 Nights in the Forest.", 0.52, 0.035),
            ("All models, textures and audio in this game are procedurally", 0.35, 0.04),
            ("generated originals. No assets are copied from any other game.", 0.28, 0.04),
            ("Built with Panda3D. Python 3.11+.", 0.1, 0.04),
        ]
        for text, y, scale in lines:
            label = make_label(text, self.root, (0, 0, y), scale=scale)
            label["text_align"] = TextNode.ACenter
        self.close = make_button("Back", self.hide, self.root, (0, 0, -0.4), width=10)

    def show(self):
        self.root.show()

    def hide(self):
        self.root.hide()
