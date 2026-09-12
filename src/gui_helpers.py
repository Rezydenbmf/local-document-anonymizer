"""Shared constants, pure formatting helpers, and small reusable
Tkinter widgets used across the DocShield GUI."""

import json
import os
import re
import subprocess
import sys
import tkinter as tk
from collections.abc import Mapping, Sequence
from datetime import datetime
from pathlib import Path

import customtkinter as ctk
from PIL import Image, ImageDraw
from tkinterdnd2 import TkinterDnD

try:
    from .anonymizer import (
        PDF_OUTPUT_MODE_ORIGINAL_REDACTION,
        PDF_OUTPUT_MODE_REBUILT_REVIEW,
        PDF_OUTPUT_MODE_VISUAL,
        PDF_REDACTION_SCOPE_SAFE,
        PDF_REDACTION_SCOPE_STRICT,
        SUPPORTED_LABELS,
        BatchResult,
    )
    from .audit import AUDIT_CATEGORY_ORDER
    from .llm_review import LLM_STATUS_AVAILABLE
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
        REVIEW_STATUS_REJECTED,
        ReviewItem,
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
    )
    from audit import AUDIT_CATEGORY_ORDER
    from llm_review import LLM_STATUS_AVAILABLE
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
        REVIEW_STATUS_REJECTED,
        ReviewItem,
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
# enough files pushes the rest of the scrollable column below the window
# with no way to reach it at all (self.content itself does not scroll).
# Grown from the original 168 once the output-folder row and "Anonimizuj"
# button moved out of this column into the always-visible "Szybkie akcje"
# panel (see _build_quick_settings_panel) - per direct user feedback that
# the freed vertical space should show more of the file list, not sit
# unused.
FILE_LIST_MAX_HEIGHT = 320
# Header row layout switches from side-by-side to stacked (see
# _update_header_layout) once the window narrows past this content width,
# so the handwritten-style personal note never gets clipped.
HEADER_STACK_BREAKPOINT = 640
# No longer read anywhere in gui_app.py - the quick-settings panel used to
# hide below this window width, but that gate was removed once the panel
# started carrying the "Anonimizuj" button itself (hiding it would have
# hidden the button too). Kept defined only because gui.py's compatibility
# shim still re-exports it as part of the public `from gui import X` API.
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


def ui_hints_config_path() -> Path:
    """Return the local file that remembers which one-time UI hints/
    warnings (the comparison window's zoom-link toggle, the approval
    lock-in warning, ...) the user has already dismissed - shared across
    every screen rather than each keeping its own file, so a single
    "restore this warning" action in Settings has one place to reach
    into. Stores hint ids only - never document content, folder paths,
    or anything else about what the user processed.
    """
    return Path.home() / ".anonimizer" / "ui_hints_seen.json"


def load_seen_hints(config_path: Path) -> set[str]:
    """Load the set of already-dismissed hint ids, tolerating a missing/
    corrupt file."""
    try:
        raw = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return set()
    if not isinstance(raw, list):
        return set()
    return {str(item) for item in raw if isinstance(item, str)}


def save_seen_hints(config_path: Path, hint_ids: set[str]) -> None:
    """Persist the dismissed-hints set, creating the config folder if needed."""
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(
        json.dumps(sorted(hint_ids), ensure_ascii=False, indent=2), encoding="utf-8"
    )


# Hint ids stored in ui_hints_config_path(). ZOOM_LINK_HINT_ID marks the
# comparison window's zoom-link toggle tooltip as already auto-flashed
# once; APPROVAL_LOCK_HINT_ID marks the "approving locks this file"
# warning (see ApprovalLockWarningDialog in gui_dialogs.py) as dismissed;
# MAGIC_PEN_HINT_ID marks the first-open "what can I do here" magic pen
# intro (see MagicPenHintDialog) as dismissed - all three survive an app
# restart via their own "Nie pokazuj ponownie" checkbox, and can be
# brought back from Settings > Ogólne.
ZOOM_LINK_HINT_ID = "zoom_link_toggle"
APPROVAL_LOCK_HINT_ID = "approval_lock_warning"
MAGIC_PEN_HINT_ID = "magic_pen_intro"


def hint_is_dismissed(hint_id: str) -> bool:
    """True once the user has dismissed the given one-time hint/warning
    (directly, or via its own "don't show again" checkbox) - persists
    across restarts, tolerating a missing/corrupt config file the same
    way every other local config in this app does."""
    return hint_id in load_seen_hints(ui_hints_config_path())


