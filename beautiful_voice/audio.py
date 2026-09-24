"""Microphone capture at 16 kHz mono, plus the short UI chimes."""

from __future__ import annotations

import threading
from typing import Callable

import numpy as np
import sounddevice as sd

from .segmenter import SAMPLE_RATE, rms_db

BLOCK = 480  # 30 ms at 16 kHz


def list_input_devices() -> list[dict]:
    """Input devices of the default host API, without duplicates."""
    try:
        devices = sd.query_devices()
        default_api = sd.default.hostapi
        default_in = sd.default.device[0]
    except Exception:
        return []
    seen: set[str] = set()
    result = []
    for index, dev in enumerate(devices):
        if dev["max_input_channels"] < 1 or dev["hostapi"] != default_api:
            continue
        name = dev["name"].strip()
        if name in seen:
            continue
        seen.add(name)
        result.append({"name": name, "index": index, "isDefault": index == default_in})
    return result


def _resolve_device(name: str) -> int | None:
    if not name:
        return None
    for dev in list_input_devices():
        if dev["name"] == name:
            return dev["index"]
    return None  # the saved microphone is gone; fall back to the default


def level_from_db(db: float) -> float:
    """Map dBFS to 0..1 for the voice bars: -55 dB is silence, -12 dB is loud."""
    return float(min(1.0, max(0.0, (db + 55.0) / 43.0)))


class _Resampler:
    """Streaming resampler for devices that refuse to open at 16 kHz."""

    def __init__(self, src_rate: float, dst_rate: float = SAMPLE_RATE) -> None:
        self.step = src_rate / dst_rate
        self.width = max(1, int(round(self.step)))  # box filter against aliasing
        self.pos = 0.0
        self.tail = np.zeros(0, dtype=np.float32)

    def __call__(self, x: np.ndarray) -> np.ndarray:
        buf = np.concatenate([self.tail, x])
        if self.width > 1:
            kernel = np.ones(self.width, dtype=np.float32) / self.width
            smooth = np.convolve(buf, kernel, mode="same")
        else:
            smooth = buf
        last = len(buf) - 1 - self.width  # keep a margin so the filter edge is never used
        if last < self.pos:
            self.tail = buf
            return np.zeros(0, dtype=np.float32)
        n = int((last - self.pos) // self.step) + 1
        idx = self.pos + np.arange(n) * self.step
        out = np.interp(idx, np.arange(len(buf)), smooth).astype(np.float32)
        nxt = self.pos + n * self.step
        keep = max(0, int(nxt) - self.width)
        self.tail = buf[keep:]
        self.pos = nxt - keep
        return out


class Recorder:
    """Records the microphone and hands every 30 ms block to ``on_block``.

    ``on_block(samples, level)`` runs on the audio thread: keep it quick.
    """

    def __init__(self, on_block: Callable[[np.ndarray, float], None]) -> None:
        self.on_block = on_block
        self._stream: sd.InputStream | None = None
        self._chunks: list[np.ndarray] = []
        self._lock = threading.Lock()
        self._resample: _Resampler | None = None

    @property
    def active(self) -> bool:
        return self._stream is not None

    def _callback(self, indata, frames, time_info, status) -> None:  # noqa: ARG002
        samples = indata[:, 0].copy()
        if self._resample is not None:
            samples = self._resample(samples)
            if not samples.size:
                return
        with self._lock:
            self._chunks.append(samples)
        try:
            self.on_block(samples, level_from_db(rms_db(samples)))
        except Exception:  # never let a UI hiccup kill the audio stream
            pass

    def start(self, device_name: str = "") -> None:
        if self._stream is not None:
            return
        device = _resolve_device(device_name)
        self._chunks = []
        self._resample = None
        try:
            stream = sd.InputStream(
                samplerate=SAMPLE_RATE, blocksize=BLOCK, channels=1, dtype="float32",
                device=device, callback=self._callback,
            )
        except Exception:
            native = sd.query_devices(device if device is not None else sd.default.device[0])
            rate = float(native["default_samplerate"])
            self._resample = _Resampler(rate)
            stream = sd.InputStream(
                samplerate=rate, blocksize=int(rate * 0.03), channels=1, dtype="float32",
                device=device, callback=self._callback,
            )
        stream.start()
        self._stream = stream

    def stop(self) -> np.ndarray:
        stream, self._stream = self._stream, None
        if stream is not None:
            try:
                stream.stop()
                stream.close()
            except Exception:
                pass
        with self._lock:
            audio = np.concatenate(self._chunks) if self._chunks else np.zeros(0, np.float32)
            self._chunks = []
        return audio


# --- chimes ---------------------------------------------------------------

def _tone(freqs: list[float], note_s: float = 0.07, volume: float = 0.12, rate: int = 44100) -> np.ndarray:
    parts = []
    for f in freqs:
        t = np.arange(int(rate * note_s)) / rate
        env = np.sin(np.pi * t / note_s) ** 2  # soft attack and release
        parts.append(np.sin(2 * np.pi * f * t) * env * volume)
    return np.concatenate(parts).astype(np.float32)


_CHIMES = {
    "start": _tone([659.25, 987.77]),  # E5 -> B5
    "stop": _tone([987.77, 783.99]),  # B5 -> G5
    "cancel": _tone([523.25, 392.0], volume=0.08),
    "error": _tone([329.63, 329.63], note_s=0.09, volume=0.1),
}


def play_chime(kind: str) -> None:
    wave = _CHIMES.get(kind)
    if wave is None:
        return
    try:
        sd.play(wave, 44100, blocking=False)
    except Exception:
        pass
