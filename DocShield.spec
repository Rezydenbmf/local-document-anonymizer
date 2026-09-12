# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller build spec for the DocShield alpha demo build.

Produces a one-folder (--onedir) bundle rather than a single .exe:
onedir starts faster, and it gives Tesseract - a native binary this
app shells out to, not a Python library, so PyInstaller cannot pack it
itself - somewhere to live right next to DocShield.exe (see
build_installer.ps1, which copies a trimmed Tesseract runtime into
dist/DocShield/tesseract/ after this spec runs).

Build with:  pyinstaller DocShield.spec --noconfirm
(build_installer.ps1 does this, plus the Tesseract copy step and the
Inno Setup compile, in one command.)
"""

from PyInstaller.utils.hooks import collect_all

block_cipher = None

# pl_core_news_sm is a separate pip-installed package (the Polish spaCy
# model), not something spacy's own PyInstaller hook reaches - it needs
# its submodules, data files (the model weights) and any binaries
# collected explicitly, or spacy.load("pl_core_news_sm") finds nothing
# at runtime despite importing cleanly.
spacy_model_datas, spacy_model_binaries, spacy_model_hidden = collect_all(
    "pl_core_news_sm"
)

a = Analysis(
    ["src/main.py"],
    pathex=["src"],
    binaries=spacy_model_binaries,
    datas=[
        ("assets/icon.ico", "assets"),
        ("assets/icon.png", "assets"),
    ]
    + spacy_model_datas,
    hiddenimports=spacy_model_hidden,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="DocShield",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    icon="assets/icon.ico",
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    name="DocShield",
)
