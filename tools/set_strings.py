"""Add or replace interface strings in every locale at once.

    python tools/set_strings.py strings.json

strings.json maps each key to its text per language:
    {"set_caption": {"en": "Show text while I speak", "ru": "...", ...}}
Existing keys are replaced in place; new ones are appended to STRINGS.
"""

import json
import re
import sys
from pathlib import Path

LOCALES = Path(__file__).resolve().parent.parent / "beautiful_voice" / "locales"

data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
for f in sorted(LOCALES.glob("*.py")):
    if f.name == "__init__.py":
        continue
    lang, text = f.stem, f.read_text(encoding="utf-8")
    for key, values in data.items():
        value = json.dumps(values[lang], ensure_ascii=False)
        pattern = re.compile(r'("' + re.escape(key) + r'":\s*)"(?:[^"\\]|\\.)*"')
        text, found = pattern.subn(lambda m: m.group(1) + value, text)
        if not found:
            end = text.rstrip().rfind("}")
            text = text[:end].rstrip() + f'\n    "{key}": {value},\n' + text[end:]
    f.write_text(text, encoding="utf-8")
    print(lang, "updated")
