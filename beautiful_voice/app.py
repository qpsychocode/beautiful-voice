"""Application entry point: wires settings, models, hotkeys, tray and QML together."""

from __future__ import annotations

import argparse
import getpass
import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from PySide6.QtCore import QTimer, QUrl
from PySide6.QtNetwork import QLocalServer, QLocalSocket
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuickControls2 import QQuickStyle
from PySide6.QtWidgets import QApplication

from . import autostart, winstyle
from .backend import Backend
from .benchmark import BenchStore
from .config import SettingsStore
from .dictation import Dictation
from .history import History
from .hotkeys import HotkeyService
from .i18n import I18n, best_match
from .models.catalog import CATALOG, RECOMMENDED, by_id
from .models.manager import ModelManager
from .paths import APP_NAME, APP_TITLE, APP_VERSION, data_dir, qml_dir
from .tray import Tray, app_icon
from .updates import Updater

TITLE_COLORS = {"light": ("#F3F4FB", "#1E1F35"), "dark": ("#11121E", "#EEEDF8")}


def _instance_key() -> str:
    return f"{APP_NAME}-{getpass.getuser()}"


def _ping_running_instance() -> bool:
    """If Beautiful Voice is already running, ask it to show its window."""
    socket = QLocalSocket()
    socket.connectToServer(_instance_key())
    if not socket.waitForConnected(300):
        return False
    socket.write(b"show")
    socket.waitForBytesWritten(300)
    socket.disconnectFromServer()
    return True


log = logging.getLogger("beautiful_voice")


def _setup_logging() -> None:
    """app.log in the data folder: what happened, never what was said."""
    handler = RotatingFileHandler(data_dir() / "app.log", maxBytes=1_000_000, backupCount=2, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.addHandler(handler)
    sys.excepthook = lambda t, v, tb: log.critical("unhandled error", exc_info=(t, v, tb))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="beautiful-voice")
    parser.add_argument("--minimized", action="store_true", help="start in the tray without opening the window")
    parser.add_argument("--shots", type=Path, help=argparse.SUPPRESS)  # render screenshots and quit
    args = parser.parse_args(argv)

    if sys.platform == "win32":
        import ctypes

        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("qpsycho.BeautifulVoice")

    QQuickStyle.setStyle("Basic")
    app = QApplication(sys.argv[:1])
    app.setApplicationName(APP_TITLE)
    app.setOrganizationName(APP_NAME)
    app.setWindowIcon(app_icon())
    app.setQuitOnLastWindowClosed(False)

    if not args.shots and _ping_running_instance():
        return 0
    server = QLocalServer()
    QLocalServer.removeServer(_instance_key())
    server.listen(_instance_key())

    _setup_logging()
    log.info("start %s on %s, frozen=%s", APP_VERSION, sys.platform, getattr(sys, "frozen", False))
    store = SettingsStore()
    store.set("ui_language", best_match(store.get("ui_language")))  # fall back to English if not translated
    i18n = I18n(store.get("ui_language"))

    def fallback_language() -> str:
        lang = store.get("language")
        return lang if lang != "auto" else i18n.lang

    history = History(store.get("history_limit"))
    models = ModelManager(endpoint=lambda: store.get("hf_endpoint"), device=lambda: store.get("compute_device"),
                          language=fallback_language, source=lambda: store.get("model_source"))
    dictation = Dictation(store, models, history)
    backend = Backend(store, i18n, history, models, dictation, BenchStore())

    hotkeys = HotkeyService(dictation.hotkey_pressed, dictation.hotkey_released, dictation.escape_pressed)
    hotkeys.hold_mode = store.get("hotkey_mode") == "hold"
    if not args.shots:
        backend.report_hotkey_error(hotkeys.start(store.get("hotkey")))
    dictation.hotkeys = hotkeys
    backend.hotkeys = hotkeys

    engine = QQmlApplicationEngine()
    engine.addImportPath(str(qml_dir()))
    ctx = engine.rootContext()
    ctx.setContextProperty("backend", backend)
    ctx.setContextProperty("i18n", i18n)
    ctx.setContextProperty("modelsModel", backend.models_model)
    ctx.setContextProperty("historyModel", backend.history_model)
    ctx.setContextProperty("benchModel", backend.bench_model)
    updater = Updater()
    ctx.setContextProperty("updater", updater)
    engine.load(QUrl.fromLocalFile(str(qml_dir() / "Main.qml")))
    engine.load(QUrl.fromLocalFile(str(qml_dir() / "Overlay.qml")))
    roots = engine.rootObjects()
    if len(roots) < 2:
        print("Failed to load the interface", file=sys.stderr)
        return 1
    window, overlay = roots[0], roots[1]
    backend.overlay = overlay

    def apply_theme(theme: str) -> None:
        caption, text = TITLE_COLORS.get(theme, TITLE_COLORS["light"])
        winstyle.style_title_bar(window, theme == "dark", caption, text)

    def show_window() -> None:
        window.show()
        window.raise_()
        window.requestActivate()
        apply_theme(store.get("theme"))

    backend.themeChanged.connect(apply_theme)
    backend.showWindowRequested.connect(show_window)
    server.newConnection.connect(lambda: (server.nextPendingConnection(), show_window()))

    tray = Tray(backend)
    tray.show()

    def quit_app() -> None:
        tray.hide()
        app.quit()

    backend.quitRequested.connect(quit_app)
    updater.quitRequested.connect(quit_app)  # the installer takes over from here
    if args.shots:
        updater.check()  # so screenshots show the update card when one exists
    else:
        updater.start()

    # Keep the autostart entry pointing at this copy of the app.
    if store.get("autostart") and autostart.supported():
        autostart.set_enabled(True)

    # The overlay must never take focus from the app you're typing in.
    overlay.create()
    winstyle.make_no_activate(overlay)

    active = by_id(store.get("active_model"))
    installed = [s.id for s in CATALOG if models.installed(s)]
    log.info("models folder %s, installed: %s, saved choice: %s", models.root, installed or "none",
             store.get("active_model") or "none")
    if active is None or not models.installed(active):
        # First run, or the model was deleted: take the recommended one if it's on disk, else any.
        pick = RECOMMENDED if RECOMMENDED in installed else (installed[0] if installed else "")
        active = by_id(pick) if pick else None
    backend.activateModel(active.id if active else "")
    if active is None and not store.get("welcomed") and not args.shots:
        log.info("first start without a model: downloading %s", RECOMMENDED)
        # First start: fetch the default model right away. It becomes active when done.
        store.set("welcomed", True)
        backend.downloadModel(RECOMMENDED)

    if args.shots:
        from .shots import capture

        show_window()
        QTimer.singleShot(600, lambda: capture(app, window, overlay, backend, args.shots))
    elif not (args.minimized or store.get("start_minimized")):
        show_window()

    code = app.exec()
    hotkeys.stop()
    dictation.shutdown()
    models.shutdown()
    server.close()
    return code


if __name__ == "__main__":
    sys.exit(main())
