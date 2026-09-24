"""The models Beautiful Voice can download.

``refs`` are published word error rates, shown on the model cards until the
user runs the benchmark on their own voice. They come from different test
sets, so they are a rough guide, not a ranking:

* Open ASR Leaderboard, English tab, snapshot 2026-09-19
  (https://huggingface.co/spaces/hf-audio/open_asr_leaderboard)
* FLEURS Russian, from the NVIDIA model cards
* GigaAM evaluation, average over 10 Russian sets
  (https://github.com/salute-developers/GigaAM/blob/main/evaluation.md)

``speed_tier`` (1 slow … 5 fast) is our estimate for a typical CPU; the
benchmark replaces it with a measured number.
"""

from __future__ import annotations

from dataclasses import dataclass

LEADERBOARD = "Open ASR Leaderboard"
FLEURS = "FLEURS"
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
    langs: tuple[str, ...]  # language codes it handles well; ("*",) means ~100 languages
    lang_count: int
    speed_tier: int
    punctuation: bool
    blurb_en: str
    blurb_ru: str
    refs: tuple[Reference, ...] = ()
    exclude: tuple[str, ...] = ()
    onnx_name: str = ""
    quantization: str | None = None
    multilingual_stream: bool = False

    def supports(self, lang: str) -> bool:
        return "*" in self.langs or lang in self.langs

    @property
    def english_only(self) -> bool:
        return self.langs == ("en",)


_EU25 = ("bg", "hr", "cs", "da", "nl", "en", "et", "fi", "fr", "de", "el", "hu", "it", "lv", "lt",
         "mt", "pl", "pt", "ro", "sk", "sl", "es", "sv", "ru", "uk")

