"""Lightweight startup checks for optional local dependencies.

The app degrades gracefully per feature already (NER, OCR, local LLM
review each have their own status handling deep in the pipeline), but
until now a user only discovered a missing piece by hitting a per-file
error mid-batch (see the scanned-PDF-without-Tesseract case that prompted
this module). These checks let the GUI tell the user up front what will
and won't work, and offer a one-click fix where one exists.

Every check function here is side-effect-free and deliberately cheap: it
never loads a full spaCy pipeline, never runs real OCR, and never blocks
on a slow network call for long. `check_environment()` is still slow
enough (importing spaCy alone takes a second or so) that callers should
run it off the GUI thread rather than during window construction.
"""

from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass

try:
    from .llm_review import LLM_STATUS_OLLAMA_NOT_FOUND, list_installed_models
    from .ner import (
        DEFAULT_NER_MODEL,
        NER_STATUS_AVAILABLE,
        NER_STATUS_DEPENDENCY_MISSING,
        check_ner_model_installed,
    )
    from .ocr import (
        COMMON_OCR_LANGUAGES_PL,
        OCR_INPUT_TYPE_IMAGE,
        OCR_STATUS_AVAILABLE,
        PRIMARY_OCR_LANGUAGE,
        detect_ocr_support,
        download_language_pack,
        list_installed_languages,
    )
except ImportError:
    from llm_review import LLM_STATUS_OLLAMA_NOT_FOUND, list_installed_models
    from ner import (
        DEFAULT_NER_MODEL,
        NER_STATUS_AVAILABLE,
        NER_STATUS_DEPENDENCY_MISSING,
        check_ner_model_installed,
    )
    from ocr import (
        COMMON_OCR_LANGUAGES_PL,
        OCR_INPUT_TYPE_IMAGE,
        OCR_STATUS_AVAILABLE,
        PRIMARY_OCR_LANGUAGE,
        detect_ocr_support,
        download_language_pack,
        list_installed_languages,
    )


ENV_ITEM_NER = "ner"
ENV_ITEM_OCR = "ocr"
ENV_ITEM_LLM = "llm"

INSTALL_ACTION_SPACY_MODEL = "spacy_model_download"
INSTALL_ACTION_OPEN_URL = "open_url"
INSTALL_ACTION_TESSDATA_DOWNLOAD = "tessdata_download"

TESSERACT_DOWNLOAD_URL = "https://github.com/UB-Mannheim/tesseract/wiki"
OLLAMA_DOWNLOAD_URL = "https://ollama.com/download"


@dataclass(frozen=True)
class EnvironmentCheckItem:
    """One optional-dependency check result, safe to show directly in the UI."""

    item: str
    ok: bool
    label_pl: str
    detail_pl: str
    install_action: str | None = None
    install_target: str | None = None


def check_ner_environment(model_name: str = DEFAULT_NER_MODEL) -> EnvironmentCheckItem:
    status = check_ner_model_installed(model_name)
    if status == NER_STATUS_AVAILABLE:
        return EnvironmentCheckItem(
            ENV_ITEM_NER, True, "Rozpoznawanie AI (NER)", "Dostępne."
        )
    if status == NER_STATUS_DEPENDENCY_MISSING:
        return EnvironmentCheckItem(
            ENV_ITEM_NER,
            False,
            "Rozpoznawanie AI (NER)",
            "Brakuje biblioteki spaCy - uruchom ponownie "
            "\"pip install -r requirements.txt\" w środowisku aplikacji.",
        )
    return EnvironmentCheckItem(
        ENV_ITEM_NER,
        False,
        "Rozpoznawanie AI (NER)",
        f"Brakuje lokalnego modelu językowego ({model_name}) - bez niego appka nie "
        "wykryje automatycznie imion, firm i miejsc (reszta wykrywania działa normalnie).",
        install_action=INSTALL_ACTION_SPACY_MODEL,
        install_target=model_name,
    )


def check_ocr_environment() -> EnvironmentCheckItem:
    """OCR is only really "available" for this app once the Tesseract
    *engine* is installed AND the Polish language pack specifically is
    present - Polish is this app's baseline language (see ocr.py's
    PRIMARY_OCR_LANGUAGE), so an English-only Tesseract install passes
    the old engine-only check but still produces the garbled OCR text
    that prompted this whole check in the first place. Both cases get
    their own distinct, actionable message rather than one generic
    "unavailable".
    """
    metadata = detect_ocr_support(OCR_INPUT_TYPE_IMAGE)
    status = metadata.get("status")
    if status != OCR_STATUS_AVAILABLE:
        return EnvironmentCheckItem(
            ENV_ITEM_OCR,
            False,
            "OCR (skany, obrazy)",
            "Silnik Tesseract nie jest zainstalowany - skany i obrazy bez warstwy "
            "tekstowej nie zostaną przetworzone (pozostałe pliki działają normalnie).",
            install_action=INSTALL_ACTION_OPEN_URL,
            install_target=TESSERACT_DOWNLOAD_URL,
        )

    installed_languages = list_installed_languages()
    if PRIMARY_OCR_LANGUAGE not in installed_languages:
        return EnvironmentCheckItem(
            ENV_ITEM_OCR,
            False,
            "OCR (skany, obrazy)",
            "Tesseract jest zainstalowany, ale brakuje polskiego pakietu "
            "językowego - podstawowego dla tej aplikacji. Bez niego OCR "
            "czyta skany po angielsku i myli polskie znaki (np. \"zawarta\" "
            "wychodzi jako \"zaware\").",
            install_action=INSTALL_ACTION_TESSDATA_DOWNLOAD,
            install_target=PRIMARY_OCR_LANGUAGE,
        )

    language_names = ", ".join(
        COMMON_OCR_LANGUAGES_PL.get(code, code) for code in installed_languages
    )
    return EnvironmentCheckItem(
        ENV_ITEM_OCR,
        True,
        "OCR (skany, obrazy)",
        f"Dostępne (języki: {language_names})." if language_names else "Dostępne.",
    )


