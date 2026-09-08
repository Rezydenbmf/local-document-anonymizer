"""CustomTkinter GUI for batch anonymization."""

from collections.abc import Mapping
import os
from pathlib import Path
import subprocess
import sys
import tkinter as tk
from tkinter import filedialog

import customtkinter as ctk
from PIL import Image
from tkinterdnd2 import DND_FILES, TkinterDnD

try:
    from .audit import AUDIT_CATEGORY_ORDER
    from .file_readers import read_docx_file, read_txt_file
    from .anonymizer import (
        PDF_OUTPUT_MODE_ORIGINAL_REDACTION,
        PDF_OUTPUT_MODE_REBUILT_REVIEW,
        PDF_OUTPUT_MODE_VISUAL,
        PDF_REDACTION_SCOPE_SAFE,
        PDF_REDACTION_SCOPE_STRICT,
        SUPPORTED_LABELS,
        BatchResult,
        anonymize_batch,
    )
    from .llm_review import LLM_STATUS_AVAILABLE, list_installed_models
    from .report import (
        DICTIONARY_STATUS_INVALID,
        DICTIONARY_STATUS_LOADED,
        DICTIONARY_STATUS_NOT_SELECTED,
    )
    from .review import (
        REVIEW_STATUS_APPROVED,
        REVIEW_STATUS_NEEDS_REVIEW,
        REVIEW_STATUS_REJECTED,
        ReviewItem,
        apply_review_statuses,
        export_approved_workspace,
        load_review_workspace,
        preferred_review_output_path,
        save_review_files,
    )
except ImportError:
    from audit import AUDIT_CATEGORY_ORDER
    from file_readers import read_docx_file, read_txt_file
    from anonymizer import (
        PDF_OUTPUT_MODE_ORIGINAL_REDACTION,
        PDF_OUTPUT_MODE_REBUILT_REVIEW,
        PDF_OUTPUT_MODE_VISUAL,
        PDF_REDACTION_SCOPE_SAFE,
        PDF_REDACTION_SCOPE_STRICT,
        SUPPORTED_LABELS,
        BatchResult,
        anonymize_batch,
    )
    from llm_review import LLM_STATUS_AVAILABLE, list_installed_models
    from report import (
        DICTIONARY_STATUS_INVALID,
        DICTIONARY_STATUS_LOADED,
        DICTIONARY_STATUS_NOT_SELECTED,
    )
    from review import (
        REVIEW_STATUS_APPROVED,
        REVIEW_STATUS_NEEDS_REVIEW,
        REVIEW_STATUS_REJECTED,
        ReviewItem,
        apply_review_statuses,
        export_approved_workspace,
        load_review_workspace,
        preferred_review_output_path,
        save_review_files,
    )


APP_TITLE = "Anonimizer"
MANUAL_REVIEW_WARNING = (
    "Wymagany jest ręczny przegląd przed użyciem lub udostępnieniem wyniku."
)
WINDOW_MIN_WIDTH = 720
WINDOW_MIN_HEIGHT = 560
WINDOW_DEFAULT_SIZE = "960x680"
SELECTED_FILE_LIST_HEIGHT = 6
LLM_NO_MODELS_HINT = "No local Ollama models found. Install/pull a model first."
LLM_MODELS_FOUND_HINT = "Select a local Ollama model for optional LLM review."
PDF_OUTPUT_LABEL_VISUAL_REDACTION = (
    "Original-layout visual redaction from detected text (recommended)"
)
PDF_OUTPUT_LABEL_REBUILT_REVIEW = (
    "Rebuilt text review PDF (simple text only)"
)
PDF_OUTPUT_LABEL_ORIGINAL_SAFE = "Experimental original-layout redaction (safe scope)"
PDF_OUTPUT_LABEL_ORIGINAL_STRICT = (
    "Experimental original-layout redaction (strict scope, may over-redact)"
)
PDF_REDACTION_SCOPE_LABELS = {
    PDF_REDACTION_SCOPE_SAFE: PDF_OUTPUT_LABEL_ORIGINAL_SAFE,
    PDF_REDACTION_SCOPE_STRICT: PDF_OUTPUT_LABEL_ORIGINAL_STRICT,
}
PDF_OUTPUT_SETTINGS_BY_LABEL = {
    PDF_OUTPUT_LABEL_VISUAL_REDACTION: (
        PDF_OUTPUT_MODE_VISUAL,
        PDF_REDACTION_SCOPE_SAFE,
    ),
    PDF_OUTPUT_LABEL_REBUILT_REVIEW: (
        PDF_OUTPUT_MODE_REBUILT_REVIEW,
        PDF_REDACTION_SCOPE_SAFE,
    ),
    PDF_OUTPUT_LABEL_ORIGINAL_SAFE: (
        PDF_OUTPUT_MODE_ORIGINAL_REDACTION,
        PDF_REDACTION_SCOPE_SAFE,
    ),
    PDF_OUTPUT_LABEL_ORIGINAL_STRICT: (
        PDF_OUTPUT_MODE_ORIGINAL_REDACTION,
        PDF_REDACTION_SCOPE_STRICT,
    ),
}
SUPPORTED_EXTENSIONS = (
    ".txt",
    ".docx",
    ".pdf",
    ".png",
    ".jpg",
    ".jpeg",
    ".tif",
    ".tiff",
)
DEFAULT_OUTPUT_SUBDIR_NAME = "Anonimizer - wyniki"


def default_output_directory() -> Path:
    """Return the default output folder under the user's Documents folder."""
    return Path.home() / "Documents" / DEFAULT_OUTPUT_SUBDIR_NAME


def _file_word(count: int) -> str:
    return "file" if count == 1 else "files"


def format_selected_file_count(count: int) -> str:
    """Format the selected file count for the GUI."""
    if count < 0:
        raise ValueError("selected file count must not be negative")
    return f"Selected files: {count}"


def format_anonymize_readiness(input_file_count: int, has_output_dir: bool) -> str:
    """Format the readiness hint shown near the anonymization button."""
    if input_file_count < 0:
        raise ValueError("input file count must not be negative")

    missing_input_files = input_file_count == 0
    missing_output_folder = not has_output_dir

    if not missing_input_files and not missing_output_folder:
        return f"Ready to anonymize {input_file_count} file(s)."
    if missing_input_files and missing_output_folder:
        return "Add at least one input file and select an output folder."
    if missing_input_files:
        return "Add at least one input file."
    return "Select an output folder."


def format_processing_status(index: int, total: int, path: Path) -> str:
    """Format the visible per-file processing status."""
    if index < 1 or total < 1 or index > total:
        raise ValueError("processing index must be within the batch size")
    return f"Processing {index}/{total}: {path.name}\nPlease wait..."


def format_llm_model_selector_state(
    status: str,
    models: list[str] | tuple[str, ...],
) -> tuple[list[str], str, str]:
    """Return combobox values, default selection, and a safe GUI hint."""
    unique_models: list[str] = []
    for model in models:
        model_name = str(model or "").strip()
        if model_name and model_name not in unique_models:
            unique_models.append(model_name)

    if status == LLM_STATUS_AVAILABLE and unique_models:
        return unique_models, unique_models[0], LLM_MODELS_FOUND_HINT

    return [], "", LLM_NO_MODELS_HINT


