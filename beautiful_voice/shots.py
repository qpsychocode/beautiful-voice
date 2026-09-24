"""Renders every page and the overlay to PNG (``--shots DIR``), for the README and design review."""

from __future__ import annotations

import math
from pathlib import Path

from PySide6.QtCore import QTimer


def capture(app, window, overlay, backend, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    theme = backend.store.get("theme")
    steps: list[tuple[int, callable]] = []

    def shot(name: str, target) -> None:
        target.grabWindow().save(str(out_dir / f"{name}.png"))

    for page in ("dictate", "models", "bench", "history", "settings"):
        steps.append((450, lambda p=page: backend.navigateRequested.emit(p)))
        steps.append((650, lambda p=page: shot(f"{theme}-{p}", window)))

    phase = {"t": 0.0}
    wobble = QTimer()
    wobble.setInterval(33)

    def feed_level() -> None:
        phase["t"] += 0.33
        t = phase["t"]
        backend._on_level(max(0.0, 0.55 + 0.35 * math.sin(t) * math.sin(t * 0.37 + 1)))

    wobble.timeout.connect(feed_level)
    steps.append((100, lambda: (backend.navigateRequested.emit("dictate"), wobble.start(),
                                backend._on_state("recording"))))
    steps.append((900, lambda: (shot(f"{theme}-overlay-recording", overlay), shot(f"{theme}-dictate-recording", window))))
    steps.append((100, lambda: (wobble.stop(), backend._on_state("processing"))))
    steps.append((500, lambda: shot(f"{theme}-overlay-processing", overlay)))
    steps.append((100, lambda: backend._on_state("done")))
    steps.append((500, lambda: shot(f"{theme}-overlay-done", overlay)))
    steps.append((100, lambda: backend._on_state("idle")))
    steps.append((400, app.quit))

    def run(i: int = 0) -> None:
        if i >= len(steps):
            return
        delay, action = steps[i]

        def fire() -> None:
            action()
            run(i + 1)

        QTimer.singleShot(delay, fire)

    run()
