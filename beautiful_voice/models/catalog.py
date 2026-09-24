"""The models Beautiful Voice can download.

``refs`` are published error rates, shown on the model cards until the user
runs the voice test. They come from different test sets, so they are a rough
guide, not a ranking:

* Open ASR Leaderboard, English tab, snapshot 2026-09-19
  (https://huggingface.co/spaces/hf-audio/open_asr_leaderboard)
* FLEURS Russian, from the NVIDIA model cards
* Nemotron 3.5 ASR model card, 1.12 s chunks with the language given
  (https://huggingface.co/nvidia/nemotron-3.5-asr-streaming-0.6b)
* GigaAM evaluation, average over 10 Russian sets
  (https://github.com/salute-developers/GigaAM/blob/main/evaluation.md)

``speed_tier`` (1 slow … 5 fast) is our estimate for a typical CPU; the
voice test replaces it with a measured number. Model descriptions live in
the locale files as ``blurb_<id>``.
"""

from __future__ import annotations

from dataclasses import dataclass

LEADERBOARD = "Open ASR Leaderboard"
FLEURS = "FLEURS"
NVIDIA_CARD = "NVIDIA"
GIGAAM_EVAL = "GigaAM eval"

_WHISPER_FILES = ("config.json", "preprocessor_config.json", "model.bin", "tokenizer.json", "vocabulary.*")


@dataclass(frozen=True)
class Reference:
    lang: str
    wer: float
    source: str


@dataclass(frozen=True)
class ModelSpec:
    id: str
    name: str
    family: str
    vendor: str
    backend: str  # faster-whisper | onnx-asr | sherpa-onnx
    repo: str
    include: tuple[str, ...]
    size_mb: int
    params: str
    langs: tuple[str, ...]  # languages it handles well; ("*",) means ~100 languages
    lang_count: int
    speed_tier: int
    refs: tuple[Reference, ...] = ()
    exclude: tuple[str, ...] = ()
    onnx_name: str = ""
    quantization: str | None = None
    multilingual_stream: bool = False
    file_suffix: str = ".int8"  # sherpa-onnx builds: "encoder.int8.onnx" vs full-precision "encoder.onnx"

    def supports(self, lang: str) -> bool:
        return "*" in self.langs or lang in self.langs

    @property
    def english_only(self) -> bool:
        return self.langs == ("en",)


_EU25 = ("bg", "hr", "cs", "da", "nl", "en", "et", "fi", "fr", "de", "el", "hu", "it", "lv", "lt",
         "mt", "pl", "pt", "ro", "sk", "sl", "es", "sv", "ru", "uk")
# Nemotron 3.5: the "transcription-ready" and "broad-coverage" tiers of its model card.
_NEMOTRON = ("en", "es", "fr", "it", "pt", "nl", "de", "tr", "ru", "ar", "hi", "ja", "ko", "vi", "uk",
             "pl", "sv", "cs", "no", "da", "bg", "fi", "hr", "sk", "zh", "hu")