def dismiss_hint(hint_id: str) -> None:
    """Mark a hint/warning as dismissed so it stops appearing. Silently
    does nothing on a write failure (e.g. a read-only home folder) -
    this is a cosmetic preference, never worth crashing the app over."""
    config_path = ui_hints_config_path()
    seen = load_seen_hints(config_path)
    seen.add(hint_id)
    try:
        save_seen_hints(config_path, seen)
    except OSError:
        pass


def restore_hint(hint_id: str) -> None:
    """Undo dismiss_hint(hint_id) - the Settings-side "show this warning
    again" action. A no-op if the hint was never dismissed in the first
    place."""
    config_path = ui_hints_config_path()
    seen = load_seen_hints(config_path)
    if hint_id not in seen:
        return
    seen.discard(hint_id)
    try:
        save_seen_hints(config_path, seen)
    except OSError:
        pass


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


def center_window_over_parent(
    window: tk.Misc, parent: tk.Misc, width: int, height: int
) -> None:
    """Position a new Toplevel's geometry centered over ``parent``'s
    current on-screen position, instead of leaving Tk/the OS to decide.

    Without an explicit position, a bare "WxH" geometry string can open
    on a different monitor than the parent window on a multi-monitor
    Windows setup - confirmed directly by a user report: Settings and
    the comparison window kept opening on a laptop's own screen while
    the main app sat on a different monitor entirely, reading as a
    stray, unrelated window rather than a dialog that belongs to the
    app being used. Falls back to the bare size string (letting Tk/the
    OS decide, the previous behavior) if the parent's geometry cannot
    be read for any reason, rather than fail a dialog open over a
    cosmetic placement detail.
    """
    try:
        parent.update_idletasks()
        parent_x = parent.winfo_x()
        parent_y = parent.winfo_y()
        parent_width = parent.winfo_width()
        parent_height = parent.winfo_height()
    except tk.TclError:
        window.geometry(f"{width}x{height}")
        return
    x = parent_x + max((parent_width - width) // 2, 0)
    y = parent_y + max((parent_height - height) // 2, 0)
    window.geometry(f"{width}x{height}+{x}+{y}")


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


# Patterns that make a *file name* itself look like it carries personal
# data. Deliberately narrower than the document-content detectors: a file
# name is short, so a loose rule here (any capitalised word, say) would
# warn on almost everything and train the user to ignore the warning.
# Only shapes that are hard to produce by accident qualify.
_FILENAME_PII_PATTERNS: tuple[tuple[str, "re.Pattern[str]"], ...] = (
    ("PESEL", re.compile(r"(?<!\d)\d{11}(?!\d)")),
    ("NIP", re.compile(r"(?<!\d)\d{10}(?!\d)")),
    ("REGON", re.compile(r"(?<!\d)(?:\d{9}|\d{14})(?!\d)")),
    ("dowód osobisty", re.compile(r"(?<![A-Za-z0-9])[A-Z]{3}\d{6}(?![A-Za-z0-9])")),
    (
        "e-mail",
        re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
    ),
    (
        "numer telefonu",
        re.compile(r"(?<!\d)(?:\+?48[\s._-]?)?\d{3}[\s._-]?\d{3}[\s._-]?\d{3}(?!\d)"),
    ),
)


def detect_filename_pii_labels(file_name: str) -> list[str]:
    """Return labels for personal data visible in a *file name* itself.

    Anonymizing a document's contents does nothing about its name: every
    output file, the review manifest and the exported workspace all
    inherit it, so "umowa_Kowalski_90020212345.pdf" leaks through a
    perfectly clean pipeline. Flagged from an audit of what ends up on
    disk; reported to the user rather than silently renamed, since the
    file name is theirs to control and a rename would break the link back
    to their own source document.
    """
    stem = Path(file_name).stem
    labels: list[str] = []
    for label, pattern in _FILENAME_PII_PATTERNS:
        if pattern.search(stem) and label not in labels:
            labels.append(label)
    return labels


def format_filename_pii_warning(file_names: Sequence[str]) -> str:
    """One-line warning naming files whose *name* carries personal data."""
    flagged = [name for name in file_names if detect_filename_pii_labels(name)]
    if not flagged:
        return ""
    shown = ", ".join(flagged[:3])
    if len(flagged) > 3:
        shown = f"{shown} i {len(flagged) - 3} inn."
    return (
        f"Uwaga: dane osobowe widoczne w samej nazwie pliku ({shown}). "
        "Anonimizacja nie zmienia nazw - rozważ zmianę przed udostępnieniem."
    )


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


PROCESSING_ANIMATION_WIDTH = 10


def format_processing_animation_frame(step: int, width: int = PROCESSING_ANIMATION_WIDTH) -> str:
    """Return one frame of a small "pencil copies a page" text animation
    shown on the processing screen - per direct user feedback that a
    plain progress bar felt bare and a small, simple, charming animation
    would be nicer while a batch runs. A pencil "✏" ping-pongs between
    two page emoji, one step per call; the caller drives ``step`` up by
    one on a timer (see AnonymizerApp._tick_processing_animation) - this
    function itself is a pure, stateless frame-position calculation so
    it can be tested without a running Tk loop.
    """
    safe_width = max(width, 2)
    cycle_length = safe_width * 2 - 2
    position = step % cycle_length
    if position >= safe_width:
        position = cycle_length - position
    dots_before = "·" * position
    dots_after = "·" * (safe_width - 1 - position)
    return f"\U0001f4c4 {dots_before}✏️{dots_after} \U0001f4c4"


def format_anonymize_button_text(input_file_count: int) -> str:
    """Label the main action button with the selected count, matching the
    mockup's "Anonimizuj 3 pliki" - falls back to the plain verb alone
    when nothing is selected yet, since "Anonimizuj 0 plików" reads oddly
    as an instruction.
    """
    if input_file_count <= 0:
        return "Anonimizuj"
    return f"Anonimizuj {input_file_count} {_pl_file_word(input_file_count)}"


def format_approval_lock_warning_title(count: int) -> str:
    """Title for ApprovalLockWarningDialog, for one file or several at once
    (bulk "Zatwierdź zaznaczone")."""
    return "Zatwierdzić plik?" if count <= 1 else "Zatwierdzić pliki?"


def format_approval_lock_warning_text(count: int) -> str:
    """Body text for ApprovalLockWarningDialog, correctly pluralized for
    Polish - approving is a one-way action (see ComparisonWindow.locked):
    the magic pen stops accepting edits on an approved file, and the only
    way back is re-running anonymization on it from scratch.
    """
    if count <= 1:
        subject = "Ten plik"
        verb = "nie będzie"
    else:
        subject = f"Wybrane {count} {_pl_file_word(count)}"
        verb = "nie będą"
    return (
        f"{subject} po zatwierdzeniu {verb} już edytowalne magic penem - "
        "aby wprowadzić zmiany, trzeba będzie uruchomić anonimizację od nowa."
    )


def _pl_edit_word(count: int) -> str:
    """Return the grammatically correct Polish word for "edit(s)" in the
    accusative case - both call sites use it as the object of a verb
    ("Zaakceptuj ...", "Zatwierdzić ..."), where singular "edycja"
    (nominative) would be wrong; "edycję" is the correct singular form
    there. The 2-4 and 5+ plural forms are the same in both cases, so
    only the count == 1 branch needed to change.
    """
    if count == 1:
        return "edycję"
    last_digit = count % 10
    last_two = count % 100
    if 2 <= last_digit <= 4 and not (12 <= last_two <= 14):
        return "edycje"
    return "edycji"


def format_save_button_text(pending_count: int) -> str:
    """Label the magic pen's save button with the pending-edit count,
    e.g. "Zaakceptuj edycję (3)" - renamed from the previous plain
    "Zapisz zmiany" per direct user feedback that "save" undersold what
    the button actually does (approving edits that then get baked into
    a regenerated PDF), and that seeing how many pending edits are about
    to be applied is useful before clicking it.
    """
    if pending_count <= 0:
        return "Zaakceptuj edycję"
    return f"Zaakceptuj {_pl_edit_word(pending_count)} ({pending_count})"


def format_pending_edit_confirmation_title(pending_count: int) -> str:
    """Title for the magic pen's save-confirmation dialog, e.g.
    "Zatwierdzić 3 edycje?" - correctly pluralized for Polish."""
    return f"Zatwierdzić {pending_count} {_pl_edit_word(pending_count)}?"


def format_page_list(pages: Sequence[int]) -> str:
    """Format a sorted, deduplicated sequence of 1-based page numbers
    for display, e.g. [1, 2, 4] -> "1, 2, 4". Empty input returns ""."""
    return ", ".join(str(page) for page in pages)


def _pl_page_word(pages: Sequence[int]) -> str:
    return "strona" if len(pages) == 1 else "strony"


def format_pending_edit_summary_lines(
    added_count: int,
    added_pages: Sequence[int],
    removed_count: int,
    removed_pages: Sequence[int],
) -> list[str]:
    """Plain-language, content-free summary of an editable PDF's pending
    manual edits - counts and page numbers only, deliberately never the
    redacted text itself: showing the actual word being hidden inside an
    "are you sure you want to apply this?" confirmation would defeat the
    entire point of anonymizing it in the first place. Used by
    ComparisonWindow's save confirmation (see also format_save_button_text
    for the button's own label)."""
    lines: list[str] = []
    if added_count:
        lines.append(
            f"Dodane ręczne zaznaczenia: {added_count} "
            f"({_pl_page_word(added_pages)} {format_page_list(added_pages)})"
        )
    if removed_count:
        lines.append(
            f"Cofnięte automatyczne zaznaczenia: {removed_count} "
            f"({_pl_page_word(removed_pages)} {format_page_list(removed_pages)})"
        )
    return lines


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


def apply_subtle_scrollbar(scrollable_frame) -> None:
    """Restyle one CTkScrollableFrame's built-in scrollbar to stay out of
    the way: an invisible track, a low-contrast thumb the rest of the
    time, and a slightly more visible thumb only while the pointer is
    actually over the scrollable area (which is also, in practice,
    whenever the user is using the mouse wheel to scroll it - scrolling
    requires hovering over the content first). Direct user feedback: the
    default scrollbars "weren't pretty" and drew more attention than a
    scrollbar should; this is applied to every CTkScrollableFrame in the
    app rather than styled ad hoc per screen.

    CTkScrollbar's button_color does not support "transparent" the way
    fg_color does (only fg_color is created with transparency=True
    upstream) - COLOR_SCROLLBAR_IDLE is a real, near-background color
    instead, close enough to both COLOR_BG and COLOR_CARD to read as
    "gone" without actually being an unsupported value.
    """
    scrollbar = getattr(scrollable_frame, "_scrollbar", None)
    if scrollbar is None:
        return
    scrollbar.configure(
        fg_color="transparent",
        button_color=COLOR_SCROLLBAR_IDLE,
        button_hover_color=COLOR_SCROLLBAR_HOVER,
    )

    def _show(_event: object = None) -> None:
        scrollbar.configure(button_color=COLOR_SCROLLBAR_HOVER)

    def _hide(_event: object = None) -> None:
        scrollbar.configure(button_color=COLOR_SCROLLBAR_IDLE)

    # Bind on both the scrollable frame's content area and its outer
    # parent frame (which also contains the scrollbar itself) so hovering
    # the thumb to actually grab it does not immediately hide it again.
    hover_targets = [scrollable_frame, getattr(scrollable_frame, "_parent_frame", None)]
    for target in hover_targets:
        if target is None:
            continue
        target.bind("<Enter>", _show, add="+")
        target.bind("<Leave>", _hide, add="+")


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
# The sidebar switched from a plain white card to this dark-navy scheme
# (mockup-requested: the light sidebar "blended into the app" and users
# could miss/ignore it) - COLOR_PRIMARY finally gets used here instead of
# sitting defined-but-unreferenced since Stage 1.
COLOR_SIDEBAR_BG = COLOR_PRIMARY
COLOR_SIDEBAR_HOVER = "#22336E"
COLOR_SIDEBAR_TEXT = "#AEB8DA"
COLOR_SIDEBAR_TEXT_MUTED = "#7C87AC"
COLOR_SIDEBAR_TRUST_BG = "#1E2E63"
# Scrollbar thumb colors for apply_subtle_scrollbar() below - low-contrast
# on purpose (direct user feedback: the default CTk scrollbars "weren't
# pretty" and drew the eye more than a scrollbar should). SCROLLBAR_IDLE
# is close enough to both COLOR_BG and COLOR_CARD that the thumb all but
# disappears until the pointer is actually over the scrollable area.
COLOR_SCROLLBAR_IDLE = "#E3E7F1"
COLOR_SCROLLBAR_HOVER = "#B7C0D6"
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


