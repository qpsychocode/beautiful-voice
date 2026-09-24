"""New-version check against GitHub Releases, and in-place updates.

Installed copies (the ones Inno Setup put on disk, recognisable by
``unins000.exe`` next to the app) download the new installer and run it
silently; it replaces the app and starts it again. Portable and source
copies open the release page instead.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import threading
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from PySide6.QtCore import Property, QObject, QTimer, QUrl, Signal, Slot
from PySide6.QtGui import QDesktopServices

from .paths import APP_VERSION, REPO_URL

API_LATEST = "https://api.github.com/repos/" + REPO_URL.split("github.com/")[1] + "/releases/latest"
SETUP_ASSET = "BeautifulVoice-Setup.exe"
USER_AGENT = f"BeautifulVoice/{APP_VERSION}"


def parse_version(text: str) -> tuple[int, ...]:
    parts = []
    for piece in text.strip().lstrip("vV").split("."):
        digits = "".join(ch for ch in piece if ch.isdigit())
        parts.append(int(digits) if digits else 0)
    return tuple(parts)


def is_newer(latest: str, current: str = APP_VERSION) -> bool:
    return parse_version(latest) > parse_version(current)


@dataclass
class Release:
    version: str
    page: str
    setup_url: str
    setup_size: int


def fetch_latest(timeout: float = 15) -> Release:
    req = urllib.request.Request(API_LATEST, headers={"User-Agent": USER_AGENT,
                                                       "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    asset = next((a for a in data.get("assets", []) if a.get("name") == SETUP_ASSET), None)
    return Release(
        version=data["tag_name"].lstrip("vV"),
        page=data.get("html_url", REPO_URL + "/releases/latest"),
        setup_url=asset["browser_download_url"] if asset else "",
        setup_size=int(asset["size"]) if asset else 0,
    )


def installed_copy() -> bool:
    """True when this app was installed by our installer and can update itself."""
    return getattr(sys, "frozen", False) and (Path(sys.executable).parent / "unins000.exe").exists()


def download_setup(release: Release, progress: Callable[[int, int], None], cancel: threading.Event) -> Path:
    target = Path(tempfile.gettempdir()) / f"BeautifulVoice-Setup-{release.version}.exe"
    if target.exists() and target.stat().st_size == release.setup_size:
        return target
    part = target.with_suffix(".part")
    req = urllib.request.Request(release.setup_url, headers={"User-Agent": USER_AGENT})
    done = 0
    with urllib.request.urlopen(req, timeout=60) as resp, open(part, "wb") as out:
        while True:
            if cancel.is_set():
                raise InterruptedError()
            chunk = resp.read(1 << 18)
            if not chunk:
                break
            out.write(chunk)
            done += len(chunk)
            progress(done, release.setup_size)
    if release.setup_size and part.stat().st_size != release.setup_size:
        part.unlink()
        raise IOError("the download was incomplete")
    os.replace(part, target)
    return target


class Updater(QObject):
    """What the interface shows: nothing, or a button to get the new version."""

    changed = Signal()
    quitRequested = Signal()
    _checked = Signal(object, str)
    _progress = Signal("qint64", "qint64")
    _downloaded = Signal(str, str)

    CHECK_EVERY_MS = 6 * 60 * 60 * 1000

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._state = "idle"  # idle | checking | latest | available | downloading | ready | error
        self._release: Release | None = None
        self._setup: Path | None = None
        self._progress_value = 0.0
        self._error = ""
        self._cancel = threading.Event()
        self._checked.connect(self._on_checked)
        self._progress.connect(self._on_progress)
        self._downloaded.connect(self._on_downloaded)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self.check)

    def start(self) -> None:
        QTimer.singleShot(8000, self.check)
        self._timer.start(self.CHECK_EVERY_MS)

    def _set(self, state: str, error: str = "") -> None:
        self._state, self._error = state, error
        self.changed.emit()

    @Slot()
    def check(self) -> None:
        if self._state in ("checking", "downloading", "ready"):
            return
        self._set("checking")

        def run() -> None:
            try:
                self._checked.emit(fetch_latest(), "")
            except Exception as exc:
                self._checked.emit(None, str(exc) or exc.__class__.__name__)

        threading.Thread(target=run, name="update-check", daemon=True).start()

    @Slot(object, str)
    def _on_checked(self, release: Release | None, error: str) -> None:
        if release is None:
            self._set("idle")  # stay quiet about network trouble; the next check retries
            return
        self._release = release
        self._set("available" if is_newer(release.version) else "latest")

    @Slot()
    def download(self) -> None:
        """Installed copies fetch the installer; others open the release page."""
        if self._release is None:
            return
        if not (installed_copy() and self._release.setup_url):
            QDesktopServices.openUrl(QUrl(self._release.page))
            return
        self._cancel.clear()
        self._progress_value = 0.0
        self._set("downloading")
        release = self._release

        def run() -> None:
            try:
                path = download_setup(release, lambda d, t: self._progress.emit(d, t), self._cancel)
                self._downloaded.emit(str(path), "")
            except Exception as exc:
                self._downloaded.emit("", str(exc) or exc.__class__.__name__)

        threading.Thread(target=run, name="update-download", daemon=True).start()

    @Slot("qint64", "qint64")
    def _on_progress(self, done: int, total: int) -> None:
        self._progress_value = done / total if total else 0.0
        self.changed.emit()

    @Slot(str, str)
    def _on_downloaded(self, path: str, error: str) -> None:
        if error:
            self._set("error", error)
            return
        self._setup = Path(path)
        self._set("ready")

    @Slot()
    def install(self) -> None:
        if self._setup is None:
            return
        run_installer(self._setup)
        self.quitRequested.emit()

    def _get_state(self) -> str:
        return self._state

    state = Property(str, _get_state, notify=changed)

    def _get_version(self) -> str:
        return self._release.version if self._release else ""

    version = Property(str, _get_version, notify=changed)

    def _get_progress(self) -> float:
        return self._progress_value

    progress = Property(float, _get_progress, notify=changed)

    def _get_error(self) -> str:
        return self._error

    error = Property(str, _get_error, notify=changed)

    def _get_self_updating(self) -> bool:
        return installed_copy()

    selfUpdating = Property(bool, _get_self_updating, constant=True)


def run_installer(setup: Path) -> None:
    """Start the installer detached; it closes this app, updates it and starts it again."""
    flags = 0x00000008 | 0x00000200  # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
    subprocess.Popen(
        [str(setup), "/SILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/SP-", "/update=1",
         f"/DIR={Path(sys.executable).parent}"],
        creationflags=flags if sys.platform == "win32" else 0,
        close_fds=True,
    )
