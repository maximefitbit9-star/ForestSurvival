"""Ninety-Nine Nights in the Wildwood - main application.

Launch on Windows with launch.bat or:  python main.py
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from direct.showbase.ShowBase import ShowBase
from direct.gui import DirectGuiGlobals
from direct.gui.DirectFrame import DirectFrame
from direct.gui.DirectButton import DirectButton
from panda3d.core import load_prc_file_data, WindowProperties, Vec3, TextNode

from game.data_loader import load_gamedata
from game.game_manager import GameManager
from game.save_system import SaveSystem
from game.class_system import ClassSystem
from game.world_manager import WorldRenderer
from game.player_controller import PlayerController
from game.building import BuildingSystem
from game.audio_manager import AudioManager
from ui.main_menu import MainMenu, CreditsScreen
from ui.hud import HUD
from ui.inventory_ui import InventoryUI
from ui.crafting_ui import CraftingUI
from ui.map_ui import MapUI
from ui.settings_ui import SettingsUI
from ui.class_ui import ClassUI
from ui.result_screens import ResultScreen
from ui.widgets import THEME, make_label, make_button, make_panel

TOOLS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tools")
sys.path.insert(0, TOOLS_DIR)


class ForestGame(ShowBase):
    def __init__(self):
        self.gamedata = load_gamedata()
        self.settings = self.gamedata.settings
        self.user_settings = dict(self.settings["user_settings"])
        self.saves = SaveSystem()
        self.profile = self.saves.load_profile()
        self.class_system = ClassSystem(self.gamedata, self.profile)
        self._generate_assets()
        load_prc_file_data("", "window-title Ninety-Nine Nights in the Wildwood")
        load_prc_file_data("", "sync-video %s" % ("1" if self.user_settings["vsync"] else "0"))
        super().__init__()
        self.audio = AudioManager(self.user_settings["sound_volume"], self.user_settings["music_volume"],
                                   loader=self.loader)
        self.apply_resolution()
        self.disable_mouse()
        self.gm = None
        self.renderer = None
        self.controller = None
        self.building = None
        self.paused = False
        self.in_menu = True
        self._ui = {}
        self._build_menus()
        self._build_pause_menu()
        self._bind_global_keys()
        self.menu_scene = self._build_menu_scene()
        self.task_mgr.add(self._menu_ambience_task, "menu_ambience")
        self.show_menu()

    # ------------------------------------------------------------ start-up

    def _generate_assets(self):
        import gen_audio
        audio_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "audio")
        if not os.path.isdir(audio_dir) or len(os.listdir(audio_dir)) < 5:
            gen_audio.generate_all()

    def _build_menu_scene(self):
        return None

    def _menu_ambience_task(self, task):
        if self.in_menu and self.audio.has("ambience_day"):
            self.audio.set_ambience("ambience_day")
        return task.cont

    # ------------------------------------------------------------- settings

    def apply_resolution(self):
        if self.win is None:
            return
        props = WindowProperties()
        w, h = self.user_settings["resolution"]
        props.setSize(w, h)
        props.setFullscreen(self.user_settings["fullscreen"])
        self.win.requestProperties(props)
        self.win.set_clear_color((0.05, 0.08, 0.06, 1))

    def apply_preset(self, preset_name=None):
        presets = self.settings["graphics_presets"]
        preset = presets[preset_name] if preset_name else presets[self.user_settings.get("preset", "high")]
        for key in ("resolution", "fullscreen", "vsync", "render_distance", "shadows",
                    "shadow_resolution", "texture_quality", "ambient_effects"):
            self.user_settings[key] = preset[key]
        if preset_name:
            self.user_settings["preset"] = preset_name
        self.apply_resolution()
        if self.renderer:
            self.renderer.render_distance = preset["render_distance"]
        self._ui["settings"].refresh() if "settings" in self._ui else None

    def toggle_fullscreen(self):
        self.user_settings["fullscreen"] = not self.user_settings["fullscreen"]
        self.user_settings["preset"] = "custom"
        self.apply_resolution()

    def toggle_vsync(self):
        self.user_settings["vsync"] = not self.user_settings["vsync"]
        self.user_settings["preset"] = "custom"
        load_prc_file_data("", "sync-video %s" % ("1" if self.user_settings["vsync"] else "0"))

    def toggle_shadows(self):
        self.user_settings["shadows"] = not self.user_settings["shadows"]
        self.user_settings["preset"] = "custom"
        if self.renderer and self.renderer.sun:
            if self.user_settings["shadows"]:
                self.renderer.sun.set_shadow_caster(True, self.user_settings["shadow_resolution"],
                                                    self.user_settings["shadow_resolution"])
            else:
                self.renderer.sun.clear_shadow_caster()

    def increase_render_distance(self):
        rd = min(400, self.user_settings["render_distance"] + 40)
        self.user_settings["render_distance"] = rd
        self.user_settings["preset"] = "custom"
        if self.renderer:
            self.renderer.render_distance = rd

    def increase_sound(self):
        self.user_settings["sound_volume"] = min(1.0, self.user_settings["sound_volume"] + 0.1)
        self.audio.set_volumes(self.user_settings["sound_volume"], self.user_settings["music_volume"])

    def increase_music(self):
        self.user_settings["music_volume"] = min(1.0, self.user_settings["music_volume"] + 0.1)
        self.audio.set_volumes(self.user_settings["sound_volume"], self.user_settings["music_volume"])

    def save_settings(self):
        path = os.path.join(self.gamedata.config_dir, "settings.json")
        import json
        self.settings["user_settings"] = self.user_settings
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.settings, f, indent=2)

    def save_profile(self):
        self.saves.save_profile(self.profile)

    # ----------------------------------------------------------------- UI

    def _build_menus(self):
        self._ui["menu"] = MainMenu(self, {
            "continue": self.continue_game,
            "new_game": self.new_game_flow,
            "load_game": self.show_save_select,
            "classes": self.show_classes,
            "settings": self.show_settings,
            "credits": self.show_credits,
            "exit": self.user_exit,
        })
        self._ui["credits"] = CreditsScreen(self)
        self._ui["settings"] = SettingsUI(self, self)
        self._ui["classes"] = ClassUI(self, self)
        self._ui["result"] = ResultScreen(self, self)
        self._save_frame = None

    def _build_pause_menu(self):
        self.pause_root = DirectFrame(frameColor=(0, 0, 0, 0.6))
        self.pause_root.set_transparency(True)
        self.pause_root.hide()
        panel = make_panel(self.pause_root, (0, 0, 0), (-0.6, 0.6, -0.6, 0.6))
        make_label("Paused", panel, (0, 0, 0.45), scale=0.08)
        make_button("Resume", self.toggle_pause, panel, (0, 0, 0.25), width=10)
        make_button("Save Game", self.save_game, panel, (0, 0, 0.1), width=10)
        make_button("Settings", lambda: (self.toggle_pause(), self.show_settings()), panel, (0, 0, -0.05), width=10)
        make_button("Main Menu", self.return_to_menu, panel, (0, 0, -0.2), width=10)
        make_button("Exit", self.user_exit, panel, (0, 0, -0.35), width=10)

    def _bind_global_keys(self):
        self.accept("escape", self.on_escape)
        self.accept("i", self.toggle_inventory)
        self.accept("c", self.toggle_crafting)
        self.accept("m", self.toggle_map)
        self.accept("e", self.interact)
        self.accept("f", self.use_flashlight)
        self.accept("f5", self.save_game)
        self.accept("b", self.cancel_placement)
        self.accept("r", self.rotate_building)
        self.accept("mouse1", self.chop)
        self.accept("mouse3", self.confirm_placement)

    # ------------------------------------------------------------ menu flow

    def show_menu(self):
        self.in_menu = True
        self._ui["menu"].show()
        if self.gm:
            self._teardown_game()

    def return_to_menu(self):
        self.save_profile()
        self.show_menu()

    def user_exit(self):
        self.save_profile()
        self.save_settings()
        self.userExit()

    def show_settings(self):
        self._ui["settings"].show()

    def show_credits(self):
        self._ui["credits"].show()

    def show_classes(self):
        self._ui["classes"].show()

    def new_game_flow(self):
        selected = getattr(self._ui["classes"], "selected_class", None) or "camper"
        self.start_game(slot=None, class_id=selected)

    def continue_game(self):
        for slot in range(SaveSystem.SLOTS):
            if self.saves.slot_info(slot):
                self.start_game(slot=slot)
                return
        self.new_game_flow()

    def show_save_select(self):
        if self._save_frame:
            self._save_frame.destroy()
        frame = DirectFrame(frameColor=(0, 0, 0, 0.7))
        frame.set_transparency(True)
        self._save_frame = frame
        make_label("Select Save Slot", frame, (0, 0, 0.8), scale=0.08)
        y = 0.5
        for slot in range(SaveSystem.SLOTS):
            info = self.saves.slot_info(slot)
            if info:
                text = "Slot %d - Day %d, Campfire %d, %d children saved" % (
                    slot + 1, info["day"], info["campfire_level"], info["children_rescued"])
                DirectButton(parent=frame, pos=(0, 0, y), scale=0.05, text=text,
                             frameColor=(0.15, 0.25, 0.15, 0.95), text_fg=THEME["text"],
                             command=self.start_game, extraArgs=[slot])
            else:
                DirectButton(parent=frame, pos=(0, 0, y), scale=0.05,
                             text="Slot %d - Empty (start new run)" % (slot + 1),
                             frameColor=(0.15, 0.2, 0.15, 0.95), text_fg=THEME["text"],
                             command=self.start_game, extraArgs=[slot])
            y -= 0.2
        make_button("Back", frame.destroy, frame, (0, 0, -0.5), width=8)

    # ----------------------------------------------------------- game setup

    def start_game(self, slot=None, class_id=None):
        try:
            self._start_game_impl(slot, class_id)
        except Exception:
            import traceback
            tb = traceback.format_exc()
            self._report_crash(tb)

    def _report_crash(self, tb):
        log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "error.log")
        try:
            with open(log_path, "w", encoding="utf-8") as f:
                f.write(tb)
        except OSError:
            pass
        print("\n=== The game crashed. The full error was saved to: ===\n%s\n=== Please share the contents of error.log. ===\n" % log_path)
        print(tb)

    def _start_game_impl(self, slot=None, class_id=None):
        if self._save_frame:
            self._save_frame.destroy()
            self._save_frame = None
        self._ui["menu"].hide()
        self._ui["classes"].hide()
        self._ui["settings"].hide()
        self.in_menu = False
        seed = self.settings["world"].get("seed") or None
        self.gm = GameManager(self.gamedata, seed=seed, class_id=class_id or "camper",
                              profile=self.profile)
        if slot is not None:
            data = self.saves.load(slot)
            if data:
                self.gm.load_dict(data)
        self.renderer = WorldRenderer(self, self.gm, self.user_settings)
        self.controller = PlayerController(self, self.gm, self.renderer, self.user_settings)
        self.controller.bind_keys()
        self.building = BuildingSystem(self, self.gm, self.renderer)
        self._ui["hud"] = HUD(self, self.gm, self.renderer)
        self._ui["inventory"] = InventoryUI(self, self.gm, self.audio)
        self._ui["crafting"] = CraftingUI(self, self.gm, self.audio,
                                          on_build=self.building.start_placement)
        self._ui["map"] = MapUI(self, self.gm)
        self._ui["hud"].show()
        self.controller.frozen = False
        self.task_mgr.add(self._game_task, "game_task")
        self.audio.set_ambience("ambience_day")
        self.current_slot = slot if slot is not None else 0

    def _teardown_game(self):
        if "game_task" in [t.name for t in self.task_mgr.get_tasks()]:
            self.task_mgr.remove("game_task")
        for key in ("hud", "inventory", "crafting", "map"):
            if key in self._ui:
                self._ui[key].hide()
        if self.renderer:
            self.renderer.root.remove_node()
            self.renderer = None
        self.gm = None
        self.controller = None
        self.building = None

    # ------------------------------------------------------------- gameplay

    def on_escape(self):
        if self.in_menu:
            return
        if any(self._ui[k].visible for k in ("inventory", "crafting", "map")):
            self._ui["inventory"].hide()
            self._ui["crafting"].hide()
            self._ui["map"].hide()
            self.controller.frozen = False
            return
        self.toggle_pause()

    def toggle_pause(self):
        self.paused = not self.paused
        self.controller.frozen = self.paused
        if self.paused:
            self.pause_root.show()
        else:
            self.pause_root.hide()

    def toggle_inventory(self):
        if self.in_menu or not self.gm:
            return
        ui = self._ui["inventory"]
        if ui.visible:
            ui.hide()
            self.controller.frozen = False
        else:
            self._close_other_panels()
            ui.show()
            self.controller.frozen = True

    def toggle_crafting(self):
        if self.in_menu or not self.gm:
            return
        ui = self._ui["crafting"]
        if ui.visible:
            ui.hide()
            self.controller.frozen = False
        else:
            self._close_other_panels()
            ui.show()
            self.controller.frozen = True

    def toggle_map(self):
        if self.in_menu or not self.gm:
            return
        ui = self._ui["map"]
        if ui.visible:
            ui.hide()
            self.controller.frozen = False
        else:
            self._close_other_panels()
            ui.show()
            self.controller.frozen = True

    def _close_other_panels(self):
        for k in ("inventory", "crafting", "map"):
            if k in self._ui and self._ui[k].visible:
                self._ui[k].hide()

    def cancel_placement(self):
        if self.building and self.building.placing:
            self.building.cancel()

    def rotate_building(self):
        if self.building and self.building.placing:
            self.building.rotate()

    def confirm_placement(self):
        if self.building and self.building.placing:
            if self.building.confirm():
                self.audio.play("build")
            else:
                self._ui["hud"].show_warning("Cannot place here - blocked or too close to the fire.")

    def use_flashlight(self):
        if not self.gm or self.gm.inventory.count("flashlight") < 1:
            if self.gm:
                self._ui["hud"].show_warning("You need a flashlight (found in houses and clinics).")
            return
        self.gm.stun_threats()
        self.audio.play("warning")
        self._ui["hud"].show_warning("The hunters flinch away from the light!")

    def _best_axe(self):
        best, order = None, ["old_axe", "good_axe", "strong_axe", "ice_axe", "chainsaw"]
        for axe in order:
            if self.gm.inventory.count(axe) > 0:
                best = axe
        return best

    def chop(self):
        if self.in_menu or not self.gm or self.controller.frozen or self.paused:
            return
        if self.building and self.building.placing:
            return
        axe = self._best_axe()
        if axe is None:
            self._ui["hud"].show_warning("You need an axe to chop trees.")
            return
        player = self.gm.player
        best, best_d = None, 5.0
        for idx, tree in enumerate(self.gm.world.trees):
            if tree.get("removed"):
                continue
            d = math.hypot(tree["x"] - player.x, tree["y"] - player.y)
            if d < best_d:
                best, best_d = idx, d
        if best is None:
            return
        result = self.gm.chop_tree(best, axe)
        self.audio.play("chop")
        if result.get("blocked"):
            self._ui["hud"].show_warning("This tree is too thick for the %s." % self.gamedata.item_name(axe))
            return
        if result.get("fell"):
            self.renderer.animate_tree_fall(best, result.get("direction", 0))
            self.audio.play("tree_fall")
            drops = result.get("drops", {})
            self._ui["hud"].show_warning("Tree felled: %s" % ", ".join(
                "%d %s" % (q, self.gamedata.item_name(i)) for i, q in drops.items()))
        else:
            self.renderer.show_tree_damage(best, result.get("damage", 0))

    def interact(self):
        if self.in_menu or not self.gm or self.controller.frozen or self.paused:
            return
        target = self._find_interaction()
        if target is None:
            return
        kind = target[0]
        if kind == "campfire":
            fuel = self._choose_fuel()
            if fuel:
                self.gm.add_fuel(fuel, 1)
                self.audio.play("collect")
            else:
                self._ui["hud"].show_warning("No fuel items in your inventory.")
        elif kind == "bench":
            self.toggle_crafting()
        elif kind == "location":
            loot = self.gm.interactor_loot(target[1])
            if loot:
                self.audio.play("collect")
                self._ui["hud"].show_warning("Found: " + ", ".join(
                    "%d %s" % (q, self.gamedata.item_name(i)) for i, q in loot.items()))
            else:
                self._ui["hud"].show_warning("Already looted.")
        elif kind == "child":
            child_id = target[1]
            if self.gm.rescue_child(child_id):
                self.audio.play("rescue")
                child = self.gm.npcs.children[child_id]
                self._ui["hud"].show_warning("Rescued %s! \"%s\"" % (
                    child.defn["name"], child.next_dialogue()), duration=6.0)
            else:
                need = self.gamedata.progression["children"]["rescue_requirements"][child_id]
                self._ui["hud"].show_warning(
                    "%s is too deep in the forest. Upgrade the campfire to level %d first." % (
                        self.gm.npcs.children[child_id].defn["name"],
                        need["campfire_level"]))
        elif kind == "plot":
            plot_id = target[1]
            plot = self.gm.farming.plots[plot_id]
            if plot.is_grown():
                result = self.gm.harvest_plot(plot_id)
                self.audio.play("collect")
                self._ui["hud"].show_warning("Harvested %d %s" % (result["qty"], self.gamedata.item_name(result["crop"])))
            elif plot.crop is None:
                seeds = next((i for i in ("carrot_seeds", "corn_seeds", "pumpkin_seeds", "chili_seeds")
                              if self.gm.inventory.count(i) > 0), None)
                if seeds:
                    self.gm.plant_crop(plot_id, seeds)
                    self.audio.play("collect")
                    self._ui["hud"].show_warning("Planted %s." % self.gamedata.item_name(seeds))
                else:
                    self._ui["hud"].show_warning("You need seeds to plant here.")
            else:
                self._ui["hud"].show_warning("The crop is still growing (%d%%)." % int(plot.growth * 100))
        elif kind == "bed":
            days = self.gm.use_bed(target[1])
            self._ui["hud"].show_warning("You slept safely. Skipped %d day(s)." % days)

    def _choose_fuel(self):
        best, best_value = None, 0
        for item_id in ("log", "coal", "biofuel", "fuel_canister", "oil_barrel"):
            if self.gm.inventory.count(item_id) > 0 and self.gamedata.fuel_value(item_id) > best_value:
                best, best_value = item_id, self.gamedata.fuel_value(item_id)
        return best

    def _find_interaction(self):
        gm = self.gm
        player = gm.player
        if math.hypot(player.x, player.y) < 5:
            return ("campfire",)
        if math.hypot(player.x, player.y - 5) < 4:
            return ("bench",)
        for loc in gm.world.locations:
            d = math.hypot(loc["x"] - player.x, loc["y"] - player.y)
            if d < 7 and loc.get("discovered"):
                if "child" in loc and not gm.npcs.children[loc["child"]].rescued:
                    return ("child", loc["child"])
                if loc.get("looted"):
                    continue
                return ("location", loc["id"])
        for struct in gm.structures:
            d = math.hypot(struct["x"] - player.x, struct["y"] - player.y)
            if d < 3:
                if struct["type"].endswith("bed"):
                    return ("bed", struct["type"])
                if gm.gamedata.structure_def(struct["type"]).get("farm"):
                    for plot in gm.farming.plots.values():
                        if abs(plot.x - struct["x"]) < 0.1 and abs(plot.y - struct["y"]) < 0.1:
                            return ("plot", plot.id)
        return None

    def _interaction_prompt(self):
        target = self._find_interaction()
        prompts = {
            "campfire": "E: Add fuel (%s)" % (self.gamedata.item_name(self._choose_fuel()) if self._choose_fuel() else "none left!"),
            "bench": "E: Open Crafting Bench",
            "location": "E: Scavenge",
            "child": "E: Rescue child",
            "plot": "E: Plant / harvest crop",
            "bed": "E: Sleep (skip a day)",
        }
        return prompts.get(target[0], "") if target else ""

    def save_game(self):
        if not self.gm:
            return
        self.saves.save(self.current_slot, self.gm.to_dict())
        self.save_profile()
        if self._ui.get("hud"):
            self._ui["hud"].show_warning("Game saved to slot %d." % (self.current_slot + 1))

    # ----------------------------------------------------------- game loop

    def _game_task(self, task):
        dt = min(globalClock.getDt(), 0.1)
        gm = self.gm
        if self.paused or any(self._ui[k].visible for k in ("inventory", "crafting", "map")):
            return task.cont
        events = gm.tick(dt)
        for ev in events:
            self._handle_event(ev)
        if not self.in_menu and self.controller:
            self.controller.update(dt)
            cam_pos = self.camera.get_pos() if self.camera is not None else gm.player
            self.renderer.update(dt, cam_pos)
            self.renderer.update_tree_visibility(cam_pos)
            if self.building:
                self.building.update_preview()
            self._ui["hud"].update(dt)
            self._ui["hud"].set_prompt(self._interaction_prompt())
            if gm.day_night.is_night():
                self.audio.set_ambience("ambience_night")
            else:
                self.audio.set_ambience("ambience_day")
            if gm.weather.is_wet:
                self.audio.set_ambience("rain")
        if gm.finished:
            self._ui["result"].show(gm)
            self.save_profile()
            self.controller.frozen = True
            return task.done
        return task.cont

    def _handle_event(self, ev):
        kind = ev.get("type")
        hud = self._ui.get("hud")
        if hud is None:
            return
        if kind == "night_start":
            hud.show_warning("Night %d falls. Stay within the campfire's light!" % ev["night"], 5)
            self.audio.play("growl")
        elif kind == "new_day":
            hud.show_warning("Day %d begins." % ev["day"])
            self.save_game()
        elif kind == "fuel_low":
            hud.show_warning("The campfire is running low on fuel!")
        elif kind == "fuel_critical":
            hud.show_warning("The fire is about to go out!")
        elif kind == "campfire_out":
            hud.show_warning("The campfire has gone out! Relight it with fuel!")
            self.audio.play("warning")
        elif kind == "starving":
            hud.show_warning("You are starving. Eat something!")
        elif kind == "spotted":
            hud.show_warning("Something has spotted you...")
            self.audio.play("growl")
        elif kind == "attack":
            hud.show_warning("You were attacked! Get to the campfire!", 2)
            self.audio.play("warning")
        elif kind == "ram_charge":
            hud.show_warning("The Ram is charging!")
        elif kind == "defeat":
            self.audio.play("defeat")
        elif kind == "victory":
            self.audio.play("victory")


if __name__ == "__main__":
    try:
        app = ForestGame()
        app.run()
    except Exception:
        import traceback
        tb = traceback.format_exc()
        log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "error.log")
        try:
            with open(log_path, "w", encoding="utf-8") as f:
                f.write(tb)
        except OSError:
            pass
        print("\n=== The game crashed. The full error was saved to: ===\n%s\n=== Please share the contents of error.log. ===\n" % log_path)
        print(tb)
        input("Press Enter to close...")
