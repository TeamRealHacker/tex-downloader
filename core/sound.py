"""Sound effects for Tex — small synthesized WAVs played via QSoundEffect.

Each sound starts with a 1-2 ms noise transient (the "click" attack of a
real UI sound) followed by a tonal body with a percussive exponential
decay. Pure sine waves are mixed with subtle harmonics and a slight
detune for body. Sounds are **normalized to peak amplitude** so the
perceived volume is consistent across the palette.

All sounds are 16-bit mono @ 22050 Hz. Total palette: ~30 KB.

  tick:    25 ms, 1700 Hz.  Sharp nav-tap.
  fetch:   90 ms, 600 -> 850 Hz.  Soft ascending pop on URL received.
  queue:   45 ms, 1400 Hz.  Bright tap on item added.
  done:   220 ms, 880 + 1320 Hz (chime).  Bell-like "ding".
  error:  170 ms, 240 -> 200 Hz.  Low soft thud with noisy attack.

The ``enabled`` flag is a hard kill-switch; ``play()`` is a no-op when off.
"""
from __future__ import annotations

import math
import random
import struct
import wave
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QUrl
from PySide6.QtMultimedia import QSoundEffect

import sys as _sys

def _assets_dir() -> Path:
    """Resolve the assets/ directory — works in dev and PyInstaller frozen mode."""
    if getattr(_sys, "frozen", False):
        if hasattr(_sys, "_MEIPASS"):
            # PyInstaller --onefile: assets extracted to temp _MEIPASS dir.
            return Path(_sys._MEIPASS) / "assets"
        # PyInstaller --onedir: assets/ lives next to the EXE.
        return Path(_sys.executable).resolve().parent / "assets"
    return Path(__file__).resolve().parent.parent / "assets"

ASSETS = _assets_dir()
SOUNDS_DIR = ASSETS / "sounds"

# (filename, freq, freq_end, duration_ms, decay_tau, click_gain, body)
#   decay_tau : exponential time constant in seconds (smaller = faster decay)
#   click_gain: 0..1, strength of the initial noise transient
#   body      : "sine" | "bell" | "thud"
SOUND_DEFS: list[tuple[str, float, float, int, float, float, str]] = [
    ("tick.wav",  1700.0, 1700.0,  25, 0.012, 0.45, "sine"),
    ("fetch.wav",  600.0,  850.0,  90, 0.040, 0.30, "sine"),
    ("queue.wav", 1400.0, 1400.0,  45, 0.018, 0.40, "sine"),
    ("done.wav",   880.0, 1320.0, 220, 0.080, 0.20, "bell"),
    ("error.wav",  240.0,  200.0, 170, 0.050, 0.55, "thud"),
]

SAMPLE_RATE = 22050
TWO_PI = 2.0 * math.pi


def _body_sample(n: int, total: int, freq: float, freq_end: float,
                 body: str, decay_tau: float) -> float:
    """Compute one sample of the tonal body.

    Linear frequency sweep. Subtle harmonics for body. Exponential
    envelope with no soft attack (sharp transient).
    """
    t = n / SAMPLE_RATE
    if freq_end == freq:
        f = freq
    else:
        f = freq + (freq_end - freq) * (n / total)
    phase = TWO_PI * f * t
    if body == "bell":
        s = (math.sin(phase)
             + 0.35 * math.sin(2.0 * phase)
             + 0.15 * math.sin(3.0 * phase))
    elif body == "thud":
        s = (math.sin(phase)
             + 0.40 * math.sin(1.5 * phase)
             + 0.20 * math.sin(2.0 * phase))
    else:  # sine
        s = math.sin(phase) + 0.20 * math.sin(2.0 * phase)
    return s * math.exp(-t / decay_tau)


def _click_sample(n: int, click_ms: float, click_gain: float,
                  rng: random.Random) -> float:
    """A 0..1 envelope for a short noise click that dies in ``click_ms``."""
    t = n / SAMPLE_RATE
    if t > click_ms / 1000.0:
        return 0.0
    env = (1.0 - t / (click_ms / 1000.0)) ** 2
    return env * click_gain * (rng.random() * 2.0 - 1.0)