CATALOG: tuple[ModelSpec, ...] = (
    ModelSpec(
        id="parakeet-tdt-0.6b-v3", name="Parakeet TDT v3", family="Parakeet", vendor="NVIDIA",
        backend="onnx-asr", repo="istupakov/parakeet-tdt-0.6b-v3-onnx",
        include=("config.json", "vocab.txt", "encoder-model.int8.onnx", "decoder_joint-model.int8.onnx"),
        onnx_name="nemo-parakeet-tdt-0.6b-v3", quantization="int8",
        size_mb=670, params="0.6B", langs=_EU25, lang_count=25, speed_tier=5, punctuation=True,
        refs=(Reference("en", 5.66, LEADERBOARD), Reference("ru", 5.51, FLEURS)),
        blurb_en="The best all-rounder: very fast on a CPU, accurate, 25 European languages including Russian.",
        blurb_ru="Лучший универсал: очень быстрая даже на процессоре, точная, 25 европейских языков, включая русский.",
    ),
    ModelSpec(
        id="gigaam-v3-e2e-rnnt", name="GigaAM v3", family="GigaAM", vendor="Sber",
        backend="onnx-asr", repo="istupakov/gigaam-v3-onnx",
        include=("config.json", "config.yaml", "v3_e2e_rnnt_*.int8.onnx", "v3_e2e_rnnt_vocab.txt"),
        onnx_name="gigaam-v3-e2e-rnnt", quantization="int8",
        size_mb=227, params="0.2B", langs=("ru",), lang_count=1, speed_tier=5, punctuation=True,
        refs=(Reference("ru", 11.2, GIGAAM_EVAL),),
        blurb_en="Made for Russian: small, fast, with punctuation. Understands only Russian.",
        blurb_ru="Сделана для русского: маленькая, быстрая, с пунктуацией. Понимает только русский.",
    ),
    ModelSpec(
        id="nemotron-3.5-asr-streaming", name="Nemotron 3.5 ASR", family="Nemotron", vendor="NVIDIA",
        backend="sherpa-onnx", repo="csukuangfj2/sherpa-onnx-nemotron-3.5-asr-streaming-0.6b-1120ms-int8-2026-06-11",
        include=("encoder.int8.onnx", "decoder.int8.onnx", "joiner.int8.onnx", "tokens.txt"),
        size_mb=651, params="0.6B",
        langs=("*",), lang_count=40, speed_tier=4, punctuation=True, multilingual_stream=True,
        refs=(Reference("en", 8.72, LEADERBOARD), Reference("ru", 9.17, FLEURS)),
        blurb_en="NVIDIA's streaming model for 40 languages, including Russian. Detects the language itself.",
        blurb_ru="Потоковая модель NVIDIA на 40 языков, включая русский. Сама определяет язык.",
    ),
    ModelSpec(
        id="nemotron-speech-streaming-en", name="Nemotron Speech EN", family="Nemotron", vendor="NVIDIA",
        backend="sherpa-onnx", repo="csukuangfj/sherpa-onnx-nemotron-speech-streaming-en-0.6b-int8-2026-01-14",
        include=("encoder.int8.onnx", "decoder.int8.onnx", "joiner.int8.onnx", "tokens.txt"),
        size_mb=631, params="0.6B", langs=("en",), lang_count=1, speed_tier=4, punctuation=True,
        refs=(Reference("en", 6.00, LEADERBOARD),),
        blurb_en="Streaming English model from NVIDIA with punctuation and capitalization.",
        blurb_ru="Потоковая английская модель NVIDIA с пунктуацией и заглавными буквами.",
    ),
    ModelSpec(
        id="canary-1b-v2", name="Canary 1B v2", family="Canary", vendor="NVIDIA",
        backend="onnx-asr", repo="istupakov/canary-1b-v2-onnx",
        include=("config.json", "vocab.txt", "encoder-model.int8.onnx", "decoder-model.int8.onnx"),
        onnx_name="nemo-canary-1b-v2", quantization="int8",
        size_mb=1030, params="1B", langs=_EU25, lang_count=25, speed_tier=3, punctuation=True,
        refs=(Reference("en", 6.55, LEADERBOARD), Reference("ru", 6.90, FLEURS)),
        blurb_en="Larger NVIDIA model for 25 European languages. Needs the speech language set in Settings.",
        blurb_ru="Крупная модель NVIDIA на 25 европейских языков. Язык речи лучше указать в настройках.",
    ),
    ModelSpec(
        id="parakeet-tdt-0.6b-v2", name="Parakeet TDT v2", family="Parakeet", vendor="NVIDIA",
        backend="onnx-asr", repo="istupakov/parakeet-tdt-0.6b-v2-onnx",
        include=("config.json", "vocab.txt", "encoder-model.int8.onnx", "decoder_joint-model.int8.onnx"),
        onnx_name="nemo-parakeet-tdt-0.6b-v2", quantization="int8",
        size_mb=661, params="0.6B", langs=("en",), lang_count=1, speed_tier=5, punctuation=True,
        refs=(Reference("en", 5.48, LEADERBOARD),),
        blurb_en="The most accurate English model here, and one of the fastest.",
        blurb_ru="Самая точная английская модель в списке и одна из самых быстрых.",
    ),
    ModelSpec(
        id="whisper-large-v3-turbo", name="Whisper Large v3 Turbo", family="Whisper", vendor="OpenAI",
        backend="faster-whisper", repo="mobiuslabsgmbh/faster-whisper-large-v3-turbo", include=_WHISPER_FILES,
        size_mb=1620, params="0.8B", langs=("*",), lang_count=99, speed_tier=2, punctuation=True,
        refs=(Reference("en", 7.03, LEADERBOARD),),
        blurb_en="Whisper for 99 languages, pruned for speed. Best with a GPU.",
        blurb_ru="Whisper на 99 языков, облегчённый ради скорости. Лучше всего — с видеокартой.",
    ),
    ModelSpec(
        id="whisper-large-v3", name="Whisper Large v3", family="Whisper", vendor="OpenAI",
        backend="faster-whisper", repo="Systran/faster-whisper-large-v3", include=_WHISPER_FILES,
        size_mb=3090, params="1.55B", langs=("*",), lang_count=99, speed_tier=1, punctuation=True,
        refs=(Reference("en", 6.50, LEADERBOARD), Reference("ru", 21.0, GIGAAM_EVAL)),
        blurb_en="The full Whisper: 99 languages, slow on a CPU.",
        blurb_ru="Полный Whisper: 99 языков, на процессоре работает медленно.",
    ),
    ModelSpec(
        id="distil-large-v3.5", name="Distil-Whisper v3.5", family="Whisper", vendor="Hugging Face",
        backend="faster-whisper", repo="distil-whisper/distil-large-v3.5-ct2", include=_WHISPER_FILES,
        size_mb=1515, params="0.76B", langs=("en",), lang_count=1, speed_tier=2, punctuation=True,
        refs=(Reference("en", 6.20, LEADERBOARD),),
        blurb_en="A distilled Whisper for English: close to Large v3, noticeably faster.",
        blurb_ru="Сжатый Whisper для английского: почти как Large v3, но заметно быстрее.",
    ),
    ModelSpec(
        id="whisper-small", name="Whisper Small", family="Whisper", vendor="OpenAI",
        backend="faster-whisper", repo="Systran/faster-whisper-small", include=_WHISPER_FILES,
        size_mb=485, params="244M", langs=("*",), lang_count=99, speed_tier=3, punctuation=True,
        blurb_en="A compact Whisper for 99 languages. Fine for short notes.",
        blurb_ru="Компактный Whisper на 99 языков. Подойдёт для коротких заметок.",
    ),
    ModelSpec(
        id="whisper-base", name="Whisper Base", family="Whisper", vendor="OpenAI",
        backend="faster-whisper", repo="Systran/faster-whisper-base", include=_WHISPER_FILES,
        size_mb=146, params="74M", langs=("*",), lang_count=99, speed_tier=4, punctuation=True,
        blurb_en="The smallest download. Quick to try, makes more mistakes.",
        blurb_ru="Самая маленькая. Быстро скачать и попробовать, но ошибается чаще.",
    ),
)

_BY_ID = {spec.id: spec for spec in CATALOG}


def by_id(model_id: str) -> ModelSpec | None:
    return _BY_ID.get(model_id)


RECOMMENDED = "parakeet-tdt-0.6b-v3"
