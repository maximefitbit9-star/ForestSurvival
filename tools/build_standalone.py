"""Builds web/standalone.html - the entire game in one self-contained file.

CSS, Three.js and all game scripts are inlined, so the file works when it is
opened from anywhere (even after being moved or copied alone) and needs no
folder structure, no server and no network. Run:

    python tools/build_standalone.py
"""
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEB = os.path.join(ROOT, "web")

SCRIPTS = [
    "vendor/three.min.js",
    "js/config.js",
    "js/logic.js",
    "js/audio.js",
    "js/render.js",
    "js/controls.js",
    "js/ui.js",
    "js/main.js",
]


def main():
    with open(os.path.join(WEB, "index.html"), "r", encoding="utf-8") as f:
        html = f.read()

    # Inline the stylesheet.
    css_path = os.path.join(WEB, "css", "style.css")
    with open(css_path, "r", encoding="utf-8") as f:
        css = f.read()
    html = re.sub(
        r'<link rel="stylesheet" href="css/style.css">',
        lambda m: "<style>\n" + css + "\n</style>",
        html,
    )

    # Inline every script, in order.
    parts = []
    for rel in SCRIPTS:
        with open(os.path.join(WEB, rel), "r", encoding="utf-8") as f:
            src = f.read()
        parts.append('<script>\n// ---- inlined from %s ----\n%s\n</script>' % (rel, src))

    # Replace the original script tags (in order) with the inlined blocks.
    inlined = iter(parts)
    for rel in SCRIPTS:
        tag = re.search(r'<script src="%s"></script>' % re.escape(rel), html)
        if not tag:
            raise SystemExit("missing script tag for " + rel)
        html = html[: tag.start()] + next(inlined) + html[tag.end():]

    out_path = os.path.join(WEB, "standalone.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    print("Wrote", out_path, os.path.getsize(out_path), "bytes")


if __name__ == "__main__":
    main()
