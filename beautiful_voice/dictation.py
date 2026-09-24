"""The dictation loop: hotkey -> record -> transcribe -> insert.

Streaming models (Nemotron) get the audio every quarter second through one
live stream, so the whole utterance keeps its context and only the last
chunk is left to decode when the user stops. Other models get finished
phrases, cut at pauses, one by one while the user keeps talking.
"""

from __future__ import annotations

import itertools
import logging
import os
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field

import numpy as np
from PySide6.QtCore import QObject, QTimer, Signal, Slot

from . import inserter
from .audio import Recorder, play_chime
from .config import SettingsStore
from .history import History, HistoryEntry
from .models.catalog import by_id
from .models.manager import ModelManager
from .segmenter import SAMPLE_RATE, Segment, Segmenter, split_offline

MIN_RECORDING_S = 0.4
log = logging.getLogger(__name__)

# Phrases Whisper is known to invent on silence or noise (it learned them from
# subtitle credits). Dropped only when they make up the whole phrase.
_HALLUCINATIONS = {
    "продолжение следует", "субтитры сделал dimatorzok", "субтитры создавал dimatorzok",
    "редактор субтитров а семкин корректор а егорова", "спасибо за просмотр",
    "thank you for watching", "thanks for watching", "thank you", "you",
    "субтитры подогнал симон",
}


def _is_hallucination(text: str) -> bool:
    key = re.sub(r"[^\w\s]", "", text.lower()).strip()
    return key in _HALLUCINATIONS


def join_phrases(parts: list[str]) -> str:
    text = " ".join(p.strip() for p in parts if p and p.strip())
    return re.sub(r"\s+([,.!?;:])", r"\1", re.sub(r"\s{2,}", " ", text)).strip()


@dataclass
class Session:
    id: int
    language: str
    target_hwnd: int
    target_is_self: bool
    started: float = field(default_factory=time.monotonic)
    texts: dict[int, str] = field(default_factory=dict)
    cancelled: bool = False
    error: str = ""
    duration: float = 0.0
    # Streaming models: audio goes into one live stream as it's spoken.
    streaming: bool = False
    live: object | None = None
    pending: list = field(default_factory=list)
    pending_samples: int = 0
    partial: str = ""
    stopped: float = 0.0


STREAM_BATCH = 4000  # samples (0.25 s) handed to the streaming model at a time


