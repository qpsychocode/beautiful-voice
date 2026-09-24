"""Thin wrappers that give every backend the same ``transcribe`` call."""

from __future__ import annotations

import os
import re
import threading
from pathlib import Path

import numpy as np

from .catalog import ModelSpec

SAMPLE_RATE = 16000


def _threads() -> int:
    """Four threads at most. On hybrid CPUs (Intel 12th gen and later) more threads spill
    onto efficiency cores and every step waits for them: on an i7-12700 Nemotron runs at
    7.4x real time with 4 threads and 0.4x with 8."""
    return max(1, min(4, (os.cpu_count() or 4) // 2))


def tidy(text: str) -> str:
    """Collapse the double spaces some models leave between sentences."""
    return re.sub(r"\s+", " ", text).strip()


class Engine:
    # Streaming engines take audio while the user is still talking (see open_stream).
    streaming = False

    def __init__(self, spec: ModelSpec) -> None:
        self.spec = spec
        self.lock = threading.Lock()
        self.device = "cpu"

    def transcribe(self, audio: np.ndarray, language: str | None = None, prompt: str | None = None) -> str:
        if audio.size < SAMPLE_RATE // 10:
            return ""
        audio = np.ascontiguousarray(audio, dtype=np.float32)
        if self.spec.english_only:
            language = "en"
        with self.lock:
            return tidy(self._transcribe(audio, language, prompt))

    def open_stream(self, language: str | None) -> "LiveStream":
        raise NotImplementedError

    def _transcribe(self, audio: np.ndarray, language: str | None, prompt: str | None) -> str:
        raise NotImplementedError

    def warm_up(self) -> None:
        """Run once on a little noise so the first real phrase isn't slowed by lazy init."""
        noise = (np.random.default_rng(0).standard_normal(SAMPLE_RATE) * 0.003).astype(np.float32)
        try:
            self.transcribe(noise, language=None)
        except Exception:
            pass

    def close(self) -> None:
        pass


class FasterWhisperEngine(Engine):
    def __init__(self, spec: ModelSpec, path: Path, device: str) -> None:
        super().__init__(spec)
        from faster_whisper import WhisperModel

        self.model = None
        if device in ("auto", "cuda"):
            try:
                import ctranslate2

                if ctranslate2.get_cuda_device_count() > 0:
                    model = WhisperModel(str(path), device="cuda", compute_type="float16")
                    # CUDA libraries load lazily; a tiny run proves they are really there.
                    list(model.transcribe(np.zeros(SAMPLE_RATE, np.float32), beam_size=1)[0])
                    self.model, self.device = model, "cuda"
            except Exception:
                self.model = None
        if self.model is None:
            self.model = WhisperModel(str(path), device="cpu", compute_type="int8", cpu_threads=_threads())

    def _transcribe(self, audio, language, prompt):
        segments, _info = self.model.transcribe(
            audio,
            language=language,
            beam_size=1,
            initial_prompt=prompt,
            condition_on_previous_text=False,
            without_timestamps=True,
            vad_filter=True,
            vad_parameters={"min_silence_duration_ms": 500},
        )
        return "".join(s.text for s in segments)

    def close(self):
        self.model = None


class OnnxAsrEngine(Engine):
    """Parakeet, Canary and GigaAM through onnx-asr."""

    def __init__(self, spec: ModelSpec, path: Path, device: str, fallback_language: str = "en") -> None:
        super().__init__(spec)
        import onnx_asr
        import onnxruntime as ort

        available = ort.get_available_providers()
        providers = ["CPUExecutionProvider"]
        if device in ("auto", "cuda"):
            for gpu in ("CUDAExecutionProvider", "DmlExecutionProvider"):
                if gpu in available:
                    providers = [gpu, "CPUExecutionProvider"]
                    self.device = "cuda" if gpu.startswith("CUDA") else "directml"
                    break
        options = ort.SessionOptions()
        options.intra_op_num_threads = _threads()
        options.inter_op_num_threads = 1
        self.model = onnx_asr.load_model(spec.onnx_name, str(path), quantization=spec.quantization,
                                         providers=providers, sess_options=options)
        # Canary cannot detect the language by itself.
        self.needs_language = spec.family == "Canary"
        self.fallback_language = fallback_language if spec.supports(fallback_language) else "en"

    def _transcribe(self, audio, language, prompt):
        if self.needs_language:
            return self.model.recognize(audio, sample_rate=SAMPLE_RATE, language=language or self.fallback_language)
        return self.model.recognize(audio, sample_rate=SAMPLE_RATE)

    def close(self):
        self.model = None


class LiveStream:
    """One utterance fed to a streaming model as it's spoken.

    All calls must come from the same worker thread.
    """

    def __init__(self, engine: "SherpaStreamingEngine", language: str | None) -> None:
        self.engine = engine
        self.stream = engine.recognizer.create_stream()
        if engine.spec.multilingual_stream:
            self.stream.set_option("language", language or "auto")
        self.stream.accept_waveform(SAMPLE_RATE, engine.lead)
        self.seconds = 0.0

    def _decode(self) -> None:
        rec = self.engine.recognizer
        while rec.is_ready(self.stream):
            rec.decode_stream(self.stream)

    def accept(self, samples: np.ndarray) -> None:
        with self.engine.lock:
            self.stream.accept_waveform(SAMPLE_RATE, np.ascontiguousarray(samples, dtype=np.float32))
            self._decode()
        self.seconds += len(samples) / SAMPLE_RATE

    def partial(self) -> str:
        with self.engine.lock:
            return tidy(self.engine.result(self.stream))

    def finish(self) -> str:
        with self.engine.lock:
            self.stream.accept_waveform(SAMPLE_RATE, self.engine.tail)
            self.stream.input_finished()
            self._decode()
            return tidy(self.engine.result(self.stream))


class SherpaStreamingEngine(Engine):
    """Nemotron streaming transducers through sherpa-onnx.

    During dictation audio goes into one LiveStream as it arrives, so the
    model keeps its context for the whole utterance and only the last chunk
    is left to decode when the user stops.
    """

    streaming = True

    def __init__(self, spec: ModelSpec, path: Path, device: str) -> None:
        super().__init__(spec)
        import sherpa_onnx

        provider = "cpu"
        if device in ("auto", "cuda"):
            try:
                import onnxruntime as ort

                if "CUDAExecutionProvider" in ort.get_available_providers():
                    provider = "cuda"
            except Exception:
                pass
        self.device = provider
        self.recognizer = sherpa_onnx.OnlineRecognizer.from_transducer(
            tokens=str(path / "tokens.txt"),
            encoder=str(path / f"encoder{spec.file_suffix}.onnx"),
            decoder=str(path / f"decoder{spec.file_suffix}.onnx"),
            joiner=str(path / f"joiner{spec.file_suffix}.onnx"),
            num_threads=_threads(),
            sample_rate=SAMPLE_RATE,
            decoding_method="greedy_search",
            provider=provider,
        )
        # A little silence before the speech, and two chunks after it so the last
        # words (which need right-hand context) are decoded too.
        self.lead = np.zeros(int(SAMPLE_RATE * 0.3), dtype=np.float32)
        self.tail = np.zeros(int(SAMPLE_RATE * 2.3), dtype=np.float32)

    def result(self, stream) -> str:
        r = self.recognizer.get_result(stream)
        return r if isinstance(r, str) else getattr(r, "text", str(r))

    def open_stream(self, language):
        if self.spec.english_only:
            language = "en"
        return LiveStream(self, language)

    def _transcribe(self, audio, language, prompt):
        stream = self.recognizer.create_stream()
        if self.spec.multilingual_stream:
            stream.set_option("language", language or "auto")
        stream.accept_waveform(SAMPLE_RATE, self.lead)
        stream.accept_waveform(SAMPLE_RATE, audio)
        stream.accept_waveform(SAMPLE_RATE, self.tail)
        stream.input_finished()
        while self.recognizer.is_ready(stream):
            self.recognizer.decode_stream(stream)
        return self.result(stream)

    def close(self):
        self.recognizer = None


def create_engine(spec: ModelSpec, path: Path, device: str = "auto", fallback_language: str = "en") -> Engine:
    if spec.backend == "faster-whisper":
        engine: Engine = FasterWhisperEngine(spec, path, device)
    elif spec.backend == "onnx-asr":
        engine = OnnxAsrEngine(spec, path, device, fallback_language)
    elif spec.backend == "sherpa-onnx":
        engine = SherpaStreamingEngine(spec, path, device)
    else:
        raise ValueError(f"Unknown backend {spec.backend}")
    engine.warm_up()
    return engine
