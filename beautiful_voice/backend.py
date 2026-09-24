"""The object QML talks to: exposes state as properties and actions as slots."""

from __future__ import annotations

import datetime as dt
import shutil
import sys
import threading
import time

from PySide6.QtCore import (QEvent, QObject, QPoint, Property, Qt, QUrl, Signal, Slot)
from PySide6.QtGui import QCursor, QDesktopServices, QGuiApplication

from . import autostart, inserter
from .audio import Recorder, list_input_devices
from .benchmark import PHRASES, BenchResult, BenchStore, run_one
from .config import SettingsStore
from .dictation import Dictation
from .history import History, HistoryEntry
from .hotkeys import _NAMED_VK, HotkeyService, parse_combo
from .i18n import I18n
from .listmodel import DictListModel
from .metrics import speed_score
from .models.catalog import CATALOG, RECOMMENDED, ModelSpec, by_id
from .models.download import DownloadCancelled
from .models.manager import ModelManager
from .paths import APP_VERSION, REPO_URL, data_dir
from .segmenter import SAMPLE_RATE

MODEL_KEYS = ["id", "name", "family", "vendor", "blurb", "meta", "sizeText", "installed", "active", "recommended",
              "downloading", "progress", "progressText", "error", "accuracy", "accuracyText", "speedValue",
              "speedText", "source", "measured", "status", "statusText", "supportsRu", "supportsEn"]
HISTORY_KEYS = ["id", "text", "time", "day", "meta"]
BENCH_KEYS = ["id", "name", "status", "statusText", "accuracy", "accuracyText", "speedValue", "speedText",
              "hypothesis", "best", "bestTone", "rtfx"]

SPEECH_LANGUAGES = [("ru", "Русский"), ("en", "English"), ("uk", "Українська"), ("de", "Deutsch"),
                    ("fr", "Français"), ("es", "Español"), ("it", "Italiano"), ("pl", "Polski"),
                    ("pt", "Português"), ("nl", "Nederlands"), ("cs", "Čeština"), ("tr", "Türkçe"),
                    ("ja", "日本語"), ("zh", "中文"), ("ko", "한국어")]

_KEY_LABELS = {"ctrl": "Ctrl", "alt": "Alt", "shift": "Shift", "win": "Win", "space": "Space", "enter": "Enter",
               "tab": "Tab", "backspace": "Backspace", "esc": "Esc", "insert": "Ins", "delete": "Del",
               "home": "Home", "end": "End", "pageup": "PgUp", "pagedown": "PgDn", "left": "←", "up": "↑",
               "right": "→", "down": "↓", "pause": "Pause", "capslock": "Caps", "scrolllock": "ScrLk",
               "printscreen": "PrtSc"}
_VK_TO_NAME = {vk: name for name, vk in _NAMED_VK.items()}
_MODIFIER_VKS = {0x10, 0x11, 0x12, 0x5B, 0x5C, 0xA0, 0xA1, 0xA2, 0xA3, 0xA4, 0xA5}
_MONTHS_RU = ["янв", "фев", "мар", "апр", "мая", "июн", "июл", "авг", "сен", "окт", "ноя", "дек"]
_MONTHS_EN = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def ru_plural(n: int, one: str, few: str, many: str) -> str:
    n = abs(n) % 100
    if 11 <= n <= 19:
        return many
    n %= 10
    return one if n == 1 else few if 2 <= n <= 4 else many


def key_labels(combo: str) -> list[str]:
    try:
        parsed = parse_combo(combo)
    except ValueError:
        return [combo]
    return [_KEY_LABELS.get(k, k.upper()) for k in (*parsed.modifiers, parsed.key)]


