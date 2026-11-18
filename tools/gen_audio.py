"""Synthesises original WAV sound effects and ambience into assets/audio.

Run manually: python tools/gen_audio.py
The game also auto-generates missing files on first launch.
"""
import math
import os
import random
import struct
import wave

AUDIO_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "audio")
RATE = 22050


def _write(name, samples, volume=0.8):
    os.makedirs(AUDIO_DIR, exist_ok=True)
    path = os.path.join(AUDIO_DIR, name)
    with wave.open(path, "w") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(RATE)
        frames = b"".join(struct.pack("<h", int(max(-1.0, min(1.0, s)) * 32767 * volume)) for s in samples)
        f.writeframes(frames)
    return path


def _silence(duration):
    return [0.0] * int(RATE * duration)


def _tone(freq, duration, fade=True, wave_type="sine"):
    n = int(RATE * duration)
    out = []
    for i in range(n):
        t = i / RATE
        if wave_type == "sine":
            v = math.sin(2 * math.pi * freq * t)
        else:
            v = math.sin(2 * math.pi * freq * t) + 0.4 * math.sin(4 * math.pi * freq * t)
        env = min(1.0, i / (RATE * 0.01)) if fade else 1.0
        env *= 1 - (i / n) ** 1.5
        out.append(v * env)
    return out


def _noise(duration, low_pass=0.2, seed=3):
    rng = random.Random(seed)
    n = int(RATE * duration)
    out = []
    v = 0.0
    for _ in range(n):
        v = v * (1 - low_pass) + rng.uniform(-1, 1) * low_pass
        out.append(v)
    return out


def _mix(*tracks):
    length = max(len(t) for t in tracks)
    return [sum(t[i] if i < len(t) else 0.0 for t in tracks) for i in range(length)]


def _concat(*tracks):
    out = []
    for t in tracks:
        out.extend(t)
    return out


def generate_all():
    files = {}
    files["wind.ogg"] = None
    rng = random.Random(99)
    ambience = _noise(8.0, 0.05, seed=7)
    files["ambience_day.wav"] = _write("ambience_day.wav",
        [s * 0.3 + 0.1 * math.sin(2 * math.pi * 0.05 * i / RATE) for i, s in enumerate(ambience)])
    files["ambience_night.wav"] = _write("ambience_night.wav",
        [s * 0.22 + 0.15 * math.sin(2 * math.pi * 0.02 * i / RATE) for i, s in enumerate(_noise(8.0, 0.03, seed=8))])
    files["rain.wav"] = _write("rain.wav", [s * 0.5 for s in _noise(6.0, 0.5, seed=9)])
    files["fire.wav"] = _write("fire.wav",
        [s * 0.4 * (0.7 + 0.3 * math.sin(2 * math.pi * 3 * i / RATE)) for i, s in enumerate(_noise(4.0, 0.3, seed=10))])
    chop = _concat(_tone(90, 0.05, wave_type="square"), _noise(0.12, 0.6, seed=11))
    files["chop.wav"] = _write("chop.wav", chop)
    files["tree_fall.wav"] = _write("tree_fall.wav", _concat(_noise(0.8, 0.15, seed=12), _tone(60, 0.4)))
    files["collect.wav"] = _write("collect.wav", _concat(_tone(660, 0.06), _tone(990, 0.08)))
    files["craft.wav"] = _write("craft.wav", _concat(_tone(440, 0.08), _tone(550, 0.08), _tone(660, 0.1)))
    files["build.wav"] = _write("build.wav", _concat(_tone(220, 0.1, wave_type="square"), _noise(0.15, 0.4, seed=13)))
    files["menu_click.wav"] = _write("menu_click.wav", _tone(880, 0.05))
    files["thunder.wav"] = _write("thunder.wav", [s * (1 - i / len(_noise(2.5, 0.1, seed=14))) * 1.2
                                                  for i, s in enumerate(_noise(2.5, 0.1, seed=14))])
    files["warning.wav"] = _write("warning.wav", _concat(_tone(330, 0.15), _silence(0.05), _tone(330, 0.15)))
    files["rescue.wav"] = _write("rescue.wav", _concat(_tone(523, 0.12), _tone(659, 0.12), _tone(784, 0.2)))
    files["victory.wav"] = _write("victory.wav", _concat(_tone(523, 0.15), _tone(659, 0.15), _tone(784, 0.15), _tone(1046, 0.4)))
    files["defeat.wav"] = _write("defeat.wav", _concat(_tone(300, 0.3), _tone(250, 0.3), _tone(180, 0.5)))
    chirps = []
    for _ in range(6):
        f = rng.uniform(1800, 3200)
        chirps = _concat(chirps, _tone(f, 0.07), _silence(rng.uniform(0.1, 0.4)))
    files["birds.wav"] = _write("birds.wav", chirps)
    files["growl.wav"] = _write("growl.wav", [s * 0.5 for s in _noise(0.7, 0.08, seed=15)])
    return {k: v for k, v in files.items() if v}


if __name__ == "__main__":
    made = generate_all()
    print("Generated %d audio files in %s" % (len(made), AUDIO_DIR))
