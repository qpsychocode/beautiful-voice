"""Draw the installer's side and corner images (packaging/wizard*.bmp).

Rendered here rather than in CI because it needs the Sitka font that ships
with Windows; the BMPs are committed.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PySide6.QtCore import QPointF, QRectF, Qt  # noqa: E402
from PySide6.QtGui import QColor, QFont, QImage, QLinearGradient, QPainter, QRadialGradient  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from beautiful_voice.tray import draw_logo  # noqa: E402

BLUE, PINK, INK = QColor("#DCE4FF"), QColor("#FBDDEC"), QColor("#1E1F35")
OUT = Path(__file__).resolve().parent.parent / "packaging"


def side(scale: int) -> QImage:
    w, h = 164 * scale, 314 * scale
    img = QImage(w, h, QImage.Format.Format_RGB32)
    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setRenderHint(QPainter.RenderHint.TextAntialiasing)
    grad = QLinearGradient(0, 0, w * 0.4, h)
    grad.setColorAt(0, BLUE)
    grad.setColorAt(1, PINK)
    p.fillRect(img.rect(), grad)
    for cx, cy, r, a in ((-0.2, -0.05, 0.9, 90), (1.1, 1.0, 0.8, 70)):
        glow = QRadialGradient(QPointF(w * cx, h * cy), w * r)
        glow.setColorAt(0, QColor(255, 255, 255, a))
        glow.setColorAt(1, QColor(255, 255, 255, 0))
        p.fillRect(img.rect(), glow)
    logo = draw_logo(56 * scale)
    p.drawPixmap(int((w - logo.width()) / 2), int(h * 0.30), logo)
    serif = QFont("Sitka Display")
    serif.setItalic(True)
    serif.setPixelSize(27 * scale)
    p.setFont(serif)
    p.setPen(INK)
    p.drawText(QRectF(0, h * 0.30 + 66 * scale, w, 36 * scale), Qt.AlignmentFlag.AlignHCenter, "Beautiful")
    caps = QFont("Segoe UI Variable Display")
    caps.setPixelSize(10 * scale)
    caps.setWeight(QFont.Weight.DemiBold)
    caps.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 4.2 * scale)
    p.setFont(caps)
    p.setPen(QColor("#666987"))
    p.drawText(QRectF(0, h * 0.30 + 102 * scale, w, 16 * scale), Qt.AlignmentFlag.AlignHCenter, "VOICE")
    p.end()
    return img


def corner(scale: int) -> QImage:
    s_w, s_h = 55 * scale, 58 * scale
    img = QImage(s_w, s_h, QImage.Format.Format_RGB32)
    img.fill(QColor("#FFFFFF"))
    p = QPainter(img)
    logo = draw_logo(44 * scale)
    p.drawPixmap(int((s_w - logo.width()) / 2), int((s_h - logo.height()) / 2), logo)
    p.end()
    return img


app = QApplication([])
for scale in (1, 2):
    side(scale).save(str(OUT / f"wizard-{scale}x.bmp"))
    corner(scale).save(str(OUT / f"wizard-small-{scale}x.bmp"))
print("installer art written")