def _synthesize(path: Path, freq: float, freq_end: float, duration_ms: int,
                decay_tau: float, click_gain: float, body: str) -> None:
    """Write a tiny mono WAV to ``path`` with sharp attack and exp decay."""
    total = max(2, int(SAMPLE_RATE * duration_ms / 1000.0))
    click_samples = int(2.0 * SAMPLE_RATE / 1000.0)  # 2 ms click
    rng = random.Random(hash(str(path)) & 0xFFFFFFFF)

    is_chime = (body == "bell") and (freq_end != freq) and duration_ms > 100
    if is_chime:
        # Two-note chime. Each note gets a fresh decay envelope starting at t=0.
        half = total // 2
        samples: list[float] = []
        # Note 1
        for n in range(half):
            t = n / SAMPLE_RATE
            s = (math.sin(TWO_PI * freq * t)
                 + 0.35 * math.sin(TWO_PI * freq * 2.0 * t)
                 + 0.15 * math.sin(TWO_PI * freq * 3.0 * t))
            samples.append(s * math.exp(-t / decay_tau))
            if n < click_samples:
                samples[-1] += _click_sample(n, 2.0, click_gain, rng)
        # Note 2 (slightly softer and faster decay)
        for n in range(total - half):
            t = n / SAMPLE_RATE
            s = (math.sin(TWO_PI * freq_end * t)
                 + 0.30 * math.sin(TWO_PI * freq_end * 2.0 * t))
            samples.append(s * math.exp(-t / (decay_tau * 0.7)) * 0.85)
    else:
        samples = []
        for n in range(total):
            s = _body_sample(n, total, freq, freq_end, body, decay_tau)
            if n < click_samples:
                s += _click_sample(n, 2.0, click_gain, rng)
            samples.append(s)

    # Normalize so the peak is 0.9 of full scale (headroom to avoid clipping).
    peak = max((abs(s) for s in samples), default=1.0) or 1.0
    norm = 0.9 / peak

    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SAMPLE_RATE)
        frames = bytearray()
        for s in samples:
            v = s * norm
            if v > 1.0:
                v = 1.0
            elif v < -1.0:
                v = -1.0
            frames += struct.pack("<h", int(v * 32767))
        w.writeframes(bytes(frames))


def _ensure_sounds() -> None:
    """Generate missing sound files. Cheap; only runs once."""
    SOUNDS_DIR.mkdir(parents=True, exist_ok=True)
    for name, f, f_end, dur, decay_tau, click_gain, body in SOUND_DEFS:
        path = SOUNDS_DIR / name
        if not path.exists() or path.stat().st_size < 100:
            try:
                _synthesize(path, f, f_end, dur, decay_tau, click_gain, body)
            except Exception:
                pass


class SoundManager:
    """Plays the small set of Tex UI sounds. All methods are no-ops if disabled.

    Sounds are preloaded at startup (not on first play) so there is no
    stutter the first time the user pastes a URL.
    """

    def __init__(self, enabled: bool = True):
        self._enabled = enabled
        self._effects: dict[str, QSoundEffect] = {}
        self._preload()

    def set_enabled(self, on: bool) -> None:
        self._enabled = bool(on)

    def is_enabled(self) -> bool:
        return self._enabled

    def _preload(self) -> None:
        _ensure_sounds()
        for name, *_ in SOUND_DEFS:
            path = SOUNDS_DIR / name
            if not path.exists():
                continue
            eff = QSoundEffect()
            eff.setSource(QUrl.fromLocalFile(str(path)))
            eff.setVolume(0.95)
            self._effects[name] = eff

    def play(self, name: str) -> None:
        """Play a sound by filename stem (e.g. 'done'). No-op if disabled or missing.
        Does not cut off the same sound if already playing — allows overlapping
        notifications when multiple downloads finish at once."""
        if not self._enabled:
            return
        eff: Optional[QSoundEffect] = self._effects.get(name + ".wav") or self._effects.get(name)
        if eff is None:
            return
        try:
            if not eff.isPlaying():
                eff.play()
        except Exception:
            pass
