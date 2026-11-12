"""End-of-run diamond rewards. Configurable formula; diamonds persist in the profile."""


def compute_diamonds(progression, nights_survived, children_rescued, locations_discovered,
                     campfire_level, victory):
    cfg = progression["diamonds"]
    total = 0
    total += nights_survived * cfg["per_night_survived"]
    total += children_rescued * cfg["per_child_rescued"]
    total += locations_discovered * cfg["per_location_discovered"]
    total += (campfire_level - 1) * cfg["campfire_level_bonus"]
    if victory:
        total += cfg["victory_bonus"]
    return int(total)
