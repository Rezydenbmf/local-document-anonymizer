"""CustomTkinter GUI for batch anonymization."""

import json
import os
import subprocess
import sys
import threading
import time
import tkinter as tk
import webbrowser
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk
from PIL import Image, ImageTk
from tkinterdnd2 import DND_FILES, TkinterDnD

try:
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
    from .audit import AUDIT_CATEGORY_ORDER
    from .dependency_updates import (
        check_dependency_updates,
        install_package_update,
    )
    from .environment_check import (
        ENV_ITEM_LLM,
        ENV_ITEM_NER,
        ENV_ITEM_OCR,
        INSTALL_ACTION_OPEN_URL,
        INSTALL_ACTION_SPACY_MODEL,
        check_environment,
        install_ner_model,
    )
    from .file_readers import read_docx_file, read_txt_file
    from .file_writers import internal_artifacts_dir
    from .llm_review import LLM_STATUS_AVAILABLE, list_installed_models
    from .manual_redaction import (
        EMPTY_MANUAL_EDITS,
        MANUAL_REDACTION_LABEL,
        ManualEdits,
        ManualRect,
        apply_manual_redaction_count_to_report_text,
        apply_pending_overrides,
        compute_visible_redaction_rects,
        load_manual_edits,
        manual_edits_path,
        rect_info_key,
        regenerate_pdf_with_manual_overrides,
        save_manual_edits,
    )
    from .report import (
        BATCH_ERROR_EMPTY_TEXT_PDF,
        BATCH_ERROR_FILE_IO,
        BATCH_ERROR_MISSING_DEPENDENCY,
        BATCH_ERROR_OCR_FAILED,
        BATCH_ERROR_OCR_UNAVAILABLE,
        BATCH_ERROR_PROCESSING_FAILED,
        BATCH_ERROR_TEXT_DECODING,
        BATCH_ERROR_UNSUPPORTED_FILE_TYPE,
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
    from audit import AUDIT_CATEGORY_ORDER
    from dependency_updates import (
        check_dependency_updates,
        install_package_update,
    )
    from environment_check import (
        ENV_ITEM_LLM,
        ENV_ITEM_NER,
        ENV_ITEM_OCR,
        INSTALL_ACTION_OPEN_URL,
        INSTALL_ACTION_SPACY_MODEL,
        check_environment,
        install_ner_model,
    )
    from file_readers import read_docx_file, read_txt_file
    from file_writers import internal_artifacts_dir
    from llm_review import LLM_STATUS_AVAILABLE, list_installed_models
    from manual_redaction import (
        EMPTY_MANUAL_EDITS,
        MANUAL_REDACTION_LABEL,
        ManualEdits,
        ManualRect,
        apply_manual_redaction_count_to_report_text,
        apply_pending_overrides,
        compute_visible_redaction_rects,
        load_manual_edits,
        manual_edits_path,
        rect_info_key,
        regenerate_pdf_with_manual_overrides,
        save_manual_edits,
    )
    from report import (
        BATCH_ERROR_EMPTY_TEXT_PDF,
        BATCH_ERROR_FILE_IO,
        BATCH_ERROR_MISSING_DEPENDENCY,
        BATCH_ERROR_OCR_FAILED,
        BATCH_ERROR_OCR_UNAVAILABLE,
        BATCH_ERROR_PROCESSING_FAILED,
        BATCH_ERROR_TEXT_DECODING,
        BATCH_ERROR_UNSUPPORTED_FILE_TYPE,
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


RECENT_FOLDERS_MAX = 15


def history_config_path() -> Path:
    """Return the local file that remembers recently used output folders.

    Stores folder paths and timestamps only - never document content, and
    never anything from inside a folder. This is a plain local file the
    user can delete at any time; it is not a database of anonymized data.
    """
    return Path.home() / ".anonimizer" / "recent_folders.json"


def load_recent_folders(config_path: Path) -> list[dict[str, str]]:
    """Load the recent-folders list, tolerating a missing/corrupt file."""
    try:
        raw = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    if not isinstance(raw, list):
        return []
    entries: list[dict[str, str]] = []
    for item in raw:
        if isinstance(item, dict) and isinstance(item.get("path"), str):
            entries.append(
                {
                    "path": item["path"],
                    "last_used": str(item.get("last_used", "")),
                }
            )
    return entries


def save_recent_folders(config_path: Path, entries: list[dict[str, str]]) -> None:
    """Persist the recent-folders list, creating the config folder if needed."""
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(
        json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def record_recent_folder(
    entries: list[dict[str, str]],
    folder_path: Path,
    timestamp: str,
) -> list[dict[str, str]]:
    """Return entries with folder_path moved to the front with a fresh
    timestamp, de-duplicated, and capped at RECENT_FOLDERS_MAX."""
    normalized = str(folder_path)
    remaining = [entry for entry in entries if entry.get("path") != normalized]
    updated = [{"path": normalized, "last_used": timestamp}, *remaining]
    return updated[:RECENT_FOLDERS_MAX]


def format_recent_folder_timestamp(timestamp: str) -> str:
    """Format a stored ISO timestamp for display, tolerating bad input."""
    try:
        parsed = datetime.fromisoformat(timestamp)
    except ValueError:
        return "nieznana data"
    return parsed.strftime("%d.%m.%Y, %H:%M")


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


def _bring_window_to_front(window: tk.Misc) -> None:
    """Raise and focus a window that was just opened or returned to.

    Tk/CustomTkinter windows on Windows can otherwise appear behind
    whatever window already had focus, which reads as broken rather than
    just unfocused.
    """
    window.deiconify()
    window.lift()
    window.focus_force()


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
    "RECZNE": "Ręcznie ukryte (magic pen)",
}
RISK_SUMMARY_TEXT_PL = {
    "ok": "Nie znaleziono podejrzanych pozostałości.",
    "warning": "Warto sprawdzić - coś może wymagać uwagi.",
    "high_risk": "Wysokie ryzyko - koniecznie sprawdź ręcznie.",
    "unknown": "Status ryzyka nieznany.",
}
BATCH_ERROR_LABELS_PL = {
    BATCH_ERROR_UNSUPPORTED_FILE_TYPE: "nieobsługiwany typ pliku",
    BATCH_ERROR_EMPTY_TEXT_PDF: (
        "PDF to skan bez warstwy tekstowej - wymaga lokalnego OCR (Tesseract), "
        "który nie jest zainstalowany lub nie wykrył tekstu"
    ),
    BATCH_ERROR_TEXT_DECODING: "pliku TXT nie udało się odczytać jako UTF-8",
    BATCH_ERROR_FILE_IO: "nie udało się odczytać lub zapisać pliku",
    BATCH_ERROR_MISSING_DEPENDENCY: "brakuje wymaganej lokalnej biblioteki",
    BATCH_ERROR_OCR_UNAVAILABLE: (
        "plik to skan/obraz i wymaga lokalnego OCR (Tesseract), "
        "który nie jest zainstalowany na tym komputerze"
    ),
    BATCH_ERROR_OCR_FAILED: "lokalny OCR (Tesseract) nie poradził sobie z tym plikiem",
    BATCH_ERROR_PROCESSING_FAILED: "przetwarzanie pliku nie powiodło się",
}


def category_label_pl(label: str) -> str:
    """Return a short Polish display label for a detected category code."""
    return CATEGORY_LABELS_PL.get(label, label)


def batch_error_label_pl(error: str) -> str:
    """Return a Polish explanation for a safe batch-processing error code."""
    return BATCH_ERROR_LABELS_PL.get(error, error)


def format_batch_error_items(batch_result: BatchResult) -> list[tuple[str, str]]:
    """Return (input_name, polish_error_reason) for every failed batch item."""
    return [
        (str(result.get("input_name", "?")), batch_error_label_pl(str(result.get("error", ""))))
        for result in batch_result.results
        if result.get("status") != "success"
    ]


def environment_status_lookup(items: Sequence | None) -> dict[str, bool]:
    """Return {item_id: ok} from a list of EnvironmentCheckItem, or an
    empty dict if the background check hasn't completed yet (items is
    None) - callers should treat a missing key as "not yet known" rather
    than "unavailable"."""
    if items is None:
        return {}
    return {item.item: item.ok for item in items}


def format_review_summary_line(approved_count: int, total_count: int) -> str:
    """Format the small counter shown above the export button."""
    return f"Zatwierdzono: {approved_count}/{total_count}"


def restrict_review_items_to_batch(
    review_items: list[ReviewItem],
    batch_results: list[dict[str, object]],
) -> list[ReviewItem]:
    """Keep only review items produced by the batch just run.

    The output folder may already contain older generated files from a
    previous session (collision-safe naming never overwrites them, so they
    linger on disk). A full-folder scan is correct when the user
    deliberately opens a folder for review later, but right after
    processing a fresh batch, mixing in unrelated old files would be
    confusing and needlessly resurfaces old output.
    """
    fresh_output_names = {
        str(result.get("output_name"))
        for result in batch_results
        if result.get("status") == "success" and result.get("output_name")
    }
    return [item for item in review_items if item.output_name in fresh_output_names]


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
    ("#141414", "r\u0119cznie ukryte (magic pen)"),
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

    def set_text(self, text: str) -> None:
        """Update the tooltip text shown on the next hover/flash."""
        self.text = text

    def flash(self, duration_ms: int = 3500) -> None:
        """Show the tooltip immediately, without waiting for a hover, then
        auto-hide it - used for a one-time first-use hint."""
        self._cancel()
        self._show()
        self.widget.after(duration_ms, self._hide)


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
        self.auto_open_on_approve = True

        self.review_dir: Path | None = None
        self.review_items: list[ReviewItem] = []
        self.review_batch_summary_names: list[str] = []
        self.last_batch_result: BatchResult | None = None
        self.original_path_by_output_name: dict[str, Path] = {}
        self._last_drop_time: float = 0.0
        self.history_config_path = history_config_path()
        self.recent_folders: list[dict[str, str]] = load_recent_folders(
            self.history_config_path
        )

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

        self.active_screen = "start"
        self.environment_items: list | None = None
        self.environment_installing: set[str] = set()

        self.dependency_updates: list | None = None
        self.package_updates_installing: set[str] = set()

        # One shared dismiss flag: missing-dependency issues and available
        # library updates render as a single combined banner (see
        # _build_status_banner) so they never stack as two separate cards
        # eating extra vertical space above the drop zone.
        self.status_banner_dismissed = False

        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("blue")

        self._build_shell()
        self.show_start_screen()
        # Off the GUI thread: importing spaCy alone costs ~1-2s, and this
        # must never make the window feel slow to open.
        self.root.after(150, self._start_environment_check)
        # Slightly staggered after the (local, fast) environment check -
        # this one makes network calls to PyPI and can legitimately take a
        # few seconds, especially when offline and every lookup times out.
        self.root.after(400, self._start_update_check)

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

        history_button = ctk.CTkButton(
            topbar,
            text="\U0001f553 Historia",
            width=100,
            height=34,
            corner_radius=8,
            fg_color="transparent",
            hover_color=COLOR_ICON_IDLE,
            text_color=COLOR_TEXT_MUTED,
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            command=self.show_history_screen,
        )
        history_button.pack(side="right", padx=(0, 8))
        IconTooltip(history_button, "Wcześniej przetworzone foldery")

        self.content = ctk.CTkFrame(self.root, fg_color="transparent")
        self.content.pack(fill="both", expand=True, padx=20, pady=16)

    def _clear_content(self) -> None:
        for widget in self.content.winfo_children():
            widget.destroy()

    # ------------------------------------------------------------------
    # Startup checks: NER/OCR/LLM availability and pip-library updates.
    # Both render into one combined banner (_build_status_banner) so a
    # missing-dependency card and an updates-available card never stack as
    # two separate boxes eating extra vertical space above the drop zone.
    # ------------------------------------------------------------------

    def _start_environment_check(self) -> None:
        def worker() -> None:
            items = check_environment()
            self.root.after(0, lambda: self._on_environment_check_done(items))

        threading.Thread(target=worker, daemon=True).start()

    def _on_environment_check_done(self, items: list) -> None:
        self.environment_items = items
        if self.active_screen == "start":
            self.show_start_screen()

    def _start_update_check(self) -> None:
        def worker() -> None:
            items = check_dependency_updates()
            self.root.after(0, lambda: self._on_update_check_done(items))

        threading.Thread(target=worker, daemon=True).start()

    def _on_update_check_done(self, items: list) -> None:
        self.dependency_updates = items
        if self.active_screen == "start":
            self.show_start_screen()

    def _dismiss_status_banner(self) -> None:
        self.status_banner_dismissed = True
        if self.active_screen == "start":
            self.show_start_screen()

    def _recheck_status(self) -> None:
        self._start_environment_check()
        self._start_update_check()

    def _install_ner_model_clicked(self, model_name: str) -> None:
        if ENV_ITEM_NER in self.environment_installing:
            return
        self.environment_installing.add(ENV_ITEM_NER)
        if self.active_screen == "start":
            self.show_start_screen()

        def worker() -> None:
            install_ner_model(model_name)
            self.root.after(0, self._on_ner_install_done)

        threading.Thread(target=worker, daemon=True).start()

    def _on_ner_install_done(self) -> None:
        self.environment_installing.discard(ENV_ITEM_NER)
        # Re-run the full check rather than assuming success - confirms the
        # install actually worked instead of just hiding the button.
        self._start_environment_check()

    def _update_package_clicked(self, package: str) -> None:
        if package in self.package_updates_installing:
            return
        installed_version = None
        latest_version = None
        for item in self.dependency_updates or []:
            if item.package == package:
                installed_version, latest_version = item.installed_version, item.latest_version
                break
        confirmed = messagebox.askyesno(
            "Aktualizacja biblioteki",
            f"Zainstalować aktualizację {package} "
            f"({installed_version} → {latest_version})?",
        )
        if not confirmed:
            return

        self.package_updates_installing.add(package)
        if self.active_screen == "start":
            self.show_start_screen()

        def worker() -> None:
            install_package_update(package)
            self.root.after(0, lambda: self._on_package_update_done(package))

        threading.Thread(target=worker, daemon=True).start()

    def _on_package_update_done(self, package: str) -> None:
        self.package_updates_installing.discard(package)
        # Re-run the full check rather than assuming success - confirms the
        # install actually worked instead of just hiding the button.
        self._start_update_check()

    def _build_status_banner(self, parent: ctk.CTkFrame) -> None:
        if self.status_banner_dismissed:
            return
        issues = [item for item in (self.environment_items or []) if not item.ok]
        updates = [
            item
            for item in (self.dependency_updates or [])
            if item.ok and item.update_available
        ]
        if not issues and not updates:
            return

        # Missing/broken dependencies are more actionable than "a newer
        # version exists" - the warning styling wins when both are present.
        is_warning = bool(issues)
        header_text = (
            "⚠ Niektóre funkcje mogą nie działać w pełni:"
            if is_warning
            else "⬆ Dostępne aktualizacje bibliotek:"
        )
        bg_color = COLOR_WARNING_SOFT if is_warning else COLOR_ACCENT_SOFT
        border_color = COLOR_WARNING if is_warning else COLOR_ACCENT
        header_color = COLOR_WARNING_TEXT if is_warning else COLOR_ACCENT_HOVER

        card = ctk.CTkFrame(
            parent,
            fg_color=bg_color,
            corner_radius=10,
            border_width=1,
            border_color=border_color,
        )
        card.pack(fill="x", pady=(0, 10))
        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="x", padx=14, pady=8)

        header_row = ctk.CTkFrame(inner, fg_color="transparent")
        header_row.pack(fill="x")
        ctk.CTkLabel(
            header_row,
            text=header_text,
            font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
            text_color=header_color,
            anchor="w",
        ).pack(side="left")
        ctk.CTkButton(
            header_row,
            text="✕",
            width=22,
            height=22,
            corner_radius=11,
            fg_color="transparent",
            hover_color=COLOR_ICON_IDLE,
            text_color=header_color,
            command=self._dismiss_status_banner,
        ).pack(side="right")

        for item in issues:
            row = ctk.CTkFrame(inner, fg_color="transparent")
            row.pack(fill="x", pady=(6, 0))
            text_col = ctk.CTkFrame(row, fg_color="transparent")
            text_col.pack(side="left", fill="x", expand=True)
            ctk.CTkLabel(
                text_col,
                text=item.label_pl,
                font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
                text_color=COLOR_TEXT,
                anchor="w",
            ).pack(fill="x")
            ctk.CTkLabel(
                text_col,
                text=item.detail_pl,
                font=ctk.CTkFont(family=FONT_FAMILY, size=10),
                text_color=COLOR_TEXT_MUTED,
                anchor="w",
                wraplength=520,
                justify="left",
            ).pack(fill="x")

            if item.item in self.environment_installing:
                ctk.CTkLabel(
                    row,
                    text="Instaluję...",
                    font=ctk.CTkFont(family=FONT_FAMILY, size=10),
                    text_color=COLOR_TEXT_MUTED,
                ).pack(side="right", padx=(8, 0))
            elif item.install_action == INSTALL_ACTION_SPACY_MODEL:
                ctk.CTkButton(
                    row,
                    text="Zainstaluj model NER",
                    width=160,
                    height=26,
                    corner_radius=8,
                    fg_color=COLOR_ACCENT,
                    hover_color=COLOR_ACCENT_HOVER,
                    font=ctk.CTkFont(family=FONT_FAMILY, size=10, weight="bold"),
                    command=lambda target=item.install_target: self._install_ner_model_clicked(
                        target
                    ),
                ).pack(side="right", padx=(8, 0))
            elif item.install_action == INSTALL_ACTION_OPEN_URL:
                ctk.CTkButton(
                    row,
                    text="Pobierz",
                    width=100,
                    height=26,
                    corner_radius=8,
                    fg_color=COLOR_ICON_IDLE,
                    hover_color=COLOR_BORDER,
                    text_color=COLOR_TEXT,
                    font=ctk.CTkFont(family=FONT_FAMILY, size=10),
                    command=lambda url=item.install_target: webbrowser.open(url),
                ).pack(side="right", padx=(8, 0))

        if issues and updates:
            ctk.CTkLabel(
                inner,
                text="Dostępne aktualizacje bibliotek:",
                font=ctk.CTkFont(family=FONT_FAMILY, size=10, weight="bold"),
                text_color=COLOR_TEXT_MUTED,
                anchor="w",
            ).pack(fill="x", pady=(8, 0))

        for item in updates:
            row = ctk.CTkFrame(inner, fg_color="transparent")
            row.pack(fill="x", pady=(6, 0))
            ctk.CTkLabel(
                row,
                text=f"{item.package}: {item.installed_version} → {item.latest_version}",
                font=ctk.CTkFont(family=FONT_FAMILY, size=11),
                text_color=COLOR_TEXT,
                anchor="w",
            ).pack(side="left", fill="x", expand=True)

            if item.package in self.package_updates_installing:
                ctk.CTkLabel(
                    row,
                    text="Instaluję...",
                    font=ctk.CTkFont(family=FONT_FAMILY, size=10),
                    text_color=COLOR_TEXT_MUTED,
                ).pack(side="right", padx=(8, 0))
            else:
                ctk.CTkButton(
                    row,
                    text="Aktualizuj",
                    width=100,
                    height=26,
                    corner_radius=8,
                    fg_color=COLOR_ACCENT,
                    hover_color=COLOR_ACCENT_HOVER,
                    font=ctk.CTkFont(family=FONT_FAMILY, size=10, weight="bold"),
                    command=lambda name=item.package: self._update_package_clicked(name),
                ).pack(side="right", padx=(8, 0))

        ctk.CTkButton(
            inner,
            text="Sprawdź ponownie",
            width=140,
            height=24,
            corner_radius=8,
            fg_color="transparent",
            hover_color=COLOR_ICON_IDLE,
            text_color=COLOR_TEXT_MUTED,
            font=ctk.CTkFont(family=FONT_FAMILY, size=10),
            command=self._recheck_status,
        ).pack(anchor="e", pady=(8, 0))

    # ------------------------------------------------------------------
    # Start screen (drag & drop)
    # ------------------------------------------------------------------

    def show_start_screen(self) -> None:
        self.active_screen = "start"
        self._clear_content()

        self._build_status_banner(self.content)

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
        # A drop on the same zone ends with a mouse-up that Tk also reports
        # as a <Button-1> click; skip opening a redundant file dialog right
        # after a real drop was just handled.
        if time.monotonic() - self._last_drop_time < 0.6:
            return
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
        self._last_drop_time = time.monotonic()
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
    # History screen
    # ------------------------------------------------------------------

    def show_history_screen(self) -> None:
        self.active_screen = "history"
        self._clear_content()
        self.recent_folders = load_recent_folders(self.history_config_path)

        header = ctk.CTkFrame(self.content, fg_color="transparent")
        header.pack(fill="x", pady=(0, 10))
        ctk.CTkButton(
            header,
            text="⬅ Wróć",
            width=90,
            height=28,
            corner_radius=8,
            fg_color="transparent",
            hover_color=COLOR_ICON_IDLE,
            text_color=COLOR_TEXT_MUTED,
            command=self.show_start_screen,
        ).pack(side="left")
        ctk.CTkLabel(
            header,
            text="Historia",
            font=ctk.CTkFont(family=FONT_FAMILY, size=15, weight="bold"),
            text_color=COLOR_TEXT,
        ).pack(side="left", padx=(12, 0))

        ctk.CTkLabel(
            self.content,
            text=(
                "Lista wcześniej użytych folderów wynikowych - same ścieżki, "
                "bez treści dokumentów. Kliknij, aby otworzyć przegląd danego folderu."
            ),
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            text_color=COLOR_TEXT_MUTED,
            wraplength=700,
            justify="left",
        ).pack(fill="x", pady=(0, 10))

        scroll = ctk.CTkScrollableFrame(
            self.content, fg_color="transparent", label_text=""
        )
        scroll.pack(fill="both", expand=True)

        if not self.recent_folders:
            ctk.CTkLabel(
                scroll,
                text="Brak historii - żaden folder nie został jeszcze użyty.",
                font=ctk.CTkFont(family=FONT_FAMILY, size=12),
                text_color=COLOR_TEXT_MUTED,
            ).pack(pady=30)
            return

        for entry in self.recent_folders:
            self._build_history_card(scroll, entry)

    def _build_history_card(
        self, parent: ctk.CTkFrame, entry: dict[str, str]
    ) -> None:
        folder_path = entry.get("path", "")
        exists = Path(folder_path).is_dir()

        card = ctk.CTkFrame(
            parent,
            corner_radius=10,
            fg_color=COLOR_CARD,
            border_width=1,
            border_color=COLOR_BORDER,
        )
        card.pack(fill="x", pady=4)
        row = ctk.CTkFrame(card, fg_color="transparent")
        row.pack(fill="x", padx=14, pady=10)

        text_col = ctk.CTkFrame(row, fg_color="transparent")
        text_col.pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(
            text_col,
            text=Path(folder_path).name or folder_path,
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
            text_color=COLOR_TEXT if exists else COLOR_TEXT_MUTED,
            anchor="w",
        ).pack(fill="x")
        ctk.CTkLabel(
            text_col,
            text=format_recent_folder_timestamp(entry.get("last_used", "")),
            font=ctk.CTkFont(family=FONT_FAMILY, size=10),
            text_color=COLOR_TEXT_MUTED,
            anchor="w",
        ).pack(fill="x")

        if exists:
            ctk.CTkButton(
                row,
                text="Otwórz",
                width=90,
                height=30,
                corner_radius=8,
                fg_color=COLOR_ACCENT,
                hover_color=COLOR_ACCENT_HOVER,
                font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
                command=lambda p=folder_path: self.open_history_folder(p),
            ).pack(side="right")
        else:
            ctk.CTkLabel(
                row,
                text="folder nie istnieje",
                font=ctk.CTkFont(family=FONT_FAMILY, size=10),
                text_color=COLOR_HIGH_RISK,
            ).pack(side="right")

    # ------------------------------------------------------------------
    # Settings modal
    # ------------------------------------------------------------------

    def open_settings(self) -> None:
        SettingsDialog(self)

    # ------------------------------------------------------------------
    # Processing screen
    # ------------------------------------------------------------------

    def show_processing_screen(self) -> None:
        self.active_screen = "processing"
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
        self.review_items = restrict_review_items_to_batch(
            self.review_items, batch_result.results
        )
        self._remember_recent_folder(self.output_dir)
        self.show_review_screen()

    def _remember_recent_folder(self, folder: Path) -> None:
        timestamp = datetime.now(timezone.utc).isoformat()
        self.recent_folders = record_recent_folder(
            self.recent_folders, folder, timestamp
        )
        try:
            save_recent_folders(self.history_config_path, self.recent_folders)
        except OSError:
            pass

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
        self.active_screen = "review"
        self._clear_content()

        header = ctk.CTkFrame(self.content, fg_color="transparent")
        header.pack(fill="x", pady=(0, 10))
        ctk.CTkButton(
            header,
            text="\u2b05 Nowe pliki",
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

        self._build_batch_errors_card(self.content)

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

    def _build_batch_errors_card(self, parent: ctk.CTkFrame) -> None:
        """Show which files from the just-run batch failed and why.

        Without this, a batch where every file errors out (e.g. a scanned
        PDF and no local OCR installed) previously landed on a silent,
        unexplained "Brak wykrytych wyników" empty review screen.
        """
        if self.last_batch_result is None:
            return
        failed_items = format_batch_error_items(self.last_batch_result)
        if not failed_items:
            return

        card = ctk.CTkFrame(
            parent,
            fg_color=COLOR_HIGH_RISK_SOFT,
            corner_radius=10,
            border_width=1,
            border_color=COLOR_HIGH_RISK,
        )
        card.pack(fill="x", pady=(0, 10))
        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="x", padx=14, pady=10)
        file_word = "pliku" if len(failed_items) == 1 else "plików"
        ctk.CTkLabel(
            inner,
            text=f"⚠ Nie udało się przetworzyć {len(failed_items)} {file_word}:",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
            text_color=COLOR_HIGH_RISK,
            anchor="w",
        ).pack(fill="x")
        for input_name, reason in failed_items:
            ctk.CTkLabel(
                inner,
                text=f"•  {input_name} — {reason}",
                font=ctk.CTkFont(family=FONT_FAMILY, size=11),
                text_color=COLOR_TEXT,
                anchor="w",
                wraplength=640,
                justify="left",
            ).pack(fill="x", padx=(10, 0), pady=(4, 0))

    def _build_legend_row(self, parent: ctk.CTkFrame) -> None:
        legend_card = ctk.CTkFrame(
            parent,
            fg_color=COLOR_CARD,
            corner_radius=10,
            border_width=1,
            border_color=COLOR_BORDER,
        )
        legend_card.pack(pady=(4, 8), padx=4, fill="x")
        legend_frame = ctk.CTkFrame(legend_card, fg_color="transparent")
        legend_frame.pack(pady=8, padx=12)
        ctk.CTkLabel(
            legend_frame,
            text="Legenda kolorów:",
            text_color=COLOR_TEXT,
            font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
        ).pack(side="left", padx=(0, 12))
        for color, text in LEGEND_ITEMS:
            item = ctk.CTkFrame(legend_frame, fg_color="transparent")
            item.pack(side="left", padx=8)
            ctk.CTkLabel(
                item,
                text="●",
                text_color=color,
                font=ctk.CTkFont(family=FONT_FAMILY, size=18, weight="bold"),
                width=16,
            ).pack(side="left")
            ctk.CTkLabel(
                item,
                text=text,
                text_color=COLOR_TEXT,
                font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            ).pack(side="left")

    def pick_review_folder(self) -> None:
        folder_path = filedialog.askdirectory(title="Wybierz folder do przeglądu")
        if not folder_path:
            return
        self.review_dir = Path(folder_path)
        self.last_batch_result = None
        self._load_review_folder()
        self._remember_recent_folder(self.review_dir)
        self.show_review_screen()

    def open_history_folder(self, folder_path: str) -> None:
        folder = Path(folder_path)
        if not folder.is_dir():
            return
        self.review_dir = folder
        self.last_batch_result = None
        self._load_review_folder()
        self._remember_recent_folder(folder)
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
        if status == REVIEW_STATUS_APPROVED:
            self._open_on_approve(item)

    def _open_on_approve(self, item: ReviewItem) -> None:
        """Open the final file once the user actually approves it - not
        right after anonymizing, since at that point they haven't looked
        at it yet and it may still need edits or rejection."""
        if not self.auto_open_on_approve or self.review_dir is None:
            return
        try:
            open_path_with_default_app(
                preferred_review_output_path(self.review_dir, item.output_name)
            )
        except OSError:
            pass

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
        self._open_internal_review_file(item.report_name)

    def open_review_checklist(self, item: ReviewItem) -> None:
        if item.checklist_name is None:
            return
        self._open_internal_review_file(item.checklist_name)

    def _open_review_file(self, file_name: str) -> None:
        if self.review_dir is None:
            return
        file_path = self.review_dir / Path(file_name).name
        try:
            open_path_with_default_app(file_path)
        except OSError:
            pass

    def _open_internal_review_file(self, file_name: str) -> None:
        """Open a report/checklist/other internal-artifact file, which
        lives in the hidden internal-artifacts subfolder, not review_dir
        itself."""
        if self.review_dir is None:
            return
        file_path = internal_artifacts_dir(self.review_dir) / Path(file_name).name
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
        report_path = internal_artifacts_dir(self.review_dir) / Path(item.report_name).name
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
        self.window.geometry("560x700")
        self.window.configure(fg_color=COLOR_BG)
        self.window.transient(app.root)
        self.window.grab_set()
        _bring_window_to_front(self.window)

        self.ner_var = tk.BooleanVar(value=app.use_ner)
        self.llm_var = tk.BooleanVar(value=app.use_llm_review)
        self.llm_model_var = tk.StringVar(value=app.llm_model_name)
        self.pdf_mode_var = tk.StringVar(value=app.pdf_output_label)
        self.auto_open_var = tk.BooleanVar(value=app.auto_open_on_approve)
        self.sensitive_terms_path = app.sensitive_terms_path
        self.environment_status = environment_status_lookup(app.environment_items)

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
            status_ok=self.environment_status.get(ENV_ITEM_NER),
        )
        self._build_toggle_section(
            body,
            "Dodatkowa weryfikacja AI (LLM)",
            "Opcjonalne, wymaga lokalnego Ollama",
            self.llm_var,
            status_ok=self.environment_status.get(ENV_ITEM_LLM),
        )
        self._build_status_row(
            body,
            "OCR (skany, obrazy)",
            "Automatyczne, wymaga lokalnego Tesseracta",
            status_ok=self.environment_status.get(ENV_ITEM_OCR),
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

        self._build_toggle_section(
            body,
            "Otwórz automatycznie po zatwierdzeniu",
            "Otwiera plik dopiero gdy klikniesz ✓ Zatwierdzony, nie od razu po anonimizacji",
            self.auto_open_var,
        )

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

    def _build_status_dot(self, parent: ctk.CTkFrame, status_ok: bool | None) -> None:
        """A small, deliberately subtle status dot - green when the
        underlying dependency is confirmed available, muted gray when
        it's confirmed missing, nothing at all while still unknown (the
        background check hasn't completed yet)."""
        if status_ok is None:
            return
        dot = ctk.CTkLabel(
            parent,
            text="●",
            font=ctk.CTkFont(family=FONT_FAMILY, size=10),
            text_color=COLOR_OK if status_ok else COLOR_ICON_IDLE,
            width=12,
        )
        dot.pack(side="left", padx=(0, 6))
        IconTooltip(
            dot,
            "Dostępne" if status_ok else "Niedostępne - patrz Ustawienia > sprawdzenie środowiska",
        )

    def _build_toggle_section(
        self,
        parent: ctk.CTkFrame,
        title: str,
        subtitle: str,
        variable: tk.BooleanVar,
        *,
        status_ok: bool | None = None,
    ) -> None:
        frame = self._section_frame(parent)
        row = ctk.CTkFrame(frame, fg_color="transparent")
        row.pack(fill="x", padx=14, pady=12)
        text_col = ctk.CTkFrame(row, fg_color="transparent")
        text_col.pack(side="left", fill="x", expand=True)
        title_row = ctk.CTkFrame(text_col, fg_color="transparent")
        title_row.pack(fill="x")
        self._build_status_dot(title_row, status_ok)
        ctk.CTkLabel(
            title_row,
            text=title,
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
            text_color=COLOR_TEXT,
            anchor="w",
        ).pack(side="left", fill="x")
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

    def _build_status_row(
        self,
        parent: ctk.CTkFrame,
        title: str,
        subtitle: str,
        *,
        status_ok: bool | None = None,
    ) -> None:
        """Same visual family as _build_toggle_section, for a dependency
        that has no on/off toggle of its own (OCR runs automatically)."""
        frame = self._section_frame(parent)
        row = ctk.CTkFrame(frame, fg_color="transparent")
        row.pack(fill="x", padx=14, pady=12)
        text_col = ctk.CTkFrame(row, fg_color="transparent")
        text_col.pack(side="left", fill="x", expand=True)
        title_row = ctk.CTkFrame(text_col, fg_color="transparent")
        title_row.pack(fill="x")
        self._build_status_dot(title_row, status_ok)
        ctk.CTkLabel(
            title_row,
            text=title,
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
            text_color=COLOR_TEXT,
            anchor="w",
        ).pack(side="left", fill="x")
        ctk.CTkLabel(
            text_col,
            text=subtitle,
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            text_color=COLOR_TEXT_MUTED,
            anchor="w",
        ).pack(fill="x")

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
        self.app.auto_open_on_approve = self.auto_open_var.get()
        self.app.sensitive_terms_path = self.sensitive_terms_path
        if self.app.use_llm_review and not self.app.llm_model_name:
            status, models = list_installed_models()
            _values, selected_model, _hint = format_llm_model_selector_state(
                status, models
            )
            self.app.llm_model_name = selected_model
        self.window.destroy()


def pdf_page_zoom(page_width_pt: float, target_width: int) -> float:
    """Return the render zoom used to scale a PDF page to ``target_width``."""
    safe_width = max(page_width_pt, 1)
    return target_width / safe_width


def ctk_widget_scaling_factor(widget: object) -> float:
    """Return the current CustomTkinter DPI scaling factor for ``widget``.

    CTkImage applies this automatically; code that draws directly onto a
    plain Tk widget (like the magic pen's tk.Canvas) has to apply it by
    hand to render at a matching on-screen size. Always falls back to 1.0
    (no scaling) rather than raising - a display-scaling mismatch is a
    cosmetic issue, never worth crashing the preview over.
    """
    try:
        return float(ctk.ScalingTracker.get_widget_scaling(widget))
    except Exception:  # noqa: BLE001 - cosmetic fallback, must never crash
        return 1.0


def canvas_point_to_pdf_point(cx: float, cy: float, zoom: float) -> tuple[float, float]:
    """Convert a canvas pixel coordinate back to PDF point coordinates."""
    safe_zoom = zoom if zoom else 1.0
    return (cx / safe_zoom, cy / safe_zoom)


def normalize_drag_rect(
    x0: float, y0: float, x1: float, y1: float
) -> tuple[float, float, float, float]:
    """Return a rectangle with x0<=x1 and y0<=y1, regardless of drag direction."""
    return (min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1))


