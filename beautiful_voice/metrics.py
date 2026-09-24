"""Accuracy and speed metrics for the benchmark."""

from __future__ import annotations

import math
import re
import unicodedata

_PUNCT = re.compile(r"[^\w\s]|_", re.UNICODE)

_NUMBER_WORDS = {
    # Models disagree on digits vs. words for small numbers; fold the common ones.
    "one": "1", "two": "2", "three": "3", "four": "4", "five": "5", "six": "6", "seven": "7",
    "eight": "8", "nine": "9", "ten": "10", "twenty": "20", "hundred": "100",
    "один": "1", "одна": "1", "два": "2", "две": "2", "три": "3", "четыре": "4", "пять": "5",
    "шесть": "6", "семь": "7", "восемь": "8", "девять": "9", "десять": "10", "двадцать": "20", "сто": "100",
}


def normalize(text: str) -> list[str]:
    text = unicodedata.normalize("NFKC", text).lower().replace("ё", "е")
    text = text.replace("-", " ").replace("—", " ").replace("–", " ")
    text = _PUNCT.sub(" ", text)
    return [_NUMBER_WORDS.get(w, w) for w in text.split()]


def edit_distance(ref: list, hyp: list) -> int:
    prev = list(range(len(hyp) + 1))
    for i, r in enumerate(ref, 1):
        cur = [i] + [0] * len(hyp)
        for j, h in enumerate(hyp, 1):
            cur[j] = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (r != h))
        prev = cur
    return prev[-1]


def wer(reference: str, hypothesis: str) -> float:
    ref, hyp = normalize(reference), normalize(hypothesis)
    if not ref:
        return 0.0 if not hyp else 1.0
    return edit_distance(ref, hyp) / len(ref)


def cer(reference: str, hypothesis: str) -> float:
    ref = list(" ".join(normalize(reference)))
    hyp = list(" ".join(normalize(hypothesis)))
    if not ref:
        return 0.0 if not hyp else 1.0
    return edit_distance(ref, hyp) / len(ref)


def accuracy_from_wer(value: float) -> float:
    """Accuracy in percent, 0..100."""
    return max(0.0, min(100.0, (1.0 - value) * 100.0))


def speed_score(rtfx: float) -> float:
    """0..1 on a log scale: real time is 0, 100x faster than real time is 1.

    On a CPU even the quick models land between 5x and 50x, so the scale tops
    out at 100x rather than at the GPU numbers leaderboards report.
    """
    if rtfx <= 1:
        return 0.0
    return max(0.0, min(1.0, math.log10(rtfx) / 2.0))