class Dictation(QObject):
    stateChanged = Signal(str)
    level = Signal(float)
    notice = Signal(str)  # message key for the overlay: "no_model", "mic_error", "empty", ...
    completed = Signal(object)  # HistoryEntry
    partialText = Signal(str)  # what's been recognized so far, while recording
    _hotkey_press = Signal()
    _hotkey_release = Signal()
    _escape = Signal()
    _finished = Signal(object, str)
    _inserted = Signal(int)

    def __init__(self, settings: SettingsStore, models: ModelManager, history: History, parent=None) -> None:
        super().__init__(parent)
        self.settings = settings
        self.models = models
        self.history = history
        self.state = "idle"
        self.recorder = Recorder(self._on_block)
        self.segmenter = Segmenter()
        self.worker = ThreadPoolExecutor(max_workers=1, thread_name_prefix="transcribe")
        self.session: Session | None = None
        self._ids = itertools.count(1)
        self._escape_grabbed = False
        self.hotkeys = None  # set by the app once the hotkey service exists

        self._max_timer = QTimer(self, singleShot=True)
        self._max_timer.timeout.connect(self.stop)
        self._settle_timer = QTimer(self, singleShot=True)
        self._settle_timer.timeout.connect(lambda: self._set_state("idle"))

        self._hotkey_press.connect(self._on_hotkey_press)
        self._hotkey_release.connect(self._on_hotkey_release)
        self._escape.connect(self.cancel)
        self._finished.connect(self._on_finished)
        self._inserted.connect(self._on_inserted)

    # --- hotkey entry points (called from the hotkey thread) ---------------

    def hotkey_pressed(self) -> None:
        self._hotkey_press.emit()

    def hotkey_released(self) -> None:
        self._hotkey_release.emit()

    def escape_pressed(self) -> None:
        self._escape.emit()

    @Slot()
    def _on_hotkey_press(self) -> None:
        if self.settings.get("hotkey_mode") == "hold":
            if self.state in ("idle", "done", "message"):
                self.start()
        else:
            self.toggle()

    @Slot()
    def _on_hotkey_release(self) -> None:
        if self.settings.get("hotkey_mode") == "hold" and self.state == "recording":
            self.stop()

    # --- state ---------------------------------------------------------------

    def _set_state(self, state: str) -> None:
        if state != self.state:
            self.state = state
            self.stateChanged.emit(state)

    def _chime(self, kind: str) -> None:
        if self.settings.get("sounds"):
            play_chime(kind)

    def _grab_escape(self, on: bool) -> None:
        if self.hotkeys is not None and on != self._escape_grabbed:
            self._escape_grabbed = on
            self.hotkeys.grab_escape(on)

    @Slot()
    def toggle(self) -> None:
        if self.state == "recording":
            self.stop()
        elif self.state in ("idle", "done", "message"):
            self.start()

    @Slot()
    def start(self) -> None:
        if self.state not in ("idle", "done", "message"):
            return
        self._settle_timer.stop()
        if not self.models.active_id():
            self._show_notice("no_model")
            return
        target = inserter.foreground_window()
        is_self = inserter.window_process_id(target) == os.getpid()
        language = self.settings.get("language")
        self.session = Session(next(self._ids), language, target, is_self)
        spec = by_id(self.models.active_id())
        self.session.streaming = bool(spec and spec.backend == "sherpa-onnx" and self.settings.get("live_transcription"))
        self.partialText.emit("")
        self.segmenter.reset()
        try:
            self.recorder.start(self.settings.get("input_device"))
        except Exception:
            self.session = None
            self._show_notice("mic_error")
            return
        self._grab_escape(True)
        self._set_state("recording")
        self._chime("start")
        self._max_timer.start(max(10, int(self.settings.get("max_recording_sec"))) * 1000)

    def _on_block(self, samples: np.ndarray, level: float) -> None:
        # Audio thread.
        self.level.emit(level)
        session = self.session
        if session is None or not self.settings.get("live_transcription"):
            return
        if session.streaming:
            session.pending.append(samples)
            session.pending_samples += len(samples)
            if session.pending_samples >= STREAM_BATCH:
                self._flush_pending(session)
            return
        for segment in self.segmenter.feed(samples):
            self._submit(session, segment)

    # --- streaming models ----------------------------------------------------

    def _flush_pending(self, session: Session) -> None:
        if not session.pending:
            return
        chunk = np.concatenate(session.pending)
        session.pending, session.pending_samples = [], 0
        self.worker.submit(self._feed, session, chunk)

    def _feed(self, session: Session, chunk: np.ndarray) -> None:
        # Worker thread: the model decodes while the user keeps talking.
        if session.cancelled or session.error:
            return
        try:
            if session.live is None:
                lang = None if session.language == "auto" else session.language
                session.live = self.models.engine(timeout=180).open_stream(lang)
            session.live.accept(chunk)
            text = session.live.partial()
        except Exception as exc:
            session.error = str(exc) or exc.__class__.__name__
            return
        if text != session.partial and session is self.session:
            session.partial = text
            self.partialText.emit(text)

    def _finish_stream(self, session: Session) -> None:
        if session.cancelled:
            return
        text = ""
        if session.live is not None and not session.error:
            try:
                text = session.live.finish()
            except Exception as exc:
                session.error = str(exc) or exc.__class__.__name__
        self._finished.emit(session, text)

    def _submit(self, session: Session, segment: Segment) -> None:
        if segment.has_speech:
            self.worker.submit(self._transcribe_segment, session, segment)

    def _transcribe_segment(self, session: Session, segment: Segment) -> None:
        if session.cancelled or session.error:
            return
        try:
            engine = self.models.engine(timeout=180)
            previous = join_phrases([session.texts[k] for k in sorted(session.texts)])
            lang = None if session.language == "auto" else session.language
            text = engine.transcribe(segment.audio, language=lang, prompt=previous[-220:] or None)
        except Exception as exc:  # surfaced to the user as a notice
            session.error = str(exc) or exc.__class__.__name__
            return
        if not _is_hallucination(text):
            session.texts[segment.index] = text

    def _finalize(self, session: Session) -> None:
        if session.cancelled:
            return
        text = join_phrases([session.texts[k] for k in sorted(session.texts)])
        self._finished.emit(session, text)

    @Slot()
    def stop(self) -> None:
        if self.state != "recording" or self.session is None:
            return
        self._max_timer.stop()
        session = self.session
        audio = self.recorder.stop()
        self._grab_escape(False)
        session.duration = len(audio) / SAMPLE_RATE
        if session.duration < MIN_RECORDING_S:
            self.cancel(quiet=True)
            return
        self._set_state("processing")
        self._chime("stop")
        session.stopped = time.monotonic()
        if session.streaming:
            self._flush_pending(session)
            self.worker.submit(self._finish_stream, session)
            return
        if self.settings.get("live_transcription"):
            tail = self.segmenter.flush()
            if tail is not None:
                self._submit(session, tail)
        else:
            for segment in split_offline(audio):
                self._submit(session, segment)
        self.worker.submit(self._finalize, session)

    @Slot()
    def cancel(self, quiet: bool = False) -> None:
        if self.state not in ("recording", "processing"):
            return
        self._max_timer.stop()
        if self.recorder.active:
            self.recorder.stop()
        self._grab_escape(False)
        if self.session is not None:
            self.session.cancelled = True
        self.session = None
        if not quiet:
            self._chime("cancel")
        self._set_state("idle")

    def _show_notice(self, key: str) -> None:
        self._chime("error")
        self.notice.emit(key)
        self._set_state("message")
        self._settle_timer.start(2600)

    @Slot(object, str)
    def _on_finished(self, session: Session, text: str) -> None:
        if session is not self.session or session.cancelled:
            return
        self.session = None
        log.info("dictation %s: %.1fs of speech, %s, ready %.2fs after stop, %d chars%s",
                 session.id, session.duration, "streamed" if session.streaming else "by phrase",
                 time.monotonic() - session.stopped, len(text), f", error: {session.error}" if session.error else "")
        if session.error:
            self.notice.emit("error:" + session.error)
            self._chime("error")
            self._set_state("message")
            self._settle_timer.start(3500)
            return
        if not text:
            self._show_notice("empty")
            return
        entry = HistoryEntry(text=text, duration=round(session.duration, 2),
                             model=self.models.active_id(), language=session.language)
        self.history.add(entry)
        self.completed.emit(entry)
        if session.target_is_self:
            # Dictated while our own window had focus: there is no field to type into,
            # the text shows up on the home screen instead.
            self._on_inserted(session.id)
            return
        payload = text + (" " if self.settings.get("trailing_space") else "")
        method = self.settings.get("insert_method")
        restore = self.settings.get("restore_clipboard")

        def run() -> None:
            try:
                inserter.insert_text(payload, session.target_hwnd, method, restore)
            finally:
                self._inserted.emit(session.id)

        threading.Thread(target=run, name="insert", daemon=True).start()

    @Slot(int)
    def _on_inserted(self, _session_id: int) -> None:
        self._set_state("done")
        self._settle_timer.start(900)

    def shutdown(self) -> None:
        if self.recorder.active:
            self.recorder.stop()
        self.worker.shutdown(wait=False, cancel_futures=True)
