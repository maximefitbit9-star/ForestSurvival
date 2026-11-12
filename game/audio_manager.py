"""Audio manager: loads synthesised WAVs, applies volumes, handles ambience loops."""
import math
import os

from panda3d.core import AudioSound

AUDIO_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "audio")


class AudioManager:
    def __init__(self, sound_volume=0.8, music_volume=0.5, loader=None):
        self.loader = loader
        self.sound_volume = sound_volume
        self.music_volume = music_volume
        self.sounds = {}
        self.ambience = None
        self._ambience_name = None
        self._scan()

    def _scan(self):
        if not os.path.isdir(AUDIO_DIR):
            return
        for name in os.listdir(AUDIO_DIR):
            if name.endswith(".wav") and self.loader is not None:
                self.sounds[os.path.splitext(name)[0]] = self.loader.loadSfx(os.path.join(AUDIO_DIR, name))

    def has(self, name):
        return name in self.sounds

    def play(self, name, volume=1.0):
        sound = self.sounds.get(name)
        if sound is None:
            return
        if sound.status() == AudioSound.PLAYING and name.startswith("ambience"):
            return
        sound.setVolume(volume * self.sound_volume)
        sound.play()

    def play_at(self, name, source_pos, listener_pos, volume=1.0):
        """Distance-attenuated playback: a lightweight stand-in for full 3D audio."""
        d = math.hypot(source_pos[0] - listener_pos[0], source_pos[1] - listener_pos[1])
        falloff = max(0.0, 1.0 - d / 60.0)
        if falloff <= 0:
            return
        self.play(name, volume * falloff)

    def set_ambience(self, name):
        if self._ambience_name == name:
            return
        if self.ambience is not None:
            self.ambience.stop()
        sound = self.sounds.get(name)
        if sound is None:
            self.ambience = None
            self._ambience_name = None
            return
        sound.setLoop(True)
        sound.setVolume(self.music_volume)
        sound.play()
        self.ambience = sound
        self._ambience_name = name

    def set_volumes(self, sound_volume, music_volume):
        self.sound_volume = sound_volume
        self.music_volume = music_volume
        if self.ambience is not None:
            self.ambience.setVolume(music_volume)

    def stop_all(self):
        for sound in self.sounds.values():
            sound.stop()
        self.ambience = None
        self._ambience_name = None
