# PyInstaller spec: builds dist/BeautifulVoice/BeautifulVoice.exe
# Run from the repository root:  pyinstaller packaging/beautiful_voice.spec --noconfirm
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs, collect_submodules, copy_metadata

root = Path(SPECPATH).parent

datas = [(str(root / "beautiful_voice" / "qml"), "beautiful_voice/qml")]
datas += collect_data_files("faster_whisper")  # Silero VAD model
datas += collect_data_files("onnx_asr")  # mel preprocessors
datas += copy_metadata("onnx-asr")  # it looks up its own version at import time
binaries = collect_dynamic_libs("ctranslate2") + collect_dynamic_libs("sherpa_onnx")
hiddenimports = collect_submodules("onnx_asr") + collect_submodules("sherpa_onnx")

a = Analysis(
    [str(root / "run.pyw")],
    pathex=[str(root)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    excludes=["tkinter", "matplotlib", "torch", "tensorflow"],
    noarchive=False,
)
# PyInstaller's PySide6 hooks pull in every Qt module. The app only needs Qt
# Quick (Controls/Basic, Layouts, Shapes, Effects), so drop the rest: Qt
# WebEngine alone is ~190 MB.
UNUSED_QT = (
    "webengine", "qt6pdf", "/qtpdf", "qt63d", "/qt3d", "quick3d", "charts", "graphs", "datavisualization",
    "location", "positioning", "sensors", "scxml", "remoteobjects", "spatialaudio", "qt6sql", "/qtsql",
    "sqldrivers", "qt6test", "/qttest", "texttospeech", "virtualkeyboard", "webchannel", "websockets", "webview",
    "bluetooth", "qt6nfc", "serialport", "multimedia", "statemachine", "qt6help", "designer", "5compat",
    "controls2imagine", "controls2material", "controls2universal", "controls2fusion", "controls2fluentwinui3",
    "controls/imagine", "controls/material", "controls/universal", "controls/fusion", "controls/fluentwinui3",
    "controls/ios", "controls/macos", "labsstylekit", "opengl32sw",
)


def _needed(entry):
    name = entry[0].replace("\\", "/").lower()
    return not any(part in name for part in UNUSED_QT)


a.binaries = [b for b in a.binaries if _needed(b)]
a.datas = [d for d in a.datas if _needed(d)]

pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="BeautifulVoice",
    console=False,
    icon=str(root / "packaging" / "icon.ico"),
)
coll = COLLECT(exe, a.binaries, a.datas, name="BeautifulVoice")
