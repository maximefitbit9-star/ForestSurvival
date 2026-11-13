"""Bundles the game's JSON configs into web/vendor-config.js for the browser build.

Run: python tools/gen_web_config.py
"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG = os.path.join(ROOT, "config")
OUT = os.path.join(ROOT, "web", "js", "config.js")


def main():
    parts = ["// Auto-generated from config/*.json - do not edit by hand.", "const GD = {"]
    for name in ("items", "recipes", "classes", "loot_tables", "progression", "settings"):
        with open(os.path.join(CONFIG, name + ".json"), "r", encoding="utf-8") as f:
            data = json.load(f)
        parts.append("  %s: %s," % (name, json.dumps(data)))
    parts.append("};")
    parts.append("if (typeof module !== 'undefined') { module.exports = { GD }; }")
    with open(OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(parts) + "\n")
    print("Wrote", OUT, os.path.getsize(OUT), "bytes")


if __name__ == "__main__":
    main()