def install_tesseract_language(lang_code: str) -> tuple[bool, str]:
    """Download one Tesseract language pack - see ocr.download_language_pack
    for what makes this safely automatable (a plain data file, not an
    installer) unlike Tesseract/Ollama themselves."""
    return download_language_pack(lang_code)


def check_llm_environment() -> EnvironmentCheckItem:
    status, _models = list_installed_models()
    if status != LLM_STATUS_OLLAMA_NOT_FOUND:
        return EnvironmentCheckItem(
            ENV_ITEM_LLM, True, "Dodatkowa weryfikacja AI (LLM)", "Dostępne (opcjonalne)."
        )
    return EnvironmentCheckItem(
        ENV_ITEM_LLM,
        False,
        "Dodatkowa weryfikacja AI (LLM)",
        "Ollama nie jest zainstalowana - to funkcja opcjonalna (domyślnie wyłączona) "
        "do dodatkowej weryfikacji po anonimizacji.",
        install_action=INSTALL_ACTION_OPEN_URL,
        install_target=OLLAMA_DOWNLOAD_URL,
    )


def refresh_path_from_registry() -> None:
    """On Windows, merge the current User+Machine PATH from the registry
    into this process's `os.environ["PATH"]`.

    Installing Tesseract or Ollama updates the registry immediately, but
    an already-running process - including this app, if it was open
    during the install - keeps the PATH snapshot it started with. Without
    this, clicking "Sprawdz ponownie" could never find a tool installed
    after the app opened; only a full app restart would pick it up. This
    makes the re-check button actually work in that case. Safe no-op on
    any error or a non-Windows platform - it never blocks or fails the
    check that calls it, it only ever adds entries, never removes any.
    """
    if sys.platform != "win32":
        return
    try:
        import winreg
    except ImportError:  # pragma: no cover - always present on win32
        return

    def _read(hive: int, subkey: str) -> str:
        try:
            with winreg.OpenKey(hive, subkey) as key:
                value, _ = winreg.QueryValueEx(key, "Path")
                return str(value or "")
        except OSError:
            return ""

    machine_path = _read(
        winreg.HKEY_LOCAL_MACHINE,
        r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment",
    )
    user_path = _read(winreg.HKEY_CURRENT_USER, "Environment")

    entries = [p for p in os.environ.get("PATH", "").split(os.pathsep) if p]
    seen = {p.casefold() for p in entries}
    for extra in (machine_path, user_path):
        for entry in extra.split(os.pathsep):
            entry = entry.strip()
            if entry and entry.casefold() not in seen:
                entries.append(entry)
                seen.add(entry.casefold())
    os.environ["PATH"] = os.pathsep.join(entries)


def check_environment(model_name: str = DEFAULT_NER_MODEL) -> list[EnvironmentCheckItem]:
    """Run every startup check and return one item per optional dependency.

    MAINTENANCE NOTE: this list is not auto-discovered - it is the
    complete, explicit set of optional local dependencies the app knows
    to check. Any future optional dependency (another OCR/LLM backend,
    a second NER model, a new local engine, ...) needs its own
    check_*_environment() added here, or the user will silently lose the
    startup warning + one-click fix for it, exactly the gap this module
    was built to close in the first place.
    """
    refresh_path_from_registry()
    return [
        check_ner_environment(model_name),
        check_ocr_environment(),
        check_llm_environment(),
    ]


def install_ner_model(
    model_name: str = DEFAULT_NER_MODEL, timeout_seconds: int = 300
) -> tuple[bool, str]:
    """Run `python -m spacy download <model_name>` in the app's own venv.

    A real, contained install (a package download inside the existing
    Python environment, no admin rights, no system changes) - unlike
    Tesseract/Ollama, which are external installers this app cannot
    safely run unattended and instead just points the user to.
    """
    try:
        completed = subprocess.run(
            [sys.executable, "-m", "spacy", "download", model_name],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_seconds,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        return False, str(error)
    if completed.returncode == 0:
        return True, ""
    return False, (completed.stderr or completed.stdout or "").strip()[-800:]


__all__ = [
    "ENV_ITEM_LLM",
    "ENV_ITEM_NER",
    "ENV_ITEM_OCR",
    "INSTALL_ACTION_OPEN_URL",
    "INSTALL_ACTION_SPACY_MODEL",
    "INSTALL_ACTION_TESSDATA_DOWNLOAD",
    "OLLAMA_DOWNLOAD_URL",
    "TESSERACT_DOWNLOAD_URL",
    "EnvironmentCheckItem",
    "check_environment",
    "check_llm_environment",
    "check_ner_environment",
    "check_ocr_environment",
    "install_ner_model",
    "install_tesseract_language",
    "refresh_path_from_registry",
]
