"""Fill a throwaway profile with sample history and benchmark results.

Used to render README screenshots without touching your real data:

    python tools/seed_demo.py <profile-dir> [--dark] [--en]
    set BEAUTIFUL_VOICE_HOME=<profile-dir>
    python -m beautiful_voice --shots docs/screenshots
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ENTRIES_RU = [
    ("Созвон переносим на четверг, в три часа. Я пришлю приглашение и короткую повестку до конца дня.", 7.4),
    ("Добавь в README раздел про тест голоса и поясни, почему цифры точности отличаются от лидерборда.", 8.9),
    ("Купить молоко, хлеб и батарейки для мыши. Забрать посылку до семи.", 5.2),
    ("Спасибо за ревью! Поправил названия переменных и вынес загрузку моделей в отдельный поток.", 7.8),
]
ENTRIES_EN = [
    ("Let's move the call to Thursday at three. I'll send an invite and a short agenda by the end of the day.", 7.1),
    ("Add a section about the voice test to the README and explain why the accuracy numbers differ from the leaderboard.", 8.6),
    ("Buy milk, bread and batteries for the mouse. Pick up the package before seven.", 5.0),
    ("Thanks for the review! I renamed the variables and moved model loading to a background thread.", 7.5),
]
RESULTS = {
    "parakeet-tdt-0.6b-v3": (96.8, 38.5, "Привет! Завтра утром у нас созвон с командой. Нужно обсудить новый дизайн приложения, проверить, насколько быстро модель превращает речь в текст, и выбрать лучший вариант для первой версии."),
    "gigaam-v3-e2e-rnnt": (100.0, 61.2, "Привет. Завтра утром у нас созвон с командой. Нужно обсудить новый дизайн приложения, проверить, насколько быстро модель превращает речь в текст и выбрать лучший вариант для первой версии."),
    "nemotron-3.5-asr-streaming": (93.5, 24.9, "Привет! Завтра утром у нас созвон с командой Нужно обсудить новый дизайн приложения, проверить, насколько быстра модель превращает речь в текст, и выбрать лучший вариант для первой версии"),
    "whisper-base": (83.9, 12.6, "Привет. Завтра утром у нас созвон с командой. Нужно обсудить новый дизайн приложения, проверить, на сколько быстро модель превращает речь в текст и выбрать лучший вариант для первой версии."),
}


def main() -> None:
    root = Path(sys.argv[1])
    dark = "--dark" in sys.argv
    lang = next((a.split("=", 1)[1] for a in sys.argv if a.startswith("--lang=")), "en" if "--en" in sys.argv else "ru")
    english = lang != "ru"
    root.mkdir(parents=True, exist_ok=True)
    (root / "settings.json").write_text(json.dumps({
        "active_model": "nemotron-3.5-asr-streaming", "ui_language": lang,
        "theme": "dark" if dark else "light", "history_limit": 10,
    }), encoding="utf-8")

    now = time.time()
    entries = []
    for i, (text, duration) in enumerate(ENTRIES_EN if english else ENTRIES_RU):
        entries.append({"id": f"demo{i}", "text": text, "duration": duration, "model": "parakeet-tdt-0.6b-v3",
                        "language": "auto", "created": now - i * 2900 - 600})
    words = sum(len(t.split()) for t, _ in ENTRIES_RU) * 31
    (root / "history.json").write_text(json.dumps({
        "version": 1, "totals": {"dictations": 128, "words": words, "seconds": words / 2.4},
        "entries": entries,
    }, ensure_ascii=False), encoding="utf-8")

    bench = root / "benchmark"
    bench.mkdir(exist_ok=True)
    (bench / "sample.json").write_text(json.dumps({"language": "ru", "phrase": 0, "seconds": 16.9}), encoding="utf-8")
    results = {}
    for model, (acc, rtfx, hyp) in RESULTS.items():
        results[model] = {"model": model, "language": "ru", "wer": round(1 - acc / 100, 4), "cer": 0.01,
                          "accuracy": acc, "rtfx": rtfx, "seconds": round(16.9 / rtfx, 3), "audio_seconds": 16.9,
                          "hypothesis": hyp, "device": "cpu", "created": now - 3600}
    (bench / "results.json").write_text(json.dumps(results, ensure_ascii=False), encoding="utf-8")
    print(f"Demo profile ready in {root}")


if __name__ == "__main__":
    main()
