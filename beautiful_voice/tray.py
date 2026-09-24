"""Tray icon and the app icon, drawn in code so there are no image assets to keep in sync."""

from __future__ import annotations

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QAction, QColor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QMenu, QSystemTrayIcon

BLUE = QColor("#7C9CF5")
PINK = QColor("#F4A6C6")
ONYX = QColor("#101019")
BARS = (0.34, 0.62, 0.9, 0.56, 0.3)


def _mix(a: QColor, b: QColor, t: float) -> QColor:
    return QColor.fromRgbF(a.redF() + (b.redF() - a.redF()) * t, a.greenF() + (b.greenF() - a.greenF()) * t,
                           a.blueF() + (b.blueF() - a.blueF()) * t)


def draw_logo(size: int, recording: bool = False) -> QPixmap:
    pix = QPixmap(size, size)
    pix.fill(Qt.GlobalColor.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(ONYX)
    p.drawRoundedRect(QRectF(0, 0, size, size), size * 0.3, size * 0.3)
    bar_w = size * 0.1
    gap = size * 0.07
    total = len(BARS) * bar_w + (len(BARS) - 1) * gap
    x = (size - total) / 2
    for i, h in enumerate(BARS):
        height = size * 0.64 * (h if not recording else min(1.0, h + 0.25))
        p.setBrush(PINK if recording else _mix(BLUE, PINK, i / (len(BARS) - 1)))
        p.drawRoundedRect(QRectF(x, (size - height) / 2, bar_w, height), bar_w / 2, bar_w / 2)
        x += bar_w + gap
    p.end()
    return pix


def app_icon(recording: bool = False) -> QIcon:
    icon = QIcon()
    for s in (16, 20, 24, 32, 40, 48, 64, 128, 256):
        icon.addPixmap(draw_logo(s, recording))
    return icon


class Tray(QSystemTrayIcon):
    def __init__(self, backend, parent=None) -> None:
        super().__init__(app_icon(), parent)
        self.backend = backend
        self._idle_icon = app_icon(False)
        self._rec_icon = app_icon(True)
        self.menu = QMenu()
        self.open_action = QAction(self.menu)
        self.dictate_action = QAction(self.menu)
        self.quit_action = QAction(self.menu)
        self.open_action.triggered.connect(backend.showMain)
        self.dictate_action.triggered.connect(backend.toggleDictation)
        self.quit_action.triggered.connect(backend.quitApp)
        self.menu.addAction(self.open_action)
        self.menu.addAction(self.dictate_action)
        self.menu.addSeparator()
        self.menu.addAction(self.quit_action)
        self.setContextMenu(self.menu)
        self.activated.connect(self._on_activated)
        backend.stateChanged.connect(self._on_state)
        backend.languageChanged.connect(self.retranslate)
        backend.hotkeyChanged.connect(self.retranslate)
        backend.windowHiddenFirstTime.connect(self._explain_background)
        self.retranslate()

    def retranslate(self) -> None:
        tr = self.backend.tr
        hotkey = "+".join(self.backend.hotkeyKeys)
        self.setToolTip(f"Beautiful Voice — {hotkey}")
        self.open_action.setText(tr("tray_open"))
        recording = self.backend.state == "recording"
        self.dictate_action.setText(f"{tr('tray_stop' if recording else 'tray_start')}\t{hotkey}")
        self.quit_action.setText(tr("tray_quit"))

    def _on_state(self) -> None:
        self.setIcon(self._rec_icon if self.backend.state == "recording" else self._idle_icon)
        self.retranslate()

    def _on_activated(self, reason) -> None:
        if reason in (QSystemTrayIcon.ActivationReason.Trigger, QSystemTrayIcon.ActivationReason.DoubleClick):
            self.backend.showMain()

    def _explain_background(self) -> None:
        hotkey = "+".join(self.backend.hotkeyKeys)
        self.showMessage("Beautiful Voice", self.backend.tr("tray_background", hotkey=hotkey), self._idle_icon, 4000)
