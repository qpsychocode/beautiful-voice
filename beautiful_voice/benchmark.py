"""The "your voice" benchmark.

The user reads a known text aloud once; the recording is then run through
every downloaded model. Accuracy is 100 − WER against that text, speed is how
many times faster than real time the model got through the recording.
"""

from __future__ import annotations

import json
import time
import wave
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np

from .metrics import accuracy_from_wer, cer, wer
from .paths import data_dir
from .segmenter import SAMPLE_RATE, split_offline

PHRASES = {
    "ru": [
        "Привет! Завтра утром у нас созвон с командой. Нужно обсудить новый дизайн приложения, проверить, "
        "насколько быстро модель превращает речь в текст, и выбрать лучший вариант для первой версии.",
        "Сегодня я наконец-то разобрал почту, ответил на вопросы клиентов и записал идеи для следующей встречи. "
        "Осталось купить продукты, забрать посылку и позвонить маме вечером.",
        "Голосовой ввод экономит время: вместо того чтобы печатать длинное сообщение, достаточно нажать сочетание "
        "клавиш, спокойно проговорить мысль и вставить готовый текст в любое поле.",
    ],
    "en": [
        "Hi there! Tomorrow morning we have a call with the team. We need to review the new app design, check how "
        "quickly each model turns speech into text, and pick the best option for the first release.",
        "Today I finally cleared my inbox, answered a few customer questions, and wrote down ideas for the next "
        "meeting. I still need to buy groceries, pick up a package, and call my mom tonight.",
        "Voice typing saves time: instead of writing a long message, you press a shortcut, calmly say what you "
        "mean, and paste the finished text into any field you like.",
    ],
}


@dataclass
class BenchResult:
    model: str
    language: str
    wer: float
    cer: float
    accuracy: float
    rtfx: float
    seconds: float  # processing time for the whole recording
    audio_seconds: float
    hypothesis: str
    device: str
    created: float


def save_wav(path: Path, audio: np.ndarray, rate: int = SAMPLE_RATE) -> None:
    pcm = (np.clip(audio, -1, 1) * 32767).astype("<i2")
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(pcm.tobytes())


def load_wav(path: Path) -> np.ndarray:
    with wave.open(str(path), "rb") as w:
        rate, channels, width = w.getframerate(), w.getnchannels(), w.getsampwidth()
        raw = w.readframes(w.getnframes())
    if width != 2:
        raise ValueError("Only 16-bit WAV files are supported")
    audio = np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32768.0
    if channels > 1:
        audio = audio.reshape(-1, channels).mean(axis=1)
    if rate != SAMPLE_RATE:
        idx = np.arange(0, len(audio), rate / SAMPLE_RATE)
        audio = np.interp(idx, np.arange(len(audio)), audio).astype(np.float32)
    return audio


def run_one(engine, audio: np.ndarray, reference: str, language: str) -> BenchResult:
    """Transcribe the recording the same way dictation does and score it."""
    segments = [s for s in split_offline(audio) if s.has_speech] or []
    lang = language if language != "auto" else None
    engine.transcribe(audio[: SAMPLE_RATE], language=lang)  # warm caches outside the timed run
    started = time.perf_counter()
    parts: list[str] = []
    for seg in segments:
        prev = " ".join(parts)
        parts.append(engine.transcribe(seg.audio, language=lang, prompt=prev[-220:] or None))
    elapsed = time.perf_counter() - started
    hypothesis = " ".join(p.strip() for p in parts if p.strip())
    audio_s = len(audio) / SAMPLE_RATE
    w = wer(reference, hypothesis)
    return BenchResult(
        model=engine.spec.id, language=language, wer=round(w, 4), cer=round(cer(reference, hypothesis), 4),
        accuracy=round(accuracy_from_wer(w), 1), rtfx=round(audio_s / max(elapsed, 1e-3), 1),
        seconds=round(elapsed, 3), audio_seconds=round(audio_s, 2), hypothesis=hypothesis,
        device=engine.device, created=time.time(),
    )


class BenchStore:
    """Latest result per model, plus the reference recording."""

    def __init__(self, root: Path | None = None) -> None:
        self.root = root or data_dir() / "benchmark"
        self.root.mkdir(parents=True, exist_ok=True)
        self.results_path = self.root / "results.json"
        self.results: dict[str, dict] = {}
        if self.results_path.exists():
            try:
                self.results = json.loads(self.results_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                self.results = {}

    @property
    def sample_path(self) -> Path:
        return self.root / "sample.wav"

    @property
    def meta_path(self) -> Path:
        return self.root / "sample.json"

    def save_sample(self, audio: np.ndarray, language: str, phrase_index: int) -> None:
        save_wav(self.sample_path, audio)
        self.meta_path.write_text(json.dumps({"language": language, "phrase": phrase_index,
                                              "seconds": len(audio) / SAMPLE_RATE}), encoding="utf-8")

    def sample(self) -> tuple[np.ndarray, str, int] | None:
        if not (self.sample_path.exists() and self.meta_path.exists()):
            return None
        meta = json.loads(self.meta_path.read_text(encoding="utf-8"))
        return load_wav(self.sample_path), meta["language"], int(meta["phrase"])

    def sample_meta(self) -> dict | None:
        if not self.meta_path.exists():
            return None
        try:
            return json.loads(self.meta_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None

    def save(self) -> None:
        self.results_path.write_text(json.dumps(self.results, ensure_ascii=False, indent=1), encoding="utf-8")

    def put(self, result: BenchResult) -> None:
        self.results[result.model] = asdict(result)
        self.save()

    def forget(self, model_id: str) -> None:
        if self.results.pop(model_id, None) is not None:
            self.save()
