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

# Every optional dependency this app loads through importlib rather than a
# plain `import` statement. PyInstaller resolves imports by reading the
# source statically, so `import_module("pytesseract")` (ocr._import_optional)
# and `import_module("spacy")` (ner.py) are invisible to it - the module
# simply never lands in the bundle, the optional-import helper quietly
# returns None, and the app reports the dependency as "not installed" on a
# machine where nothing is actually wrong.
#
# That is exactly how the first packaged build shipped with OCR dead:
# pytesseract was missing, so detect_ocr_support() bailed out at its first
# check and the code that finds (and unpacks) the bundled Tesseract never
# ran at all. spacy survives on its own via pyinstaller-hooks-contrib, but
# it is listed here too - relying on a third-party hook to keep covering a
# dynamic import is the same silent failure waiting to happen again.
#
# installer/verify_bundle.py enforces this list against the built exe.
DYNAMIC_OPTIONAL_IMPORTS = [
    "pytesseract",
    "spacy",
]

a = Analysis(
    ["src/main.py"],
    pathex=["src"],
    binaries=spacy_model_binaries,
    datas=[
        ("assets/icon.ico", "assets"),
        ("assets/icon.png", "assets"),
    ]
    + spacy_model_datas,
    hiddenimports=spacy_model_hidden + DYNAMIC_OPTIONAL_IMPORTS,
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