def is_degenerate_drag_rect(
    x0: float, y0: float, x1: float, y1: float, *, min_size: float = 4.0
) -> bool:
    """True when a dragged rectangle is too small to be an intentional selection."""
    return (x1 - x0) < min_size or (y1 - y0) < min_size


BASE_PREVIEW_WIDTH = 460
ZOOM_MIN = 0.5
ZOOM_MAX = 3.0
ZOOM_STEP = 0.1
ZOOM_DEFAULT = 1.0
ZOOM_LINK_HINT_ID = "zoom_link_toggle"


def clamp_zoom_level(
    value: float, minimum: float = ZOOM_MIN, maximum: float = ZOOM_MAX
) -> float:
    """Clamp a preview zoom multiplier to a sane, always-legible range."""
    return round(min(max(value, minimum), maximum), 2)


def zoom_percent_label(value: float) -> str:
    """Format a zoom multiplier as a whole-percent label, e.g. 1.2 -> '120%'."""
    return f"{round(value * 100)}%"


def zoom_step_from_scroll_event(event: object) -> int:
    """Return -1/0/+1 zoom-out/none/zoom-in for one Ctrl+scroll event."""
    event_num = getattr(event, "num", None)
    if event_num == 4:
        return 1
    if event_num == 5:
        return -1
    delta = int(getattr(event, "delta", 0) or 0)
    if delta > 0:
        return 1
    if delta < 0:
        return -1
    return 0


