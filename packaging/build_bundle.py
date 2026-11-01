"""Freeze the desktop app with PyInstaller. Run from the repo root: python packaging/build_bundle.py

Output: dist/Summarizer/ on every system, plus dist/Summarizer.app on macOS.
The installers (Inno Setup, WiX, hdiutil, nfpm, appimagetool) are all made from this one bundle.
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ICONS = ROOT / "packaging" / "icons"
SEP = ";" if sys.platform == "win32" else ":"

args = [
    sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean",
    "--name", "Summarizer", "--windowed", "--onedir",
    "--distpath", str(ROOT / "dist"), "--workpath", str(ROOT / "build"), "--specpath", str(ROOT / "build"),
    "--add-data", f"{ROOT / 'text_summarizer' / 'static'}{SEP}text_summarizer/static",
]
for pkg in ("fastembed", "onnxruntime", "pysbd", "trafilatura", "justext", "courlan", "htmldate"):
    args += ["--collect-all", pkg]
if sys.platform == "win32":
    args += ["--icon", str(ICONS / "icon.ico")]
elif sys.platform == "darwin":
    args += ["--icon", str(ICONS / "icon.icns"), "--osx-bundle-identifier", "io.github.aweebtaku.summarizer"]
args.append(str(ROOT / "text_summarizer" / "desktop.py"))

print(" ".join(args))
sys.exit(subprocess.call(args, cwd=ROOT))
