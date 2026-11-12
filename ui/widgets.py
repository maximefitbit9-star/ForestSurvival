"""Shared DirectGui widget helpers and the game's visual theme."""
from direct.gui.DirectFrame import DirectFrame
from direct.gui.DirectButton import DirectButton
from direct.gui.DirectLabel import DirectLabel

THEME = {
    "bg": (0.06, 0.09, 0.07, 0.9),
    "panel": (0.08, 0.12, 0.09, 0.95),
    "accent": (0.35, 0.65, 0.35, 1),
    "text": (0.92, 0.95, 0.9, 1),
    "warning": (0.95, 0.6, 0.2, 1),
    "danger": (0.9, 0.25, 0.2, 1),
}


def make_button(text, command, parent, pos, extra_args=None, scale=0.05, width=12):
    return DirectButton(
        text=text, command=command, extraArgs=extra_args or [],
        parent=parent, pos=pos, scale=scale,
        frameColor=(THEME["bg"][:3] + (0.85,), THEME["accent"][:3] + (1,), (0.2, 0.4, 0.2, 1), THEME["bg"][:3] + (0.95,)),
        text_fg=THEME["text"], text_scale=1.0, textMayChange=0,
        pressEffect=1, frameSize=(-width / 2, width / 2, -0.8, 1.0))


def make_label(text, parent, pos, scale=0.05, colour=None, align=None):
    kwargs = {}
    if align is not None:
        kwargs["text_align"] = align
    return DirectLabel(text=text, parent=parent, pos=pos, scale=scale,
                       text_fg=colour or THEME["text"], frameColor=(0, 0, 0, 0), **kwargs)


def make_panel(parent, pos, size, frame_colour=None):
    left, right, bottom, top = size
    return DirectFrame(parent=parent, pos=pos, frameColor=frame_colour or THEME["panel"],
                       frameSize=(left, right, bottom, top))


def make_progress_bar(parent, pos, width=1.2, height=0.06):
    bg = DirectFrame(parent=parent, pos=pos, frameColor=(0.1, 0.1, 0.1, 0.9),
                     frameSize=(0, width, 0, height))
    fill = DirectFrame(parent=bg, pos=(0, 0, 0), frameColor=THEME["accent"],
                       frameSize=(0, width, 0, height))
    return bg, fill


def set_bar(fill, fraction, width=1.2):
    fraction = max(0.0, min(1.0, fraction))
    fill["frameSize"] = (0, width * fraction, 0, fill["frameSize"][3])
