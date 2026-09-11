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
from PIL import Image, ImageDraw, ImageTk
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


APP_TITLE = "DocShield"
APP_TAGLINE = "Anonimizuj dokumenty"
APP_SUBTITLE = "Chroń dane wrażliwe. Szybko, bezpiecznie i lokalnie."
# A small, deliberately personal touch on the start screen - rendered in
# a script-style font so it reads as a handwritten note, not a generic
# label (see the app's own design notes in pomysly/).
APP_PERSONAL_NOTE = "Twoje dokumenty. Tylko u Ciebie."
APP_VERSION = "0.1.0"
APP_ABOUT_TEXT = (
    "DocShield to lokalny anonimizator dokumentów: wykrywa i ukrywa dane "
    "wrażliwe w plikach PDF, DOCX i TXT bez wysyłania niczego poza Twój "
    "komputer - żadnego internetu, żadnej chmury, żadnego zewnętrznego API."
)
SCRIPT_FONT_FAMILY = "Segoe Script"
APP_ICON_PATH = Path(__file__).resolve().parent.parent / "assets" / "icon.png"
APP_ICON_ICO_PATH = Path(__file__).resolve().parent.parent / "assets" / "icon.ico"
# Identifies this app to Windows as distinct from the plain python.exe
# process running it, so the taskbar shows our own icon instead of
# python.exe's generic one (and groups repeated launches under it).
# Must be set once, before any window is created - see start_gui().
APP_USER_MODEL_ID = "DocShield.AnonimizatorDokumentow"
MANUAL_REVIEW_WARNING = (
    "Wymagany jest ręczny przegląd przed użyciem lub udostępnieniem wyniku."
)
WINDOW_MIN_WIDTH = 720
WINDOW_MIN_HEIGHT = 560
WINDOW_DEFAULT_SIZE = "960x680"
SELECTED_FILE_LIST_HEIGHT = 6
# Bounds the selected-files list to a fixed height with its own internal
# scrollbar once it holds more entries than fit - without this, adding
# enough files pushes the output-folder row and the "Anonimizuj" button
# below the window with no way to reach them at all (self.content itself
# does not scroll). Kept deliberately small (space for ~3 cards) so the
# always-visible action controls stay the priority even on a short window.
FILE_LIST_MAX_HEIGHT = 168
# Header row layout switches from side-by-side to stacked (see
# _update_header_layout) once the window narrows past this content width,
# so the handwritten-style personal note never gets clipped.
HEADER_STACK_BREAKPOINT = 640
# The start screen's quick-settings side panel is only shown above this
# window width - checked once at build time (not re-flowed live like the
# header, since this is a nice-to-have panel, not a control that must
# always be reachable) so it never squeezes the main column unusably.
QUICK_SETTINGS_MIN_WIDTH = 880
QUICK_SETTINGS_PANEL_WIDTH = 240
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
DEFAULT_OUTPUT_SUBDIR_NAME = "DocShield - wyniki"

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
    just unfocused. lift() + focus_force() alone are not always enough:
    Windows can silently refuse a foreground-focus request
    (SetForegroundWindow, what focus_force() ultimately calls) from a
    process that was not already in the foreground - a deliberate
    anti-focus-stealing OS rule. Briefly forcing "-topmost" uses a
    different call (SetWindowPos with HWND_TOPMOST) that is not subject
    to that same restriction, so it reliably wins the Z-order fight even
    when focus_force() alone would silently do nothing.

    Confirmed directly (not just in theory): releasing "-topmost" too
    soon after setting it undoes the whole fix - the window manager can
    still let some other window reclaim the front the moment it is no
    longer forced, before this one has genuinely finished becoming the
    real foreground window. 600ms gives that transition enough time to
    actually land before "-topmost" is switched back off, so the window
    does not end up pinned above everything else forever either.
    """
    window.deiconify()
    window.lift()
    window.attributes("-topmost", True)
    window.focus_force()
    window.after(600, lambda: window.attributes("-topmost", False))


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


def truncate_filename_middle(name: str, max_length: int = 26) -> str:
    """Shorten a filename for display, eliding the middle rather than the
    end - keeps the start (usually the most distinguishing part between
    similarly-named files) and the tail (extension, "_ANON" markers)
    visible, which a plain end-cut would otherwise hide. A fixed pixel
    width budget doesn't scale to how long real generated output names
    get (multiple existing category/collision suffixes), so this is a
    text-level truncation rather than trying to win back a few more
    pixels of column width.
    """
    if len(name) <= max_length or max_length <= 5:
        return name
    keep_end = min(10, max_length // 3)
    keep_start = max_length - keep_end - 1
    return f"{name[:keep_start]}…{name[-keep_end:]}"


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


def _pl_document_word(count: int) -> str:
    """Return the grammatically correct Polish word for "document(s)"."""
    if count == 1:
        return "dokument"
    last_digit = count % 10
    last_two = count % 100
    if 2 <= last_digit <= 4 and not (12 <= last_two <= 14):
        return "dokumenty"
    return "dokumentów"


def format_review_heading_subtitle(count: int) -> str:
    """Subtitle under the review screen's "Wyniki anonimizacji" heading."""
    if count == 1:
        return "1 dokument został przetworzony."
    word = _pl_document_word(count)
    if word == "dokumenty":
        # 2-4 (excluding 12-14): "zostały przetworzone", not the
        # 5+/genitive "zostało przetworzonych" form.
        return f"{count} dokumenty zostały przetworzone."
    return f"{count} dokumentów zostało przetworzonych."


def format_anonymize_button_text(input_file_count: int) -> str:
    """Label the main action button with the selected count, matching the
    mockup's "Anonimizuj 3 pliki" - falls back to the plain verb alone
    when nothing is selected yet, since "Anonimizuj 0 plików" reads oddly
    as an instruction.
    """
    if input_file_count <= 0:
        return "Anonimizuj"
    return f"Anonimizuj {input_file_count} {_pl_file_word(input_file_count)}"


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

COLOR_BG = "#EBF0FB"
COLOR_CARD = "#FFFFFF"
COLOR_BORDER = "#D7DEEA"
# Two blues, deliberately distinct: a dark navy/indigo for brand identity
# (sidebar, logo mark, big trust moments) and a brighter indigo-blue for
# interactive accents (buttons, links, active state) - the design brief
# calls for "granat/indygo jako kolor główny" plus a separate accent,
# not one blue doing both jobs.
COLOR_PRIMARY = "#16265C"
COLOR_PRIMARY_SOFT = "#E9ECF8"
COLOR_ACCENT = "#3D5AFE"
COLOR_ACCENT_HOVER = "#2F45D6"
COLOR_ACCENT_SOFT = "#E8EAFE"
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
_FILE_TYPE_ICON_CACHE: dict[tuple[str, int], "ctk.CTkImage"] = {}


def _draw_file_type_icon(color: str, size: int = 40) -> Image.Image:
    """Draw a small colored, document-shaped icon (rounded tile, white
    page with a folded top-right corner) for one file type - closer to
    the mockup's per-type icons than a plain colored rectangle of text,
    without needing to ship bespoke image assets per type. Drawn at 4x
    and downsampled for smooth edges.
    """
    scale = 4
    canvas_size = size * scale
    image = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    radius = canvas_size * 0.22
    draw.rounded_rectangle(
        (0, 0, canvas_size - 1, canvas_size - 1), radius=radius, fill=color
    )

    doc_w = canvas_size * 0.42
    doc_h = canvas_size * 0.52
    fold = doc_w * 0.3
    left = (canvas_size - doc_w) / 2
    top = (canvas_size - doc_h) / 2
    right = left + doc_w
    bottom = top + doc_h
    draw.polygon(
        [
            (left, top),
            (right - fold, top),
            (right, top + fold),
            (right, bottom),
            (left, bottom),
        ],
        fill="#FFFFFF",
    )
    draw.polygon(
        [(right - fold, top), (right, top + fold), (right - fold, top + fold)],
        fill=color,
    )
    return image.resize((size, size), Image.LANCZOS)


