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
