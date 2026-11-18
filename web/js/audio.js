// Web Audio synthesised sound effects - no audio files needed, fully offline.
"use strict";

const AudioSys = {
  ctx: null,
  soundVolume: 0.8,
  musicVolume: 0.5,
  ambienceNodes: null,
  ambienceName: null,

  init() {
    if (this.ctx) return;
    try {
      const Ctx = window.AudioContext || window.webkitAudioContext;
      if (!Ctx) return;
      this.ctx = new Ctx();
    } catch (e) { this.ctx = null; }
  },
  resume() { if (this.ctx && this.ctx.state === "suspended") this.ctx.resume(); },

  _tone(freq, duration, type, volume, when) {
    const ctx = this.ctx;
    if (!ctx) return;
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.type = type || "sine";
    osc.frequency.value = freq;
    const t = (when || 0);
    gain.gain.setValueAtTime(0.0001, ctx.currentTime + t);
    gain.gain.exponentialRampToValueAtTime(volume, ctx.currentTime + t + 0.01);
    gain.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + t + duration);
    osc.connect(gain).connect(ctx.destination);
    osc.start(ctx.currentTime + t);
    osc.stop(ctx.currentTime + t + duration + 0.05);
  },

  _noise(duration, volume, filterFreq) {
    const ctx = this.ctx;
    if (!ctx) return;
    const n = Math.floor(ctx.sampleRate * duration);
    const buffer = ctx.createBuffer(1, n, ctx.sampleRate);
    const data = buffer.getChannelData(0);
    for (let i = 0; i < n; i++) data[i] = Math.random() * 2 - 1;
    const src = ctx.createBufferSource();
    src.buffer = buffer;
    const filter = ctx.createBiquadFilter();
    filter.type = "lowpass";
    filter.frequency.value = filterFreq || 800;
    const gain = ctx.createGain();
    gain.gain.setValueAtTime(volume, ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + duration);
    src.connect(filter).connect(gain).connect(ctx.destination);
    src.start();
  },

  play(name, volume) {
    if (!this.ctx) return;
    this.resume();
    const v = (volume == null ? 1 : volume) * this.soundVolume;
    switch (name) {
      case "chop": this._tone(90, 0.08, "square", 0.25 * v); this._noise(0.1, 0.2 * v, 600); break;
      case "tree_fall": this._noise(0.8, 0.35 * v, 300); this._tone(60, 0.4, "sine", 0.3 * v); break;
      case "collect": this._tone(660, 0.06, "sine", 0.2 * v); this._tone(990, 0.08, "sine", 0.2 * v, 0.06); break;
      case "craft": this._tone(440, 0.08, "sine", 0.2 * v); this._tone(550, 0.08, "sine", 0.2 * v, 0.08);
        this._tone(660, 0.1, "sine", 0.2 * v, 0.16); break;
      case "build": this._tone(220, 0.1, "square", 0.2 * v); this._noise(0.15, 0.2 * v, 500); break;
      case "menu_click": this._tone(880, 0.05, "sine", 0.15 * v); break;
      case "warning": this._tone(330, 0.15, "sine", 0.25 * v); this._tone(330, 0.15, "sine", 0.25 * v, 0.2); break;
      case "thunder": this._noise(2.5, 0.7 * v, 200); break;
      case "rescue": this._tone(523, 0.12, "sine", 0.25 * v); this._tone(659, 0.12, "sine", 0.25 * v, 0.12);
        this._tone(784, 0.2, "sine", 0.25 * v, 0.24); break;
      case "victory": [523, 659, 784, 1046].forEach((f, i) => this._tone(f, 0.3, "sine", 0.3 * v, i * 0.15)); break;
      case "defeat": [300, 250, 180].forEach((f, i) => this._tone(f, 0.4, "sine", 0.3 * v, i * 0.35)); break;
      case "growl": this._tone(70, 0.6, "sawtooth", 0.2 * v); break;
      case "birds": [1800, 2400, 2100].forEach((f, i) => this._tone(f, 0.07, "sine", 0.1 * v, i * 0.15)); break;
    }
  },

  setAmbience(name) {
    if (this.ambienceName === name) return;
    this.stopAmbience();
    if (!this.ctx || this.musicVolume <= 0) { this.ambienceName = name; return; }
    const ctx = this.ctx;
    const n = Math.floor(ctx.sampleRate * 4);
    const buffer = ctx.createBuffer(1, n, ctx.sampleRate);
    const data = buffer.getChannelData(0);
    let v = 0;
    for (let i = 0; i < n; i++) {
      v = v * 0.97 + (Math.random() * 2 - 1) * 0.03;
      data[i] = v;
    }
    const src = ctx.createBufferSource();
    src.buffer = buffer;
    src.loop = true;
    const filter = ctx.createBiquadFilter();
    filter.type = "lowpass";
    filter.frequency.value = name === "rain" ? 2500 : (name === "night" ? 300 : 700);
    const gain = ctx.createGain();
    gain.gain.value = (name === "rain" ? 0.35 : 0.18) * this.musicVolume;
    src.connect(filter).connect(gain).connect(ctx.destination);
    src.start();
    this.ambienceNodes = { src, gain };
    this.ambienceName = name;
  },

  stopAmbience() {
    if (this.ambienceNodes) {
      try { this.ambienceNodes.src.stop(); } catch (e) { /* already stopped */ }
      this.ambienceNodes = null;
    }
    this.ambienceName = null;
  },

  setVolumes(sound, music) {
    this.soundVolume = sound;
    this.musicVolume = music;
    if (this.ambienceNodes) this.ambienceNodes.gain.gain.value = 0.18 * music;
  },
};

if (typeof module !== "undefined") module.exports = { AudioSys };
