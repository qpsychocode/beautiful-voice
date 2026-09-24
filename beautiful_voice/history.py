"""Dictation history with a user-set size limit.

Only the newest ``limit`` entries are kept; adding one more drops the oldest.
Lifetime totals (words, dictations, seconds spoken) are stored separately so
they survive trimming.
"""

from __future__ import annotations

import json
import os
import re
import tempfile
import threading
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path

from .paths import data_dir


# Chinese characters and Japanese kana: each counts as a word, since these
# scripts don't separate words with spaces.
_CJK = re.compile(r"[぀-ヿ㐀-䶿一-鿿豈-﫿]")


def count_words(text: str) -> int:
    cjk = len(_CJK.findall(text))
    return cjk + len(_CJK.sub(" ", text).split())


@dataclass
class HistoryEntry:
    text: str
    duration: float
    model: str
    language: str = ""
    created: float = field(default_factory=time.time)
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])

    @property
    def words(self) -> int:
        return count_words(self.text)

    def to_dict(self) -> dict:
        data = asdict(self)
        data["words"] = self.words
        return data


@dataclass
class Totals:
    dictations: int = 0
    words: int = 0
    seconds: float = 0.0


class History:
    def __init__(self, limit: int = 10, path: Path | None = None) -> None:
        self.path = path or data_dir() / "history.json"
        self.limit = max(1, limit)
        self._lock = threading.Lock()
        self.entries: list[HistoryEntry] = []  # newest first
        self.totals = Totals()
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return
        known = {"text", "duration", "model", "language", "created", "id"}
        for item in raw.get("entries", []):
            try:
                self.entries.append(HistoryEntry(**{k: v for k, v in item.items() if k in known}))
            except TypeError:
                continue
        totals = raw.get("totals", {})
        self.totals = Totals(
            dictations=int(totals.get("dictations", 0)),
            words=int(totals.get("words", 0)),
            seconds=float(totals.get("seconds", 0.0)),
        )
        self._trim()

    def _save(self) -> None:
        payload = {
            "version": 1,
            "totals": asdict(self.totals),
            "entries": [asdict(e) for e in self.entries],
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=self.path.parent, prefix=".history-", suffix=".json")
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False, indent=1)
        os.replace(tmp, self.path)

    def _trim(self) -> list[HistoryEntry]:
        dropped = self.entries[self.limit :]
        del self.entries[self.limit :]
        return dropped

    def add(self, entry: HistoryEntry) -> list[HistoryEntry]:
        """Store an entry; returns the entries that fell off the end."""
        with self._lock:
            self.entries.insert(0, entry)
            self.totals.dictations += 1
            self.totals.words += entry.words
            self.totals.seconds += entry.duration
            dropped = self._trim()
            self._save()
            return dropped

    def set_limit(self, limit: int) -> list[HistoryEntry]:
        with self._lock:
            self.limit = max(1, limit)
            dropped = self._trim()
            if dropped:
                self._save()
            return dropped

    def delete(self, entry_id: str) -> bool:
        with self._lock:
            before = len(self.entries)
            self.entries = [e for e in self.entries if e.id != entry_id]
            if len(self.entries) == before:
                return False
            self._save()
            return True

    def clear(self) -> None:
        with self._lock:
            self.entries.clear()
            self._save()
