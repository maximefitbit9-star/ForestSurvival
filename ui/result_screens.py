"""Victory and defeat screens with run statistics and diamond rewards."""
from panda3d.core import TextNode
from direct.gui import DirectGuiGlobals
from direct.gui.DirectFrame import DirectFrame

from .widgets import THEME, make_label, make_button


class ResultScreen:
    def __init__(self, base, app):
        self.base = base
        self.app = app
        self.root = DirectFrame(frameColor=(0, 0, 0, 0.85))
        self.root.set_transparency(True)
        self.root.hide()
        self.title = make_label("", self.root, (0, 0, 0.7), scale=0.1)
        self.title["text_align"] = TextNode.ACenter
        self.stats = make_label("", self.root, (0, 0, 0.2), scale=0.05)
        self.stats["text_align"] = TextNode.ACenter
        self.diamonds = make_label("", self.root, (0, 0, -0.1), scale=0.07, colour=(0.5, 0.8, 1.0, 1))
        self.diamonds["text_align"] = TextNode.ACenter
        self.menu_btn = make_button("Main Menu", self._to_menu, self.root, (0, 0, -0.4), width=14)
        self.again_btn = make_button("New Run", self._new_run, self.root, (0, 0, -0.55), width=14)

    def show(self, gm):
        if gm.victory:
            self.title["text"] = "You Survived All 99 Nights!"
            self.title["text_fg"] = (0.4, 0.95, 0.4, 1)
        else:
            self.title["text"] = "The Forest Claimed You"
            self.title["text_fg"] = THEME["danger"]
        stats = gm.run_stats
        self.stats["text"] = (
            "Nights survived: %d\nChildren rescued: %d of 4\nLocations discovered: %d\n"
            "Trees felled: %d\nCampfire level: %d" % (
                stats["nights_survived"], gm.npcs.rescued_count(),
                stats["locations_discovered"], stats.get("trees_felled", 0), gm.campfire.level))
        self.diamonds["text"] = "Diamonds earned: %d (saved forever)" % getattr(gm, "earned_diamonds", 0)
        self.root.show()

    def _to_menu(self):
        self.root.hide()
        self.app.return_to_menu()

    def _new_run(self):
        self.root.hide()
        self.app.start_new_game()

    def hide(self):
        self.root.hide()
