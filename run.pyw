"""Double-click launcher (no console window). Also used by the autostart entry."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from beautiful_voice.app import main  # noqa: E402

sys.exit(main())