def get_file_type_icon(badge_text: str, size: int = 32) -> "ctk.CTkImage":
    """Return a cached file-type icon image, generating it on first use.
    Cached at module level (keyed by badge text + size, e.g. ("PDF", 32))
    rather than per-widget since the same handful of icons is reused
    across every file card and review row, at a couple of fixed sizes.
    """
    key = (badge_text, size)
    if key not in _FILE_TYPE_ICON_CACHE:
        color = FILE_TYPE_COLORS.get(badge_text, COLOR_TEXT_MUTED)
        pil_image = _draw_file_type_icon(color, size=size)
        _FILE_TYPE_ICON_CACHE[key] = ctk.CTkImage(
            light_image=pil_image, size=(size, size)
        )
    return _FILE_TYPE_ICON_CACHE[key]


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

    def __init__(
        self,
        widget: tk.Widget,
        text: str,
        delay_ms: int = 400,
        enabled: bool = True,
    ) -> None:
        self.widget = widget
        self.text = text
        self.delay_ms = delay_ms
        # Most tooltips (e.g. "Usuń z listy") label a control and should
        # always work; a few newer ones are pure how-it-works hints that
        # the "Pokazuj podpowiedzi o obsłudze" setting can turn off -
        # enabled=False makes this a permanent no-op rather than
        # conditionally binding/unbinding later.
        self.enabled = enabled
        self._after_id: str | None = None
        self._tip_window: tk.Toplevel | None = None
        if not enabled:
            return
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
        if not self.enabled:
            return
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
        self.show_usage_hints = True

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

        self.file_card_frame: ctk.CTkScrollableFrame | None = None
        self._header_row: ctk.CTkFrame | None = None
        self._heading_col: ctk.CTkFrame | None = None
        self._personal_note_label: ctk.CTkLabel | None = None
        self._header_stacked = False
        self._header_configure_after_id: str | None = None
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
        self.selected_review_output_names: set[str] = set()
        self.selection_count_label: ctk.CTkLabel | None = None
        self.bulk_approve_button: ctk.CTkButton | None = None
        self.bulk_reject_button: ctk.CTkButton | None = None

        self.active_screen = "start"
        self._nav_buttons: dict[str, ctk.CTkButton] = {}
        self._app_icon_photo: ImageTk.PhotoImage | None = None
        self._sidebar_badge_image: ctk.CTkImage | None = None
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
        # A real update() (not just update_idletasks()) so the window is
        # actually mapped/realized before the first show_start_screen()
        # measures widths - e.g. the quick-settings panel decides whether
        # to show itself based on the window's real width, which without
        # this is still an unrealized placeholder (observed ~200px)
        # regardless of WINDOW_DEFAULT_SIZE, hiding the panel forever
        # since nothing else ever re-triggers that check.
        self.root.update()
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

    def _load_app_icon(self, window: tk.Misc) -> None:
        """Set the window/titlebar/taskbar icon from the bundled asset.

        Never fatal: a missing or unreadable icon file must never stop
        the app from opening. iconphoto() needs a live PhotoImage kept
        somewhere for as long as the window exists, or Tk garbage-collects
        it and the icon silently reverts - self._app_icon_photo holds
        that reference.

        On Windows, iconphoto() alone is not enough for the *taskbar*
        icon specifically: Explorer prefers a real .ico (multi-size,
        proper ICO container) over a PNG handed to iconphoto, and without
        a distinct AppUserModelID (set once, in start_gui(), before any
        window exists) Windows can group this window under the plain
        python.exe taskbar entry and show its generic icon instead of
        ours. iconbitmap() is tried first for that reason, with
        iconphoto() as a fallback/for platforms where it is a no-op.
        """
        if APP_ICON_ICO_PATH.exists():
            try:
                window.iconbitmap(default=str(APP_ICON_ICO_PATH))
            except tk.TclError:
                pass
        if not APP_ICON_PATH.exists():
            return
        try:
            icon_image = Image.open(APP_ICON_PATH)
            self._app_icon_photo = ImageTk.PhotoImage(icon_image)
            window.iconphoto(True, self._app_icon_photo)
        except (OSError, tk.TclError):
            pass

    def _build_shell(self) -> None:
        self.root.title(APP_TITLE)
        self.root.geometry(WINDOW_DEFAULT_SIZE)
        self.root.minsize(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)
        self.root.configure(fg_color=COLOR_BG)
        self._load_app_icon(self.root)

        shell = ctk.CTkFrame(self.root, fg_color="transparent")
        shell.pack(fill="both", expand=True)

        self._build_sidebar(shell).pack(side="left", fill="y")

        self.content = ctk.CTkFrame(shell, fg_color="transparent")
        self.content.pack(side="left", fill="both", expand=True, padx=20, pady=16)

    def _build_sidebar(self, parent: ctk.CTkFrame) -> ctk.CTkFrame:
        sidebar = ctk.CTkFrame(parent, fg_color=COLOR_CARD, corner_radius=0, width=208)
        sidebar.pack_propagate(False)

        # The whole brand row (icon + name) is clickable and always goes
        # home, matching the standard "click the logo" convention - a
        # second, redundant way back to the start screen alongside the
        # "Anonimizacja" nav item below, available from any screen
        # (including modals-adjacent screens like Historia).
        brand_row = ctk.CTkFrame(sidebar, fg_color="transparent", cursor="hand2")
        brand_row.pack(fill="x", padx=18, pady=(22, 28))
        brand_clickables: list[tk.Misc] = [brand_row]
        if APP_ICON_PATH.exists():
            try:
                badge_image = Image.open(APP_ICON_PATH)
                badge = ctk.CTkImage(light_image=badge_image, size=(32, 32))
                self._sidebar_badge_image = badge
                badge_label = ctk.CTkLabel(
                    brand_row, image=badge, text="", cursor="hand2"
                )
                badge_label.pack(side="left", padx=(0, 8))
                brand_clickables.append(badge_label)
            except (OSError, tk.TclError):
                pass
        brand_text_col = ctk.CTkFrame(brand_row, fg_color="transparent", cursor="hand2")
        brand_text_col.pack(side="left")
        brand_clickables.append(brand_text_col)
        brand_title_label = ctk.CTkLabel(
            brand_text_col,
            text=APP_TITLE,
            font=ctk.CTkFont(family=FONT_FAMILY, size=16, weight="bold"),
            text_color=COLOR_TEXT,
            cursor="hand2",
        )
        brand_title_label.pack(anchor="w")
        brand_subtitle_label = ctk.CTkLabel(
            brand_text_col,
            text="Anonimizator dokumentów",
            font=ctk.CTkFont(family=FONT_FAMILY, size=10),
            text_color=COLOR_TEXT_MUTED,
            cursor="hand2",
        )
        brand_subtitle_label.pack(anchor="w")
        brand_clickables.extend([brand_title_label, brand_subtitle_label])
        for widget in brand_clickables:
            widget.bind("<Button-1>", lambda _e: self.show_start_screen())

        nav_col = ctk.CTkFrame(sidebar, fg_color="transparent")
        nav_col.pack(fill="x", padx=10)
        self._nav_buttons = {}
        nav_items = (
            ("start", "\U0001f4c4", "Anonimizacja", self.show_start_screen, None),
            (
                "history",
                "\U0001f553",
                "Historia",
                self.show_history_screen,
                "Wcześniej przetworzone foldery",
            ),
            ("settings", "⚙", "Ustawienia", self.open_settings, None),
            ("about", "\U00002139", "O programie", self.open_about, None),
        )
        for key, glyph, label, command, tooltip in nav_items:
            button = ctk.CTkButton(
                nav_col,
                text=f"{glyph}   {label}",
                anchor="w",
                height=38,
                corner_radius=8,
                fg_color="transparent",
                hover_color=COLOR_ICON_IDLE,
                text_color=COLOR_TEXT_MUTED,
                font=ctk.CTkFont(family=FONT_FAMILY, size=13),
                command=command,
            )
            button.pack(fill="x", pady=(0, 4))
            if tooltip:
                IconTooltip(button, tooltip)
            self._nav_buttons[key] = button

        # Empty expanding spacer pushes the trust badge to the bottom.
        ctk.CTkFrame(sidebar, fg_color="transparent").pack(fill="both", expand=True)

        trust_card = ctk.CTkFrame(sidebar, fg_color=COLOR_BG, corner_radius=10)
        trust_card.pack(fill="x", padx=14, pady=16)
        trust_title_row = ctk.CTkFrame(trust_card, fg_color="transparent")
        trust_title_row.pack(fill="x", padx=12, pady=(10, 2))
        ctk.CTkLabel(
            trust_title_row,
            text="\U0001f512",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            text_color=COLOR_OK,
        ).pack(side="left", padx=(0, 4))
        ctk.CTkLabel(
            trust_title_row,
            text="Przetwarzanie lokalne",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
            text_color=COLOR_TEXT,
            anchor="w",
        ).pack(side="left")
        ctk.CTkLabel(
            trust_card,
            text="Pliki nie opuszczają\ntwojego komputera.",
            font=ctk.CTkFont(family=FONT_FAMILY, size=10),
            text_color=COLOR_TEXT_MUTED,
            justify="left",
            anchor="w",
        ).pack(fill="x", padx=12, pady=(0, 10))

        ctk.CTkLabel(
            sidebar,
            text=f"v{APP_VERSION}",
            font=ctk.CTkFont(family=FONT_FAMILY, size=9),
            text_color=COLOR_TEXT_MUTED,
        ).pack(anchor="w", padx=18, pady=(0, 10))

        self._update_sidebar_active_state()
        return sidebar

    def _update_sidebar_active_state(self) -> None:
        """Highlight whichever sidebar item the current screen belongs to.

        Processing and review are steps of the same anonymization flow
        "Anonimizacja" was clicked to start, not destinations of their
        own, so both map back to that same nav item. "Ustawienia" opens
        a modal rather than swapping self.content, so it has no
        persistent active state to show - it stays a plain action button.
        """
        if not self._nav_buttons:
            return
        active_key = "history" if self.active_screen == "history" else "start"
        for key, button in self._nav_buttons.items():
            if key in ("settings", "about"):
                continue
            is_active = key == active_key
            button.configure(
                fg_color=COLOR_ACCENT_SOFT if is_active else "transparent",
                text_color=COLOR_ACCENT if is_active else COLOR_TEXT_MUTED,
            )

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

    def _build_header_row(self, parent: ctk.CTkFrame) -> None:
        """Build the tagline/subtitle plus handwritten-style personal note.

        Side-by-side at normal widths; below HEADER_STACK_BREAKPOINT the
        note drops onto its own line at a smaller size instead of being
        clipped - see _apply_header_layout, which reconfigures these same
        widgets in place (no rebuild) whenever the window crosses that
        breakpoint.
        """
        header_row = ctk.CTkFrame(parent, fg_color="transparent")
        header_row.pack(fill="x", pady=(0, 16))
        self._header_row = header_row

        heading_col = ctk.CTkFrame(header_row, fg_color="transparent")
        self._heading_col = heading_col
        ctk.CTkLabel(
            heading_col,
            text=APP_TAGLINE,
            font=ctk.CTkFont(family=FONT_FAMILY, size=22, weight="bold"),
            text_color=COLOR_TEXT,
        ).pack(anchor="w")
        ctk.CTkLabel(
            heading_col,
            text=APP_SUBTITLE,
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            text_color=COLOR_TEXT_MUTED,
        ).pack(anchor="w", pady=(2, 0))

        # A small, deliberately personal touch - see APP_PERSONAL_NOTE's
        # own docstring-style comment at its definition for why.
        self._personal_note_label = ctk.CTkLabel(
            header_row,
            text=APP_PERSONAL_NOTE,
            font=ctk.CTkFont(family=SCRIPT_FONT_FAMILY, size=18),
            text_color=COLOR_ACCENT,
        )
        self._header_stacked = False
        self._apply_header_layout(force=True)

        # Bound on this specific header_row instance, rebuilt fresh every
        # time show_start_screen runs, so there is never more than one
        # live binding to worry about.
        header_row.bind("<Configure>", self._on_header_row_configure)

    def _on_header_row_configure(self, _event: object = None) -> None:
        # Debounced: a live resize drag fires many Configure events per
        # second, and re-measuring/reflowing on every single one is the
        # same expensive-cascade trap found earlier with a different
        # spacer (see PROJECT_STATE.md) - only the settled width matters.
        if self._header_configure_after_id is not None:
            self.root.after_cancel(self._header_configure_after_id)
        self._header_configure_after_id = self.root.after(
            150, self._apply_header_layout
        )

    def _apply_header_layout(self, force: bool = False) -> None:
        self._header_configure_after_id = None
        if (
            self._header_row is None
            or not self._header_row.winfo_exists()
            or self._heading_col is None
            or self._personal_note_label is None
        ):
            return
        width = self._header_row.winfo_width()
        stacked = width > 1 and width < HEADER_STACK_BREAKPOINT
        if stacked == self._header_stacked and not force:
            return
        self._header_stacked = stacked
        self._heading_col.pack_forget()
        self._personal_note_label.pack_forget()
        if stacked:
            self._heading_col.pack(anchor="w", fill="x")
            self._personal_note_label.configure(
                font=ctk.CTkFont(family=SCRIPT_FONT_FAMILY, size=14)
            )
            self._personal_note_label.pack(anchor="w", pady=(6, 0))
        else:
            self._heading_col.pack(side="left")
            self._personal_note_label.configure(
                font=ctk.CTkFont(family=SCRIPT_FONT_FAMILY, size=18)
            )
            self._personal_note_label.pack(side="right", anchor="n", padx=(10, 4))

    def _build_resume_review_banner(self, parent: ctk.CTkFrame) -> None:
        """Offer a way back to an in-progress review from the start screen.

        Navigating "Anonimizacja"/the logo away from the review screen
        does not clear self.review_items - the batch just finished is
        still there - but before this there was no way back to it short
        of reprocessing the same files, reported directly by the user
        after doing exactly that by accident.
        """
        if not self.review_items:
            return
        banner = ctk.CTkFrame(
            parent,
            corner_radius=10,
            fg_color=COLOR_ACCENT_SOFT,
            border_width=1,
            border_color=COLOR_ACCENT,
        )
        banner.pack(fill="x", pady=(0, 14))
        row = ctk.CTkFrame(banner, fg_color="transparent")
        row.pack(fill="x", padx=14, pady=10)
        ctk.CTkLabel(
            row,
            text=(
                f"Masz otwarty przegląd wyników ({len(self.review_items)} "
                "plików)."
            ),
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            text_color=COLOR_TEXT,
        ).pack(side="left")
        ctk.CTkButton(
            row,
            text="Wróć do przeglądu",
            height=28,
            corner_radius=8,
            fg_color=COLOR_ACCENT,
            hover_color=COLOR_ACCENT_HOVER,
            font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
            command=self.show_review_screen,
        ).pack(side="right")

    def _build_quick_settings_panel(self, parent: ctk.CTkFrame) -> ctk.CTkFrame:
        """A start-screen shortcut to the most-used detection settings,
        mirroring the mockup's "Domyślne ustawienia" card. Deliberately
        only wraps settings that are real, already-wired toggles
        (self.use_ner, self.use_llm_review) - OCR has no such toggle in
        this app (it runs automatically when available, there is nothing
        to switch off), so that row stays a read-only status like it
        already is in the full Settings dialog, rather than adding a
        checkbox that would not actually control anything.
        """
        panel = ctk.CTkFrame(
            parent,
            corner_radius=12,
            fg_color=COLOR_CARD,
            border_width=1,
            border_color=COLOR_BORDER,
            width=QUICK_SETTINGS_PANEL_WIDTH,
        )
        panel.pack_propagate(False)
        inner = ctk.CTkFrame(panel, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=14, pady=14)

        header_row = ctk.CTkFrame(inner, fg_color="transparent", cursor="hand2")
        header_row.pack(fill="x", pady=(0, 10))
        header_row.bind("<Button-1>", lambda _e: self.open_settings())
        ctk.CTkLabel(
            header_row,
            text="⚙",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13),
            text_color=COLOR_ACCENT,
            cursor="hand2",
        ).pack(side="left", padx=(0, 6))
        ctk.CTkLabel(
            header_row,
            text="Domyślne ustawienia",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
            text_color=COLOR_TEXT,
            cursor="hand2",
        ).pack(side="left")

        env_status = environment_status_lookup(self.environment_items)

        ctk.CTkLabel(
            inner,
            text="Wykrywanie podstawowe",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
            text_color=COLOR_TEXT,
            anchor="w",
        ).pack(fill="x", pady=(0, 0))
        ctk.CTkLabel(
            inner,
            text="PESEL, NIP, REGON, telefon, e-mail, daty (zawsze aktywne)",
            font=ctk.CTkFont(family=FONT_FAMILY, size=10),
            text_color=COLOR_TEXT_MUTED,
            anchor="w",
            wraplength=QUICK_SETTINGS_PANEL_WIDTH - 40,
            justify="left",
        ).pack(fill="x", pady=(0, 10))

        ner_var = tk.BooleanVar(value=self.use_ner)

        def _on_ner_toggle() -> None:
            self.use_ner = ner_var.get()

        ctk.CTkCheckBox(
            inner,
            text="Rozszerzone wykrywanie (AI)",
            variable=ner_var,
            command=_on_ner_toggle,
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            text_color=COLOR_TEXT,
            fg_color=COLOR_ACCENT,
            hover_color=COLOR_ACCENT_HOVER,
        ).pack(anchor="w", pady=(0, 2))
        ctk.CTkLabel(
            inner,
            text="Imiona, nazwiska, nazwy firm i miejscowości",
            font=ctk.CTkFont(family=FONT_FAMILY, size=10),
            text_color=COLOR_TEXT_MUTED,
            anchor="w",
            wraplength=QUICK_SETTINGS_PANEL_WIDTH - 40,
            justify="left",
        ).pack(fill="x", padx=(24, 0), pady=(0, 10))

        llm_var = tk.BooleanVar(value=self.use_llm_review)

        def _on_llm_toggle() -> None:
            self.use_llm_review = llm_var.get()

        ctk.CTkCheckBox(
            inner,
            text="Dodatkowa kontrola wyniku (AI)",
            variable=llm_var,
            command=_on_llm_toggle,
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            text_color=COLOR_TEXT,
            fg_color=COLOR_ACCENT,
            hover_color=COLOR_ACCENT_HOVER,
        ).pack(anchor="w", pady=(0, 2))
        ctk.CTkLabel(
            inner,
            text="Sprawdzenie, czy nic nie zostało pominięte (Ollama)",
            font=ctk.CTkFont(family=FONT_FAMILY, size=10),
            text_color=COLOR_TEXT_MUTED,
            anchor="w",
            wraplength=QUICK_SETTINGS_PANEL_WIDTH - 40,
            justify="left",
        ).pack(fill="x", padx=(24, 0), pady=(0, 10))

        ocr_row = ctk.CTkFrame(inner, fg_color="transparent")
        ocr_row.pack(fill="x", pady=(0, 10))
        ocr_ok = env_status.get(ENV_ITEM_OCR)
        # ocr_ok is None while the background environment check hasn't
        # completed yet (runs ~150ms after startup) - that must not read
        # as "confirmed unavailable" (an empty dot + a neutral "checking"
        # line instead), the same "absent while unknown" rule
        # _build_status_dot already follows for this exact data in the
        # full Settings dialog. This row rebuilds with the real status
        # once the check finishes, via _on_environment_check_done.
        ctk.CTkLabel(
            ocr_row,
            text="●" if ocr_ok is not None else "",
            font=ctk.CTkFont(family=FONT_FAMILY, size=10),
            text_color=COLOR_OK if ocr_ok else COLOR_ICON_IDLE,
            width=14,
        ).pack(side="left", anchor="n", pady=(3, 0))
        ocr_col = ctk.CTkFrame(ocr_row, fg_color="transparent")
        ocr_col.pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(
            ocr_col,
            text="OCR dla skanów i zdjęć",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            text_color=COLOR_TEXT,
            anchor="w",
        ).pack(fill="x")
        if ocr_ok is None:
            ocr_status_text = "Sprawdzanie dostępności..."
        elif ocr_ok:
            ocr_status_text = "Automatyczne, gdy dostępne"
        else:
            ocr_status_text = "Niedostępne - patrz Ustawienia"
        ctk.CTkLabel(
            ocr_col,
            text=ocr_status_text,
            font=ctk.CTkFont(family=FONT_FAMILY, size=10),
            text_color=COLOR_TEXT_MUTED,
            anchor="w",
        ).pack(fill="x")

        dict_row = ctk.CTkFrame(inner, fg_color="transparent")
        dict_row.pack(fill="x", pady=(0, 10))
        dict_col = ctk.CTkFrame(dict_row, fg_color="transparent")
        dict_col.pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(
            dict_col,
            text="Własny słownik",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            text_color=COLOR_TEXT,
            anchor="w",
        ).pack(fill="x")
        ctk.CTkLabel(
            dict_col,
            text=(
                self.sensitive_terms_path.name
                if self.sensitive_terms_path is not None
                else "Nie wybrano"
            ),
            font=ctk.CTkFont(family=FONT_FAMILY, size=10),
            text_color=COLOR_TEXT_MUTED,
            anchor="w",
        ).pack(fill="x")
        ctk.CTkButton(
            dict_row,
            text="Zmień",
            width=54,
            height=24,
            corner_radius=6,
            fg_color="transparent",
            border_width=1,
            border_color=COLOR_BORDER,
            hover_color=COLOR_ICON_IDLE,
            text_color=COLOR_TEXT,
            font=ctk.CTkFont(family=FONT_FAMILY, size=10),
            command=lambda: self.open_settings(initial_tab="Słownik"),
        ).pack(side="right")

        ctk.CTkButton(
            inner,
            text="Więcej ustawień →",
            fg_color="transparent",
            hover_color=COLOR_ICON_IDLE,
            text_color=COLOR_ACCENT,
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            anchor="w",
            command=self.open_settings,
        ).pack(fill="x", pady=(4, 0))

        return panel

    def show_start_screen(self) -> None:
        self.active_screen = "start"
        self._update_sidebar_active_state()
        self._clear_content()

        # Two regions: a pinned bottom bar (output folder + the
        # "Anonimizuj" button - the controls that must stay reachable no
        # matter what) packed *first* with side="bottom" so it always
        # gets its space claimed, and a scrollable upper region for
        # everything else, taking whatever is left. Without this, a
        # short window (or - before FILE_LIST_MAX_HEIGHT - simply enough
        # selected files) could push the button below the window with no
        # way to reach it at all, since self.content itself never
        # scrolled. The file list additionally gets its own small bounded
        # scroll area inside this outer one, so a long file list doesn't
        # by itself push the drop zone and header far out of view.
        # A second, narrower column on the right holds the quick-settings
        # panel (see _build_quick_settings_panel) - packed *before* the
        # main column, and only above QUICK_SETTINGS_MIN_WIDTH, so it
        # claims its fixed width first and never squeezes the main flow
        # down to something unusable on a narrower window.
        columns_row = ctk.CTkFrame(self.content, fg_color="transparent")
        columns_row.pack(fill="both", expand=True)
        # update_idletasks forces Tk to actually compute current geometry
        # first - without it, winfo_width() can still report a stale/
        # unrealized placeholder size (e.g. right at app startup, before
        # the first real layout pass), which would wrongly hide this
        # panel on a plenty-wide window and never show it again since
        # nothing else re-triggers a rebuild.
        self.root.update_idletasks()
        show_quick_settings = self.root.winfo_width() >= QUICK_SETTINGS_MIN_WIDTH
        if show_quick_settings:
            self._build_quick_settings_panel(columns_row).pack(
                side="right", fill="y", padx=(12, 0)
            )
        main_col = ctk.CTkFrame(columns_row, fg_color="transparent")
        main_col.pack(side="left", fill="both", expand=True)

        bottom_bar = ctk.CTkFrame(main_col, fg_color="transparent")
        bottom_bar.pack(side="bottom", fill="x")
        scroll_region = ctk.CTkScrollableFrame(main_col, fg_color="transparent")
        scroll_region.pack(side="top", fill="both", expand=True)

        self._build_header_row(scroll_region)
        self._build_resume_review_banner(scroll_region)

        self._build_status_banner(scroll_region)

        drop_frame = ctk.CTkFrame(
            scroll_region,
            corner_radius=16,
            fg_color=COLOR_ACCENT_SOFT,
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
        self.drop_hint_label.pack(pady=28)
        drop_frame.bind("<Button-1>", lambda _e: self.pick_files())
        self.drop_hint_label.bind("<Button-1>", lambda _e: self.pick_files())

        drop_frame.drop_target_register(DND_FILES)
        drop_frame.dnd_bind("<<Drop>>", self._on_files_dropped)

        privacy_row = ctk.CTkLabel(
            scroll_region,
            text="\U0001f512  Przetwarzane lokalnie, dane nie opuszczają Twojego komputera",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            text_color=COLOR_TEXT_MUTED,
        )
        privacy_row.pack(pady=(10, 14))

        self.file_card_frame = ctk.CTkScrollableFrame(
            scroll_region,
            fg_color="transparent",
            height=FILE_LIST_MAX_HEIGHT,
        )
        self.file_card_frame.pack(fill="x", pady=(0, 14))
        self._refresh_file_cards()

        ctk.CTkLabel(
            bottom_bar,
            text="Folder wynikowy",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
            text_color=COLOR_TEXT,
            anchor="w",
        ).pack(fill="x", pady=(6, 4))
        output_row = ctk.CTkFrame(bottom_bar, fg_color="transparent")
        output_row.pack(fill="x", pady=(0, 6))
        path_field = ctk.CTkFrame(
            output_row,
            corner_radius=8,
            fg_color=COLOR_CARD,
            border_width=1,
            border_color=COLOR_BORDER,
        )
        path_field.pack(side="left", fill="x", expand=True, padx=(0, 8))
        path_field_inner = ctk.CTkFrame(path_field, fg_color="transparent")
        path_field_inner.pack(fill="x", padx=10, pady=7)
        ctk.CTkLabel(
            path_field_inner,
            text="\U0001f4c1",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13),
        ).pack(side="left", padx=(0, 8))
        self.output_dir_value_label = ctk.CTkLabel(
            path_field_inner,
            text=self._output_dir_display_text(),
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            text_color=COLOR_TEXT,
            anchor="w",
        )
        self.output_dir_value_label.pack(side="left", fill="x", expand=True)
        ctk.CTkButton(
            output_row,
            text="Zmień",
            width=90,
            height=36,
            corner_radius=8,
            fg_color="transparent",
            border_width=1,
            border_color=COLOR_BORDER,
            hover_color=COLOR_ICON_IDLE,
            text_color=COLOR_TEXT,
            command=self.pick_output_dir,
        ).pack(side="right")

        self.status_label = ctk.CTkLabel(
            bottom_bar,
            text=format_readiness_pl(
                len(self.selected_paths), self.output_dir is not None
            ),
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            text_color=COLOR_TEXT_MUTED,
        )
        self.status_label.pack(pady=(4, 10))

        self.anonymize_button = ctk.CTkButton(
            bottom_bar,
            text="Anonimizuj",
            height=48,
            corner_radius=10,
            fg_color=COLOR_ACCENT,
            hover_color=COLOR_ACCENT_HOVER,
            font=ctk.CTkFont(family=FONT_FAMILY, size=16, weight="bold"),
            state="disabled",
            command=self.start_anonymize,
        )
        self.anonymize_button.pack(fill="x", pady=(0, 4))
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
        badge = ctk.CTkLabel(card, image=get_file_type_icon(badge_text), text="")
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

        self._refresh_file_cards()
        self._update_readiness(
            status_override=format_drop_result(added, len(unsupported))
        )

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

    def _update_readiness(self, status_override: str | None = None) -> None:
        """Refresh the status line and the "Anonimizuj" button.

        status_override lets a caller show a one-off message (e.g. what a
        drop/pick just did) in the same status_label this always updates,
        without duplicating the button-ready/text logic below just to
        avoid this method's own unconditional readiness text - passing it
        replaces only that one line, once, for this call.
        """
        if self.status_label is not None:
            self.status_label.configure(
                text=status_override
                or format_readiness_pl(
                    len(self.selected_paths), self.output_dir is not None
                )
            )
        if self.anonymize_button is not None:
            ready = bool(self.selected_paths) and self.output_dir is not None
            self.anonymize_button.configure(
                text=format_anonymize_button_text(len(self.selected_paths))
            )
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
        self._update_sidebar_active_state()
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

    def open_settings(self, initial_tab: str | None = None) -> None:
        SettingsDialog(self, initial_tab=initial_tab)

    def open_about(self) -> None:
        AboutDialog(self)

    # ------------------------------------------------------------------
    # Processing screen
    # ------------------------------------------------------------------

    def show_processing_screen(self) -> None:
        self.active_screen = "processing"
        self._update_sidebar_active_state()
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
        self.selected_review_output_names = set()
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
        self._update_sidebar_active_state()
        self._clear_content()

        title_row = ctk.CTkFrame(self.content, fg_color="transparent")
        title_row.pack(fill="x", pady=(0, 4))
        title_col = ctk.CTkFrame(title_row, fg_color="transparent")
        title_col.pack(side="left")
        ctk.CTkLabel(
            title_col,
            text="Wyniki anonimizacji",
            font=ctk.CTkFont(family=FONT_FAMILY, size=20, weight="bold"),
            text_color=COLOR_TEXT,
        ).pack(anchor="w")
        ctk.CTkLabel(
            title_col,
            text=format_review_heading_subtitle(len(self.review_items)),
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            text_color=COLOR_TEXT_MUTED,
        ).pack(anchor="w")

        header = ctk.CTkFrame(self.content, fg_color="transparent")
        header.pack(fill="x", pady=(6, 10))
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
        self._build_review_stat_cards(self.content)
        self._build_selection_bar(self.content)

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

    def _build_review_stat_cards(self, parent: ctk.CTkFrame) -> None:
        """Four at-a-glance counts, always the same four regardless of
        folder: the three manual-review statuses plus the total. Batch
        processing failures (files that never even produced a result)
        are a different concept, already covered by the more useful
        named-files-and-reasons banner from _build_batch_errors_card, so
        they are not duplicated here as a bare count.
        """
        counts = {
            REVIEW_STATUS_APPROVED: 0,
            REVIEW_STATUS_NEEDS_REVIEW: 0,
            REVIEW_STATUS_REJECTED: 0,
        }
        for item in self.review_items:
            counts[item.status] = counts.get(item.status, 0) + 1

        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", pady=(0, 10))
        stats = (
            ("Zatwierdzone", counts[REVIEW_STATUS_APPROVED], COLOR_OK, COLOR_OK_SOFT, "✓"),
            (
                "Wymaga przeglądu",
                counts[REVIEW_STATUS_NEEDS_REVIEW],
                COLOR_NEEDS_REVIEW,
                COLOR_NEEDS_REVIEW_SOFT,
                "!",
            ),
            (
                "Odrzucone",
                counts[REVIEW_STATUS_REJECTED],
                COLOR_HIGH_RISK,
                COLOR_HIGH_RISK_SOFT,
                "✕",
            ),
            (
                "Wszystkie pliki",
                len(self.review_items),
                COLOR_TEXT,
                COLOR_ICON_IDLE,
                "\U0001f4c4",
            ),
        )
        for index, (label, count, color, soft, glyph) in enumerate(stats):
            card = ctk.CTkFrame(
                row,
                fg_color=COLOR_CARD,
                corner_radius=10,
                border_width=1,
                border_color=COLOR_BORDER,
            )
            card.pack(
                side="left",
                fill="x",
                expand=True,
                padx=(0, 8) if index < len(stats) - 1 else 0,
            )
            inner = ctk.CTkFrame(card, fg_color="transparent")
            inner.pack(fill="x", padx=14, pady=12)
            ctk.CTkLabel(
                inner,
                text=glyph,
                width=32,
                height=32,
                corner_radius=16,
                fg_color=soft,
                text_color=color,
                font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
            ).pack(side="left", padx=(0, 10))
            text_col = ctk.CTkFrame(inner, fg_color="transparent")
            text_col.pack(side="left")
            ctk.CTkLabel(
                text_col,
                text=str(count),
                font=ctk.CTkFont(family=FONT_FAMILY, size=20, weight="bold"),
                text_color=COLOR_TEXT,
                anchor="w",
            ).pack(anchor="w")
            ctk.CTkLabel(
                text_col,
                text=label,
                font=ctk.CTkFont(family=FONT_FAMILY, size=11),
                text_color=COLOR_TEXT_MUTED,
                anchor="w",
            ).pack(anchor="w")

    def _build_selection_bar(self, parent: ctk.CTkFrame) -> None:
        bar = ctk.CTkFrame(parent, fg_color="transparent")
        bar.pack(fill="x", pady=(0, 6))
        self.selection_count_label = ctk.CTkLabel(
            bar,
            text=self._selection_summary_text(),
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            text_color=COLOR_TEXT_MUTED,
        )
        self.selection_count_label.pack(side="left")
        self.bulk_reject_button = ctk.CTkButton(
            bar,
            text="Odrzuć zaznaczone",
            width=150,
            height=28,
            corner_radius=8,
            fg_color="transparent",
            hover_color=COLOR_HIGH_RISK_SOFT,
            text_color=COLOR_HIGH_RISK,
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            state="disabled",
            command=lambda: self._bulk_set_status(REVIEW_STATUS_REJECTED),
        )
        self.bulk_reject_button.pack(side="right", padx=(6, 0))
        self.bulk_approve_button = ctk.CTkButton(
            bar,
            text="Zatwierdź zaznaczone",
            width=160,
            height=28,
            corner_radius=8,
            fg_color="transparent",
            hover_color=COLOR_OK_SOFT,
            text_color=COLOR_OK,
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            state="disabled",
            command=lambda: self._bulk_set_status(REVIEW_STATUS_APPROVED),
        )
        self.bulk_approve_button.pack(side="right")

    def _selection_summary_text(self) -> str:
        return f"{len(self.selected_review_output_names)} zaznaczonych"

    def _toggle_review_selection(self, item: ReviewItem, checked: bool) -> None:
        if checked:
            self.selected_review_output_names.add(item.output_name)
        else:
            self.selected_review_output_names.discard(item.output_name)
        self._update_bulk_action_state()

    def _update_bulk_action_state(self) -> None:
        if self.selection_count_label is not None:
            self.selection_count_label.configure(text=self._selection_summary_text())
        has_selection = bool(self.selected_review_output_names)
        for button in (self.bulk_approve_button, self.bulk_reject_button):
            if button is not None:
                button.configure(state="normal" if has_selection else "disabled")

    def _bulk_set_status(self, status: str) -> None:
        targets = [
            item
            for item in self.review_items
            if item.output_name in self.selected_review_output_names
        ]
        for item in targets:
            self.set_review_status(item, status)
        # Clear the selection once acted on, rather than leaving the same
        # files pre-selected for a second, likely-accidental bulk action.
        self.selected_review_output_names = set()
        self._refresh_review_cards()
        self._update_bulk_action_state()

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

        self._build_review_table_header(self.review_cards_frame)
        for item in self.review_items:
            self._build_review_table_row(item)

    def _build_review_table_header(self, parent: ctk.CTkFrame) -> None:
        header = ctk.CTkFrame(parent, fg_color="transparent")
        header.pack(fill="x", padx=6, pady=(0, 4))
        header.grid_columnconfigure(1, weight=1, minsize=220)
        ctk.CTkLabel(header, text="", width=24).grid(row=0, column=0)
        for column, text, width in (
            (1, "Nazwa pliku", None),
            (2, "Status", 130),
            (3, "Ryzyko", 60),
            (4, "Akcje", 160),
        ):
            ctk.CTkLabel(
                header,
                text=text,
                width=width or 0,
                font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
                text_color=COLOR_TEXT_MUTED,
                anchor="w",
            ).grid(row=0, column=column, sticky="w", padx=6)

    def _build_review_table_row(self, item: ReviewItem) -> None:
        assert self.review_cards_frame is not None
        row = ctk.CTkFrame(
            self.review_cards_frame,
            corner_radius=8,
            fg_color=COLOR_CARD,
            border_width=1,
            border_color=COLOR_BORDER,
        )
        row.pack(fill="x", pady=3, padx=4)

        inner = ctk.CTkFrame(row, fg_color="transparent")
        inner.pack(fill="x", padx=10, pady=8)
        inner.grid_columnconfigure(1, weight=1, minsize=220)

        checkbox_var = tk.BooleanVar(
            value=item.output_name in self.selected_review_output_names
        )
        ctk.CTkCheckBox(
            inner,
            text="",
            variable=checkbox_var,
            width=20,
            checkbox_width=18,
            checkbox_height=18,
            fg_color=COLOR_ACCENT,
            hover_color=COLOR_ACCENT_HOVER,
            command=lambda: self._toggle_review_selection(item, checkbox_var.get()),
        ).grid(row=0, column=0, padx=(0, 6))

        name_col = ctk.CTkFrame(inner, fg_color="transparent")
        name_col.grid(row=0, column=1, sticky="ew", padx=6)
        badge_text = file_type_badge(Path(item.output_name))
        ctk.CTkLabel(
            name_col, image=get_file_type_icon(badge_text, size=24), text=""
        ).pack(side="left", padx=(0, 8))
        name_label = ctk.CTkLabel(
            name_col,
            text=truncate_filename_middle(item.output_name),
            font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
            text_color=COLOR_TEXT,
            anchor="w",
            width=190,
        )
        name_label.pack(side="left", fill="x", expand=True)
        if len(item.output_name) > 26:
            IconTooltip(name_label, item.output_name)

        status_styles = {
            REVIEW_STATUS_APPROVED: (COLOR_OK, COLOR_OK_SOFT),
            REVIEW_STATUS_REJECTED: (COLOR_HIGH_RISK, COLOR_HIGH_RISK_SOFT),
            REVIEW_STATUS_NEEDS_REVIEW: (COLOR_NEEDS_REVIEW, COLOR_NEEDS_REVIEW_SOFT),
        }
        status_color, status_soft = status_styles.get(
            item.status, (COLOR_TEXT_MUTED, COLOR_ICON_IDLE)
        )
        ctk.CTkLabel(
            inner,
            text=review_status_label_pl(item.status),
            width=130,
            corner_radius=6,
            fg_color=status_soft,
            text_color=status_color,
            font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
        ).grid(row=0, column=2, padx=6)

        risk_key = risk_style_key(item.risk_level)
        risk_color, risk_soft, risk_glyph = RISK_STYLES[risk_key]
        ctk.CTkLabel(
            inner,
            text=risk_glyph,
            width=24,
            height=24,
            corner_radius=12,
            fg_color=risk_soft,
            text_color=risk_color,
            font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
        ).grid(row=0, column=3, padx=6)

        actions = ctk.CTkFrame(inner, fg_color="transparent")
        actions.grid(row=0, column=4, padx=(6, 0))

        self._build_status_icon_button(
            actions, "👁", "Porównaj oryginał i wynik", COLOR_TEXT_MUTED, False,
            lambda: self.open_comparison(item),
        )
        self._build_status_icon_button(
            actions, "✓", "Zatwierdź", COLOR_OK,
            item.status == REVIEW_STATUS_APPROVED,
            lambda: self.set_review_status(item, REVIEW_STATUS_APPROVED),
        )
        self._build_status_icon_button(
            actions, "!", "Wymaga przeglądu", COLOR_NEEDS_REVIEW,
            item.status == REVIEW_STATUS_NEEDS_REVIEW,
            lambda: self.set_review_status(item, REVIEW_STATUS_NEEDS_REVIEW),
        )
        self._build_status_icon_button(
            actions, "✕", "Odrzuć", COLOR_HIGH_RISK,
            item.status == REVIEW_STATUS_REJECTED,
            lambda: self.set_review_status(item, REVIEW_STATUS_REJECTED),
        )
        self._build_status_icon_button(
            actions, "ℹ", "Szczegóły", COLOR_ACCENT, False,
            lambda: self.open_summary(item),
        )

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
            width=28,
            height=28,
            corner_radius=14,
            fg_color=active_color if active else COLOR_ICON_IDLE,
            hover_color=active_color,
            text_color="#FFFFFF" if active else COLOR_TEXT_MUTED,
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            command=command,
        )
        button.pack(side="left", padx=2)
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

    def __init__(self, app: AnonymizerApp, initial_tab: str | None = None) -> None:
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
        self.show_hints_var = tk.BooleanVar(value=app.show_usage_hints)
        self.sensitive_terms_path = app.sensitive_terms_path
        self.environment_status = environment_status_lookup(app.environment_items)

        self._build(initial_tab)

    def _build(self, initial_tab: str | None = None) -> None:
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

        tabview = ctk.CTkTabview(
            self.window,
            fg_color=COLOR_BG,
            segmented_button_fg_color=COLOR_CARD,
            segmented_button_selected_color=COLOR_ACCENT,
            segmented_button_selected_hover_color=COLOR_ACCENT_HOVER,
            segmented_button_unselected_color=COLOR_CARD,
            segmented_button_unselected_hover_color=COLOR_ICON_IDLE,
            text_color=COLOR_TEXT,
        )
        tabview.pack(fill="both", expand=True, padx=20, pady=(0, 6))

        self._build_detection_tab(tabview.add("Wykrywanie danych"))
        self._build_pdf_tab(tabview.add("Dokumenty PDF"))
        self._build_dictionary_tab(tabview.add("Słownik"))
        self._build_general_tab(tabview.add("Ogólne"))
        if initial_tab is not None:
            try:
                tabview.set(initial_tab)
            except ValueError:
                pass

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

    def _build_detection_tab(self, tab: ctk.CTkFrame) -> None:
        self._build_static_info_row(
            tab,
            "Podstawowe wykrywanie",
            "Zawsze aktywne - PESEL, NIP, REGON, numery kont, telefony, "
            "e-maile, daty, podstawowe wzorce",
        )
        self._build_toggle_section(
            tab,
            "Rozpoznawanie AI (NER)",
            "Wykrywa imiona, firmy i miejsca",
            self.ner_var,
            status_ok=self.environment_status.get(ENV_ITEM_NER),
        )
        self._build_toggle_section(
            tab,
            "Dodatkowa weryfikacja AI (LLM)",
            "Opcjonalne, wymaga lokalnego Ollama",
            self.llm_var,
            status_ok=self.environment_status.get(ENV_ITEM_LLM),
        )
        self._build_status_row(
            tab,
            "OCR (skany, obrazy)",
            "Automatyczne, wymaga lokalnego Tesseracta",
            status_ok=self.environment_status.get(ENV_ITEM_OCR),
        )

    def _build_pdf_tab(self, tab: ctk.CTkFrame) -> None:
        pdf_section = self._section_frame(tab)
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

    def _build_dictionary_tab(self, tab: ctk.CTkFrame) -> None:
        dict_section = self._section_frame(tab)
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

    def _build_general_tab(self, tab: ctk.CTkFrame) -> None:
        self._build_toggle_section(
            tab,
            "Otwórz automatycznie po zatwierdzeniu",
            "Otwiera plik dopiero gdy klikniesz ✓ Zatwierdzony, nie od razu po anonimizacji",
            self.auto_open_var,
        )
        self._build_toggle_section(
            tab,
            "Pokazuj podpowiedzi o obsłudze",
            "Dymki tłumaczące np. narzędzia łapki/lupy w podglądzie porównania",
            self.show_hints_var,
        )

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

    def _build_static_info_row(
        self, parent: ctk.CTkFrame, title: str, subtitle: str
    ) -> None:
        """Same visual family as the toggle/status rows, for a layer that
        is neither optional nor a dependency to check - just always on
        and worth being upfront about (the regex/dictionary baseline)."""
        frame = self._section_frame(parent)
        row = ctk.CTkFrame(frame, fg_color="transparent")
        row.pack(fill="x", padx=14, pady=12)
        text_col = ctk.CTkFrame(row, fg_color="transparent")
        text_col.pack(side="left", fill="x", expand=True)
        title_row = ctk.CTkFrame(text_col, fg_color="transparent")
        title_row.pack(fill="x")
        ctk.CTkLabel(
            title_row,
            text="●",
            font=ctk.CTkFont(family=FONT_FAMILY, size=10),
            text_color=COLOR_OK,
            width=12,
        ).pack(side="left", padx=(0, 6))
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
            wraplength=420,
            justify="left",
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
        self.app.show_usage_hints = self.show_hints_var.get()
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


