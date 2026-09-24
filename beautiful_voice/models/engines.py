"""Thin wrappers that give every backend the same ``transcribe`` call."""

from __future__ import annotations

import os
import threading
from pathlib import Path

import numpy as np

from .catalog import ModelSpec

SAMPLE_RATE = 16000


def _threads() -> int:
    return max(1, min(8, (os.cpu_count() or 4)))


class Engine:
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
            return self._transcribe(audio, language, prompt).strip()

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
        self.model = onnx_asr.load_model(spec.onnx_name, str(path), quantization=spec.quantization, providers=providers)
        # Canary cannot detect the language by itself.
        self.needs_language = spec.family == "Canary"
        self.fallback_language = fallback_language if spec.supports(fallback_language) else "en"

    def _transcribe(self, audio, language, prompt):
        if self.needs_language:
            return self.model.recognize(audio, sample_rate=SAMPLE_RATE, language=language or self.fallback_language)
        return self.model.recognize(audio, sample_rate=SAMPLE_RATE)

    def close(self):
        self.model = None


class SherpaStreamingEngine(Engine):
    """Nemotron streaming transducers through sherpa-onnx.

    The model is streaming, but our phrases arrive whole, so each phrase is fed
    as one stream and decoded to the end.
    """

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
            encoder=str(path / "encoder.int8.onnx"),
            decoder=str(path / "decoder.int8.onnx"),
            joiner=str(path / "joiner.int8.onnx"),
            num_threads=_threads(),
            sample_rate=SAMPLE_RATE,
            decoding_method="greedy_search",
            provider=provider,
        )
        self.tail = np.zeros(int(SAMPLE_RATE * 1.2), dtype=np.float32)  # lets the last chunk through

    def _transcribe(self, audio, language, prompt):
        stream = self.recognizer.create_stream()
        if self.spec.multilingual_stream:
            stream.set_option("language", language or "auto")
        stream.accept_waveform(SAMPLE_RATE, audio)
        stream.accept_waveform(SAMPLE_RATE, self.tail)
        stream.input_finished()
        while self.recognizer.is_ready(stream):
            self.recognizer.decode_stream(stream)
        result = self.recognizer.get_result(stream)
        return result if isinstance(result, str) else getattr(result, "text", str(result))

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