def mousewheel_scroll_units(event: object) -> int:
    """Return comfortable canvas scroll units for mouse wheel/touchpad events."""
    event_num = getattr(event, "num", None)
    if event_num == 4:
        return -3
    if event_num == 5:
        return 3

    delta = int(getattr(event, "delta", 0) or 0)
    if delta == 0:
        return 0

    steps = max(1, abs(delta) // 120)
    direction = -1 if delta > 0 else 1
    return direction * steps * 3


def pdf_redaction_scope_from_gui_label(label: str) -> str:
    """Return the internal PDF redaction scope for a GUI combobox label."""
    settings = PDF_OUTPUT_SETTINGS_BY_LABEL.get(str(label).strip())
    if settings is None:
        return PDF_REDACTION_SCOPE_SAFE
    return settings[1]


def pdf_output_mode_from_gui_label(label: str) -> str:
    """Return the internal PDF output mode for a GUI combobox label."""
    settings = PDF_OUTPUT_SETTINGS_BY_LABEL.get(str(label).strip())
    if settings is None:
        return PDF_OUTPUT_MODE_VISUAL
    return settings[0]


def remove_paths_by_indexes(paths: list[Path], indexes: tuple[int, ...]) -> list[Path]:
    """Return paths with the selected GUI indexes removed."""
    remove_indexes = {index for index in indexes if 0 <= index < len(paths)}
    return [path for index, path in enumerate(paths) if index not in remove_indexes]


def format_batch_status(batch_result: BatchResult) -> str:
    """Format a plain-language safe batch status."""
    file_label = _file_word(batch_result.input_count)
    folder_name = batch_result.summary_path.parent.name or "selected output folder"
    if batch_result.error_count:
        result_text = (
            f"Processed {batch_result.success_count} of "
            f"{batch_result.input_count} selected {file_label}. "
            "Some files could not be processed; see the batch summary."
        )
    else:
        result_text = f"Processed all {batch_result.input_count} selected {file_label}."

    return (
        f"{result_text} Outputs were written to {folder_name}. "
        f"Batch summary: {batch_result.summary_path.name}. "
        "Manual review is required before using or sharing results."
    )


def format_approved_export_status(
    exported_output_count: int,
    copied_report_count: int,
    missing_report_count: int,
    index_name: str,
) -> str:
    """Format a safe approved workspace export status."""
    file_label = _file_word(exported_output_count)
    if missing_report_count:
        report_text = (
            f"Copied {copied_report_count} matching report(s); "
            f"{missing_report_count} report(s) were missing."
        )
    else:
        report_text = f"Copied {copied_report_count} matching report(s)."

    return (
        f"Exported {exported_output_count} approved _ANON {file_label} "
        f"to the approved workspace. {report_text} "
        f"Index: {index_name}. "
        "Approved is a manual user decision, not a guarantee of complete anonymization."
    )


def open_path_with_default_app(path: Path) -> None:
    """Open a local file with the operating system default application."""
    if not path.exists():
        raise FileNotFoundError(path)

    if hasattr(os, "startfile"):
        os.startfile(str(path))
        return

    opener = "open" if sys.platform == "darwin" else "xdg-open"
    subprocess.Popen([opener, str(path)])


def format_counters(counters: dict[str, int]) -> str:
    """Format anonymization counters without exposing source values."""
    labels = list(SUPPORTED_LABELS)
    for label in sorted(counters):
        if label not in labels:
            labels.append(label)

    lines = [f"{label}: {counters.get(label, 0)}" for label in labels]
    lines.append(f"TOTAL: {sum(counters.values())}")
    return "\n".join(lines)


def format_audit_result(audit_result: dict[str, object] | None) -> str:
    """Format safe audit metadata for the GUI."""
    if audit_result is None:
        return "Audit status: not run"

    status = audit_result.get("status")
    if status == "warning":
        lines = ["Audit status: WARNING - manual review required"]
    elif status == "ok":
        lines = ["Audit status: OK"]
    else:
        lines = ["Audit status: unknown"]

    risk_level = audit_result.get("risk_level")
    if risk_level in ("ok", "warning", "high_risk"):
        lines.append(f"Risk level: {risk_level}")

    findings = audit_result.get("findings")
    if not isinstance(findings, dict):
        lines.append("Possible remaining sensitive patterns: unavailable")
        return "\n".join(lines)

    non_zero = [
        (label, findings.get(label, 0))
        for label in AUDIT_CATEGORY_ORDER
        if findings.get(label, 0)
    ]
    if not non_zero:
        lines.append("Possible remaining sensitive patterns: none")
    else:
        lines.append("Possible remaining sensitive patterns:")
        for label, count in non_zero:
            lines.append(f"{label}: {count}")

    return "\n".join(lines)


def format_dictionary_result(dictionary_result: Mapping[str, object] | None) -> str:
    """Format safe dictionary workflow metadata for the GUI."""
    if dictionary_result is None:
        return "Dictionary status: not selected"

    status = dictionary_result.get("status")
    label_counters = dictionary_result.get("label_counters", {})
    if not isinstance(label_counters, Mapping):
        return "Dictionary status: unavailable"

    matches_found = any(
        isinstance(count, int) and count > 0 for count in label_counters.values()
    )

    if status == DICTIONARY_STATUS_NOT_SELECTED:
        return "Dictionary status: not selected"
    if status == DICTIONARY_STATUS_INVALID:
        return "Dictionary status: invalid; dictionary replacements skipped"
    if status == DICTIONARY_STATUS_LOADED:
        match_text = "yes" if matches_found else "no"
        return f"Dictionary status: loaded; matches found: {match_text}"

    return "Dictionary status: unknown"


def format_safe_path_list(paths: list[Path], empty_text: str) -> str:
    """Format selected paths as safe filenames only."""
    if not paths:
        return empty_text

    names = [path.name for path in paths]
    if len(names) <= 5:
        return ", ".join(names)
    return f"{', '.join(names[:5])}, and {len(names) - 5} more"


def format_batch_audit_result(batch_result: BatchResult | None) -> str:
    """Format aggregate audit status counts for the GUI."""
    if batch_result is None:
        return "Audit statuses: not run"

    counts = batch_result.audit_status_counts
    risk_counts = batch_result.risk_level_counts
    audit_counters = batch_result.audit_category_counters
    lines = [
        "Audit statuses:",
        f"OK: {counts.get('ok', 0)}",
        f"WARNING: {counts.get('warning', 0)}",
        f"Not run: {counts.get('not run', 0)}",
        "Risk levels:",
        f"ok: {risk_counts.get('ok', 0)}",
        f"warning: {risk_counts.get('warning', 0)}",
        f"high_risk: {risk_counts.get('high_risk', 0)}",
    ]

    non_zero_categories = [
        (label, audit_counters.get(label, 0))
        for label in AUDIT_CATEGORY_ORDER
        if audit_counters.get(label, 0)
    ]
    if non_zero_categories:
        lines.append("Audit warning categories:")
        for label, count in non_zero_categories:
            lines.append(f"{label}: {count}")
    ocr_used_count = sum(
        1 for result in batch_result.results if result.get("ocr_used") is True
    )
    ocr_unavailable_count = sum(
        1
        for result in batch_result.results
        if result.get("ocr_status")
        in ("dependency_missing", "engine_not_found", "unavailable")
    )
    lines.extend(
        [
            "OCR:",
            f"used: {ocr_used_count}",
            f"unavailable or failed: {ocr_unavailable_count}",
        ]
    )
    ner_used_count = sum(
        1 for result in batch_result.results if result.get("ner_used") is True
    )
    ner_unavailable_or_disabled_count = sum(
        1
        for result in batch_result.results
        if result.get("ner_status")
        in (
            "dependency_missing",
            "model_missing",
            "disabled",
            "unavailable",
            "processing_error",
        )
    )
    lines.extend(
        [
            "Local NER:",
            f"used: {ner_used_count}",
            f"unavailable or disabled: {ner_unavailable_or_disabled_count}",
        ]
    )
    llm_attempted_count = sum(
        1
        for result in batch_result.results
        if result.get("llm_review_status")
        in ("completed", "timeout", "invalid_response", "processing_error")
    )
    llm_attempt_failed_count = sum(
        1
        for result in batch_result.results
        if result.get("llm_review_status")
        in ("timeout", "invalid_response", "processing_error")
    )
    llm_unavailable_or_disabled_count = sum(
        1
        for result in batch_result.results
        if result.get("llm_review_status")
        in (
            "disabled",
            "unavailable",
            "ollama_not_found",
            "service_unavailable",
            "no_model_configured",
            "model_missing",
        )
    )
    llm_status_counts = batch_result.llm_review_status_counts
    ollama_unavailable_count = (
        llm_status_counts.get("ollama_not_found", 0)
        + llm_status_counts.get("service_unavailable", 0)
    )
    lines.extend(
        [
            "Local LLM review:",
            f"attempted: {llm_attempted_count}",
            f"attempted but failed safely: {llm_attempt_failed_count}",
            f"unavailable, disabled, or skipped: {llm_unavailable_or_disabled_count}",
            f"completed: {llm_status_counts.get('completed', 0)}",
            f"no model configured: {llm_status_counts.get('no_model_configured', 0)}",
            f"ollama unavailable: {ollama_unavailable_count}",
        ]
    )
    return "\n".join(lines)


def format_batch_dictionary_result(
    batch_result: BatchResult,
    sensitive_terms_path: Path | None,
) -> str:
    """Format safe aggregate dictionary status for a batch result."""
    if sensitive_terms_path is None:
        return format_dictionary_result(None)

    statuses = {
        result.get("dictionary_status")
        for result in batch_result.results
        if result.get("status") == "success"
    }
    if DICTIONARY_STATUS_INVALID in statuses:
        return "Dictionary status: invalid; dictionary replacements skipped"
    if DICTIONARY_STATUS_LOADED in statuses:
        return "Dictionary status: loaded; see per-file reports for match counts"
    return "Dictionary status: selected; no successful file reported dictionary status"


def file_type_badge(path: Path) -> str:
    """Return a short upper-case file-type badge label for a file card."""
    suffix = path.suffix.lower().lstrip(".")
    known = {
        "pdf": "PDF",
        "docx": "DOCX",
        "txt": "TXT",
        "png": "PNG",
        "jpg": "JPG",
        "jpeg": "JPG",
        "tif": "TIF",
        "tiff": "TIF",
    }
    if suffix in known:
        return known[suffix]
    return suffix[:4].upper() if suffix else "FILE"


def parse_dropped_file_paths(data: str) -> list[Path]:
    """Parse a tkinterdnd2 drop event data string into a list of paths.

    Multiple dropped paths are space-separated; a path containing spaces is
    wrapped in curly braces, e.g. "{C:/My Docs/a.pdf} C:/b.pdf".
    """
    text = str(data or "")
    paths: list[str] = []
    current: list[str] = []
    in_braces = False
    for char in text:
        if char == "{":
            in_braces = True
            continue
        if char == "}":
            in_braces = False
            paths.append("".join(current))
            current = []
            continue
        if char == " " and not in_braces:
            if current:
                paths.append("".join(current))
                current = []
            continue
        current.append(char)
    if current:
        paths.append("".join(current))
    return [Path(value) for value in paths if value]


def filter_supported_paths(paths: list[Path]) -> tuple[list[Path], list[Path]]:
    """Split paths into (supported, unsupported) by file extension."""
    supported: list[Path] = []
    unsupported: list[Path] = []
    for path in paths:
        if path.suffix.lower() in SUPPORTED_EXTENSIONS:
            supported.append(path)
        else:
            unsupported.append(path)
    return supported, unsupported


def _pl_file_word(count: int) -> str:
    """Return the grammatically correct Polish word for "file(s)"."""
    if count == 1:
        return "plik"
    last_digit = count % 10
    last_two = count % 100
    if 2 <= last_digit <= 4 and not (12 <= last_two <= 14):
        return "pliki"
    return "plików"


def format_drop_result(added_count: int, rejected_count: int) -> str:
    """Format a safe Polish status line after files are dropped or picked."""
    if added_count and rejected_count:
        return (
            f"Dodano {added_count} {_pl_file_word(added_count)}. "
            f"Pominięto {rejected_count} nieobsługiwanych "
            f"{_pl_file_word(rejected_count)}."
        )
    if added_count:
        return f"Dodano {added_count} {_pl_file_word(added_count)}."
    if rejected_count:
        return (
            f"Nie dodano plików - {rejected_count} nieobsługiwanych "
            f"{_pl_file_word(rejected_count)} pominięto."
        )
    return "Wybrane pliki były już na liście."


def format_readiness_pl(input_file_count: int, has_output_dir: bool) -> str:
    """Format the Polish readiness hint shown on the start screen."""
    if input_file_count < 0:
        raise ValueError("input file count must not be negative")

    missing_input_files = input_file_count == 0
    missing_output_folder = not has_output_dir

    if not missing_input_files and not missing_output_folder:
        return (
            f"Gotowe do anonimizacji: {input_file_count} "
            f"{_pl_file_word(input_file_count)}."
        )
    if missing_input_files and missing_output_folder:
        return "Dodaj co najmniej jeden plik i wybierz folder wynikowy."
    if missing_input_files:
        return "Dodaj co najmniej jeden plik."
    return "Wybierz folder wynikowy."


def format_short_path(path: Path, max_length: int = 48) -> str:
    """Shorten a long path for display, keeping the most relevant tail.

    Keeps whole path components starting from the end, adding one more as
    long as "...<sep><kept components>" still fits max_length, but always
    keeps at least the final component even if that alone is longer.
    """
    text = str(path)
    if len(text) <= max_length:
        return text

    kept: list[str] = []
    for part in reversed(path.parts):
        candidate = [part, *kept]
        prefixed = f"...{os.sep}{os.sep.join(candidate)}"
        if len(prefixed) > max_length and kept:
            break
        kept = candidate
    return f"...{os.sep}{os.sep.join(kept)}"


PDF_OUTPUT_SHORT_LABELS = {
    PDF_OUTPUT_LABEL_VISUAL_REDACTION: "PDF do przeglądu (polecane)",
    PDF_OUTPUT_LABEL_REBUILT_REVIEW: "Odtworzony tekst PDF",
    PDF_OUTPUT_LABEL_ORIGINAL_SAFE: "Eksperymentalny zamazany PDF",
    PDF_OUTPUT_LABEL_ORIGINAL_STRICT: "Eksperymentalny zamazany PDF (szeroki zakres)",
}


def risk_style_key(risk_level: str | None) -> str:
    """Return the RISK_STYLES key for a review item's risk level."""
    if risk_level in ("ok", "warning", "high_risk"):
        return risk_level
    return "unknown"


def review_status_label_pl(status: str) -> str:
    """Return a short Polish label for a manual review status."""
    if status == REVIEW_STATUS_APPROVED:
        return "zatwierdzony"
    if status == REVIEW_STATUS_REJECTED:
        return "odrzucony"
    return "wymaga przeglądu"


def parse_report_summary(report_text: str) -> dict[str, object]:
    """Parse the handful of fields needed for a human-friendly summary out
    of a safe generated _RAPORT.txt file. Only reads labels and counts that
    the report already exposes; never touches source values."""
    categories: list[tuple[str, int]] = []
    in_categories = False
    risk_level = "unknown"
    manual_review_required = True

    for raw_line in report_text.splitlines():
        line = raw_line.strip()
        if line == "Detected categories:":
            in_categories = True
            continue
        if in_categories:
            if line.startswith("* ") and ":" in line:
                label, _, count_text = line[2:].rpartition(":")
                count_text = count_text.strip()
                if count_text.lstrip("-").isdigit():
                    count = int(count_text)
                    if count > 0:
                        categories.append((label.strip(), count))
                continue
            in_categories = False

        if line.startswith("Risk level:"):
            risk_level = line.split(":", 1)[1].strip()
        elif line.startswith("Manual review required:"):
            manual_review_required = line.split(":", 1)[1].strip().lower() == "yes"

    return {
        "categories": categories,
        "risk_level": risk_level,
        "manual_review_required": manual_review_required,
    }


CATEGORY_LABELS_PL = {
    "PESEL": "PESEL",
    "EMAIL": "E-mail",
    "TELEFON": "Telefon",
    "DATA": "Data",
    "ULICA": "Ulica",
    "MIEJSCOWOSC": "Miejscowość",
    "POSTAL_CODE": "Kod pocztowy",
    "NIP": "NIP",
    "REGON": "REGON",
    "DOWOD_OSOBISTY": "Dowód osobisty",
    "IBAN": "IBAN",
    "PERSON_NAME_TYPO": "Nazwisko (nietypowy zapis)",
    "NER_PERSON": "Osoba (AI)",
    "NER_ORG": "Organizacja (AI)",
    "NER_LOCATION": "Lokalizacja (AI)",
    "NER_MISC": "Inne (AI)",
}
RISK_SUMMARY_TEXT_PL = {
    "ok": "Nie znaleziono podejrzanych pozostałości.",
    "warning": "Warto sprawdzić - coś może wymagać uwagi.",
    "high_risk": "Wysokie ryzyko - koniecznie sprawdź ręcznie.",
    "unknown": "Status ryzyka nieznany.",
}


def category_label_pl(label: str) -> str:
    """Return a short Polish display label for a detected category code."""
    return CATEGORY_LABELS_PL.get(label, label)


def format_review_summary_line(approved_count: int, total_count: int) -> str:
    """Format the small counter shown above the export button."""
    return f"Zatwierdzono: {approved_count}/{total_count}"


# ---------------------------------------------------------------------------
# Visual design tokens
# ---------------------------------------------------------------------------

COLOR_BG = "#F7F9FC"
COLOR_CARD = "#FFFFFF"
COLOR_BORDER = "#D7DEEA"
COLOR_ACCENT = "#2F80ED"
COLOR_ACCENT_HOVER = "#2568C4"
COLOR_ACCENT_SOFT = "#E8F0FE"
COLOR_TEXT = "#1A2333"
COLOR_TEXT_MUTED = "#5B6472"
COLOR_OK = "#27AE60"
COLOR_OK_SOFT = "#E5F6EC"
COLOR_WARNING = "#F2994A"
COLOR_WARNING_SOFT = "#FCEEE1"
COLOR_HIGH_RISK = "#EB5757"
COLOR_HIGH_RISK_SOFT = "#FCE8E8"
COLOR_ICON_IDLE = "#EEF1F6"
COLOR_NEEDS_REVIEW = "#5B6FE0"
COLOR_NEEDS_REVIEW_SOFT = "#EAECFC"
COLOR_WARNING_TEXT = "#92400E"
FONT_FAMILY = "Segoe UI"
FILE_TYPE_COLORS = {
    "PDF": "#E24A4A",
    "DOCX": "#2F6FE4",
    "TXT": "#6B7280",
    "PNG": "#8E5CE0",
    "JPG": "#8E5CE0",
    "TIF": "#8E5CE0",
}
RISK_STYLES = {
    "ok": (COLOR_OK, COLOR_OK_SOFT, "\u2713"),
    "warning": (COLOR_WARNING, COLOR_WARNING_SOFT, "\u26a0"),
    "high_risk": (COLOR_HIGH_RISK, COLOR_HIGH_RISK_SOFT, "!"),
    "unknown": (COLOR_TEXT_MUTED, COLOR_ICON_IDLE, "?"),
}
# Matches the color legend already used in generated PDF review files
# (see PDF_REDACTION_COLORS / PDF_REDACTION_COLOR_LEGEND in pdf_redaction.py
# and report.py) so the same colors mean the same thing everywhere.
LEGEND_ITEMS = (
    ("#D91F1F", "PESEL, NIP, REGON, dow\u00f3d, IBAN, kod pocztowy"),
    ("#F2731F", "telefon, nietypowe nazwisko, osoba (AI)"),
    ("#2659D9", "e-mail"),
    ("#737373", "data"),
    ("#806BB3", "organizacja (AI)"),
    ("#408C59", "lokalizacja, ulica, miejscowo\u015b\u0107"),
)


class DnDCTk(ctk.CTk, TkinterDnD.DnDWrapper):
    """A CustomTkinter root window mixed with tkinterdnd2 drag-and-drop."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.TkdndVersion = TkinterDnD._require(self)


class IconTooltip:
    """A small hover tooltip for an icon-only button."""

    def __init__(self, widget: tk.Widget, text: str, delay_ms: int = 400) -> None:
        self.widget = widget
        self.text = text
        self.delay_ms = delay_ms
        self._after_id: str | None = None
        self._tip_window: tk.Toplevel | None = None
        widget.bind("<Enter>", self._schedule, add="+")
        widget.bind("<Leave>", self._hide, add="+")
        widget.bind("<Button-1>", self._hide, add="+")

    def _schedule(self, _event: object = None) -> None:
        self._cancel()
        self._after_id = self.widget.after(self.delay_ms, self._show)

    def _cancel(self) -> None:
        if self._after_id is not None:
            self.widget.after_cancel(self._after_id)
            self._after_id = None

    def _show(self) -> None:
        if self._tip_window is not None:
            return
        x = self.widget.winfo_rootx() + self.widget.winfo_width() // 2
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 6
        window = tk.Toplevel(self.widget)
        window.wm_overrideredirect(True)
        window.wm_geometry(f"+{x}+{y}")
        window.attributes("-topmost", True)
        label = tk.Label(
            window,
            text=self.text,
            background="#1A2333",
            foreground="#FFFFFF",
            font=(FONT_FAMILY, 9),
            padx=8,
            pady=3,
            borderwidth=0,
        )
        label.pack()
        self._tip_window = window

    def _hide(self, _event: object = None) -> None:
        self._cancel()
        if self._tip_window is not None:
            self._tip_window.destroy()
            self._tip_window = None


class AnonymizerApp:
    """CustomTkinter application: drop files -> anonymize -> review."""

    def __init__(self, root: DnDCTk) -> None:
        self.root = root
        self.selected_paths: list[Path] = []
        self.output_dir: Path | None = self._prepare_default_output_dir()
        self.sensitive_terms_path: Path | None = None
        self.use_ner = True
        self.use_llm_review = False
        self.llm_model_name = ""
        self.pdf_output_label = PDF_OUTPUT_LABEL_VISUAL_REDACTION

        self.review_dir: Path | None = None
        self.review_items: list[ReviewItem] = []
        self.review_batch_summary_names: list[str] = []
        self.last_batch_result: BatchResult | None = None
        self.original_path_by_output_name: dict[str, Path] = {}

        self.file_card_frame: ctk.CTkFrame | None = None
        self.drop_hint_label: ctk.CTkLabel | None = None
        self.anonymize_button: ctk.CTkButton | None = None
        self.output_dir_value_label: ctk.CTkLabel | None = None
        self.status_label: ctk.CTkLabel | None = None
        self.progress_bar: ctk.CTkProgressBar | None = None
        self.progress_status_label: ctk.CTkLabel | None = None
        self.progress_file_label: ctk.CTkLabel | None = None
        self.review_cards_frame: ctk.CTkFrame | None = None
        self.review_summary_label: ctk.CTkLabel | None = None
        self.export_button: ctk.CTkButton | None = None

        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("blue")

        self._build_shell()
        self.show_start_screen()

    # ------------------------------------------------------------------
    # Shell
    # ------------------------------------------------------------------

    def _prepare_default_output_dir(self) -> Path | None:
        candidate = default_output_directory()
        try:
            candidate.mkdir(parents=True, exist_ok=True)
        except OSError:
            return None
        return candidate

    def _build_shell(self) -> None:
        self.root.title(APP_TITLE)
        self.root.geometry(WINDOW_DEFAULT_SIZE)
        self.root.minsize(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)
        self.root.configure(fg_color=COLOR_BG)

        topbar = ctk.CTkFrame(self.root, fg_color="transparent", height=44)
        topbar.pack(fill="x", padx=20, pady=(14, 0))

        title_label = ctk.CTkLabel(
            topbar,
            text=APP_TITLE,
            font=ctk.CTkFont(family=FONT_FAMILY, size=16, weight="bold"),
            text_color=COLOR_TEXT,
        )
        title_label.pack(side="left")

        settings_button = ctk.CTkButton(
            topbar,
            text="\u2699",
            width=34,
            height=34,
            corner_radius=17,
            fg_color="transparent",
            hover_color=COLOR_ICON_IDLE,
            text_color=COLOR_TEXT_MUTED,
            font=ctk.CTkFont(family=FONT_FAMILY, size=16),
            command=self.open_settings,
        )
        settings_button.pack(side="right")
        IconTooltip(settings_button, "Ustawienia")

        self.content = ctk.CTkFrame(self.root, fg_color="transparent")
        self.content.pack(fill="both", expand=True, padx=20, pady=16)

    def _clear_content(self) -> None:
        for widget in self.content.winfo_children():
            widget.destroy()

    # ------------------------------------------------------------------
    # Start screen (drag & drop)
    # ------------------------------------------------------------------

    def show_start_screen(self) -> None:
        self._clear_content()

        drop_frame = ctk.CTkFrame(
            self.content,
            corner_radius=16,
            fg_color=COLOR_CARD,
            border_width=2,
            border_color=COLOR_BORDER,
        )
        drop_frame.pack(fill="x", pady=(0, 4))

        self.drop_hint_label = ctk.CTkLabel(
            drop_frame,
            text=(
                "\u2b06\n\nPrzeci\u0105gnij pliki tutaj albo kliknij, aby wybra\u0107"
            ),
            font=ctk.CTkFont(family=FONT_FAMILY, size=16),
            text_color=COLOR_TEXT,
            justify="center",
        )
        self.drop_hint_label.pack(pady=48)
        drop_frame.bind("<Button-1>", lambda _e: self.pick_files())
        self.drop_hint_label.bind("<Button-1>", lambda _e: self.pick_files())

        drop_frame.drop_target_register(DND_FILES)
        drop_frame.dnd_bind("<<Drop>>", self._on_files_dropped)

        privacy_row = ctk.CTkLabel(
            self.content,
            text="\U0001f512  Przetwarzane lokalnie, dane nie opuszczają Twojego komputera",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            text_color=COLOR_TEXT_MUTED,
        )
        privacy_row.pack(pady=(10, 14))

        self.file_card_frame = ctk.CTkFrame(self.content, fg_color="transparent")
        self.file_card_frame.pack(fill="x", pady=(0, 14))
        self._refresh_file_cards()

        output_row = ctk.CTkFrame(self.content, fg_color="transparent")
        output_row.pack(fill="x", pady=(0, 6))
        ctk.CTkLabel(
            output_row,
            text="Folder wynikowy:",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            text_color=COLOR_TEXT_MUTED,
        ).pack(side="left")
        self.output_dir_value_label = ctk.CTkLabel(
            output_row,
            text=self._output_dir_display_text(),
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            text_color=COLOR_TEXT,
        )
        self.output_dir_value_label.pack(side="left", padx=(8, 0))
        ctk.CTkButton(
            output_row,
            text="Wybierz folder",
            width=130,
            height=30,
            corner_radius=8,
            fg_color=COLOR_ICON_IDLE,
            hover_color=COLOR_BORDER,
            text_color=COLOR_TEXT,
            command=self.pick_output_dir,
        ).pack(side="right")

        self.status_label = ctk.CTkLabel(
            self.content,
            text=format_readiness_pl(
                len(self.selected_paths), self.output_dir is not None
            ),
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            text_color=COLOR_TEXT_MUTED,
        )
        self.status_label.pack(pady=(4, 14))

        self.anonymize_button = ctk.CTkButton(
            self.content,
            text="Anonimizuj",
            height=48,
            corner_radius=10,
            fg_color=COLOR_ACCENT,
            hover_color=COLOR_ACCENT_HOVER,
            font=ctk.CTkFont(family=FONT_FAMILY, size=16, weight="bold"),
            state="disabled",
            command=self.start_anonymize,
        )
        self.anonymize_button.pack(fill="x")
        self._update_readiness()

    def _output_dir_display_text(self) -> str:
        if self.output_dir is None:
            return "nie wybrano"
        return format_short_path(self.output_dir)

    def _refresh_file_cards(self) -> None:
        if self.file_card_frame is None:
            return
        for widget in self.file_card_frame.winfo_children():
            widget.destroy()

        for index, path in enumerate(self.selected_paths):
            self._build_file_card(self.file_card_frame, index, path)

    def _build_file_card(self, parent: ctk.CTkFrame, index: int, path: Path) -> None:
        card = ctk.CTkFrame(
            parent,
            corner_radius=10,
            fg_color=COLOR_CARD,
            border_width=1,
            border_color=COLOR_BORDER,
            height=44,
        )
        card.pack(fill="x", pady=4)
        card.pack_propagate(False)

        badge_text = file_type_badge(path)
        badge = ctk.CTkLabel(
            card,
            text=badge_text,
            width=44,
            height=26,
            corner_radius=6,
            fg_color=FILE_TYPE_COLORS.get(badge_text, COLOR_TEXT_MUTED),
            text_color="#FFFFFF",
            font=ctk.CTkFont(family=FONT_FAMILY, size=10, weight="bold"),
        )
        badge.pack(side="left", padx=(10, 10), pady=9)

        ctk.CTkLabel(
            card,
            text=path.name,
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            text_color=COLOR_TEXT,
            anchor="w",
        ).pack(side="left", fill="x", expand=True)

        remove_button = ctk.CTkButton(
            card,
            text="\u2715",
            width=28,
            height=28,
            corner_radius=14,
            fg_color="transparent",
            hover_color=COLOR_HIGH_RISK_SOFT,
            text_color=COLOR_TEXT_MUTED,
            command=lambda i=index: self.remove_file_at(i),
        )
        remove_button.pack(side="right", padx=8)
        IconTooltip(remove_button, "Usu\u0144 z listy")

    def pick_files(self) -> None:
        file_paths = filedialog.askopenfilenames(
            title="Wybierz pliki",
            filetypes=[
                ("Obslugiwane pliki", "*.txt *.docx *.pdf *.png *.jpg *.jpeg *.tif *.tiff"),
                ("Wszystkie pliki", "*.*"),
            ],
        )
        if not file_paths:
            return
        self._add_paths([Path(value) for value in file_paths])

    def _on_files_dropped(self, event: object) -> None:
        paths = parse_dropped_file_paths(getattr(event, "data", ""))
        self._add_paths(paths)

    def _add_paths(self, paths: list[Path]) -> None:
        supported, unsupported = filter_supported_paths(paths)
        added = 0
        for path in supported:
            if path not in self.selected_paths:
                self.selected_paths.append(path)
                added += 1

        if self.status_label is not None:
            self.status_label.configure(
                text=format_drop_result(added, len(unsupported))
            )
        self._refresh_file_cards()
        self._update_readiness()

    def remove_file_at(self, index: int) -> None:
        self.selected_paths = remove_paths_by_indexes(self.selected_paths, (index,))
        self._refresh_file_cards()
        self._update_readiness()

    def pick_output_dir(self) -> None:
        folder_path = filedialog.askdirectory(title="Wybierz folder wynikowy")
        if not folder_path:
            return
        self.output_dir = Path(folder_path)
        if self.output_dir_value_label is not None:
            self.output_dir_value_label.configure(
                text=self._output_dir_display_text()
            )
        self._update_readiness()

    def _update_readiness(self) -> None:
        if self.status_label is not None:
            self.status_label.configure(
                text=format_readiness_pl(
                    len(self.selected_paths), self.output_dir is not None
                )
            )
        if self.anonymize_button is not None:
            ready = bool(self.selected_paths) and self.output_dir is not None
            if ready:
                self.anonymize_button.configure(
                    state="normal",
                    fg_color=COLOR_ACCENT,
                    hover_color=COLOR_ACCENT_HOVER,
                    text_color="#FFFFFF",
                )
            else:
                self.anonymize_button.configure(
                    state="disabled",
                    fg_color=COLOR_ICON_IDLE,
                    hover_color=COLOR_ICON_IDLE,
                    text_color=COLOR_TEXT_MUTED,
                )

    # ------------------------------------------------------------------
    # Settings modal
    # ------------------------------------------------------------------

    def open_settings(self) -> None:
        SettingsDialog(self)

    # ------------------------------------------------------------------
    # Processing screen
    # ------------------------------------------------------------------

    def show_processing_screen(self) -> None:
        self._clear_content()

        wrapper = ctk.CTkFrame(self.content, fg_color="transparent")
        wrapper.place(relx=0.5, rely=0.42, anchor="center")

        ctk.CTkLabel(
            wrapper,
            text="\U0001f4c4",
            font=ctk.CTkFont(family=FONT_FAMILY, size=48),
            text_color=COLOR_ACCENT,
        ).pack(pady=(0, 24))

        self.progress_bar = ctk.CTkProgressBar(
            wrapper, width=320, height=10, corner_radius=5, progress_color=COLOR_ACCENT
        )
        self.progress_bar.set(0.0)
        self.progress_bar.pack(pady=(0, 16))

        self.progress_status_label = ctk.CTkLabel(
            wrapper,
            text="Przygotowuję...",
            font=ctk.CTkFont(family=FONT_FAMILY, size=15),
            text_color=COLOR_TEXT,
        )
        self.progress_status_label.pack()

        self.progress_file_label = ctk.CTkLabel(
            wrapper,
            text="",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            text_color=COLOR_TEXT_MUTED,
        )
        self.progress_file_label.pack(pady=(4, 0))

    def _update_processing(self, index: int, total: int, path: Path) -> None:
        if self.progress_bar is not None:
            self.progress_bar.set(index / total if total else 0.0)
        if self.progress_status_label is not None:
            self.progress_status_label.configure(
                text=f"Analizuję plik {index} z {total}..."
            )
        if self.progress_file_label is not None:
            self.progress_file_label.configure(text=path.name)
        self.root.update_idletasks()

    # ------------------------------------------------------------------
    # Run batch
    # ------------------------------------------------------------------

    def start_anonymize(self) -> None:
        if not self.selected_paths or self.output_dir is None:
            return

        self.show_processing_screen()
        self.root.update_idletasks()

        try:
            batch_result = anonymize_batch(
                self.selected_paths,
                self.output_dir,
                sensitive_terms_path=self.sensitive_terms_path,
                use_ner=self.use_ner,
                use_llm_review=self.use_llm_review,
                llm_model_name=self.llm_model_name,
                pdf_redaction_scope=pdf_redaction_scope_from_gui_label(
                    self.pdf_output_label
                ),
                pdf_output_mode=pdf_output_mode_from_gui_label(
                    self.pdf_output_label
                ),
                progress_callback=self._update_processing,
            )
        except Exception:
            self.show_start_screen()
            if self.status_label is not None:
                self.status_label.configure(
                    text="Błąd: przetwarzanie nie powiodło się. Sprawdź pliki i folder."
                )
            return

        self.last_batch_result = batch_result
        self.original_path_by_output_name = self._build_original_path_map(
            batch_result
        )
        self.review_dir = self.output_dir
        self._load_review_folder()
        self.show_review_screen()

    def _build_original_path_map(
        self, batch_result: BatchResult
    ) -> dict[str, Path]:
        sources_by_name = {path.name: path for path in self.selected_paths}
        mapping: dict[str, Path] = {}
        for result in batch_result.results:
            if result.get("status") != "success":
                continue
            input_name = result.get("input_name")
            output_name = result.get("output_name")
            source_path = sources_by_name.get(str(input_name))
            if source_path is not None and output_name:
                mapping[str(output_name)] = source_path
        return mapping

    # ------------------------------------------------------------------
    # Review screen
    # ------------------------------------------------------------------

    def _load_review_folder(self) -> None:
        if self.review_dir is None:
            self.review_items = []
            self.review_batch_summary_names = []
            return
        try:
            workspace = load_review_workspace(self.review_dir)
        except OSError:
            self.review_items = []
            self.review_batch_summary_names = []
            return
        self.review_items = workspace.items
        self.review_batch_summary_names = workspace.batch_summary_names

    def show_review_screen(self) -> None:
        self._clear_content()

        header = ctk.CTkFrame(self.content, fg_color="transparent")
        header.pack(fill="x", pady=(0, 10))
        ctk.CTkButton(
            header,
            text="\u2b05 Nowy batch",
            width=110,
            height=28,
            corner_radius=8,
            fg_color="transparent",
            hover_color=COLOR_ICON_IDLE,
            text_color=COLOR_TEXT_MUTED,
            command=self.show_start_screen,
        ).pack(side="left")
        ctk.CTkButton(
            header,
            text="Wybierz inny folder",
            width=150,
            height=28,
            corner_radius=8,
            fg_color="transparent",
            hover_color=COLOR_ICON_IDLE,
            text_color=COLOR_TEXT_MUTED,
            command=self.pick_review_folder,
        ).pack(side="right")

        scroll = ctk.CTkScrollableFrame(
            self.content, fg_color="transparent", label_text=""
        )
        scroll.pack(fill="both", expand=True, pady=(0, 10))
        self.review_cards_frame = scroll
        self._refresh_review_cards()

        bottom_bar = ctk.CTkFrame(self.content, fg_color="transparent")
        bottom_bar.pack(fill="x")
        self.review_summary_label = ctk.CTkLabel(
            bottom_bar,
            text=self._review_summary_text(),
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            text_color=COLOR_TEXT_MUTED,
        )
        self.review_summary_label.pack(side="left")
        self.export_button = ctk.CTkButton(
            bottom_bar,
            text="Eksportuj zatwierdzone",
            height=38,
            corner_radius=8,
            fg_color=COLOR_ACCENT,
            hover_color=COLOR_ACCENT_HOVER,
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
            command=self.export_approved,
        )
        self.export_button.pack(side="right")
        self._update_export_button_state()

        self._build_legend_row(self.content)

        warning = ctk.CTkLabel(
            self.content,
            text=f"⚠  {MANUAL_REVIEW_WARNING}",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
            text_color=COLOR_WARNING_TEXT,
            fg_color=COLOR_WARNING_SOFT,
            corner_radius=8,
        )
        warning.pack(pady=(8, 0), ipadx=10, ipady=6)

    def _build_legend_row(self, parent: ctk.CTkFrame) -> None:
        legend_frame = ctk.CTkFrame(parent, fg_color="transparent")
        legend_frame.pack(pady=(2, 4))
        for color, text in LEGEND_ITEMS:
            item = ctk.CTkFrame(legend_frame, fg_color="transparent")
            item.pack(side="left", padx=8)
            ctk.CTkLabel(
                item,
                text="●",
                text_color=color,
                font=ctk.CTkFont(family=FONT_FAMILY, size=12),
                width=14,
            ).pack(side="left")
            ctk.CTkLabel(
                item,
                text=text,
                text_color=COLOR_TEXT_MUTED,
                font=ctk.CTkFont(family=FONT_FAMILY, size=10),
            ).pack(side="left")

    def pick_review_folder(self) -> None:
        folder_path = filedialog.askdirectory(title="Wybierz folder do przeglądu")
        if not folder_path:
            return
        self.review_dir = Path(folder_path)
        self._load_review_folder()
        self.show_review_screen()

    def _review_summary_text(self) -> str:
        approved = sum(
            1 for item in self.review_items if item.status == REVIEW_STATUS_APPROVED
        )
        return format_review_summary_line(approved, len(self.review_items))

    def _update_export_button_state(self) -> None:
        if self.export_button is None:
            return
        approved = any(
            item.status == REVIEW_STATUS_APPROVED for item in self.review_items
        )
        if approved:
            self.export_button.configure(
                state="normal",
                fg_color=COLOR_ACCENT,
                hover_color=COLOR_ACCENT_HOVER,
                text_color="#FFFFFF",
            )
        else:
            self.export_button.configure(
                state="disabled",
                fg_color=COLOR_ICON_IDLE,
                hover_color=COLOR_ICON_IDLE,
                text_color=COLOR_TEXT_MUTED,
            )

    def _refresh_review_cards(self) -> None:
        if self.review_cards_frame is None:
            return
        for widget in self.review_cards_frame.winfo_children():
            widget.destroy()

        if not self.review_items:
            ctk.CTkLabel(
                self.review_cards_frame,
                text="Brak wykrytych wyników w tym folderze.",
                font=ctk.CTkFont(family=FONT_FAMILY, size=12),
                text_color=COLOR_TEXT_MUTED,
            ).pack(pady=20)
            return

        for item in self.review_items:
            self._build_review_card(item)

    def _build_review_card(self, item: ReviewItem) -> None:
        assert self.review_cards_frame is not None
        card = ctk.CTkFrame(
            self.review_cards_frame,
            corner_radius=12,
            fg_color=COLOR_CARD,
            border_width=1,
            border_color=COLOR_BORDER,
        )
        card.pack(fill="x", pady=6)

        row = ctk.CTkFrame(card, fg_color="transparent")
        row.pack(fill="x", padx=14, pady=12)

        badge_text = file_type_badge(Path(item.output_name))
        ctk.CTkLabel(
            row,
            text=badge_text,
            width=44,
            height=26,
            corner_radius=6,
            fg_color=FILE_TYPE_COLORS.get(badge_text, COLOR_TEXT_MUTED),
            text_color="#FFFFFF",
            font=ctk.CTkFont(family=FONT_FAMILY, size=10, weight="bold"),
        ).pack(side="left", padx=(0, 10))

        ctk.CTkLabel(
            row,
            text=item.output_name,
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
            text_color=COLOR_TEXT,
        ).pack(side="left")

        risk_key = risk_style_key(item.risk_level)
        risk_color, risk_soft, risk_glyph = RISK_STYLES[risk_key]
        ctk.CTkLabel(
            row,
            text=risk_glyph,
            width=22,
            height=22,
            corner_radius=11,
            fg_color=risk_soft,
            text_color=risk_color,
            font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
        ).pack(side="left", padx=10)

        actions = ctk.CTkFrame(row, fg_color="transparent")
        actions.pack(side="right")

        self._build_status_icon_button(
            actions, "\U0001f441", "Por\u00f3wnaj orygina\u0142 i wynik", COLOR_TEXT_MUTED, False,
            lambda: self.open_comparison(item),
        )
        self._build_status_icon_button(
            actions, "\u2713", "Zatwierd\u017a", COLOR_OK,
            item.status == REVIEW_STATUS_APPROVED,
            lambda: self.set_review_status(item, REVIEW_STATUS_APPROVED),
        )
        self._build_status_icon_button(
            actions, "!", "Wymaga przegl\u0105du", COLOR_NEEDS_REVIEW,
            item.status == REVIEW_STATUS_NEEDS_REVIEW,
            lambda: self.set_review_status(item, REVIEW_STATUS_NEEDS_REVIEW),
        )
        self._build_status_icon_button(
            actions, "\u2715", "Odrzu\u0107", COLOR_HIGH_RISK,
            item.status == REVIEW_STATUS_REJECTED,
            lambda: self.set_review_status(item, REVIEW_STATUS_REJECTED),
        )

        details = ctk.CTkFrame(card, fg_color="transparent")
        details.pack(fill="x", padx=14, pady=(0, 10))
        ctk.CTkButton(
            details,
            text="ℹ Szczegóły",
            width=110,
            height=24,
            corner_radius=6,
            fg_color="transparent",
            hover_color=COLOR_ICON_IDLE,
            text_color=COLOR_ACCENT,
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            command=lambda: self.open_summary(item),
        ).pack(side="left")

    def _build_status_icon_button(
        self,
        parent: ctk.CTkFrame,
        glyph: str,
        tooltip: str,
        active_color: str,
        active: bool,
        command,
    ) -> None:
        button = ctk.CTkButton(
            parent,
            text=glyph,
            width=32,
            height=32,
            corner_radius=16,
            fg_color=active_color if active else COLOR_ICON_IDLE,
            hover_color=active_color,
            text_color="#FFFFFF" if active else COLOR_TEXT_MUTED,
            font=ctk.CTkFont(family=FONT_FAMILY, size=13),
            command=command,
        )
        button.pack(side="left", padx=3)
        IconTooltip(button, tooltip)

    def set_review_status(self, item: ReviewItem, status: str) -> None:
        self.review_items = apply_review_statuses(
            self.review_items, {item.output_name: status}
        )
        if self.review_dir is not None:
            try:
                save_review_files(
                    self.review_dir,
                    items=self.review_items,
                    batch_summary_names=self.review_batch_summary_names,
                )
            except OSError:
                pass
        self._refresh_review_cards()
        self._update_export_button_state()
        self._flash_status_saved(status)

    def _flash_status_saved(self, status: str) -> None:
        if self.review_summary_label is None:
            return
        self.review_summary_label.configure(
            text=f"✓ Zapisano status: {review_status_label_pl(status)}"
        )
        self.root.after(1200, self._restore_review_summary_text)

    def _restore_review_summary_text(self) -> None:
        if self.review_summary_label is not None:
            self.review_summary_label.configure(text=self._review_summary_text())

    def _find_review_item(self, output_name: str) -> ReviewItem | None:
        for item in self.review_items:
            if item.output_name == output_name:
                return item
        return None

    def open_review_output(self, item: ReviewItem) -> None:
        if self.review_dir is None:
            return
        preferred_path = preferred_review_output_path(self.review_dir, item.output_name)
        self._open_review_file(preferred_path.name)

    def open_review_report(self, item: ReviewItem) -> None:
        if item.report_name is None:
            return
        self._open_review_file(item.report_name)

    def open_review_checklist(self, item: ReviewItem) -> None:
        if item.checklist_name is None:
            return
        self._open_review_file(item.checklist_name)

    def _open_review_file(self, file_name: str) -> None:
        if self.review_dir is None:
            return
        file_path = self.review_dir / Path(file_name).name
        try:
            open_path_with_default_app(file_path)
        except OSError:
            pass

    def export_approved(self) -> None:
        if self.review_dir is None:
            return
        try:
            export_approved_workspace(self.review_dir)
        except (FileNotFoundError, ValueError, OSError):
            return
        if self.review_summary_label is not None:
            self.review_summary_label.configure(
                text=self._review_summary_text() + " - wyeksportowano"
            )

    def open_summary(self, item: ReviewItem) -> None:
        if self.review_dir is None or item.report_name is None:
            return
        report_path = self.review_dir / Path(item.report_name).name
        try:
            report_text = report_path.read_text(encoding="utf-8")
        except OSError:
            return
        summary = parse_report_summary(report_text)
        SummaryDialog(self, item, summary)

    def open_comparison(self, item: ReviewItem) -> None:
        if self.review_dir is None:
            return
        original_path = self.original_path_by_output_name.get(item.output_name)
        result_path = preferred_review_output_path(self.review_dir, item.output_name)
        ComparisonWindow(self, item, original_path, result_path)


class SettingsDialog:
    """Modal settings window for advanced anonymization options."""

    def __init__(self, app: AnonymizerApp) -> None:
        self.app = app
        self.window = ctk.CTkToplevel(app.root)
        self.window.title("Ustawienia")
        self.window.geometry("560x560")
        self.window.configure(fg_color=COLOR_BG)
        self.window.transient(app.root)
        self.window.grab_set()

        self.ner_var = tk.BooleanVar(value=app.use_ner)
        self.llm_var = tk.BooleanVar(value=app.use_llm_review)
        self.llm_model_var = tk.StringVar(value=app.llm_model_name)
        self.pdf_mode_var = tk.StringVar(value=app.pdf_output_label)
        self.sensitive_terms_path = app.sensitive_terms_path

        self._build()

    def _build(self) -> None:
        header = ctk.CTkFrame(self.window, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=(18, 10))
        ctk.CTkLabel(
            header,
            text="Ustawienia",
            font=ctk.CTkFont(family=FONT_FAMILY, size=18, weight="bold"),
            text_color=COLOR_TEXT,
        ).pack(side="left")
        ctk.CTkButton(
            header,
            text="\u2715",
            width=28,
            height=28,
            corner_radius=14,
            fg_color="transparent",
            hover_color=COLOR_ICON_IDLE,
            text_color=COLOR_TEXT_MUTED,
            command=self.window.destroy,
        ).pack(side="right")

        body = ctk.CTkFrame(self.window, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=20)

        self._build_toggle_section(
            body,
            "Rozpoznawanie AI (NER)",
            "Wykrywa imiona, firmy i miejsca",
            self.ner_var,
        )
        self._build_toggle_section(
            body,
            "Dodatkowa weryfikacja AI (LLM)",
            "Opcjonalne, wymaga lokalnego Ollama",
            self.llm_var,
        )

        dict_section = self._section_frame(body)
        dict_row = ctk.CTkFrame(dict_section, fg_color="transparent")
        dict_row.pack(fill="x", padx=14, pady=12)
        text_col = ctk.CTkFrame(dict_row, fg_color="transparent")
        text_col.pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(
            text_col,
            text="Prywatny słownik terminów",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
            text_color=COLOR_TEXT,
            anchor="w",
        ).pack(fill="x")
        self.dict_hint_label = ctk.CTkLabel(
            text_col,
            text=self._dict_hint_text(),
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            text_color=COLOR_TEXT_MUTED,
            anchor="w",
        )
        self.dict_hint_label.pack(fill="x")
        ctk.CTkButton(
            dict_row,
            text="Wybierz plik",
            width=110,
            height=30,
            corner_radius=8,
            fg_color=COLOR_ICON_IDLE,
            hover_color=COLOR_BORDER,
            text_color=COLOR_TEXT,
            command=self._pick_sensitive_terms_file,
        ).pack(side="right")

        pdf_section = self._section_frame(body)
        pdf_inner = ctk.CTkFrame(pdf_section, fg_color="transparent")
        pdf_inner.pack(fill="x", padx=14, pady=12)
        ctk.CTkLabel(
            pdf_inner,
            text="Format wyjściowy PDF",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
            text_color=COLOR_TEXT,
            anchor="w",
        ).pack(fill="x", pady=(0, 8))
        for label in PDF_OUTPUT_SETTINGS_BY_LABEL:
            ctk.CTkRadioButton(
                pdf_inner,
                text=PDF_OUTPUT_SHORT_LABELS.get(label, label),
                value=label,
                variable=self.pdf_mode_var,
                font=ctk.CTkFont(family=FONT_FAMILY, size=11),
                text_color=COLOR_TEXT,
            ).pack(anchor="w", pady=3)

        ctk.CTkButton(
            self.window,
            text="Zapisz i zamknij",
            height=42,
            corner_radius=8,
            fg_color=COLOR_ACCENT,
            hover_color=COLOR_ACCENT_HOVER,
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
            command=self._save_and_close,
        ).pack(fill="x", padx=20, pady=16)

    def _section_frame(self, parent: ctk.CTkFrame) -> ctk.CTkFrame:
        frame = ctk.CTkFrame(
            parent,
            corner_radius=10,
            fg_color=COLOR_CARD,
            border_width=1,
            border_color=COLOR_BORDER,
        )
        frame.pack(fill="x", pady=6)
        return frame

    def _build_toggle_section(
        self,
        parent: ctk.CTkFrame,
        title: str,
        subtitle: str,
        variable: tk.BooleanVar,
    ) -> None:
        frame = self._section_frame(parent)
        row = ctk.CTkFrame(frame, fg_color="transparent")
        row.pack(fill="x", padx=14, pady=12)
        text_col = ctk.CTkFrame(row, fg_color="transparent")
        text_col.pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(
            text_col,
            text=title,
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
            text_color=COLOR_TEXT,
            anchor="w",
        ).pack(fill="x")
        ctk.CTkLabel(
            text_col,
            text=subtitle,
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            text_color=COLOR_TEXT_MUTED,
            anchor="w",
        ).pack(fill="x")
        ctk.CTkSwitch(
            row, text="", variable=variable, progress_color=COLOR_ACCENT
        ).pack(side="right")

    def _dict_hint_text(self) -> str:
        if self.sensitive_terms_path is None:
            return "Brak wybranego pliku"
        return self.sensitive_terms_path.name

    def _pick_sensitive_terms_file(self) -> None:
        file_path = filedialog.askopenfilename(
            title="Wybierz plik ze słownikiem",
            filetypes=[("Pliki TXT", "*.txt"), ("Wszystkie pliki", "*.*")],
        )
        if not file_path:
            return
        self.sensitive_terms_path = Path(file_path)
        self.dict_hint_label.configure(text=self._dict_hint_text())

    def _save_and_close(self) -> None:
        self.app.use_ner = self.ner_var.get()
        self.app.use_llm_review = self.llm_var.get()
        self.app.pdf_output_label = self.pdf_mode_var.get()
        self.app.sensitive_terms_path = self.sensitive_terms_path
        if self.app.use_llm_review and not self.app.llm_model_name:
            status, models = list_installed_models()
            _values, selected_model, _hint = format_llm_model_selector_state(
                status, models
            )
            self.app.llm_model_name = selected_model
        self.window.destroy()


def _render_text_block(parent: ctk.CTkBaseClass, text: str) -> None:
    box = ctk.CTkTextbox(
        parent,
        width=440,
        height=600,
        wrap="word",
        fg_color=COLOR_CARD,
        text_color=COLOR_TEXT,
        font=ctk.CTkFont(family=FONT_FAMILY, size=11),
    )
    box.pack(fill="both", expand=True, padx=4, pady=4)
    box.insert("1.0", text)
    box.configure(state="disabled")


def render_document_preview(
    parent: ctk.CTkBaseClass, path: Path, target_width: int = 460
) -> list["ctk.CTkImage"]:
    """Render a document's pages/content into the given scrollable frame.

    Returns the CTkImage objects created so the caller can keep a strong
    reference alive for the window's lifetime (Tk drops images that are
    only referenced by the widget itself once the local variable is gone).
    """
    images: list[ctk.CTkImage] = []
    suffix = path.suffix.lower()
    try:
        if suffix == ".pdf":
            import pymupdf as fitz

            with fitz.open(path) as document:
                for page in document:
                    page_width = max(page.rect.width, 1)
                    zoom = target_width / page_width
                    pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom))
                    pil_image = Image.frombytes(
                        "RGB", (pix.width, pix.height), pix.samples
                    )
                    ctk_image = ctk.CTkImage(
                        light_image=pil_image,
                        size=(pix.width, pix.height),
                    )
                    images.append(ctk_image)
                    ctk.CTkLabel(parent, image=ctk_image, text="").pack(pady=6)
        elif suffix in (".png", ".jpg", ".jpeg", ".tif", ".tiff"):
            pil_image = Image.open(path)
            pil_image.thumbnail((target_width, 3000))
            ctk_image = ctk.CTkImage(
                light_image=pil_image, size=pil_image.size
            )
            images.append(ctk_image)
            ctk.CTkLabel(parent, image=ctk_image, text="").pack(pady=6)
        elif suffix == ".docx":
            _render_text_block(parent, read_docx_file(path))
        elif suffix == ".txt":
            _render_text_block(parent, read_txt_file(path))
        else:
            ctk.CTkLabel(
                parent,
                text=f"Brak podglądu dla typu pliku: {suffix or 'nieznany'}",
                text_color=COLOR_TEXT_MUTED,
            ).pack(pady=30)
    except Exception:  # noqa: BLE001 - preview must never crash the app
        ctk.CTkLabel(
            parent,
            text="Nie udało się wczytać podglądu tego pliku.",
            text_color=COLOR_HIGH_RISK,
            wraplength=380,
            justify="left",
        ).pack(pady=30, padx=16)
    return images


class ComparisonWindow:
    """Side-by-side original-vs-anonymized preview (view only, no editing)."""

    def __init__(
        self,
        app: AnonymizerApp,
        item: ReviewItem,
        original_path: Path | None,
        result_path: Path,
    ) -> None:
        self.app = app
        self._images: list[ctk.CTkImage] = []

        window = ctk.CTkToplevel(app.root)
        self.window = window
        window.title(f"Porównanie - {item.output_name}")
        window.geometry("1120x740")
        window.configure(fg_color=COLOR_BG)
        window.transient(app.root)

        ctk.CTkLabel(
            window,
            text=item.output_name,
            font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"),
            text_color=COLOR_TEXT,
        ).pack(anchor="w", padx=20, pady=(16, 4))

        panes = ctk.CTkFrame(window, fg_color="transparent")
        panes.pack(fill="both", expand=True, padx=20, pady=(4, 8))
        panes.columnconfigure(0, weight=1)
        panes.columnconfigure(1, weight=1)
        panes.rowconfigure(1, weight=1)

        ctk.CTkLabel(
            panes,
            text="Oryginał",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
            text_color=COLOR_TEXT_MUTED,
        ).grid(row=0, column=0, sticky="w", pady=(0, 6))
        ctk.CTkLabel(
            panes,
            text="Po anonimizacji",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
            text_color=COLOR_TEXT_MUTED,
        ).grid(row=0, column=1, sticky="w", padx=(16, 0), pady=(0, 6))

        left_frame = ctk.CTkScrollableFrame(
            panes, fg_color=COLOR_CARD, corner_radius=10, label_text=""
        )
        left_frame.grid(row=1, column=0, sticky="nsew", padx=(0, 8))
        right_frame = ctk.CTkScrollableFrame(
            panes, fg_color=COLOR_CARD, corner_radius=10, label_text=""
        )
        right_frame.grid(row=1, column=1, sticky="nsew", padx=(8, 0))

        if original_path is not None and original_path.exists():
            self._images.extend(render_document_preview(left_frame, original_path))
        else:
            ctk.CTkLabel(
                left_frame,
                text=(
                    "Oryginał niedostępny - ten folder nie pochodzi z "
                    "bieżącej sesji przetwarzania."
                ),
                text_color=COLOR_TEXT_MUTED,
                wraplength=380,
                justify="left",
            ).pack(pady=30, padx=16)

        if result_path.exists():
            self._images.extend(render_document_preview(right_frame, result_path))
        else:
            ctk.CTkLabel(
                right_frame,
                text="Plik wynikowy nie został znaleziony.",
                text_color=COLOR_TEXT_MUTED,
            ).pack(pady=30)

        app._build_legend_row(window)

        ctk.CTkButton(
            window,
            text="Zamknij",
            width=140,
            height=36,
            corner_radius=8,
            fg_color=COLOR_ACCENT,
            hover_color=COLOR_ACCENT_HOVER,
            command=window.destroy,
        ).pack(pady=(0, 16))


class SummaryDialog:
    """A human-readable summary popup, built from safe report data only."""

    def __init__(
        self,
        app: AnonymizerApp,
        item: ReviewItem,
        summary: dict[str, object],
    ) -> None:
        self.app = app
        self.item = item
        window = ctk.CTkToplevel(app.root)
        self.window = window
        window.title("Szczegóły")
        window.geometry("480x520")
        window.configure(fg_color=COLOR_BG)
        window.transient(app.root)
        window.grab_set()

        header = ctk.CTkFrame(window, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=(18, 6))
        ctk.CTkLabel(
            header,
            text=item.output_name,
            font=ctk.CTkFont(family=FONT_FAMILY, size=15, weight="bold"),
            text_color=COLOR_TEXT,
            anchor="w",
        ).pack(side="left", fill="x", expand=True)
        ctk.CTkButton(
            header,
            text="✕",
            width=28,
            height=28,
            corner_radius=14,
            fg_color="transparent",
            hover_color=COLOR_ICON_IDLE,
            text_color=COLOR_TEXT_MUTED,
            command=window.destroy,
        ).pack(side="right")

        risk_key = risk_style_key(str(summary.get("risk_level") or ""))
        risk_color, risk_soft, risk_glyph = RISK_STYLES[risk_key]
        risk_row = ctk.CTkFrame(window, corner_radius=10, fg_color=risk_soft)
        risk_row.pack(fill="x", padx=20, pady=(4, 12))
        inner = ctk.CTkFrame(risk_row, fg_color="transparent")
        inner.pack(fill="x", padx=14, pady=12)
        ctk.CTkLabel(
            inner,
            text=risk_glyph,
            width=30,
            height=30,
            corner_radius=15,
            fg_color=risk_color,
            text_color="#FFFFFF",
            font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"),
        ).pack(side="left", padx=(0, 10))
        ctk.CTkLabel(
            inner,
            text=RISK_SUMMARY_TEXT_PL.get(risk_key, RISK_SUMMARY_TEXT_PL["unknown"]),
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            text_color=COLOR_TEXT,
            anchor="w",
            wraplength=360,
            justify="left",
        ).pack(side="left", fill="x", expand=True)

        ctk.CTkLabel(
            window,
            text="Wykryte kategorie danych:",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
            text_color=COLOR_TEXT,
            anchor="w",
        ).pack(fill="x", padx=20)

        chips_frame = ctk.CTkScrollableFrame(
            window, fg_color="transparent", label_text=""
        )
        chips_frame.pack(fill="both", expand=True, padx=20, pady=(6, 6))
        categories = summary.get("categories")
        if isinstance(categories, list) and categories:
            for label, count in categories:
                row = ctk.CTkFrame(
                    chips_frame,
                    corner_radius=8,
                    fg_color=COLOR_CARD,
                    border_width=1,
                    border_color=COLOR_BORDER,
                )
                row.pack(fill="x", pady=3)
                ctk.CTkLabel(
                    row,
                    text=category_label_pl(str(label)),
                    font=ctk.CTkFont(family=FONT_FAMILY, size=11),
                    text_color=COLOR_TEXT,
                    anchor="w",
                ).pack(side="left", padx=10, pady=6)
                ctk.CTkLabel(
                    row,
                    text=str(count),
                    font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
                    text_color=COLOR_ACCENT,
                ).pack(side="right", padx=10)
        else:
            ctk.CTkLabel(
                chips_frame,
                text="Nie wykryto żadnych kategorii danych wrażliwych.",
                font=ctk.CTkFont(family=FONT_FAMILY, size=11),
                text_color=COLOR_TEXT_MUTED,
            ).pack(pady=10)

        dev_row = ctk.CTkFrame(window, fg_color="transparent")
        dev_row.pack(fill="x", padx=20, pady=(0, 16))
        ctk.CTkButton(
            dev_row,
            text="Otwórz surowy raport (deweloperskie)",
            height=24,
            corner_radius=6,
            fg_color="transparent",
            hover_color=COLOR_ICON_IDLE,
            text_color=COLOR_TEXT_MUTED,
            font=ctk.CTkFont(family=FONT_FAMILY, size=10),
            command=lambda: app.open_review_report(item),
        ).pack(anchor="w")
        ctk.CTkButton(
            dev_row,
            text="Otwórz surową checklistę (deweloperskie)",
            height=24,
            corner_radius=6,
            fg_color="transparent",
            hover_color=COLOR_ICON_IDLE,
            text_color=COLOR_TEXT_MUTED,
            font=ctk.CTkFont(family=FONT_FAMILY, size=10),
            command=lambda: app.open_review_checklist(item),
        ).pack(anchor="w")


def start_gui() -> None:
    """Start the CustomTkinter desktop application."""
    root = DnDCTk()
    AnonymizerApp(root)
    root.mainloop()


def main() -> None:
    """Run the GUI when this module is executed as a script."""
    start_gui()


if __name__ == "__main__":
    main()