CATALOG: tuple[ModelSpec, ...] = (
    ModelSpec(
        id="nemotron-3.5-asr-streaming", name="Nemotron 3.5 ASR", family="Nemotron", vendor="NVIDIA",
        backend="sherpa-onnx", repo="csukuangfj2/sherpa-onnx-nemotron-3.5-asr-streaming-0.6b-1120ms-int8-2026-06-11",
        include=("encoder.int8.onnx", "decoder.int8.onnx", "joiner.int8.onnx", "tokens.txt"),
        size_mb=651, params="0.6B", langs=_NEMOTRON, lang_count=32, speed_tier=4, multilingual_stream=True,
        refs=(Reference("en", 8.72, LEADERBOARD), Reference("ru", 9.17, FLEURS),
              Reference("es", 4.11, NVIDIA_CARD), Reference("it", 4.25, NVIDIA_CARD),
              Reference("pt", 5.48, NVIDIA_CARD), Reference("hi", 6.81, NVIDIA_CARD),
              Reference("ko", 7.12, NVIDIA_CARD), Reference("de", 8.31, NVIDIA_CARD),
              Reference("fr", 9.03, NVIDIA_CARD), Reference("ja", 11.48, NVIDIA_CARD),
              Reference("ar", 12.03, NVIDIA_CARD), Reference("zh", 19.28, NVIDIA_CARD)),
    ),
    ModelSpec(
        # The same model without 8-bit compression: measurably more accurate on real
        # dictation, 3.5x the download and somewhat slower, still fast enough to stream.
        id="nemotron-3.5-asr-streaming-full", name="Nemotron 3.5 ASR · Max", family="Nemotron", vendor="NVIDIA",
        backend="sherpa-onnx", repo="csukuangfj2/sherpa-onnx-nemotron-3.5-asr-streaming-0.6b-1120ms-2026-06-11",
        include=("encoder.onnx", "encoder.data", "decoder.onnx", "joiner.onnx", "tokens.txt"),
        size_mb=2595, params="0.6B", langs=_NEMOTRON, lang_count=32, speed_tier=3, multilingual_stream=True,
        file_suffix="",
        refs=(Reference("en", 8.72, LEADERBOARD), Reference("ru", 9.17, FLEURS),
              Reference("es", 4.11, NVIDIA_CARD), Reference("it", 4.25, NVIDIA_CARD),
              Reference("pt", 5.48, NVIDIA_CARD), Reference("hi", 6.81, NVIDIA_CARD),
              Reference("ko", 7.12, NVIDIA_CARD), Reference("de", 8.31, NVIDIA_CARD),
              Reference("fr", 9.03, NVIDIA_CARD), Reference("ja", 11.48, NVIDIA_CARD),
              Reference("ar", 12.03, NVIDIA_CARD), Reference("zh", 19.28, NVIDIA_CARD)),
    ),
    ModelSpec(
        id="parakeet-tdt-0.6b-v3", name="Parakeet TDT v3", family="Parakeet", vendor="NVIDIA",
        backend="onnx-asr", repo="istupakov/parakeet-tdt-0.6b-v3-onnx",
        include=("config.json", "vocab.txt", "encoder-model.int8.onnx", "decoder_joint-model.int8.onnx"),
        onnx_name="nemo-parakeet-tdt-0.6b-v3", quantization="int8",
        size_mb=670, params="0.6B", langs=_EU25, lang_count=25, speed_tier=5,
        refs=(Reference("en", 5.66, LEADERBOARD), Reference("ru", 5.51, FLEURS)),
    ),
    ModelSpec(
        id="gigaam-v3-e2e-rnnt", name="GigaAM v3", family="GigaAM", vendor="Sber",
        backend="onnx-asr", repo="istupakov/gigaam-v3-onnx",
        include=("config.json", "config.yaml", "v3_e2e_rnnt_*.int8.onnx", "v3_e2e_rnnt_vocab.txt"),
        onnx_name="gigaam-v3-e2e-rnnt", quantization="int8",
        size_mb=227, params="0.2B", langs=("ru",), lang_count=1, speed_tier=5,
        refs=(Reference("ru", 11.2, GIGAAM_EVAL),),
    ),
    ModelSpec(
        id="canary-1b-v2", name="Canary 1B v2", family="Canary", vendor="NVIDIA",
        backend="onnx-asr", repo="istupakov/canary-1b-v2-onnx",
        include=("config.json", "vocab.txt", "encoder-model.int8.onnx", "decoder-model.int8.onnx"),
        onnx_name="nemo-canary-1b-v2", quantization="int8",
        size_mb=1030, params="1B", langs=_EU25, lang_count=25, speed_tier=3,
        refs=(Reference("en", 6.55, LEADERBOARD), Reference("ru", 6.90, FLEURS)),
    ),
    ModelSpec(
        id="parakeet-tdt-0.6b-v2", name="Parakeet TDT v2", family="Parakeet", vendor="NVIDIA",
        backend="onnx-asr", repo="istupakov/parakeet-tdt-0.6b-v2-onnx",
        include=("config.json", "vocab.txt", "encoder-model.int8.onnx", "decoder_joint-model.int8.onnx"),
        onnx_name="nemo-parakeet-tdt-0.6b-v2", quantization="int8",
        size_mb=661, params="0.6B", langs=("en",), lang_count=1, speed_tier=5,
        refs=(Reference("en", 5.48, LEADERBOARD),),
    ),
    ModelSpec(
        id="nemotron-speech-streaming-en", name="Nemotron Speech EN", family="Nemotron", vendor="NVIDIA",
        backend="sherpa-onnx", repo="csukuangfj/sherpa-onnx-nemotron-speech-streaming-en-0.6b-int8-2026-01-14",
        include=("encoder.int8.onnx", "decoder.int8.onnx", "joiner.int8.onnx", "tokens.txt"),
        size_mb=631, params="0.6B", langs=("en",), lang_count=1, speed_tier=4,
        refs=(Reference("en", 6.00, LEADERBOARD),),
    ),
    ModelSpec(
        id="whisper-large-v3-turbo", name="Whisper Large v3 Turbo", family="Whisper", vendor="OpenAI",
        backend="faster-whisper", repo="mobiuslabsgmbh/faster-whisper-large-v3-turbo", include=_WHISPER_FILES,
        size_mb=1620, params="0.8B", langs=("*",), lang_count=99, speed_tier=2,
        refs=(Reference("en", 7.03, LEADERBOARD),),
    ),
    ModelSpec(
        id="whisper-large-v3", name="Whisper Large v3", family="Whisper", vendor="OpenAI",
        backend="faster-whisper", repo="Systran/faster-whisper-large-v3", include=_WHISPER_FILES,
        size_mb=3090, params="1.55B", langs=("*",), lang_count=99, speed_tier=1,
        refs=(Reference("en", 6.50, LEADERBOARD), Reference("ru", 21.0, GIGAAM_EVAL)),
    ),
    ModelSpec(
        id="distil-large-v3.5", name="Distil-Whisper v3.5", family="Whisper", vendor="Hugging Face",
        backend="faster-whisper", repo="distil-whisper/distil-large-v3.5-ct2", include=_WHISPER_FILES,
        size_mb=1515, params="0.76B", langs=("en",), lang_count=1, speed_tier=2,
        refs=(Reference("en", 6.20, LEADERBOARD),),
    ),
    ModelSpec(
        id="whisper-small", name="Whisper Small", family="Whisper", vendor="OpenAI",
        backend="faster-whisper", repo="Systran/faster-whisper-small", include=_WHISPER_FILES,
        size_mb=485, params="244M", langs=("*",), lang_count=99, speed_tier=3,
    ),
    ModelSpec(
        id="whisper-base", name="Whisper Base", family="Whisper", vendor="OpenAI",
        backend="faster-whisper", repo="Systran/faster-whisper-base", include=_WHISPER_FILES,
        size_mb=146, params="74M", langs=("*",), lang_count=99, speed_tier=4,
    ),
)

_BY_ID = {spec.id: spec for spec in CATALOG}

# Downloaded automatically on first start: it covers the most widely spoken
# languages, detects the language itself and is quick on an ordinary CPU.
RECOMMENDED = "nemotron-3.5-asr-streaming"


def by_id(model_id: str) -> ModelSpec | None:
    return _BY_ID.get(model_id)