def zoom_link_glyph(linked: bool) -> str:
    """Return the padlock glyph for the zoom-link toggle's current state.

    A closed padlock ("locked together") for linked zoom and an open
    padlock ("free to move independently") for unlinked - the glyph itself
    should suggest the meaning without requiring a hover or prior
    knowledge of the convention.
    """
    return "🔒" if linked else "🔓"


def zoom_link_tooltip_text(linked: bool) -> str:
    """Return hover-tooltip text describing the zoom-link toggle's state
    and what clicking it will do next."""
    if linked:
        return (
            "🔒 Powiększenie połączone: oba podglądy skalują się razem. "
            "Kliknij, aby ustawiać każdy osobno."
        )
    return (
        "🔓 Powiększenie niezależne: każdy podgląd osobno. "
        "Kliknij, aby połączyć oba."
    )


def ui_hints_config_path() -> Path:
    """Return the local file that remembers which one-time UI hints (for
    example the zoom-link toggle) the user has already seen.

    Stores hint ids only - never document content, folder paths, or
    anything else about what the user processed.
    """
    return Path.home() / ".anonimizer" / "ui_hints_seen.json"


def load_seen_hints(config_path: Path) -> set[str]:
    """Load the set of already-seen hint ids, tolerating a missing/corrupt file."""
    try:
        raw = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return set()
    if not isinstance(raw, list):
        return set()
    return {str(item) for item in raw if isinstance(item, str)}


