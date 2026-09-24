"""Write packaging/icon.ico and docs/icon.png from the same drawing the app uses at runtime.

The .ico holds every size Windows asks for (16 px in lists up to 256 px in
large views), each drawn at its own size rather than scaled, so small icons
stay crisp.
"""

import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PySide6.QtCore import QBuffer, QByteArray, QIODevice  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from beautiful_voice.tray import draw_logo  # noqa: E402

SIZES = (16, 20, 24, 32, 40, 48, 64, 96, 128, 256)


def png_bytes(size: int) -> bytes:
    data = QByteArray()
    buf = QBuffer(data)
    buf.open(QIODevice.OpenModeFlag.WriteOnly)
    draw_logo(size).save(buf, "PNG")
    return bytes(data)


def write_ico(path: Path) -> None:
    images = [(s, png_bytes(s)) for s in SIZES]
    header = struct.pack("<HHH", 0, 1, len(images))
    offset = 6 + 16 * len(images)
    entries, blobs = b"", b""
    for size, blob in images:
        dim = 0 if size >= 256 else size  # 0 means 256 in the ICO directory
        entries += struct.pack("<BBBBHHII", dim, dim, 0, 0, 1, 32, len(blob), offset + len(blobs))
        blobs += blob
    path.write_bytes(header + entries + blobs)


root = Path(__file__).resolve().parent.parent
app = QApplication([])
(root / "packaging").mkdir(exist_ok=True)
(root / "site").mkdir(exist_ok=True)
draw_logo(256).save(str(root / "docs" / "icon.png"))
draw_logo(256).save(str(root / "site" / "icon.png"))
write_ico(root / "packaging" / "icon.ico")
print("icons written:", ", ".join(map(str, SIZES)))

if sys.platform == "darwin":
    # macOS wants an .icns; iconutil builds it from a folder of named PNGs.
    import subprocess
    import tempfile

    iconset = Path(tempfile.mkdtemp()) / "icon.iconset"
    iconset.mkdir()
    for size in (16, 32, 128, 256, 512):
        draw_logo(size).save(str(iconset / f"icon_{size}x{size}.png"))
        draw_logo(size * 2).save(str(iconset / f"icon_{size}x{size}@2x.png"))
    subprocess.run(["iconutil", "-c", "icns", str(iconset), "-o", str(root / "packaging" / "icon.icns")], check=True)
    print("icon.icns written")
