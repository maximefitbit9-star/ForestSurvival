"""Pure-logic inventory with stacking, moving, splitting and storage."""
import random


class InventorySlot:
    def __init__(self, item_id, quantity):
        self.item_id = item_id
        self.quantity = quantity

    def is_empty(self):
        return self.item_id is None or self.quantity <= 0


class Inventory:
    def __init__(self, gamedata, size=24):
        self.gd = gamedata
        self.size = size
        self.slots = [InventorySlot(None, 0) for _ in range(size)]

    def stack_limit(self, item_id):
        if not self.gd.has_item(item_id):
            return 1
        return self.gd.item(item_id).get("stack", 1)

    def count(self, item_id):
        return sum(s.quantity for s in self.slots if s.item_id == item_id)

    def free_slots(self):
        return sum(1 for s in self.slots if s.is_empty())

    def used_slots(self):
        return sum(1 for s in self.slots if not s.is_empty())

    def add(self, item_id, quantity=1):
        """Adds items, filling partial stacks first. Returns the amount added."""
        if quantity <= 0 or not self.gd.has_item(item_id):
            return 0
        added = 0
        limit = self.stack_limit(item_id)
        for slot in self.slots:
            if slot.item_id == item_id and slot.quantity < limit:
                take = min(limit - slot.quantity, quantity - added)
                slot.quantity += take
                added += take
                if added >= quantity:
                    return added
        for slot in self.slots:
            if slot.is_empty():
                take = min(limit, quantity - added)
                slot.item_id = item_id
                slot.quantity = take
                added += take
                if added >= quantity:
                    return added
        return added

    def remove(self, item_id, quantity=1):
        """Removes items. Returns the amount actually removed."""
        if self.count(item_id) < quantity:
            return 0
        remaining = quantity
        for slot in self.slots:
            if slot.item_id == item_id:
                take = min(slot.quantity, remaining)
                slot.quantity -= take
                remaining -= take
                if slot.quantity <= 0:
                    slot.item_id = None
                if remaining <= 0:
                    break
        return quantity - remaining

    def has(self, requirements):
        """requirements: dict of item_id -> quantity."""
        return all(self.count(i) >= q for i, q in requirements.items())

    def consume(self, requirements):
        if not self.has(requirements):
            return False
        for item_id, qty in requirements.items():
            self.remove(item_id, qty)
        return True

    def move(self, from_idx, to_idx):
        if not (0 <= from_idx < self.size and 0 <= to_idx < self.size) or from_idx == to_idx:
            return False
        src, dst = self.slots[from_idx], self.slots[to_idx]
        if dst.is_empty():
            self.slots[from_idx], self.slots[to_idx] = dst, src
            return True
        if src.item_id == dst.item_id:
            limit = self.stack_limit(src.item_id)
            take = min(limit - dst.quantity, src.quantity)
            if take <= 0:
                return False
            dst.quantity += take
            src.quantity -= take
            if src.quantity <= 0:
                src.item_id = None
            return True
        self.slots[from_idx], self.slots[to_idx] = dst, src
        return True

    def split(self, index):
        """Splits a stack in half into the first free slot. Returns the new slot index or None."""
        slot = self.slots[index]
        if slot.is_empty() or slot.quantity < 2:
            return None
        half = slot.quantity // 2
        for i, other in enumerate(self.slots):
            if other.is_empty():
                other.item_id = slot.item_id
                other.quantity = half
                slot.quantity -= half
                return i
        return None

    def use(self, index):
        """Uses a consumable item (food or medical). Returns an effects dict or None."""
        slot = self.slots[index]
        if slot.is_empty():
            return None
        item = self.gd.item(slot.item_id)
        effects = None
        if "food" in item:
            effects = dict(item["food"])
        elif "use" in item:
            effects = dict(item["use"])
        if effects is not None:
            self.remove(slot.item_id, 1)
        return effects

    def clear(self):
        for slot in self.slots:
            slot.item_id = None
            slot.quantity = 0

    def to_dict(self):
        return [{"id": s.item_id, "qty": s.quantity} for s in self.slots]

    def from_dict(self, data):
        self.clear()
        for i, entry in enumerate(data[: self.size]):
            self.slots[i].item_id = entry.get("id")
            self.slots[i].quantity = int(entry.get("qty", 0))

    def random_loot_rolls(self):
        return random