class Backend(QObject):
    stateChanged = Signal()
    levelChanged = Signal()
    noticeChanged = Signal()
    settingsChanged = Signal()
    modelChanged = Signal()
    lastChanged = Signal()
    hotkeyChanged = Signal()
    devicesChanged = Signal()
    countsChanged = Signal()
    benchChanged = Signal()
    navigateRequested = Signal(str)
    themeChanged = Signal(str)
    languageChanged = Signal()
    windowHiddenFirstTime = Signal()
    showWindowRequested = Signal()
    quitRequested = Signal()

    _progress = Signal(str, "qint64", "qint64")
    _download_done = Signal(str, str)
    _model_status = Signal(str)
    _bench_level = Signal(float)
    _bench_event = Signal(str, str, object)

    def __init__(self, settings: SettingsStore, i18n: I18n, history: History, models: ModelManager,
                 dictation: Dictation, bench: BenchStore, parent=None) -> None:
        super().__init__(parent)
        self.store = settings
        self.i18n = i18n
        self.history = history
        self.models = models
        self.dictation = dictation
        self.bench = bench
        self.hotkeys: HotkeyService | None = None
        self.overlay = None

        self.models_model = DictListModel(MODEL_KEYS, parent=self)
        self.history_model = DictListModel(HISTORY_KEYS, parent=self)
        self.bench_model = DictListModel(BENCH_KEYS, parent=self)

        self._state = "idle"
        self._level = 0.0
        self._notice = ""
        self._hotkey_error = ""
        self._capturing = False
        self._downloads: dict[str, dict] = {}
        self._dl_errors: dict[str, str] = {}
        self._hidden_once = False
        self._microphones = self._list_microphones()

        # Benchmark state
        self._bench_state = "ready" if bench.sample_meta() else "empty"
        meta = bench.sample_meta() or {}
        self._bench_lang = meta.get("language") or ("ru" if i18n.lang == "ru" else "en")
        self._bench_phrase = int(meta.get("phrase", 0))
        self._bench_seconds = float(meta.get("seconds", 0.0))
        self._bench_level_value = 0.0
        self._bench_status = ""
        self._bench_cancel = threading.Event()
        self._bench_recorder = Recorder(lambda _s, level: self._bench_level.emit(level))

        dictation.stateChanged.connect(self._on_state)
        dictation.level.connect(self._on_level)
        dictation.notice.connect(self._on_notice)
        dictation.completed.connect(self._on_completed)
        models.on_status(lambda status: self._model_status.emit(status))
        self._model_status.connect(self._on_model_status)
        self._progress.connect(self._on_progress)
        self._download_done.connect(self._on_download_done)
        self._bench_level.connect(self._on_bench_level)
        self._bench_event.connect(self._on_bench_event)
        i18n.changed.connect(self._on_language)

        self.models_model.set_items([self._model_row(s) for s in CATALOG])
        self._rebuild_history()
        self._rebuild_bench()

    # ------------------------------------------------------------------ helpers

    def tr(self, key: str, **kw) -> str:
        return self.i18n.tr(key, **kw)

    def _size_text(self, mb: float) -> str:
        ru = self.i18n.lang == "ru"
        if mb >= 1000:
            value = f"{mb / 1000:.1f}".replace(".", "," if ru else ".")
            return f"{value} {'ГБ' if ru else 'GB'}"
        return f"{mb:.0f} {'МБ' if ru else 'MB'}"

    def _pref_lang(self) -> str:
        lang = self.store.get("language")
        if lang in ("ru", "en"):
            return lang
        return "ru" if self.i18n.lang == "ru" else "en"

    def _when(self, ts: float) -> str:
        day = dt.date.fromtimestamp(ts)
        today = dt.date.today()
        if day == today:
            return self.tr("today")
        if day == today - dt.timedelta(days=1):
            return self.tr("yesterday")
        months = _MONTHS_RU if self.i18n.lang == "ru" else _MONTHS_EN
        return f"{day.day} {months[day.month - 1]}"

    @staticmethod
    def _speed_text(rtfx: float) -> str:
        return f"×{rtfx:.0f}" if rtfx >= 10 else f"×{rtfx:.1f}"

    def _langs_text(self, spec: ModelSpec) -> str:
        if spec.lang_count > 1:
            n = spec.lang_count
            if self.i18n.lang == "ru":
                return f"{n} {ru_plural(n, 'язык', 'языка', 'языков')}"
            return self.tr("langs_many", n=n)
        return self.tr("langs_one_ru") if spec.langs == ("ru",) else self.tr("langs_one_en")

    def _model_row(self, spec: ModelSpec) -> dict:
        installed = self.models.installed(spec)
        active = spec.id == self.models.active_id()
        download = self._downloads.get(spec.id)
        result = self.bench.results.get(spec.id)
        row: dict = {
            "id": spec.id, "name": spec.name, "family": spec.family, "vendor": spec.vendor,
            "blurb": spec.blurb_ru if self.i18n.lang == "ru" else spec.blurb_en,
            "meta": f"{spec.params} · {self._size_text(spec.size_mb)} · {self._langs_text(spec)}",
            "sizeText": self._size_text(spec.size_mb),
            "installed": installed, "active": active, "recommended": spec.id == RECOMMENDED,
            "downloading": download is not None, "progress": 0.0, "progressText": "",
            "error": self._dl_errors.get(spec.id, ""),
            "supportsRu": spec.supports("ru"), "supportsEn": spec.supports("en"),
            "status": "", "statusText": "",
        }
        if download is not None:
            done, total = download["done"], max(1, download["total"])
            row["progress"] = done / total
            row["progressText"] = self.tr("progress", done=self._size_text(done / 1e6),
                                          total=self._size_text(total / 1e6), pct=int(100 * done / total))
        if result:
            rtfx = float(result["rtfx"])
            row.update(accuracy=float(result["accuracy"]), accuracyText=f"{result['accuracy']:.1f}%",
                       speedValue=speed_score(rtfx), speedText=self._speed_text(rtfx), measured=True,
                       source=self.tr("source_measured", when=self._when(result["created"])))
        else:
            pref = self._pref_lang()
            ref = next((r for r in spec.refs if r.lang == pref), None) or (spec.refs[0] if spec.refs else None)
            if ref:
                acc = round(100 - ref.wer, 1)
                row.update(accuracy=acc, accuracyText=f"{acc:.1f}%",
                           source=self.tr("source_ref", source=ref.source, lang=self.tr("lang_" + ref.lang)))
            else:
                row.update(accuracy=-1.0, accuracyText="", source=self.tr("source_none"))
            row.update(speedValue=spec.speed_tier / 5, speedText=self.tr(f"speed_tier_{spec.speed_tier}"),
                       measured=False)
        if active:
            status = self.models.status
            row["status"] = status
            row["statusText"] = {
                "ready": self.tr("status_ready"),
                "loading": self.tr("status_loading"),
                "error": self.tr("status_error", error=self.models.error[:120]),
            }.get(status, "")
        return row

    def _refresh_model(self, model_id: str) -> None:
        spec = by_id(model_id)
        if spec is not None:
            self.models_model.update(model_id, **self._model_row(spec))

    def _refresh_models(self) -> None:
        for spec in CATALOG:
            self.models_model.update(spec.id, **self._model_row(spec))
        self.modelChanged.emit()
        self.countsChanged.emit()

    def _history_row(self, entry: HistoryEntry) -> dict:
        spec = by_id(entry.model)
        seconds = int(round(entry.duration))
        words = entry.words
        if self.i18n.lang == "ru":
            meta = f"{words} {ru_plural(words, 'слово', 'слова', 'слов')} · {seconds // 60}:{seconds % 60:02d}"
        else:
            meta = f"{words} {'word' if words == 1 else 'words'} · {seconds // 60}:{seconds % 60:02d}"
        if spec:
            meta += f" · {spec.name}"
        return {"id": entry.id, "text": entry.text, "time": time.strftime("%H:%M", time.localtime(entry.created)),
                "day": self._when(entry.created), "meta": meta}

    def _rebuild_history(self) -> None:
        self.history_model.set_items([self._history_row(e) for e in self.history.entries])
        self.lastChanged.emit()

    def _list_microphones(self) -> list[dict]:
        return [{"value": "", "label": self.tr("mic_default")}] + [
            {"value": d["name"], "label": d["name"]} for d in list_input_devices()
        ]

    # --------------------------------------------------------------- properties

    def _get_state(self) -> str:
        return self._state

    state = Property(str, _get_state, notify=stateChanged)

    def _get_level(self) -> float:
        return self._level

    level = Property(float, _get_level, notify=levelChanged)

    def _get_notice(self) -> str:
        return self._notice

    notice = Property(str, _get_notice, notify=noticeChanged)

    def _get_settings(self) -> dict:
        return self.store.as_dict()

    settings = Property("QVariantMap", _get_settings, notify=settingsChanged)

    def _get_active_id(self) -> str:
        return self.models.active_id()

    activeModelId = Property(str, _get_active_id, notify=modelChanged)

    def _get_active_model(self) -> dict:
        row = self.models_model.get(self.models.active_id()) if self.models.active_id() else None
        return row or {}

    activeModel = Property("QVariantMap", _get_active_model, notify=modelChanged)

    def _get_model_status(self) -> str:
        return self.models.status

    modelStatus = Property(str, _get_model_status, notify=modelChanged)

    def _get_installed_count(self) -> int:
        return sum(1 for s in CATALOG if self.models.installed(s))

    installedCount = Property(int, _get_installed_count, notify=countsChanged)

    def _get_downloading_count(self) -> int:
        return len(self._downloads)

    downloadingCount = Property(int, _get_downloading_count, notify=countsChanged)

    def _get_last_text(self) -> str:
        return self.history.entries[0].text if self.history.entries else ""

    lastText = Property(str, _get_last_text, notify=lastChanged)

    def _get_last_meta(self) -> str:
        if not self.history.entries:
            return ""
        row = self._history_row(self.history.entries[0])
        return f"{row['day']}, {row['time']} · {row['meta']}"

    lastMeta = Property(str, _get_last_meta, notify=lastChanged)

    def _get_totals_text(self) -> str:
        totals = self.history.totals
        if totals.dictations == 0:
            return ""
        words, count = totals.words, totals.dictations
        minutes = int(round(words / 40 - totals.seconds / 60))  # typing at ~40 wpm vs. speaking time
        if self.i18n.lang == "ru":
            head = (f"Вы надиктовали {words:,} {ru_plural(words, 'слово', 'слова', 'слов')} "
                    f"за {count} {ru_plural(count, 'диктовку', 'диктовки', 'диктовок')}").replace(",", " ")
            return head + (f" и сэкономили около {minutes} мин набора." if minutes >= 1 else ".")
        head = f"You've dictated {words:,} {'word' if words == 1 else 'words'} in {count} " \
               f"{'dictation' if count == 1 else 'dictations'}"
        return head + (f" and saved about {minutes} min of typing." if minutes >= 1 else ".")

    totalsText = Property(str, _get_totals_text, notify=lastChanged)

    def _get_history_subtitle(self) -> str:
        n = self.history.limit
        if self.i18n.lang == "ru":
            return (f"Хранится не больше {n} {ru_plural(n, 'диктовки', 'диктовок', 'диктовок')}: "
                    f"когда лимит заполнен, самая старая удаляется. Лимит меняется в настройках.")
        return self.tr("history_subtitle", n=n)

    historySubtitle = Property(str, _get_history_subtitle, notify=lastChanged)

    def _get_hotkey_keys(self) -> list:
        return key_labels(self.store.get("hotkey"))

    hotkeyKeys = Property("QVariantList", _get_hotkey_keys, notify=hotkeyChanged)

    def _get_hotkey_error(self) -> str:
        return self._hotkey_error

    hotkeyError = Property(str, _get_hotkey_error, notify=hotkeyChanged)

    def _get_capturing(self) -> bool:
        return self._capturing

    capturingHotkey = Property(bool, _get_capturing, notify=hotkeyChanged)

    def _get_microphones(self) -> list:
        return self._microphones

    microphones = Property("QVariantList", _get_microphones, notify=devicesChanged)

    def _get_speech_languages(self) -> list:
        return [{"value": "auto", "label": self.tr("lang_auto")}] + [
            {"value": code, "label": label} for code, label in SPEECH_LANGUAGES
        ]

    speechLanguages = Property("QVariantList", _get_speech_languages, notify=languageChanged)

    def _get_compute_hint(self) -> str:
        engine = self.models.active_engine()
        if engine is None:
            return self.tr("compute_hint_none")
        names = {"cpu": "CPU", "cuda": "GPU (CUDA)", "directml": "GPU (DirectML)"}
        return self.tr("compute_hint", device=names.get(engine.device, engine.device))

    computeHint = Property(str, _get_compute_hint, notify=modelChanged)

    def _get_is_windows(self) -> bool:
        return sys.platform == "win32"

    isWindows = Property(bool, _get_is_windows, constant=True)

    def _get_version(self) -> str:
        return APP_VERSION

    version = Property(str, _get_version, constant=True)

    # Benchmark properties
    def _get_bench_state(self) -> str:
        return self._bench_state

    benchState = Property(str, _get_bench_state, notify=benchChanged)

    def _get_bench_language(self) -> str:
        return self._bench_lang

    benchLanguage = Property(str, _get_bench_language, notify=benchChanged)

    def _get_bench_phrase(self) -> str:
        phrases = PHRASES[self._bench_lang]
        return phrases[self._bench_phrase % len(phrases)]

    benchPhrase = Property(str, _get_bench_phrase, notify=benchChanged)

    def _get_bench_seconds(self) -> float:
        return self._bench_seconds

    benchSeconds = Property(float, _get_bench_seconds, notify=benchChanged)

    def _get_bench_level(self) -> float:
        return self._bench_level_value

    benchLevel = Property(float, _get_bench_level, notify=levelChanged)

    def _get_bench_status(self) -> str:
        return self._bench_status

    benchStatus = Property(str, _get_bench_status, notify=benchChanged)

    def _get_bench_sample_text(self) -> str:
        if self._bench_seconds <= 0:
            return self.tr("bench_no_sample")
        seconds = f"{self._bench_seconds:.1f}"
        return self.tr("bench_sample", seconds=seconds.replace(".", ",") if self.i18n.lang == "ru" else seconds)

    benchSampleText = Property(str, _get_bench_sample_text, notify=benchChanged)

    # ------------------------------------------------------------ dictation glue

    @Slot(str)
    def _on_state(self, state: str) -> None:
        self._state = state
        if state != "recording":
            self._level = 0.0
            self.levelChanged.emit()
        self.stateChanged.emit()

    @Slot(float)
    def _on_level(self, level: float) -> None:
        self._level = level
        self.levelChanged.emit()

    @Slot(str)
    def _on_notice(self, key: str) -> None:
        if key.startswith("error:"):
            self._notice = self.tr("notice_error", error=key[6:][:90])
        else:
            self._notice = self.tr("notice_" + key)
        self.noticeChanged.emit()

    @Slot(object)
    def _on_completed(self, entry: HistoryEntry) -> None:
        self._rebuild_history()

    @Slot(str)
    def _on_model_status(self, _status: str) -> None:
        self._refresh_model(self.models.active_id() or self.store.get("active_model"))
        self.modelChanged.emit()

    @Slot()
    def toggleDictation(self) -> None:  # noqa: N802
        self.dictation.toggle()

    @Slot()
    def cancelDictation(self) -> None:  # noqa: N802
        self.dictation.cancel()

    @Slot()
    def placeOverlay(self) -> None:  # noqa: N802
        """Centre the pill at the bottom of the screen the mouse is on."""
        if self.overlay is None:
            return
        screen = QGuiApplication.screenAt(QCursor.pos()) or QGuiApplication.primaryScreen()
        geo = screen.availableGeometry()
        w, h = self.overlay.width(), self.overlay.height()
        self.overlay.setScreen(screen)
        self.overlay.setPosition(QPoint(geo.x() + (geo.width() - w) // 2, geo.y() + geo.height() - h - 16))

    # ------------------------------------------------------------------- models

    @Slot(str)
    def downloadModel(self, model_id: str) -> None:  # noqa: N802
        spec = by_id(model_id)
        if spec is None or model_id in self._downloads:
            return
        cancel = threading.Event()
        self._downloads[model_id] = {"done": 0, "total": spec.size_mb * 1_000_000, "cancel": cancel}
        self._dl_errors.pop(model_id, None)
        self._refresh_model(model_id)
        self.countsChanged.emit()

        def run() -> None:
            try:
                self.models.download(spec, lambda d, t: self._progress.emit(model_id, d, t), cancel)
            except DownloadCancelled:
                self._download_done.emit(model_id, "cancelled")
            except Exception as exc:
                self._download_done.emit(model_id, str(exc) or exc.__class__.__name__)
            else:
                self._download_done.emit(model_id, "")

        threading.Thread(target=run, name=f"download-{model_id}", daemon=True).start()

    @Slot(str, "qint64", "qint64")
    def _on_progress(self, model_id: str, done: int, total: int) -> None:
        info = self._downloads.get(model_id)
        if info is None:
            return
        info["done"], info["total"] = done, total
        self._refresh_model(model_id)

    @Slot(str, str)
    def _on_download_done(self, model_id: str, error: str) -> None:
        self._downloads.pop(model_id, None)
        spec = by_id(model_id)
        if error == "cancelled":
            if spec is not None:
                shutil.rmtree(self.models.path(spec), ignore_errors=True)
        elif error:
            self._dl_errors[model_id] = self.tr("download_failed", error=error[:140])
        elif not self.models.active_id():
            self.activateModel(model_id)  # the first model becomes the active one
        self._refresh_model(model_id)
        self._rebuild_bench()
        self.countsChanged.emit()

    @Slot(str)
    def cancelDownload(self, model_id: str) -> None:  # noqa: N802
        info = self._downloads.get(model_id)
        if info:
            info["cancel"].set()

    @Slot(str)
    def activateModel(self, model_id: str) -> None:  # noqa: N802
        previous = self.models.active_id()
        self.store.set("active_model", model_id)
        self.models.set_active(model_id)
        for mid in {previous, model_id}:
            if mid:
                self._refresh_model(mid)
        self.modelChanged.emit()
        self.settingsChanged.emit()

    @Slot(str)
    def deleteModel(self, model_id: str) -> None:  # noqa: N802
        spec = by_id(model_id)
        if spec is None:
            return
        was_active = model_id == self.models.active_id()
        self.models.delete(spec)
        self.bench.forget(model_id)
        if was_active:
            fallback = next((s.id for s in CATALOG if self.models.installed(s)), "")
            self.activateModel(fallback)
        self._refresh_models()
        self._rebuild_bench()

    @Slot()
    def openModelsFolder(self) -> None:  # noqa: N802
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.models.root)))

    @Slot()
    def openDataFolder(self) -> None:  # noqa: N802
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(data_dir())))

    @Slot()
    def openRepo(self) -> None:  # noqa: N802
        QDesktopServices.openUrl(QUrl(REPO_URL))

    # ------------------------------------------------------------------ history

    @Slot(str)
    def copyText(self, text: str) -> None:  # noqa: N802
        inserter.copy_to_clipboard(text)

    @Slot(str)
    def deleteHistory(self, entry_id: str) -> None:  # noqa: N802
        if self.history.delete(entry_id):
            self.history_model.remove(entry_id)
            self.lastChanged.emit()

    @Slot()
    def clearHistory(self) -> None:  # noqa: N802
        self.history.clear()
        self._rebuild_history()

    # ----------------------------------------------------------------- settings

    @Slot(str, "QVariant")
    def setSetting(self, key: str, value) -> None:  # noqa: N802
        if key == "history_limit":
            value = int(value)
        if not self.store.set(key, value):
            return
        value = self.store.get(key)
        if key == "ui_language":
            self.i18n.set_lang(value)
        elif key == "theme":
            self.themeChanged.emit(value)
        elif key == "history_limit":
            self.history.set_limit(value)
            self._rebuild_history()
        elif key == "language":
            self._refresh_models()
        elif key == "compute_device":
            self.models.reload()
        elif key == "autostart":
            autostart.set_enabled(value)
        elif key == "hotkey_mode" and self.hotkeys is not None:
            self.hotkeys.hold_mode = value == "hold"
        self.settingsChanged.emit()

    @Slot()
    def _on_language(self) -> None:
        self._microphones = self._list_microphones()
        self._refresh_models()
        self._rebuild_history()
        self._rebuild_bench()
        self.languageChanged.emit()
        self.devicesChanged.emit()
        self.benchChanged.emit()

    @Slot()
    def refreshMicrophones(self) -> None:  # noqa: N802
        self._microphones = self._list_microphones()
        self.devicesChanged.emit()

    # Hotkey capture: while active, the next key combination pressed in our
    # window becomes the new shortcut.
    @Slot(bool)
    def captureHotkey(self, on: bool) -> None:  # noqa: N802
        if on == self._capturing:
            return
        self._capturing = on
        app = QGuiApplication.instance()
        if on:
            self._hotkey_error = ""
            app.installEventFilter(self)
        else:
            app.removeEventFilter(self)
        self.hotkeyChanged.emit()

    def eventFilter(self, obj, event) -> bool:  # noqa: N802
        if not self._capturing or event.type() != QEvent.Type.KeyPress:
            return False
        vk = event.nativeVirtualKey() if sys.platform == "win32" else 0
        mods = event.modifiers()
        names = []
        if mods & Qt.KeyboardModifier.ControlModifier:
            names.append("ctrl")
        if mods & Qt.KeyboardModifier.AltModifier:
            names.append("alt")
        if mods & Qt.KeyboardModifier.ShiftModifier:
            names.append("shift")
        if mods & Qt.KeyboardModifier.MetaModifier:
            names.append("win")
        if vk:
            if vk in _MODIFIER_VKS:
                return True
            key = _VK_TO_NAME.get(vk)
        else:
            key = self._qt_key_name(event.key())
            if key is None and event.key() in (Qt.Key.Key_Control, Qt.Key.Key_Shift, Qt.Key.Key_Alt, Qt.Key.Key_Meta):
                return True
        if key == "esc" and not names:
            self.captureHotkey(False)
            return True
        if key is None:
            return True
        self.captureHotkey(False)
        self.setHotkey("+".join([*names, key]))
        return True

    @staticmethod
    def _qt_key_name(key: int) -> str | None:
        if Qt.Key.Key_A <= key <= Qt.Key.Key_Z:
            return chr(key).lower()
        if Qt.Key.Key_0 <= key <= Qt.Key.Key_9:
            return chr(key)
        if Qt.Key.Key_F1 <= key <= Qt.Key.Key_F24:
            return f"f{key - Qt.Key.Key_F1 + 1}"
        return {Qt.Key.Key_Space: "space", Qt.Key.Key_Return: "enter", Qt.Key.Key_Enter: "enter",
                Qt.Key.Key_Tab: "tab", Qt.Key.Key_Escape: "esc", Qt.Key.Key_Insert: "insert",
                Qt.Key.Key_Delete: "delete", Qt.Key.Key_Home: "home", Qt.Key.Key_End: "end"}.get(key)

    @Slot(str, result=str)
    def setHotkey(self, combo: str) -> str:  # noqa: N802
        try:
            parse_combo(combo)
        except ValueError:
            self._hotkey_error = self.tr("hotkey_invalid")
            self.hotkeyChanged.emit()
            return self._hotkey_error
        error = self.hotkeys.rebind(combo) if self.hotkeys is not None else None
        if error:
            self._hotkey_error = self.tr("hotkey_busy")
        else:
            self._hotkey_error = ""
            self.store.set("hotkey", combo)
            self.settingsChanged.emit()
        self.hotkeyChanged.emit()
        return self._hotkey_error

    def report_hotkey_error(self, error: str | None) -> None:
        self._hotkey_error = self.tr("hotkey_busy") if error else ""
        self.hotkeyChanged.emit()

    # -------------------------------------------------------------- benchmark

    def _rebuild_bench(self) -> None:
        rows = []
        for spec in CATALOG:
            if not self.models.installed(spec):
                continue
            result = self.bench.results.get(spec.id)
            if result and result.get("language") == self._bench_lang:
                rows.append(self._bench_row(spec, "done", result))
        rows.sort(key=lambda r: (-r["accuracy"], -r["rtfx"]))
        self._mark_best(rows)
        self.bench_model.set_items(rows)

    def _bench_row(self, spec: ModelSpec, status: str, result: dict | None = None) -> dict:
        row = {"id": spec.id, "name": spec.name, "status": status, "statusText": "", "accuracy": 0.0,
               "accuracyText": "", "speedValue": 0.0, "speedText": "", "hypothesis": "", "best": "",
               "bestTone": "", "rtfx": 0.0}
        if status == "waiting":
            row["statusText"] = self.tr("bench_waiting")
        elif status == "loading":
            row["statusText"] = self.tr("bench_loading")
        elif status == "running":
            row["statusText"] = self.tr("bench_running")
        elif status == "done" and result:
            rtfx = float(result["rtfx"])
            device = {"cpu": "CPU", "cuda": "GPU"}.get(result.get("device", "cpu"), result.get("device", ""))
            fmt = (lambda v: f"{v:.1f}".replace(".", ",")) if self.i18n.lang == "ru" else (lambda v: f"{v:.1f}")
            row.update(accuracy=float(result["accuracy"]), accuracyText=f"{result['accuracy']:.1f}%",
                       speedValue=speed_score(rtfx), speedText=self._speed_text(rtfx), rtfx=rtfx,
                       hypothesis=result.get("hypothesis", ""),
                       statusText=self.tr("bench_done_status", wer=fmt(result["wer"] * 100),
                                          seconds=fmt(result["seconds"]), audio=fmt(result["audio_seconds"]),
                                          device=device))
        return row

    def _mark_best(self, rows: list[dict]) -> None:
        done = [r for r in rows if r["status"] == "done"]
        if len(done) < 2:
            return
        best_acc = max(done, key=lambda r: r["accuracy"])
        fastest = max(done, key=lambda r: r["rtfx"])
        if fastest is best_acc:
            best_acc.update(best=self.tr("bench_best_both"), bestTone="ink")
        else:
            best_acc.update(best=self.tr("bench_most_accurate"), bestTone="blue")
            fastest.update(best=self.tr("bench_fastest"), bestTone="pink")

    @Slot(float)
    def _on_bench_level(self, level: float) -> None:
        self._bench_level_value = level
        self.levelChanged.emit()

    @Slot(str)
    def benchSetLanguage(self, lang: str) -> None:  # noqa: N802
        if lang in PHRASES and lang != self._bench_lang and self._bench_state not in ("recording", "running"):
            self._bench_lang = lang
            self._bench_phrase = 0
            self._bench_seconds = 0.0
            self._bench_state = "empty"
            self._bench_status = ""
            self._rebuild_bench()
            self.benchChanged.emit()

    @Slot()
    def benchNextPhrase(self) -> None:  # noqa: N802
        if self._bench_state in ("recording", "running"):
            return
        self._bench_phrase = (self._bench_phrase + 1) % len(PHRASES[self._bench_lang])
        self._bench_seconds = 0.0
        self._bench_state = "empty"
        self.benchChanged.emit()

    @Slot()
    def benchRecordToggle(self) -> None:  # noqa: N802
        if self._bench_state == "running":
            return
        if self._bench_state == "recording":
            audio = self._bench_recorder.stop()
            seconds = len(audio) / SAMPLE_RATE
            if seconds < 3:
                self._bench_state = "empty" if self._bench_seconds <= 0 else "ready"
                self._bench_status = self.tr("bench_too_short")
            else:
                self.bench.save_sample(audio, self._bench_lang, self._bench_phrase)
                self.bench.results.clear()
                self.bench.save()
                self._bench_seconds = seconds
                self._bench_state = "ready"
                self._bench_status = ""
                self._rebuild_bench()
                self._refresh_models()
            self._bench_level_value = 0.0
            self.levelChanged.emit()
            self.benchChanged.emit()
            return
        if self.dictation.state in ("recording", "processing"):
            return
        try:
            self._bench_recorder.start(self.store.get("input_device"))
        except Exception:
            self._bench_status = self.tr("notice_mic_error")
            self.benchChanged.emit()
            return
        self._bench_state = "recording"
        self._bench_status = ""
        self.benchChanged.emit()

    @Slot()
    def benchRun(self) -> None:  # noqa: N802
        if self._bench_state != "ready":
            return
        sample = self.bench.sample()
        if sample is None:
            return
        audio, lang, phrase_index = sample
        reference = PHRASES[lang][phrase_index % len(PHRASES[lang])]
        specs = [s for s in CATALOG if self.models.installed(s) and s.supports(lang)]
        if not specs:
            return
        self._bench_cancel.clear()
        self._bench_state = "running"
        self.bench_model.set_items([self._bench_row(s, "waiting") for s in specs])
        self.benchChanged.emit()

        def run() -> None:
            for i, spec in enumerate(specs, 1):
                if self._bench_cancel.is_set():
                    break
                self._bench_event.emit("progress", spec.id, (i, len(specs)))
                engine = None
                owned = False
                try:
                    active = self.models.active_engine()
                    if active is not None and active.spec.id == spec.id:
                        engine = active
                    else:
                        engine, owned = self.models.load(spec), True
                    self._bench_event.emit("running", spec.id, None)
                    result = run_one(engine, audio, reference, lang)
                    self._bench_event.emit("result", spec.id, result)
                except Exception as exc:
                    self._bench_event.emit("error", spec.id, str(exc) or exc.__class__.__name__)
                finally:
                    if owned and engine is not None:
                        engine.close()
            self._bench_event.emit("finished", "", self._bench_cancel.is_set())

        threading.Thread(target=run, name="benchmark", daemon=True).start()

    @Slot()
    def benchCancel(self) -> None:  # noqa: N802
        self._bench_cancel.set()

    @Slot(str, str, object)
    def _on_bench_event(self, kind: str, model_id: str, payload) -> None:
        spec = by_id(model_id) if model_id else None
        if kind == "progress" and spec:
            i, n = payload
            self._bench_status = self.tr("bench_progress", name=spec.name, i=i, n=n)
            self.bench_model.update(model_id, **self._bench_row(spec, "loading"))
        elif kind == "running" and spec:
            self.bench_model.update(model_id, **self._bench_row(spec, "running"))
        elif kind == "result" and spec:
            result: BenchResult = payload
            self.bench.put(result)
            self.bench_model.update(model_id, **self._bench_row(spec, "done", self.bench.results[model_id]))
            self._refresh_model(model_id)
            self.modelChanged.emit()
        elif kind == "error" and spec:
            row = self._bench_row(spec, "error")
            row["statusText"] = str(payload)[:120]
            self.bench_model.update(model_id, **row)
        elif kind == "finished":
            self._bench_state = "ready"
            self._bench_status = self.tr("bench_cancelled" if payload else "bench_finished")
            self._rebuild_bench()
        self.benchChanged.emit()

    # ------------------------------------------------------------------- window

    @Slot()
    def windowHidden(self) -> None:  # noqa: N802
        if not self._hidden_once:
            self._hidden_once = True
            self.windowHiddenFirstTime.emit()

    @Slot()
    def showMain(self) -> None:  # noqa: N802
        self.showWindowRequested.emit()

    @Slot()
    def quitApp(self) -> None:  # noqa: N802
        self.quitRequested.emit()
