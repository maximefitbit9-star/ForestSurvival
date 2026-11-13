"""Class system: diamond purchases persist across runs in the player profile."""


class ClassSystem:
    def __init__(self, gamedata, profile):
        self.gd = gamedata
        self.profile = profile

    def all_classes(self):
        return self.gd.classes["classes"]

    def is_owned(self, class_id):
        return class_id in self.profile.get("owned_classes", ["camper"])

    def price(self, class_id):
        return self.gd.class_data(class_id)["price"]

    def can_buy(self, class_id):
        return not self.is_owned(class_id) and self.profile.get("diamonds", 0) >= self.price(class_id)

    def buy(self, class_id):
        if not self.can_buy(class_id):
            return False
        self.profile["diamonds"] -= self.price(class_id)
        self.profile.setdefault("owned_classes", ["camper"])
        if class_id not in self.profile["owned_classes"]:
            self.profile["owned_classes"].append(class_id)
        return True

    def starting_items(self, class_id):
        return self.gd.class_data(class_id).get("starting_items", {})

    def passives(self, class_id):
        return self.gd.class_data(class_id).get("passives", {})