def scroll_sync_units(event: object) -> int:
    """Return the exact canvas ``yview scroll`` unit count CustomTkinter's
    own CTkScrollableFrame uses internally for one wheel event.

    Deliberately mirrors that library's private ``_mouse_wheel_all``
    formula (not the more forgiving ``mousewheel_scroll_units`` used
    elsewhere) so a linked pane scrolls in exact lockstep with the pane
    the cursor is actually over, instead of gradually drifting out of
    sync from using a different step size.
    """
    event_num = getattr(event, "num", None)
    if event_num == 4:
        return -1
    if event_num == 5:
        return 1
    delta = int(getattr(event, "delta", 0) or 0)
    if sys.platform == "darwin":
        return -delta
    return -int(delta / 6)


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
        # Manual-mode tool pinning: None means the modeless default (LMB
        # draws, RMB always erases). Pinning to "draw" or "erase" locks
        # LMB to that one action - RMB keeps working as erase regardless,
        # so pinning never takes away the existing shortcut, only adds a
        # single-button way to work for anyone who'd rather pick a tool
        # explicitly. _transient_tool tracks a chip lighting up because
        # its action is actually happening right now (independent of
        # pinning), cleared the moment that press/click ends.
        self.pinned_tool: str | None = None
        self._transient_tool: str | None = None
        self._tool_chips: dict[str, tuple[ctk.CTkFrame, ctk.CTkLabel, ctk.CTkLabel]] = {}
        self.left_frame: ctk.CTkScrollableFrame | None = None
        self.right_frame: ctk.CTkScrollableFrame | None = None
        self.original_zoom = ZOOM_DEFAULT
        self.result_zoom = ZOOM_DEFAULT
        self.zoom_linked = True
        self.original_zoom_label: ctk.CTkEntry | None = None
        self.result_zoom_label: ctk.CTkEntry | None = None
        self._link_buttons: list[ctk.CTkButton] = []
        self._link_tooltips: list[IconTooltip] = []
        # "Łapka" (hand/pan) and "lupa" (zoom-on-scroll) are one shared
        # tool state for the whole window, not per-pane - toggle buttons
        # exist in both pane headers for convenience, kept in sync via
        # these lists, matching the existing zoom-link button pattern.
        self.active_pointer_tool: str | None = None
        self._hand_buttons: list[ctk.CTkButton] = []
        self._zoom_tool_buttons: list[ctk.CTkButton] = []

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
        # Plain (no Ctrl) scroll: while panes are locked together, mirror
        # it onto the other pane too, so scrolling either one moves both -
        # each CTkScrollableFrame already scrolls itself via its own
        # internal bind_all, this only adds the *other* pane's half.
        window.bind("<MouseWheel>", self._on_scroll_sync)
        window.bind("<Button-4>", self._on_scroll_sync)
        window.bind("<Button-5>", self._on_scroll_sync)
        window.bind("<Escape>", self._clear_pointer_tool)
        window.protocol("WM_DELETE_WINDOW", self._close)

        ctk.CTkLabel(
            window,
            text=item.output_name,
            font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"),
            text_color=COLOR_TEXT,
        ).pack(anchor="w", padx=20, pady=(16, 4))

        # content_row holds the draggable original/result split on the
        # left and, for PDFs, the fixed-width magic pen sidebar
        # ("Korekta anonimizacji" + color legend) on the right - a
        # standalone column beside both panes rather than a toolbar row
        # above one of them, so both pane headers stay identical and
        # naturally start at the same height with no special-casing
        # needed (the toolbar-above-header/matching-spacer trick from
        # earlier the same day is retired along with the toolbar itself).
        content_row = ctk.CTkFrame(window, fg_color="transparent")
        content_row.pack(fill="both", expand=True, padx=20, pady=(4, 8))

        # A real draggable splitter (tk.PanedWindow) instead of a fixed
        # 50/50 grid: dragging the sash resizes one side and shrinks the
        # other, like a normal split view.
        paned = tk.PanedWindow(
            content_row,
            orient=tk.HORIZONTAL,
            sashwidth=6,
            sashrelief="flat",
            bg=COLOR_BORDER,
            bd=0,
            showhandle=False,
        )
        paned.pack(side="left", fill="both", expand=True)

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

        if self.magic_pen_available:
            self._build_magic_pen_sidebar(content_row).pack(
                side="left", fill="y", padx=(12, 0)
            )

        self._rebuild_original_pane()

        if self.magic_pen_available:
            self.edits = load_manual_edits(manual_edits_path(result_path))
            self._reload_visible_rects()
            self._build_magic_pen_pane(right_frame)
        else:
            self._rebuild_result_pane()

        if self.magic_pen_available:
            # Tk's pack() hands out space in the order widgets are
            # packed, not visual order - whatever is packed first gets
            # first claim on the row's width, and whatever is packed
            # last is the first to be squeezed out when the window gets
            # narrow. "Zapisz zmiany" is packed before "Anuluj zmiany"
            # for exactly that reason: it must never be the one that
            # disappears when the window is shrunk (confirmed as a real
            # bug earlier the same day, in the toolbar this replaces).
            bottom_actions = ctk.CTkFrame(window, fg_color="transparent")
            bottom_actions.pack(fill="x", padx=20, pady=(0, 8))
            self.save_button = ctk.CTkButton(
                bottom_actions,
                text="Zapisz zmiany",
                width=140,
                height=32,
                corner_radius=8,
                fg_color=COLOR_ICON_IDLE,
                hover_color=COLOR_ACCENT_HOVER,
                text_color=COLOR_TEXT_MUTED,
                font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
                state="disabled",
                command=self._save_pending_changes,
            )
            self.save_button.pack(side="right")
            self.cancel_button = ctk.CTkButton(
                bottom_actions,
                text="Anuluj zmiany",
                width=130,
                height=32,
                corner_radius=8,
                fg_color="transparent",
                hover_color=COLOR_ICON_IDLE,
                text_color=COLOR_TEXT_MUTED,
                font=ctk.CTkFont(family=FONT_FAMILY, size=12),
                state="disabled",
                command=self._cancel_pending_changes,
            )
            self.cancel_button.pack(side="right", padx=(0, 8))
        else:
            # No sidebar in this case (magic pen is PDF-only), so the
            # color legend still needs a home - the existing horizontal
            # row at the bottom, same as before.
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
        zoom_label = ctk.CTkEntry(
            zoom_row,
            width=42,
            height=22,
            justify="center",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            text_color=COLOR_TEXT_MUTED,
            fg_color=COLOR_CARD,
            border_width=1,
            border_color=COLOR_BORDER,
        )
        zoom_label.insert(0, zoom_percent_label(ZOOM_DEFAULT))
        zoom_label.bind(
            "<Return>", lambda _e, s=side: self._commit_zoom_entry(s)
        )
        zoom_label.bind(
            "<FocusOut>", lambda _e, s=side: self._commit_zoom_entry(s)
        )
        zoom_label.pack(side="left")
        IconTooltip(
            zoom_label,
            "Wpisz wartość i naciśnij Enter, by ustawić powiększenie ręcznie.",
            enabled=self.app.show_usage_hints,
        )
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

        hand_button = ctk.CTkButton(
            zoom_row,
            text="\U0001f590",
            width=26,
            height=22,
            corner_radius=6,
            fg_color=COLOR_ICON_IDLE,
            hover_color=COLOR_ACCENT_HOVER,
            text_color=COLOR_TEXT,
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            command=lambda: self._toggle_pointer_tool("hand"),
        )
        hand_button.pack(side="left", padx=(0, 2))
        self._hand_buttons.append(hand_button)
        IconTooltip(
            hand_button,
            "Łapka: przeciągnij, by przesunąć widok bez użycia scrolla. "
            "Kliknij ponownie lub Esc, by wyłączyć.",
            enabled=self.app.show_usage_hints,
        )
        zoom_tool_button = ctk.CTkButton(
            zoom_row,
            text="\U0001f50d",
            width=26,
            height=22,
            corner_radius=6,
            fg_color=COLOR_ICON_IDLE,
            hover_color=COLOR_ACCENT_HOVER,
            text_color=COLOR_TEXT,
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            command=lambda: self._toggle_pointer_tool("zoom"),
        )
        zoom_tool_button.pack(side="left", padx=(0, 6))
        self._zoom_tool_buttons.append(zoom_tool_button)
        IconTooltip(
            zoom_tool_button,
            "Lupa: przewiń, by powiększać/pomniejszać bez Ctrl. "
            "Wskazówka: Ctrl + scroll działa zawsze, nawet bez lupy. "
            "Kliknij ponownie lub Esc, by wyłączyć.",
            enabled=self.app.show_usage_hints,
        )

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
            IconTooltip(
                link_button,
                zoom_link_tooltip_text(self.zoom_linked),
                enabled=self.app.show_usage_hints,
            )
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

    def _on_scroll_sync(self, event: object) -> None:
        """Mirror plain (no Ctrl) scrolling onto the other pane while the
        two are locked together. The pane under the cursor already scrolls
        itself via CTkScrollableFrame's own internal binding - this only
        scrolls the *other* one, by the same amount, so both move as one.
        A no-op once unlinked: each pane is then free to scroll on its own.
        """
        widget = self.window.winfo_containing(event.x_root, event.y_root)
        side = self._pane_side_for_widget(widget)
        if side is None:
            return
        if self.active_pointer_tool == "zoom":
            # "Lupa" active: plain scroll zooms, same as if Ctrl were
            # held - Ctrl+scroll itself keeps working too either way.
            self._adjust_zoom(side, zoom_step_from_scroll_event(event))
            return
        if not self.zoom_linked:
            return
        other_frame = self.right_frame if side == "original" else self.left_frame
        self._scroll_pane_by(other_frame, scroll_sync_units(event))

    @staticmethod
    def _find_textbox_in(frame: ctk.CTkScrollableFrame) -> ctk.CTkTextbox | None:
        for widget in frame.winfo_children():
            if isinstance(widget, ctk.CTkTextbox):
                return widget
        return None

    def _scroll_pane_by(self, frame: ctk.CTkScrollableFrame | None, units: int) -> None:
        """Scroll one pane by ``units``.

        A DOCX/TXT pane's only child is one fixed-height CTkTextbox (see
        _render_text_block) - scrolling through a document longer than
        that box is the textbox's *own* internal yview, not a move of the
        outer CTkScrollableFrame's canvas (which barely has anything else
        to scroll), so mirroring has to target the textbox directly or a
        long document's sync is invisible even though this method runs.
        A PDF/image pane has no such textbox, so it falls back to the
        outer canvas as before. Reaches into private
        CTkTextbox._textbox/CTkScrollableFrame._parent_canvas - there is
        no public API for programmatic scrolling - so this stays
        defensive and silently does nothing on any error rather than risk
        crashing the preview over a cosmetic scroll-sync feature.
        """
        if frame is None or units == 0:
            return
        textbox = self._find_textbox_in(frame)
        if textbox is not None:
            try:
                textbox._textbox.yview_scroll(units, "units")
            except tk.TclError:
                pass
            return
        canvas = getattr(frame, "_parent_canvas", None)
        if canvas is None:
            return
        try:
            if canvas.yview() != (0.0, 1.0):
                canvas.yview_scroll(units, "units")
        except tk.TclError:
            pass

    def _scroll_pane_to_top(self, frame: ctk.CTkScrollableFrame | None) -> None:
        if frame is None:
            return
        textbox = self._find_textbox_in(frame)
        if textbox is not None:
            try:
                textbox._textbox.yview_moveto(0.0)
            except tk.TclError:
                pass
        canvas = getattr(frame, "_parent_canvas", None)
        if canvas is None:
            return
        try:
            canvas.yview_moveto(0.0)
        except tk.TclError:
            pass

    def _pane_side_for_widget(self, widget: object) -> str | None:
        """Identify which pane (if either) a widget belongs to.

        CTkScrollableFrame embeds its actual content Frame *inside* an
        internal scrolling Canvas (via ``canvas.create_window``), not the
        other way around - so ``self.left_frame`` never appears in that
        canvas's own ``.master`` chain. Without also matching its private
        ``_parent_canvas``/``_parent_frame``, a cursor sitting over blank
        canvas space rather than directly over rendered page content (e.g.
        past the bottom of a short page, or in the padding around it)
        would resolve to neither pane and silently do nothing.
        """
        left_widgets = {
            self.left_frame,
            getattr(self.left_frame, "_parent_canvas", None),
            getattr(self.left_frame, "_parent_frame", None),
        }
        right_widgets = {
            self.right_frame,
            getattr(self.right_frame, "_parent_canvas", None),
            getattr(self.right_frame, "_parent_frame", None),
        }
        node = widget
        while node is not None:
            if node in left_widgets:
                return "original"
            if node in right_widgets:
                return "result"
            node = getattr(node, "master", None)
        return None

    def _toggle_zoom_link(self) -> None:
        self.zoom_linked = not self.zoom_linked
        if self.zoom_linked:
            # Re-locking is a full reset to the default view for both
            # panes - not just syncing to whatever zoom/scroll position
            # the left pane happened to be at - so "back to automatic"
            # is one predictable state every time, not a moving target.
            self.original_zoom = ZOOM_DEFAULT
            self.result_zoom = ZOOM_DEFAULT
            self._rebuild_original_pane()
            self._rebuild_result_pane()
            self._scroll_pane_to_top(self.left_frame)
            self._scroll_pane_to_top(self.right_frame)
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

    @staticmethod
    def _set_zoom_entry_text(entry: ctk.CTkEntry, text: str) -> None:
        entry.delete(0, "end")
        entry.insert(0, text)

    def _update_zoom_controls(self) -> None:
        if self.original_zoom_label is not None:
            self._set_zoom_entry_text(
                self.original_zoom_label, zoom_percent_label(self.original_zoom)
            )
        if self.result_zoom_label is not None:
            self._set_zoom_entry_text(
                self.result_zoom_label, zoom_percent_label(self.result_zoom)
            )
        glyph = zoom_link_glyph(self.zoom_linked)
        tooltip_text = zoom_link_tooltip_text(self.zoom_linked)
        for button, tooltip in zip(self._link_buttons, self._link_tooltips):
            button.configure(
                text=glyph,
                fg_color=COLOR_ACCENT if self.zoom_linked else COLOR_ICON_IDLE,
                text_color="#FFFFFF" if self.zoom_linked else COLOR_TEXT_MUTED,
            )
            tooltip.set_text(tooltip_text)

    def _commit_zoom_entry(self, side: str) -> None:
        """Apply a manually-typed zoom percentage (e.g. "150" or "150%")
        from the entry for ``side``, clamped to the normal zoom range -
        invalid text just resets the entry back to the current zoom
        rather than raising or silently doing nothing.
        """
        entry = self.original_zoom_label if side == "original" else self.result_zoom_label
        current = self.original_zoom if side == "original" else self.result_zoom
        if entry is None:
            return
        raw = entry.get().strip().rstrip("%")
        try:
            percent = float(raw)
        except ValueError:
            self._set_zoom_entry_text(entry, zoom_percent_label(current))
            return
        new_value = clamp_zoom_level(percent / 100)
        if self.zoom_linked:
            self.original_zoom = new_value
            self.result_zoom = new_value
            self._rebuild_original_pane()
            self._rebuild_result_pane()
        elif side == "original":
            self.original_zoom = new_value
            self._rebuild_original_pane()
        else:
            self.result_zoom = new_value
            self._rebuild_result_pane()
        self._update_zoom_controls()

    def _toggle_pointer_tool(self, tool: str) -> None:
        """Toggle the shared hand/zoom pointer tool - clicking the
        already-active tool's button turns it back off (modeless
        default: plain scroll pans linked panes, Ctrl+scroll zooms)."""
        self.active_pointer_tool = None if self.active_pointer_tool == tool else tool
        self._refresh_pointer_tool_visuals()

    def _clear_pointer_tool(self, _event: object = None) -> None:
        """Esc cancels whichever pointer tool is active, if any."""
        if self.active_pointer_tool is not None:
            self.active_pointer_tool = None
            self._refresh_pointer_tool_visuals()

    def _refresh_pointer_tool_visuals(self) -> None:
        hand_active = self.active_pointer_tool == "hand"
        zoom_active = self.active_pointer_tool == "zoom"
        for button in self._hand_buttons:
            button.configure(
                fg_color=COLOR_ACCENT if hand_active else COLOR_ICON_IDLE,
                text_color="#FFFFFF" if hand_active else COLOR_TEXT,
            )
        for button in self._zoom_tool_buttons:
            button.configure(
                fg_color=COLOR_ACCENT if zoom_active else COLOR_ICON_IDLE,
                text_color="#FFFFFF" if zoom_active else COLOR_TEXT,
            )
        cursor = "fleur" if hand_active else ("sizing" if zoom_active else "arrow")
        for frame in (self.left_frame, self.right_frame):
            canvas = getattr(frame, "_parent_canvas", None)
            if canvas is not None:
                try:
                    canvas.configure(cursor=cursor)
                except tk.TclError:
                    pass

    def _pan_target(self, frame: ctk.CTkScrollableFrame) -> tk.Misc | None:
        """The widget hand-tool panning should actually scan_mark/
        scan_dragto for this pane - the same textbox-vs-canvas choice
        _scroll_pane_by makes for plain scroll sync, and for the same
        reason: a DOCX/TXT pane's real scrollable content is the inner
        CTkTextbox's own view, not the outer CTkScrollableFrame canvas
        (which has little to no scroll range of its own around one
        fixed-height textbox). Panning the outer canvas there would
        silently do nothing.
        """
        textbox = self._find_textbox_in(frame)
        if textbox is not None:
            return textbox._textbox
        return getattr(frame, "_parent_canvas", None)

    def _bind_pane_panning(self, widget: tk.Misc, frame: ctk.CTkScrollableFrame) -> None:
        """Recursively wire hand-tool drag-to-pan onto every descendant of
        a freshly-rendered pane, forwarding to whatever _pan_target
        resolves to via scan_mark/scan_dragto (the standard Tk pattern
        for this). A no-op whenever the hand tool isn't active, so this
        never interferes with normal clicking/scrolling. Bound with
        add="+" so it only ever adds to, never replaces, any existing
        binding on the same widget. Skips CTkScrollbar descendants so
        the hand tool never fights a scrollbar's own native drag.
        """
        if not isinstance(widget, ctk.CTkScrollbar):
            widget.bind(
                "<ButtonPress-1>",
                lambda e, f=frame: self._on_pan_press(e, f),
                add="+",
            )
            widget.bind(
                "<B1-Motion>", lambda e, f=frame: self._on_pan_drag(e, f), add="+"
            )
        for child in widget.winfo_children():
            self._bind_pane_panning(child, frame)

    def _on_pan_press(self, event: object, frame: ctk.CTkScrollableFrame) -> None:
        if self.active_pointer_tool != "hand":
            return
        target = self._pan_target(frame)
        if target is not None:
            target.scan_mark(event.x_root, event.y_root)

    def _on_pan_drag(self, event: object, frame: ctk.CTkScrollableFrame) -> None:
        if self.active_pointer_tool != "hand":
            return
        target = self._pan_target(frame)
        if target is None:
            return
        # tkinter.Canvas.scan_dragto takes an optional gain (used here for
        # a direct, 1:1 drag instead of Tk's own fast default); plain
        # tkinter.Text.scan_dragto - the inner textbox on a DOCX/TXT pane -
        # takes no such argument at all and raises TypeError if given one.
        try:
            target.scan_dragto(event.x_root, event.y_root, gain=1)
        except TypeError:
            target.scan_dragto(event.x_root, event.y_root)

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
        self._bind_pane_panning(self.left_frame, self.left_frame)

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
        self._bind_pane_panning(self.right_frame, self.right_frame)

    # -- magic pen: toolbar -------------------------------------------------

    def _build_magic_pen_sidebar(self, parent: ctk.CTkFrame) -> ctk.CTkFrame:
        """The right-hand "Korekta anonimizacji" panel: the pinnable tool
        buttons plus the color legend, stacked vertically - a fixed-width
        column standing beside both preview panes rather than a toolbar
        row above one of them. Moving the tools here also retires the
        toolbar-above-header/matching-spacer trick from earlier the same
        day: with no toolbar row sitting above "Po anonimizacji" anymore,
        both pane headers are simply identical again and naturally start
        at the same height with nothing extra needed.
        """
        sidebar = ctk.CTkFrame(
            parent,
            fg_color=COLOR_CARD,
            corner_radius=10,
            border_width=1,
            border_color=COLOR_BORDER,
            width=200,
        )
        sidebar.pack_propagate(False)
        inner = ctk.CTkFrame(sidebar, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=14, pady=14)

        ctk.CTkLabel(
            inner,
            text="Korekta anonimizacji",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
            text_color=COLOR_TEXT,
            anchor="w",
        ).pack(fill="x", pady=(0, 10))

        # Modeless by default: LMB draws a new redaction, RMB always
        # toggles an existing one, no mode to switch first. These are
        # also clickable: clicking one pins LMB to that single action (a
        # "manual" mode for anyone who'd rather pick a tool explicitly
        # than remember which mouse button does what) - clicking the same
        # one again returns to the modeless default. Independently of
        # pinning, a chip also lights up for as long as its action is
        # actually in progress (LMB held down / RMB clicked), so these
        # double as a live "this is what's happening" indicator too.
        self._tool_chips["draw"] = self._build_tool_chip(
            inner, "✏", "Dodaj zaznaczenie", "draw"
        )
        self._tool_chips["erase"] = self._build_tool_chip(
            inner, "🧹", "Usuń zaznaczenie", "erase"
        )
        self._refresh_tool_chip_visuals()

        self.pen_status_label = ctk.CTkLabel(
            inner,
            text="",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            text_color=COLOR_TEXT_MUTED,
            anchor="w",
            wraplength=168,
            justify="left",
        )
        self.pen_status_label.pack(fill="x", pady=(4, 0))

        ctk.CTkFrame(inner, fg_color=COLOR_BORDER, height=1).pack(fill="x", pady=14)

        ctk.CTkLabel(
            inner,
            text="Kategorie danych",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
            text_color=COLOR_TEXT,
            anchor="w",
        ).pack(fill="x", pady=(0, 8))
        for color, text in LEGEND_ITEMS:
            row = ctk.CTkFrame(inner, fg_color="transparent")
            row.pack(fill="x", pady=3)
            ctk.CTkLabel(
                row,
                text="●",
                text_color=color,
                font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"),
                width=16,
            ).pack(side="left")
            ctk.CTkLabel(
                row,
                text=text,
                text_color=COLOR_TEXT,
                font=ctk.CTkFont(family=FONT_FAMILY, size=10),
                anchor="w",
                wraplength=150,
                justify="left",
            ).pack(side="left", fill="x", expand=True)

        return sidebar

    def _build_tool_chip(
        self, parent: ctk.CTkFrame, glyph: str, label: str, tool: str
    ) -> tuple[ctk.CTkFrame, ctk.CTkLabel, ctk.CTkLabel]:
        chip = ctk.CTkFrame(parent, fg_color=COLOR_BG, corner_radius=8, cursor="hand2")
        chip.pack(fill="x", pady=(0, 8))
        row = ctk.CTkFrame(chip, fg_color="transparent")
        row.pack(fill="x", padx=10, pady=8)
        glyph_label = ctk.CTkLabel(
            row,
            text=glyph,
            font=ctk.CTkFont(family=FONT_FAMILY, size=14),
            text_color=COLOR_TEXT,
        )
        glyph_label.pack(side="left", padx=(0, 8))
        text_label = ctk.CTkLabel(
            row,
            text=label,
            font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
            text_color=COLOR_TEXT_MUTED,
            anchor="w",
        )
        text_label.pack(side="left", fill="x", expand=True)
        for widget in (chip, row, glyph_label, text_label):
            widget.bind("<Button-1>", lambda _e, t=tool: self._toggle_pinned_tool(t))
        IconTooltip(
            chip,
            "Kliknij, aby przypisać LPM tylko do tego narzędzia (tryb ręczny). "
            "PPM zawsze usuwa zaznaczenie, niezależnie od wybranego trybu. "
            "Kliknij ponownie, aby wrócić do trybu automatycznego.",
        )
        return (chip, glyph_label, text_label)

    def _toggle_pinned_tool(self, tool: str) -> None:
        self.pinned_tool = None if self.pinned_tool == tool else tool
        self._refresh_tool_chip_visuals()

    def _flash_tool_chip(self, tool: str) -> None:
        """Briefly light up a chip for a one-shot action (a right-click has
        no natural "held" duration the way a LMB drag does)."""
        self._transient_tool = tool
        self._refresh_tool_chip_visuals()
        self.window.after(250, self._clear_transient_tool)

    def _clear_transient_tool(self) -> None:
        self._transient_tool = None
        self._refresh_tool_chip_visuals()

    def _refresh_tool_chip_visuals(self) -> None:
        for tool, chip_widgets in self._tool_chips.items():
            self._set_tool_chip_active(
                chip_widgets,
                active=(self.pinned_tool == tool or self._transient_tool == tool),
            )

    def _set_tool_chip_active(
        self,
        chip_widgets: tuple[ctk.CTkFrame, ctk.CTkLabel, ctk.CTkLabel],
        *,
        active: bool,
    ) -> None:
        chip, glyph_label, text_label = chip_widgets
        if active:
            chip.configure(fg_color=COLOR_ACCENT)
            glyph_label.configure(text_color="#FFFFFF")
            text_label.configure(text_color="#FFFFFF")
        else:
            chip.configure(fg_color=COLOR_CARD)
            glyph_label.configure(text_color=COLOR_TEXT)
            text_label.configure(text_color=COLOR_TEXT_MUTED)

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
        """LMB draws a new redaction by default; pinned to "erase" it
        instead toggles the rectangle under the cursor immediately, the
        same one-click action RMB always performs. Either way, the
        matching tool chip lights up for as long as the button is held.
        """
        active_tool = self.pinned_tool or "draw"
        self._transient_tool = active_tool
        self._refresh_tool_chip_visuals()
        if active_tool == "erase":
            self._erase_at_point(event.x, event.y, page_number)
            return
        self._drag_start = (event.x, event.y)
        self._drag_rect_id = None

    def _on_pane_right_click(self, event: tk.Event, page_number: int) -> None:
        """Right button always toggles the rectangle under the cursor,
        regardless of the pinned tool - pinning to "draw" only locks in
        what LMB does, it never takes this shortcut away."""
        self._flash_tool_chip("erase")
        self._erase_at_point(event.x, event.y, page_number)

    def _erase_at_point(self, x: float, y: float, page_number: int) -> None:
        zoom = self._page_zoom.get(page_number, 1.0)
        px, py = canvas_point_to_pdf_point(x, y, zoom)
        hit = find_rect_at_point(self._hit_test_pool(), page_number, px, py)
        if hit is not None:
            self._toggle_pending_remove(hit)

    def _on_pane_drag(self, event: tk.Event, page_number: int) -> None:
        if self.pinned_tool == "erase":
            return
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
        self._transient_tool = None
        self._refresh_tool_chip_visuals()
        if self.pinned_tool == "erase":
            return
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


