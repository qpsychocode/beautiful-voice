"""Every ``t.<key>`` used by the interface must exist in the translations."""

import re
from pathlib import Path

from beautiful_voice.i18n import STRINGS

QML = Path(__file__).resolve().parent.parent / "beautiful_voice" / "qml"


def test_qml_keys_are_translated():
    used = set()
    for f in QML.rglob("*.qml"):
        used |= set(re.findall(r"\b(?:page|card|window|i18n)\.t\.([a-z_0-9]+)", f.read_text(encoding="utf-8")))
    assert len(used) > 50
    missing = sorted(k for k in used if k not in STRINGS["en"])
    assert not missing, missing
