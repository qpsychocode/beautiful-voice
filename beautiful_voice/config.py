"""User settings, persisted as JSON next to the history file."""

from __future__ import annotations

import json
import locale
import os
import tempfile
import threading
from dataclasses import asdict, dataclass, fields
from pathlib import Path
from typing import Any

from .paths import data_dir


def _system_ui_language() -> str:
    try:
        code = locale.getlocale()[0] or ""
    except ValueError:
        code = ""
    if not code and os.name == "nt":
        import ctypes

        lang_id = ctypes.windll.kernel32.GetUserDefaultUILanguage()
        code = locale.windows_locale.get(lang_id, "")
    return "ru" if code.lower().startswith(("ru", "russian")) else "en"


@dataclass
class Settings:
    hotkey: str = "ctrl+shift+space"
    hotkey_mode: str = "toggle"  # "toggle": press to start, press again to insert. "hold": talk while held.
    active_model: str = ""
    language: str = "auto"
    input_device: str = ""  # device name; empty means the system default
    insert_method: str = "paste"  # "paste" through the clipboard or "type" character by character
    restore_clipboard: bool = True
    trailing_space: bool = True
    live_transcription: bool = True
    history_limit: int = 10
    sounds: bool = True
    ui_language: str = ""
    theme: str = "light"
    autostart: bool = False
    start_minimized: bool = False
    compute_device: str = "auto"  # auto | cpu | cuda
    max_recording_sec: int = 600
    hf_endpoint: str = "https://huggingface.co"
    welcomed: bool = False

    @classmethod
    def keys(cls) -> list[str]:
        return [f.name for f in fields(cls)]


class SettingsStore:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or data_dir() / "settings.json"
        self._lock = threading.Lock()
        self.settings = self._load()

    def _load(self) -> Settings:
        settings = Settings()
        if self.path.exists():
            try:
                raw = json.loads(self.path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                raw = {}
            for f in fields(Settings):
                if f.name in raw:
                    value = raw[f.name]
                    default = getattr(settings, f.name)
                    if isinstance(default, bool):
                        value = bool(value)
                    elif isinstance(default, int):
                        try:
                            value = int(value)
                        except (TypeError, ValueError):
                            continue
                    elif isinstance(default, str):
                        value = str(value)
                    setattr(settings, f.name, value)
        if not settings.ui_language:
            settings.ui_language = _system_ui_language()
        settings.history_limit = max(1, min(settings.history_limit, 5000))
        return settings

    def get(self, key: str) -> Any:
        return getattr(self.settings, key)

    def set(self, key: str, value: Any) -> bool:
        """Update one value and save. Returns False when nothing changed."""
        if key not in Settings.keys():
            raise KeyError(key)
        current = getattr(self.settings, key)
        if isinstance(current, bool):
            value = bool(value)
        elif isinstance(current, int):
            value = int(value)
        else:
            value = str(value)
        if key == "history_limit":
            value = max(1, min(value, 5000))
        if value == current:
            return False
        setattr(self.settings, key, value)
        self.save()
        return True

    def as_dict(self) -> dict[str, Any]:
        return asdict(self.settings)

    def save(self) -> None:
        with self._lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            fd, tmp = tempfile.mkstemp(dir=self.path.parent, prefix=".settings-", suffix=".json")
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(self.as_dict(), fh, ensure_ascii=False, indent=2)
            os.replace(tmp, self.path)