class AboutDialog:
    """A small "O programie" modal: what the app is, version, and the
    same local-only privacy statement shown elsewhere in the app -
    deliberately no personal author info (name/email), just the product
    facts, consistent with the rest of the app never surfacing anything
    beyond safe, generic status text.
    """

    def __init__(self, app: AnonymizerApp) -> None:
        self.app = app
        window = ctk.CTkToplevel(app.root)
        self.window = window
        window.title("O programie")
        window.geometry("420x360")
        window.resizable(False, False)
        window.configure(fg_color=COLOR_BG)
        window.transient(app.root)
        window.grab_set()
        app._load_app_icon(window)
        _bring_window_to_front(window)

        header = ctk.CTkFrame(window, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=(20, 6))
        if APP_ICON_PATH.exists():
            try:
                icon_image = Image.open(APP_ICON_PATH)
                self._icon_image = ctk.CTkImage(light_image=icon_image, size=(40, 40))
                ctk.CTkLabel(header, image=self._icon_image, text="").pack(
                    side="left", padx=(0, 10)
                )
            except (OSError, tk.TclError):
                pass
        title_col = ctk.CTkFrame(header, fg_color="transparent")
        title_col.pack(side="left")
        ctk.CTkLabel(
            title_col,
            text=APP_TITLE,
            font=ctk.CTkFont(family=FONT_FAMILY, size=18, weight="bold"),
            text_color=COLOR_TEXT,
        ).pack(anchor="w")
        ctk.CTkLabel(
            title_col,
            text=f"Wersja {APP_VERSION}",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            text_color=COLOR_TEXT_MUTED,
        ).pack(anchor="w")

        ctk.CTkLabel(
            window,
            text=APP_ABOUT_TEXT,
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            text_color=COLOR_TEXT,
            wraplength=370,
            justify="left",
        ).pack(fill="x", padx=20, pady=(10, 16))

        trust_card = ctk.CTkFrame(window, corner_radius=10, fg_color=COLOR_CARD)
        trust_card.pack(fill="x", padx=20, pady=(0, 16))
        trust_row = ctk.CTkFrame(trust_card, fg_color="transparent")
        trust_row.pack(fill="x", padx=14, pady=12)
        ctk.CTkLabel(
            trust_row,
            text="\U0001f512",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13),
            text_color=COLOR_OK,
        ).pack(side="left", padx=(0, 8))
        ctk.CTkLabel(
            trust_row,
            text=(
                "Wszystkie operacje wykonywane są lokalnie. Żadne dane nie "
                "są wysyłane do internetu ani do chmury."
            ),
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            text_color=COLOR_TEXT,
            wraplength=310,
            justify="left",
            anchor="w",
        ).pack(side="left", fill="x", expand=True)

        ctk.CTkButton(
            window,
            text="Zamknij",
            height=32,
            corner_radius=8,
            fg_color=COLOR_ACCENT,
            hover_color=COLOR_ACCENT_HOVER,
            command=window.destroy,
        ).pack(pady=(0, 20))


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


def _set_windows_app_user_model_id() -> None:
    """Give this process its own taskbar identity on Windows.

    Never fatal - a failure here only means the taskbar icon may fall
    back to python.exe's generic one, not that the app can't run. Must
    run before the first window is created (see _load_app_icon's
    docstring for why).
    """
    if sys.platform != "win32":
        return
    try:
        import ctypes

        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            APP_USER_MODEL_ID
        )
    except (OSError, AttributeError):
        pass


def start_gui() -> None:
    """Start the CustomTkinter desktop application."""
    _set_windows_app_user_model_id()
    root = DnDCTk()
    AnonymizerApp(root)
    root.mainloop()


def main() -> None:
    """Run the GUI when this module is executed as a script."""
    start_gui()


if __name__ == "__main__":
    main()