def save_seen_hints(config_path: Path, hint_ids: set[str]) -> None:
    """Persist the seen-hints set, creating the config folder if needed."""
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(
        json.dumps(sorted(hint_ids), ensure_ascii=False, indent=2), encoding="utf-8"
    )


def find_rect_at_point(
    rects: Sequence[Mapping[str, object]], page_number: int, x: float, y: float
) -> Mapping[str, object] | None:
    """Return the top-most rect on a page whose bounds contain the point."""
    for rect in reversed(list(rects)):
        if int(rect.get("page", -1)) != page_number:
            continue
        if (
            float(rect["x0"]) <= x <= float(rect["x1"])
            and float(rect["y0"]) <= y <= float(rect["y1"])
        ):
            return rect
    return None


def _render_text_block(parent: ctk.CTkBaseClass, text: str, zoom: float = 1.0) -> None:
    box = ctk.CTkTextbox(
        parent,
        width=int(440 * zoom),
        height=int(600 * zoom),
        wrap="word",
        fg_color=COLOR_CARD,
        text_color=COLOR_TEXT,
        font=ctk.CTkFont(family=FONT_FAMILY, size=max(1, round(11 * zoom))),
    )
    box.pack(fill="both", expand=True, padx=4, pady=4)
    box.insert("1.0", text)
    box.configure(state="disabled")


