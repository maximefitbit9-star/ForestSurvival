"""Robust save system: atomic JSON writes, three slots, and a persistent profile."""
import json
import os
import tempfile
import time

SAVE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "saves")
PROFILE_PATH = os.path.join(SAVE_DIR, "profile.json")


def _atomic_write(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except Exception:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise


def _safe_read(path, default):
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        backup = path + ".corrupt"
        try:
            os.replace(path, backup)
        except OSError:
            pass
        return default


class SaveSystem:
    SLOTS = 3

    def __init__(self, save_dir=None, profile_path=None):
        self.save_dir = save_dir or SAVE_DIR
        self.profile_path = profile_path or PROFILE_PATH
        os.makedirs(self.save_dir, exist_ok=True)

    def slot_path(self, slot):
        return os.path.join(self.save_dir, "slot_%d.json" % slot)

    def slot_info(self, slot):
        data = _safe_read(self.slot_path(slot), None)
        if data is None:
            return None
        return {
            "day": data.get("day", 1),
            "class": data.get("class", "camper"),
            "children_rescued": sum(1 for c in data.get("children", {}).values() if c.get("rescued")),
            "campfire_level": data.get("campfire", {}).get("level", 1),
            "saved_at": data.get("saved_at", 0),
        }

    def save(self, slot, state):
        state = dict(state)
        state["saved_at"] = time.time()
        state["version"] = 1
        _atomic_write(self.slot_path(slot), state)
        return True

    def load(self, slot):
        return _safe_read(self.slot_path(slot), None)

    def delete(self, slot):
        path = self.slot_path(slot)
        if os.path.exists(path):
            os.remove(path)
            return True
        return False

    def load_profile(self):
        profile = _safe_read(self.profile_path, None)
        if profile is None:
            profile = {"diamonds": 0, "owned_classes": ["camper"], "best_day": 0, "wins": 0, "runs": 0}
        profile.setdefault("diamonds", 0)
        profile.setdefault("owned_classes", ["camper"])
        return profile

    def save_profile(self, profile):
        _atomic_write(self.profile_path, profile)
