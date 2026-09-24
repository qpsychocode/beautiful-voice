"""Cuts a live 16 kHz stream into phrases at natural pauses.

Each finished phrase can be transcribed while the user keeps talking, so when
they stop only the last few seconds are left to process. The voice detector is
a plain energy gate with an adaptive noise floor: cheap enough to run inside
the audio callback and good enough to find the gaps between phrases.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

SAMPLE_RATE = 16000


def rms_db(samples: np.ndarray) -> float:
    if samples.size == 0:
        return -120.0
    rms = float(np.sqrt(np.mean(np.square(samples, dtype=np.float64))))
    return 20.0 * np.log10(max(rms, 1e-6))


@dataclass
class Segment:
    audio: np.ndarray
    index: int
    has_speech: bool


class Segmenter:
    def __init__(
        self,
        sample_rate: int = SAMPLE_RATE,
        frame_ms: int = 30,
        min_segment_s: float = 3.0,
        max_segment_s: float = 24.0,
        pause_s: float = 0.45,
        speech_margin_db: float = 9.0,
        silence_floor_db: float = -58.0,
    ) -> None:
        self.sr = sample_rate
        self.frame = int(sample_rate * frame_ms / 1000)
        self.min_frames = int(min_segment_s * 1000 / frame_ms)
        self.max_frames = int(max_segment_s * 1000 / frame_ms)
        self.pause_frames = max(1, int(pause_s * 1000 / frame_ms))
        self.margin = speech_margin_db
        self.silence_floor = silence_floor_db
        self.reset()

    def reset(self) -> None:
        self._pending = np.zeros(0, dtype=np.float32)  # samples not yet framed
        self._frames: list[np.ndarray] = []  # frames of the current segment
        self._levels: list[float] = []
        self._speech: list[bool] = []
        self._noise_db: float | None = None
        self._silence_run = 0
        self._count = 0

    def _classify(self, db: float) -> bool:
        # The floor falls instantly to quiet frames and creeps up slowly, so
        # steady background noise raises it but speech does not.
        if self._noise_db is None or db < self._noise_db:
            self._noise_db = db
        else:
            self._noise_db += 0.004 * (db - self._noise_db)
        return db > self._noise_db + self.margin and db > self.silence_floor

    def _emit(self, n_frames: int) -> Segment:
        audio = np.concatenate(self._frames[:n_frames]) if n_frames else np.zeros(0, np.float32)
        has_speech = sum(self._speech[:n_frames]) >= 5
        del self._frames[:n_frames], self._levels[:n_frames], self._speech[:n_frames]
        segment = Segment(audio=audio, index=self._count, has_speech=has_speech)
        self._count += 1
        return segment

    def feed(self, samples: np.ndarray) -> list[Segment]:
        """Add audio; returns any phrases that just finished."""
        out: list[Segment] = []
        data = np.concatenate([self._pending, samples.astype(np.float32, copy=False)])
        n = len(data) // self.frame
        self._pending = data[n * self.frame :]
        for i in range(n):
            frame = data[i * self.frame : (i + 1) * self.frame]
            db = rms_db(frame)
            speech = self._classify(db)
            self._frames.append(frame)
            self._levels.append(db)
            self._speech.append(speech)
            self._silence_run = 0 if speech else self._silence_run + 1

            length = len(self._frames)
            if length >= self.min_frames and self._silence_run >= self.pause_frames:
                # Cut in the middle of the pause so neither side loses a syllable.
                cut = length - self._silence_run // 2
                out.append(self._emit(cut))
                self._silence_run = len(self._frames)
            elif length >= self.max_frames:
                # Nobody paused for a long time: cut at the quietest moment of the last 3 s.
                window = min(length - 1, int(3000 / 30))
                tail = self._levels[-window:]
                cut = length - window + int(np.argmin(tail)) + 1
                out.append(self._emit(cut))
                self._silence_run = 0
        return out

    def flush(self) -> Segment | None:
        """Return whatever is left when recording stops."""
        if self._pending.size:
            self._frames.append(self._pending)
            self._levels.append(rms_db(self._pending))
            self._speech.append(False)
            self._pending = np.zeros(0, dtype=np.float32)
        if not self._frames:
            return None
        segment = self._emit(len(self._frames))
        # A short last word may be too brief for the counter; trust loudness then.
        if not segment.has_speech and segment.audio.size:
            segment.has_speech = rms_db(segment.audio) > self.silence_floor + 10
        return segment


def split_offline(audio: np.ndarray, **kwargs) -> list[Segment]:
    """Segment a finished recording the same way the live path does."""
    seg = Segmenter(**kwargs)
    parts = seg.feed(audio)
    last = seg.flush()
    if last is not None:
        parts.append(last)
    return parts