def render_document_preview(
    parent: ctk.CTkBaseClass, path: Path, target_width: int = BASE_PREVIEW_WIDTH
) -> list["ctk.CTkImage"]:
    """Render a document's pages/content into the given scrollable frame.

    ``target_width`` also scales DOCX/TXT text-block previews (relative to
    ``BASE_PREVIEW_WIDTH``), so the same zoom control works for every
    supported preview type.

    Returns the CTkImage objects created so the caller can keep a strong
    reference alive for the window's lifetime (Tk drops images that are
    only referenced by the widget itself once the local variable is gone).
    """
    images: list[ctk.CTkImage] = []
    suffix = path.suffix.lower()
    text_zoom = target_width / BASE_PREVIEW_WIDTH
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
            _render_text_block(parent, read_docx_file(path), zoom=text_zoom)
        elif suffix == ".txt":
            _render_text_block(parent, read_txt_file(path), zoom=text_zoom)
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
    """Side-by-side original-vs-anonymized preview.

    For PDF outputs with a known original from the current session, the
    right pane ("Po anonimizacji") also offers the magic pen: manually hide
    a piece of text automatic detection missed, or undo a specific
    automatically detected rectangle. Every edit is staged locally and only
    takes effect on "Zapisz zmiany", which regenerates the true-redacted PDF
    from the original source file (see manual_redaction.py) — never by
    drawing over the already redacted output.
    """

    def __init__(
        self,
        app: AnonymizerApp,
        item: ReviewItem,
        original_path: Path | None,
        result_path: Path,
    ) -> None:
        self.app = app
        self.item = item
        self.source_path = original_path
        self.original_path = original_path
        self.result_path = result_path
        self._images: list[ctk.CTkImage] = []
        self._tk_images: list[ImageTk.PhotoImage] = []
        self._page_canvases: dict[int, tk.Canvas] = {}
        self._page_zoom: dict[int, float] = {}
        self._overlay_ids: dict[int, list[int]] = {}
        self._drag_start: tuple[float, float] | None = None
        self._drag_rect_id: int | None = None
        self.edits: ManualEdits = EMPTY_MANUAL_EDITS
        self.visible_rects: list[dict[str, object]] = []
        self.pending_remove_keys: set = set()
        self.pending_add_rects: list[ManualRect] = []
        self.save_button: ctk.CTkButton | None = None
        self.cancel_button: ctk.CTkButton | None = None
        self.pen_status_label: ctk.CTkLabel | None = None
        self.left_frame: ctk.CTkScrollableFrame | None = None
        self.right_frame: ctk.CTkScrollableFrame | None = None
        self.original_zoom = ZOOM_DEFAULT
        self.result_zoom = ZOOM_DEFAULT
        self.zoom_linked = True
        self.original_zoom_label: ctk.CTkLabel | None = None
        self.result_zoom_label: ctk.CTkLabel | None = None
        self._link_buttons: list[ctk.CTkButton] = []
        self._link_tooltips: list[IconTooltip] = []

        self.magic_pen_available = bool(
            original_path is not None
            and original_path.exists()
            and result_path.exists()
            and result_path.suffix.lower() == ".pdf"
        )

        window = ctk.CTkToplevel(app.root)
        self.window = window
        window.title(f"Porównanie - {item.output_name}")
        window.geometry("1120x780")
        window.minsize(760, 520)
        window.resizable(True, True)
        window.configure(fg_color=COLOR_BG)
        # Deliberately NOT window.transient(app.root): on Windows, a
        # transient window is treated as a dialog of its parent and loses
        # the native maximize button even with resizable(True, True) set -
        # this window needs to behave like a normal, fully maximizable
        # window so the magic pen has room to work precisely.
        window.bind("<Control-MouseWheel>", self._on_ctrl_scroll)
        window.bind("<Control-Button-4>", self._on_ctrl_scroll)
        window.bind("<Control-Button-5>", self._on_ctrl_scroll)
        window.protocol("WM_DELETE_WINDOW", self._close)

        ctk.CTkLabel(
            window,
            text=item.output_name,
            font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"),
            text_color=COLOR_TEXT,
        ).pack(anchor="w", padx=20, pady=(16, 4))

        # A real draggable splitter (tk.PanedWindow) instead of a fixed
        # 50/50 grid: dragging the sash resizes one side and shrinks the
        # other, like a normal split view.
        paned = tk.PanedWindow(
            window,
            orient=tk.HORIZONTAL,
            sashwidth=6,
            sashrelief="flat",
            bg=COLOR_BORDER,
            bd=0,
            showhandle=False,
        )
        paned.pack(fill="both", expand=True, padx=20, pady=(4, 8))

        left_container = ctk.CTkFrame(paned, fg_color="transparent")
        right_container = ctk.CTkFrame(paned, fg_color="transparent")
        paned.add(left_container, minsize=280, width=530, stretch="always")
        paned.add(right_container, minsize=280, width=530, stretch="always")

        self._build_pane_header(left_container, "Oryginał", "original").pack(
            fill="x", pady=(0, 6)
        )
        self._build_pane_header(right_container, "Po anonimizacji", "result").pack(
            fill="x", pady=(0, 6)
        )

        if self.magic_pen_available:
            self._build_magic_pen_toolbar(right_container).pack(fill="x", pady=(0, 6))

        left_frame = ctk.CTkScrollableFrame(
            left_container, fg_color=COLOR_CARD, corner_radius=10, label_text=""
        )
        left_frame.pack(fill="both", expand=True)
        self.left_frame = left_frame
        right_frame = ctk.CTkScrollableFrame(
            right_container, fg_color=COLOR_CARD, corner_radius=10, label_text=""
        )
        right_frame.pack(fill="both", expand=True)
        self.right_frame = right_frame

        self._rebuild_original_pane()

        if self.magic_pen_available:
            self.edits = load_manual_edits(manual_edits_path(result_path))
            self._reload_visible_rects()
            self._build_magic_pen_pane(right_frame)
        else:
            self._rebuild_result_pane()

        app._build_legend_row(window)

        ctk.CTkButton(
            window,
            text="Zamknij",
            width=140,
            height=36,
            corner_radius=8,
            fg_color=COLOR_ACCENT,
            hover_color=COLOR_ACCENT_HOVER,
            command=self._close,
        ).pack(pady=(0, 16))

        window.after(700, self._maybe_show_zoom_link_hint)
        # Opening a preview should visibly come to the front, not appear
        # behind whatever window was already open.
        _bring_window_to_front(window)

    def _close(self) -> None:
        """Close this window and bring the main app window back to front -
        matches _bring_window_to_front's rule for opening: whichever
        window the user just acted on should end up on top."""
        self.window.destroy()
        _bring_window_to_front(self.app.root)

    # -- zoom: independent or linked, like a dual-zone climate control ------

    def _build_pane_header(
        self, parent: ctk.CTkFrame, title: str, side: str
    ) -> ctk.CTkFrame:
        header = ctk.CTkFrame(parent, fg_color="transparent")
        ctk.CTkLabel(
            header,
            text=title,
            font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
            text_color=COLOR_TEXT_MUTED,
        ).pack(side="left")

        zoom_row = ctk.CTkFrame(header, fg_color="transparent")
        zoom_row.pack(side="right")
        ctk.CTkButton(
            zoom_row,
            text="－",
            width=24,
            height=22,
            corner_radius=6,
            fg_color=COLOR_ICON_IDLE,
            hover_color=COLOR_ACCENT_HOVER,
            text_color=COLOR_TEXT,
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            command=lambda: self._adjust_zoom(side, -1),
        ).pack(side="left", padx=(0, 2))
        zoom_label = ctk.CTkLabel(
            zoom_row,
            text=zoom_percent_label(ZOOM_DEFAULT),
            width=40,
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            text_color=COLOR_TEXT_MUTED,
        )
        zoom_label.pack(side="left")
        ctk.CTkButton(
            zoom_row,
            text="＋",
            width=24,
            height=22,
            corner_radius=6,
            fg_color=COLOR_ICON_IDLE,
            hover_color=COLOR_ACCENT_HOVER,
            text_color=COLOR_TEXT,
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            command=lambda: self._adjust_zoom(side, 1),
        ).pack(side="left", padx=(2, 6))
        link_button = ctk.CTkButton(
            zoom_row,
            text=zoom_link_glyph(self.zoom_linked),
            width=26,
            height=22,
            corner_radius=6,
            fg_color=COLOR_ACCENT,
            hover_color=COLOR_ACCENT_HOVER,
            text_color="#FFFFFF",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            command=self._toggle_zoom_link,
        )
        link_button.pack(side="left")
        self._link_buttons.append(link_button)
        self._link_tooltips.append(
            IconTooltip(link_button, zoom_link_tooltip_text(self.zoom_linked))
        )
        if side == "original":
            self.original_zoom_label = zoom_label
        else:
            self.result_zoom_label = zoom_label
        return header

    def _on_ctrl_scroll(self, event: object) -> None:
        widget = self.window.winfo_containing(event.x_root, event.y_root)
        side = self._pane_side_for_widget(widget)
        if side is None:
            return
        self._adjust_zoom(side, zoom_step_from_scroll_event(event))

    def _pane_side_for_widget(self, widget: object) -> str | None:
        node = widget
        while node is not None:
            if node is self.left_frame:
                return "original"
            if node is self.right_frame:
                return "result"
            node = getattr(node, "master", None)
        return None

    def _toggle_zoom_link(self) -> None:
        self.zoom_linked = not self.zoom_linked
        if self.zoom_linked and self.result_zoom != self.original_zoom:
            self.result_zoom = self.original_zoom
            self._rebuild_result_pane()
        self._update_zoom_controls()

    def _adjust_zoom(self, side: str, step: int) -> None:
        if step == 0:
            return
        delta = step * ZOOM_STEP
        if self.zoom_linked:
            new_value = clamp_zoom_level(self.original_zoom + delta)
            changed = new_value != self.original_zoom or new_value != self.result_zoom
            self.original_zoom = new_value
            self.result_zoom = new_value
            if changed:
                self._rebuild_original_pane()
                self._rebuild_result_pane()
        elif side == "original":
            new_value = clamp_zoom_level(self.original_zoom + delta)
            if new_value != self.original_zoom:
                self.original_zoom = new_value
                self._rebuild_original_pane()
        else:
            new_value = clamp_zoom_level(self.result_zoom + delta)
            if new_value != self.result_zoom:
                self.result_zoom = new_value
                self._rebuild_result_pane()
        self._update_zoom_controls()

    def _update_zoom_controls(self) -> None:
        if self.original_zoom_label is not None:
            self.original_zoom_label.configure(text=zoom_percent_label(self.original_zoom))
        if self.result_zoom_label is not None:
            self.result_zoom_label.configure(text=zoom_percent_label(self.result_zoom))
        glyph = zoom_link_glyph(self.zoom_linked)
        tooltip_text = zoom_link_tooltip_text(self.zoom_linked)
        for button, tooltip in zip(self._link_buttons, self._link_tooltips):
            button.configure(
                text=glyph,
                fg_color=COLOR_ACCENT if self.zoom_linked else COLOR_ICON_IDLE,
                text_color="#FFFFFF" if self.zoom_linked else COLOR_TEXT_MUTED,
            )
            tooltip.set_text(tooltip_text)

    def _maybe_show_zoom_link_hint(self) -> None:
        """Auto-show the link-toggle tooltip once, the first time this
        window is ever opened, instead of relying only on discovering it
        by hovering - a lightweight, one-time onboarding hint."""
        if not self._link_tooltips:
            return
        config_path = ui_hints_config_path()
        seen = load_seen_hints(config_path)
        if ZOOM_LINK_HINT_ID in seen:
            return
        self._link_tooltips[-1].flash(4500)
        seen.add(ZOOM_LINK_HINT_ID)
        try:
            save_seen_hints(config_path, seen)
        except OSError:
            pass

    def _rebuild_original_pane(self) -> None:
        if self.left_frame is None:
            return
        for widget in self.left_frame.winfo_children():
            widget.destroy()
        if self.original_path is not None and self.original_path.exists():
            self._images.extend(
                render_document_preview(
                    self.left_frame,
                    self.original_path,
                    target_width=int(BASE_PREVIEW_WIDTH * self.original_zoom),
                )
            )
        else:
            ctk.CTkLabel(
                self.left_frame,
                text=(
                    "Oryginał niedostępny - ten folder nie pochodzi z "
                    "bieżącej sesji przetwarzania."
                ),
                text_color=COLOR_TEXT_MUTED,
                wraplength=380,
                justify="left",
            ).pack(pady=30, padx=16)

    def _rebuild_result_pane(self) -> None:
        if self.right_frame is None:
            return
        if self.magic_pen_available:
            self._reload_pdf_pane()
            return
        for widget in self.right_frame.winfo_children():
            widget.destroy()
        if self.result_path.exists():
            self._images.extend(
                render_document_preview(
                    self.right_frame,
                    self.result_path,
                    target_width=int(BASE_PREVIEW_WIDTH * self.result_zoom),
                )
            )
        else:
            ctk.CTkLabel(
                self.right_frame,
                text="Plik wynikowy nie został znaleziony.",
                text_color=COLOR_TEXT_MUTED,
            ).pack(pady=30)

    # -- magic pen: toolbar -------------------------------------------------

    def _build_magic_pen_toolbar(self, parent: ctk.CTkFrame) -> ctk.CTkFrame:
        toolbar = ctk.CTkFrame(parent, fg_color="transparent")
        # Modeless: LMB always draws a new redaction, RMB always toggles an
        # existing one - no mode to switch first, so these are a static
        # legend rather than clickable buttons.
        for glyph, label in (
            ("✏", "LPM: zaznacz do ukrycia"),
            ("🧹", "PPM: usuń zaznaczenie"),
        ):
            chip = ctk.CTkFrame(toolbar, fg_color=COLOR_CARD, corner_radius=6)
            chip.pack(side="left", padx=(0, 6))
            ctk.CTkLabel(
                chip,
                text=glyph,
                font=ctk.CTkFont(family=FONT_FAMILY, size=13),
                text_color=COLOR_TEXT,
            ).pack(side="left", padx=(8, 4), pady=4)
            ctk.CTkLabel(
                chip,
                text=label,
                font=ctk.CTkFont(family=FONT_FAMILY, size=10),
                text_color=COLOR_TEXT_MUTED,
            ).pack(side="left", padx=(0, 8), pady=4)

        self.pen_status_label = ctk.CTkLabel(
            toolbar,
            text="",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            text_color=COLOR_TEXT_MUTED,
        )
        self.pen_status_label.pack(side="left", padx=10)

        self.cancel_button = ctk.CTkButton(
            toolbar,
            text="Anuluj zmiany",
            width=120,
            height=26,
            corner_radius=8,
            fg_color="transparent",
            hover_color=COLOR_ICON_IDLE,
            text_color=COLOR_TEXT_MUTED,
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            state="disabled",
            command=self._cancel_pending_changes,
        )
        self.cancel_button.pack(side="right", padx=(6, 0))
        self.save_button = ctk.CTkButton(
            toolbar,
            text="Zapisz zmiany",
            width=130,
            height=26,
            corner_radius=8,
            fg_color=COLOR_ICON_IDLE,
            hover_color=COLOR_ACCENT_HOVER,
            text_color=COLOR_TEXT_MUTED,
            font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
            state="disabled",
            command=self._save_pending_changes,
        )
        self.save_button.pack(side="right")
        return toolbar

    # -- magic pen: rendering -------------------------------------------------

    def _reload_visible_rects(self) -> None:
        if self.source_path is None:
            self.visible_rects = []
            return
        try:
            self.visible_rects = compute_visible_redaction_rects(
                self.source_path,
                edits=self.edits,
                sensitive_terms_path=self.app.sensitive_terms_path,
                use_ner=self.app.use_ner,
            )
        except (OSError, RuntimeError, ValueError):
            self.visible_rects = []

    def _build_magic_pen_pane(self, parent: ctk.CTkBaseClass) -> None:
        target_width = int(BASE_PREVIEW_WIDTH * self.result_zoom)
        # The "Oryginał" pane renders through CTkImage, which silently
        # scales by the display's DPI factor (customtkinter's own
        # get_widget_scaling) so it looks crisp on a scaled display. This
        # pane draws straight onto a plain tk.Canvas for the magic pen's
        # click/drag overlay, which has no such awareness - without
        # matching that factor here, the two pages visibly render at
        # different sizes on any non-100% display (confirmed: 125% on the
        # pilot machine). Multiplying it into the render zoom, and storing
        # that same effective zoom in self._page_zoom, keeps every later
        # coordinate conversion (click/drag/overlay) correctly aligned
        # without touching any of that code.
        dpi_scale = ctk_widget_scaling_factor(parent)
        try:
            import pymupdf as fitz

            with fitz.open(self.result_path) as document:
                for page_index, page in enumerate(document, start=1):
                    zoom = pdf_page_zoom(max(page.rect.width, 1), target_width) * dpi_scale
                    pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom))
                    pil_image = Image.frombytes(
                        "RGB", (pix.width, pix.height), pix.samples
                    )
                    tk_image = ImageTk.PhotoImage(pil_image)
                    self._tk_images.append(tk_image)
                    canvas = tk.Canvas(
                        parent,
                        width=pix.width,
                        height=pix.height,
                        highlightthickness=0,
                        bg="#FFFFFF",
                        cursor="tcross",
                    )
                    canvas.pack(pady=6)
                    canvas.create_image(0, 0, anchor="nw", image=tk_image)
                    self._page_canvases[page_index] = canvas
                    self._page_zoom[page_index] = zoom
                    # Modeless: left button always draws a new redaction,
                    # right button always toggles an existing one - no mode
                    # to switch first.
                    canvas.bind(
                        "<ButtonPress-1>",
                        lambda event, p=page_index: self._on_pane_press(event, p),
                    )
                    canvas.bind(
                        "<B1-Motion>",
                        lambda event, p=page_index: self._on_pane_drag(event, p),
                    )
                    canvas.bind(
                        "<ButtonRelease-1>",
                        lambda event, p=page_index: self._on_pane_release(event, p),
                    )
                    canvas.bind(
                        "<ButtonPress-3>",
                        lambda event, p=page_index: self._on_pane_right_click(event, p),
                    )
        except Exception:  # noqa: BLE001 - preview must never crash the app
            ctk.CTkLabel(
                parent,
                text="Nie udało się wczytać podglądu tego pliku.",
                text_color=COLOR_HIGH_RISK,
                wraplength=380,
                justify="left",
            ).pack(pady=30, padx=16)
            self.magic_pen_available = False

    def _reload_pdf_pane(self) -> None:
        if self.right_frame is None:
            return
        for canvas in self._page_canvases.values():
            canvas.destroy()
        self._page_canvases = {}
        self._page_zoom = {}
        self._overlay_ids = {}
        self._tk_images = []
        self._build_magic_pen_pane(self.right_frame)
        # A rebuild also happens on a plain zoom change (not just after a
        # save, which already cleared pending state) - repaint any
        # still-pending overlay so an in-progress selection is not visually
        # lost just because the page was rescaled and its canvas recreated.
        for page_number in self._page_canvases:
            self._redraw_overlay(page_number)

    # -- magic pen: interaction -------------------------------------------------

    def _hit_test_pool(self) -> list[dict[str, object]]:
        """Every rect a "remove" click can target: staged-for-removal rects
        stay in this pool (still shown, still clickable) so clicking one a
        second time can toggle the pending removal back off."""
        pending = [
            {
                "page": rect.page,
                "label": MANUAL_REDACTION_LABEL,
                "x0": rect.x0,
                "y0": rect.y0,
                "x1": rect.x1,
                "y1": rect.y1,
            }
            for rect in self.pending_add_rects
        ]
        return list(self.visible_rects) + pending

    def _on_pane_press(self, event: tk.Event, page_number: int) -> None:
        """Left button always starts drawing a new redaction rectangle."""
        self._drag_start = (event.x, event.y)
        self._drag_rect_id = None

    def _on_pane_right_click(self, event: tk.Event, page_number: int) -> None:
        """Right button always toggles the rectangle under the cursor."""
        zoom = self._page_zoom.get(page_number, 1.0)
        px, py = canvas_point_to_pdf_point(event.x, event.y, zoom)
        hit = find_rect_at_point(self._hit_test_pool(), page_number, px, py)
        if hit is not None:
            self._toggle_pending_remove(hit)

    def _on_pane_drag(self, event: tk.Event, page_number: int) -> None:
        if self._drag_start is None:
            return
        canvas = self._page_canvases.get(page_number)
        if canvas is None:
            return
        if self._drag_rect_id is not None:
            canvas.delete(self._drag_rect_id)
        x0, y0 = self._drag_start
        self._drag_rect_id = canvas.create_rectangle(
            x0, y0, event.x, event.y, outline="#dc2626", width=2, dash=(4, 2)
        )

    def _on_pane_release(self, event: tk.Event, page_number: int) -> None:
        if self._drag_start is None:
            return
        canvas = self._page_canvases.get(page_number)
        x0, y0 = self._drag_start
        self._drag_start = None
        if canvas is not None and self._drag_rect_id is not None:
            canvas.delete(self._drag_rect_id)
        self._drag_rect_id = None

        cx0, cy0, cx1, cy1 = normalize_drag_rect(x0, y0, event.x, event.y)
        if is_degenerate_drag_rect(cx0, cy0, cx1, cy1):
            return
        zoom = self._page_zoom.get(page_number, 1.0)
        px0, py0 = canvas_point_to_pdf_point(cx0, cy0, zoom)
        px1, py1 = canvas_point_to_pdf_point(cx1, cy1, zoom)
        self.pending_add_rects.append(
            ManualRect(page=page_number, x0=px0, y0=py0, x1=px1, y1=py1)
        )
        self._redraw_overlay(page_number)
        self._update_pending_state()

    def _toggle_pending_remove(self, hit: Mapping[str, object]) -> None:
        key = rect_info_key(hit)
        page_number = int(hit["page"])
        for index, rect in enumerate(self.pending_add_rects):
            rect_key = rect_info_key(
                {
                    "page": rect.page,
                    "label": MANUAL_REDACTION_LABEL,
                    "x0": rect.x0,
                    "y0": rect.y0,
                    "x1": rect.x1,
                    "y1": rect.y1,
                }
            )
            if rect_key == key:
                # A not-yet-saved manual addition: clicking it again in
                # remove mode simply cancels that pending addition.
                del self.pending_add_rects[index]
                self._redraw_overlay(page_number)
                self._update_pending_state()
                return
        if key in self.pending_remove_keys:
            # Clicking an already-staged-for-removal rect a second time
            # un-stages it, so a misclick doesn't require cancelling every
            # other pending change to undo.
            self.pending_remove_keys.discard(key)
        else:
            self.pending_remove_keys.add(key)
        self._redraw_overlay(page_number)
        self._update_pending_state()

    def _redraw_overlay(self, page_number: int) -> None:
        canvas = self._page_canvases.get(page_number)
        if canvas is None:
            return
        for item_id in self._overlay_ids.get(page_number, []):
            canvas.delete(item_id)
        zoom = self._page_zoom.get(page_number, 1.0)
        drawn_ids: list[int] = []

        for key in self.pending_remove_keys:
            for rect_info in self.visible_rects:
                if int(rect_info["page"]) != page_number:
                    continue
                if rect_info_key(rect_info) != key:
                    continue
                x0 = float(rect_info["x0"]) * zoom
                y0 = float(rect_info["y0"]) * zoom
                x1 = float(rect_info["x1"]) * zoom
                y1 = float(rect_info["y1"]) * zoom
                drawn_ids.append(
                    canvas.create_rectangle(x0, y0, x1, y1, outline="#16a34a", width=3)
                )
                break

        for rect in self.pending_add_rects:
            if rect.page != page_number:
                continue
            x0, y0, x1, y1 = rect.x0 * zoom, rect.y0 * zoom, rect.x1 * zoom, rect.y1 * zoom
            drawn_ids.append(
                canvas.create_rectangle(
                    x0, y0, x1, y1, fill="#111827", outline="#dc2626", width=2
                )
            )

        self._overlay_ids[page_number] = drawn_ids

    def _has_pending_changes(self) -> bool:
        return bool(self.pending_remove_keys) or bool(self.pending_add_rects)

    def _update_pending_state(self) -> None:
        has_pending = self._has_pending_changes()
        if self.save_button is not None:
            self.save_button.configure(
                state="normal" if has_pending else "disabled",
                fg_color=COLOR_ACCENT if has_pending else COLOR_ICON_IDLE,
                text_color="#FFFFFF" if has_pending else COLOR_TEXT_MUTED,
            )
        if self.cancel_button is not None:
            self.cancel_button.configure(state="normal" if has_pending else "disabled")
        if self.pen_status_label is not None:
            count = len(self.pending_remove_keys) + len(self.pending_add_rects)
            self.pen_status_label.configure(
                text=f"Niezapisane zmiany: {count}" if has_pending else ""
            )

    def _cancel_pending_changes(self) -> None:
        self.pending_remove_keys = set()
        self.pending_add_rects = []
        for page_number in list(self._page_canvases.keys()):
            self._redraw_overlay(page_number)
        self._update_pending_state()

    def _save_pending_changes(self) -> None:
        if not self._has_pending_changes() or self.source_path is None:
            return
        new_edits = apply_pending_overrides(
            self.edits, self.visible_rects, self.pending_remove_keys, self.pending_add_rects
        )
        if self.pen_status_label is not None:
            self.pen_status_label.configure(text="Zapisywanie...")
            self.window.update_idletasks()

        # Regenerate to a staging file first and only replace the live
        # output once that fully succeeds, so an interrupted or failed
        # regeneration (disk full, process killed) can never truncate or
        # corrupt the existing good output. The sidecar is written last,
        # after the real file is already safely in place, since it is the
        # smallest and least failure-prone step of the three.
        staging_path = self.result_path.with_name(
            f"{self.result_path.stem}.tmp{self.result_path.suffix}"
        )
        try:
            regenerate_pdf_with_manual_overrides(
                self.source_path,
                output_path=staging_path,
                edits=new_edits,
                sensitive_terms_path=self.app.sensitive_terms_path,
                use_ner=self.app.use_ner,
            )
            os.replace(staging_path, self.result_path)
            save_manual_edits(manual_edits_path(self.result_path), new_edits)
        except (OSError, RuntimeError, ValueError):
            try:
                staging_path.unlink(missing_ok=True)
            except OSError:
                pass
            if self.pen_status_label is not None:
                self.pen_status_label.configure(text="Nie udało się zapisać zmian.")
            return

        self.edits = new_edits
        self.pending_remove_keys = set()
        self.pending_add_rects = []
        self._reload_visible_rects()
        self._reload_pdf_pane()
        self._patch_report_with_manual_count(len(new_edits.added))
        self.app.set_review_status(self.item, REVIEW_STATUS_NEEDS_REVIEW)
        self._update_pending_state()
        if self.pen_status_label is not None:
            self.pen_status_label.configure(text="✓ Zmiany zapisane")

    def _patch_report_with_manual_count(self, manual_count: int) -> None:
        if self.app.review_dir is None or self.item.report_name is None:
            return
        report_path = (
            internal_artifacts_dir(self.app.review_dir) / Path(self.item.report_name).name
        )
        try:
            report_text = report_path.read_text(encoding="utf-8")
            report_path.write_text(
                apply_manual_redaction_count_to_report_text(report_text, manual_count),
                encoding="utf-8",
            )
        except OSError:
            pass


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
        _bring_window_to_front(window)

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
