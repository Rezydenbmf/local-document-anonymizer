"""Fail the build if the packaged exe is missing a module it needs.

This exists because of a real shipped bug. `ocr.py` and `ner.py` load
their optional dependencies through `importlib.import_module(name)`, and
PyInstaller resolves imports by reading source statically - it cannot see
a dynamic import, so `pytesseract` was never bundled. Nothing failed
loudly: the optional-import helper returned None exactly as it would on a
machine without the library, the app reported "Silnik Tesseract nie jest
zainstalowany", and the code that unpacks the bundled Tesseract never
even ran. The installer, the bundled engine and the extraction logic were
all fine; the app just could not see them.

What made it expensive was the verification gap, not the bug. It had been
"verified" by running the *source* through the dev virtualenv with
sys.frozen patched on - which proves the logic works, but says nothing
about what actually made it into the bundle, because the virtualenv has
every dependency installed. This script closes that gap by inspecting the
built artifact itself.

Run: python installer/verify_bundle.py dist/DocShield/DocShield.exe
Exits non-zero (and names what is missing) if anything is absent.
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

# Modules the app imports dynamically, plus the ones whose absence would
# silently disable a headline feature. Keep in sync with
# DocShield.spec's DYNAMIC_OPTIONAL_IMPORTS.
REQUIRED_MODULES = (
    "pytesseract",  # OCR for scans - the one that actually shipped broken
    "spacy",  # NER
    "pl_core_news_sm",  # the Polish NER model itself
    "PIL.Image",  # image handling for OCR
    "pymupdf",  # PDF geometry / redaction
    "docx",  # DOCX output
    "pypdf",
    "zipfile",  # unpacks the bundled Tesseract runtime
    "customtkinter",
    "tkinterdnd2",
)

# Files the installer must find next to the exe.
REQUIRED_FILES = ("tesseract_runtime.zip",)


def bundled_modules(exe_path: Path) -> set[str]:
    """Every module name inside the exe's embedded PYZ archive."""
    from PyInstaller.archive.readers import CArchiveReader, ZlibArchiveReader

    archive = CArchiveReader(str(exe_path))
    with tempfile.TemporaryDirectory() as staging:
        pyz_path = Path(staging) / "PYZ.pyz"
        pyz_path.write_bytes(archive.extract("PYZ.pyz"))
        return set(ZlibArchiveReader(str(pyz_path)).toc.keys())


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("Uzycie: python verify_bundle.py <sciezka/do/DocShield.exe>")
        return 2

    exe_path = Path(argv[1]).resolve()
    if not exe_path.is_file():
        print(f"BLAD: nie znaleziono {exe_path}")
        return 1

    modules = bundled_modules(exe_path)
    missing_modules = [name for name in REQUIRED_MODULES if name not in modules]

    bundle_dir = exe_path.parent
    missing_files = [
        name for name in REQUIRED_FILES if not (bundle_dir / name).is_file()
    ]

    print(f"Modulow w paczce: {len(modules)}")
    for name in REQUIRED_MODULES:
        status = "BRAK" if name in missing_modules else "OK"
        print(f"  {name:20} {status}")
    for name in REQUIRED_FILES:
        status = "BRAK" if name in missing_files else "OK"
        print(f"  {name:20} {status}")

    if missing_modules or missing_files:
        print()
        if missing_modules:
            print(f"BRAKUJE MODULOW: {', '.join(missing_modules)}")
            print(
                "Dodaj je do DYNAMIC_OPTIONAL_IMPORTS w DocShield.spec "
                "(PyInstaller nie widzi importow przez import_module)."
            )
        if missing_files:
            print(f"BRAKUJE PLIKOW: {', '.join(missing_files)}")
        return 1

    print("\nPaczka kompletna.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
