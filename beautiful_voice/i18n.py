"""Interface languages. Each one lives in ``locales/<code>.py``; English is the reference."""

from __future__ import annotations

from PySide6.QtCore import Property, QDate, QLocale, QObject, Signal

# Plain imports (not by name at runtime) so PyInstaller bundles every locale.
from .locales import de, en, es, fr, hi, ja, pt, ru, zh

# Most-spoken first; this is also the order of the language picker.
LOCALES = {"en": en, "zh": zh, "hi": hi, "es": es, "fr": fr, "pt": pt, "ru": ru, "de": de, "ja": ja}
_SLAVIC = {"ru", "uk", "pl", "cs"}

STRINGS: dict[str, dict[str, str]] = {code: mod.STRINGS for code, mod in LOCALES.items()}


def languages() -> list[dict]:
    return [{"value": code, "label": mod.NAME} for code, mod in LOCALES.items()]


def phrases(code: str) -> list[str]:
    mod = LOCALES.get(code)
    return list(mod.PHRASES) if mod else []


def best_match(system_code: str) -> str:
    code = (system_code or "").lower().replace("-", "_").split("_")[0]
    return code if code in LOCALES else "en"


class I18n(QObject):
    changed = Signal()

    def __init__(self, lang: str = "en", parent=None) -> None:
        super().__init__(parent)
        self._lang = lang if lang in LOCALES else "en"

    @property
    def lang(self) -> str:
        return self._lang

    @property
    def locale(self) -> QLocale:
        return QLocale(self._lang)

    def set_lang(self, lang: str) -> None:
        lang = lang if lang in LOCALES else "en"
        if lang != self._lang:
            self._lang = lang
            self.changed.emit()

    def tr(self, key: str, **kwargs) -> str:
        text = STRINGS[self._lang].get(key) or STRINGS["en"].get(key, key)
        return text.format(**kwargs) if kwargs else text

    def number(self, value: float, decimals: int = 0) -> str:
        if decimals == 0:
            return self.locale.toString(int(round(value)))
        return self.locale.toString(float(value), "f", decimals)

    def plural(self, n: int, base: str) -> str:
        """``plural(5, "words")`` -> "5 words" / "5 слов" / "5 个词"."""
        if self._lang in _SLAVIC:
            m = abs(n) % 100
            form = "many" if 11 <= m <= 19 else "one" if m % 10 == 1 else "few" if 2 <= m % 10 <= 4 else "many"
        else:
            form = "one" if n == 1 else "many"
        return self.tr(f"{base}_{form}", n=self.number(n))

    def short_date(self, date: QDate) -> str:
        fmt = "M月d日" if self._lang in ("zh", "ja") else "d MMM"
        return self.locale.toString(date, fmt)

    def _strings(self) -> dict:
        merged = dict(STRINGS["en"])
        merged.update(STRINGS[self._lang])
        return merged

    t = Property("QVariantMap", _strings, notify=changed)

    def _get_code(self) -> str:
        return self._lang

    code = Property(str, _get_code, notify=changed)
