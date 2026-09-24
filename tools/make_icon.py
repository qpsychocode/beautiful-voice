"""Write packaging/icon.ico and docs/icon.png from the same drawing the app uses at runtime."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PySide6.QtGui import QImageWriter  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from beautiful_voice.tray import draw_logo  # noqa: E402

root = Path(__file__).resolve().parent.parent
app = QApplication([])
(root / "packaging").mkdir(exist_ok=True)
(root / "docs").mkdir(exist_ok=True)
draw_logo(256).save(str(root / "docs" / "icon.png"))
writer = QImageWriter(str(root / "packaging" / "icon.ico"), b"ico")
if not writer.write(draw_logo(256).toImage()):
    raise SystemExit(f"Could not write icon.ico: {writer.errorString()}")
print("icons written")
