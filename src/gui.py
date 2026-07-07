"""Tkinter GUI for batch anonymization."""

from collections.abc import Mapping
import os
from pathlib import Path
import subprocess
import sys
import tkinter as tk
from tkinter import filedialog, ttk

try:
    from .audit import AUDIT_CATEGORY_ORDER
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
        REVIEW_STATUSES,
        REVIEW_STATUS_APPROVED,
        ReviewItem,
        apply_review_statuses,
        export_approved_workspace,
        load_review_workspace,
        preferred_review_output_path,
        save_review_files,
    )
except ImportError:
    from audit import AUDIT_CATEGORY_ORDER
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
        REVIEW_STATUSES,
        REVIEW_STATUS_APPROVED,
        ReviewItem,
        apply_review_statuses,
        export_approved_workspace,
        load_review_workspace,
        preferred_review_output_path,
        save_review_files,
    )


APP_TITLE = "Local Document Anonymizer"
MANUAL_REVIEW_WARNING = (
    "Manual review required before using or sharing the anonymized result."
)
WINDOW_MIN_WIDTH = 720
WINDOW_MIN_HEIGHT = 560
WINDOW_DEFAULT_SIZE = "900x720"
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


class AnonymizerGui:
    """Small Tkinter application for anonymizing selected files."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.selected_paths: list[Path] = []
        self.output_dir: Path | None = None
        self.sensitive_terms_path: Path | None = None
        self.selected_path_var = tk.StringVar(value="No files selected.")
        self.selected_file_count_var = tk.StringVar(
            value=format_selected_file_count(0)
        )
        self.output_dir_var = tk.StringVar(value="No output folder selected.")
        self.sensitive_terms_var = tk.StringVar(value=format_dictionary_result(None))
        self.use_ner_var = tk.BooleanVar(value=True)
        self.use_llm_review_var = tk.BooleanVar(value=False)
        self.llm_model_var = tk.StringVar(value="")
        self.llm_model_hint_var = tk.StringVar(value=LLM_NO_MODELS_HINT)
        self.pdf_redaction_scope_var = tk.StringVar(
            value=PDF_OUTPUT_LABEL_VISUAL_REDACTION
        )
        self.readiness_var = tk.StringVar(
            value=format_anonymize_readiness(0, False)
        )
        self.status_var = tk.StringVar(
            value="Select input files and an output folder to begin."
        )
        self.counters_var = tk.StringVar(value=format_counters({}))
        self.audit_var = tk.StringVar(value=format_batch_audit_result(None))
        self.output_path_var = tk.StringVar(value="No outputs yet.")
        self.report_path_var = tk.StringVar(value="No reports yet.")
        self.review_dir: Path | None = None
        self.review_items: list[ReviewItem] = []
        self.review_batch_summary_names: list[str] = []
        self.review_dir_var = tk.StringVar(value="No review folder selected.")
        self.review_status_var = tk.StringVar(
            value="Load an output folder to begin manual review tracking."
        )
        self.review_status_choice_var = tk.StringVar(value=REVIEW_STATUS_APPROVED)
        self.scroll_canvas: tk.Canvas | None = None
        self.selected_files_listbox: tk.Listbox | None = None
        self.review_tree: ttk.Treeview | None = None
        self.anonymize_button: ttk.Button | None = None
        self.llm_model_combobox: ttk.Combobox | None = None
        self.pdf_redaction_scope_combobox: ttk.Combobox | None = None
        self.wrap_labels: list[ttk.Label] = []

        self._build()

    def _build(self) -> None:
        self.root.title(APP_TITLE)
        self.root.geometry(WINDOW_DEFAULT_SIZE)
        self.root.minsize(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        container = ttk.Frame(self.root)
        container.grid(row=0, column=0, sticky="nsew")
        container.columnconfigure(0, weight=1)
        container.rowconfigure(0, weight=1)

        canvas = tk.Canvas(container, highlightthickness=0)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.scroll_canvas = canvas

        main = ttk.Frame(canvas, padding=16)
        main_window = canvas.create_window((0, 0), window=main, anchor="nw")
        main.bind(
            "<Configure>",
            lambda _event: canvas.configure(scrollregion=canvas.bbox("all")),
        )
        canvas.bind(
            "<Configure>",
            lambda event: canvas.itemconfigure(main_window, width=event.width),
        )
        canvas.bind("<MouseWheel>", self._on_mousewheel)
        canvas.bind("<Button-4>", self._on_mousewheel)
        canvas.bind("<Button-5>", self._on_mousewheel)

        main.columnconfigure(1, weight=1)

        title = ttk.Label(main, text=APP_TITLE, font=("Segoe UI", 14, "bold"))
        title.grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 14))

        file_button_frame = ttk.Frame(main)
        file_button_frame.grid(row=1, column=0, columnspan=3, sticky="ew", pady=(0, 8))
        file_button_frame.columnconfigure(3, weight=1)

        select_button = ttk.Button(
            file_button_frame, text="Add files", command=self.select_file
        )
        select_button.grid(row=0, column=0, sticky="w")

        ttk.Button(
            file_button_frame,
            text="Remove selected",
            command=self.remove_selected_files,
        ).grid(row=0, column=1, sticky="w", padx=(8, 0))

        ttk.Button(
            file_button_frame,
            text="Clear files",
            command=self.clear_selected_files,
        ).grid(row=0, column=2, sticky="w", padx=(8, 0))

        ttk.Label(main, textvariable=self.selected_file_count_var).grid(
            row=2, column=0, columnspan=3, sticky="w", pady=(0, 6)
        )

        selected_files_frame = ttk.Frame(main)
        selected_files_frame.grid(
            row=3, column=0, columnspan=3, sticky="ew", pady=(0, 10)
        )
        selected_files_frame.columnconfigure(0, weight=1)
        self.selected_files_listbox = tk.Listbox(
            selected_files_frame,
            height=SELECTED_FILE_LIST_HEIGHT,
            selectmode="extended",
            exportselection=False,
        )
        selected_files_scrollbar = ttk.Scrollbar(
            selected_files_frame,
            orient="vertical",
            command=self.selected_files_listbox.yview,
        )
        self.selected_files_listbox.configure(
            yscrollcommand=selected_files_scrollbar.set
        )
        self.selected_files_listbox.grid(row=0, column=0, sticky="ew")
        selected_files_scrollbar.grid(row=0, column=1, sticky="ns")
        self._refresh_selected_files_display()

        output_dir_button = ttk.Button(
            main, text="Select output folder", command=self.select_output_dir
        )
        output_dir_button.grid(row=4, column=0, sticky="w", pady=(0, 10))

        ttk.Label(main, text="Output folder:").grid(
            row=5, column=0, sticky="nw", pady=(0, 10)
        )
        output_dir_label = ttk.Label(
            main, textvariable=self.output_dir_var, wraplength=500
        )
        output_dir_label.grid(row=5, column=1, columnspan=2, sticky="ew", pady=(0, 10))
        self.wrap_labels.append(output_dir_label)

        terms_button = ttk.Button(
            main,
            text="Select sensitive terms file",
            command=self.select_sensitive_terms_file,
        )
        terms_button.grid(row=6, column=0, sticky="w", pady=(0, 10))

        ttk.Label(main, text="Sensitive terms:").grid(
            row=7, column=0, sticky="nw", pady=(0, 10)
        )
        terms_label = ttk.Label(
            main, textvariable=self.sensitive_terms_var, wraplength=500
        )
        terms_label.grid(row=7, column=1, columnspan=2, sticky="ew", pady=(0, 10))
        self.wrap_labels.append(terms_label)

        ttk.Checkbutton(
            main,
            text="Use local NER if available",
            variable=self.use_ner_var,
            command=self._reset_batch_display,
        ).grid(row=8, column=0, columnspan=3, sticky="w", pady=(0, 10))

        ttk.Checkbutton(
            main,
            text="Use local LLM review if available",
            variable=self.use_llm_review_var,
            command=self._reset_batch_display,
        ).grid(row=9, column=0, columnspan=3, sticky="w", pady=(0, 10))

        ttk.Label(main, text="LLM model:").grid(
            row=10, column=0, sticky="w", pady=(0, 10)
        )
        llm_model_frame = ttk.Frame(main)
        llm_model_frame.grid(row=10, column=1, columnspan=2, sticky="ew", pady=(0, 10))
        llm_model_frame.columnconfigure(0, weight=1)
        self.llm_model_combobox = ttk.Combobox(
            llm_model_frame,
            textvariable=self.llm_model_var,
            state="readonly",
            values=(),
        )
        self.llm_model_combobox.grid(row=0, column=0, sticky="ew")
        ttk.Button(
            llm_model_frame,
            text="Refresh models",
            command=self.refresh_llm_models,
        ).grid(row=0, column=1, sticky="e", padx=(8, 0))

        llm_model_hint_label = ttk.Label(
            main,
            textvariable=self.llm_model_hint_var,
            wraplength=500,
        )
        llm_model_hint_label.grid(
            row=11, column=1, columnspan=2, sticky="ew", pady=(0, 10)
        )
        self.wrap_labels.append(llm_model_hint_label)

        ttk.Label(main, text="PDF output:").grid(
            row=12, column=0, sticky="w", pady=(0, 10)
        )
        self.pdf_redaction_scope_combobox = ttk.Combobox(
            main,
            textvariable=self.pdf_redaction_scope_var,
            state="readonly",
            values=tuple(PDF_OUTPUT_SETTINGS_BY_LABEL.keys()),
        )
        self.pdf_redaction_scope_combobox.grid(
            row=12, column=1, columnspan=2, sticky="ew", pady=(0, 10)
        )

        pdf_output_hint_label = ttk.Label(
            main,
            text=(
                "Recommended visual PDF keeps the original layout and applies "
                "true redaction to detected text coordinates. Image-only text "
                "may still require OCR/manual review."
            ),
            wraplength=500,
        )
        pdf_output_hint_label.grid(
            row=13, column=1, columnspan=2, sticky="ew", pady=(0, 10)
        )
        self.wrap_labels.append(pdf_output_hint_label)

        self.anonymize_button = ttk.Button(
            main,
            text="Anonymize batch",
            command=self.anonymize_selected_files,
            state="disabled",
        )
        self.anonymize_button.grid(row=14, column=0, sticky="w", pady=(0, 14))

        readiness_label = ttk.Label(
            main,
            textvariable=self.readiness_var,
            wraplength=500,
        )
        readiness_label.grid(row=14, column=1, columnspan=2, sticky="ew", pady=(0, 14))
        self.wrap_labels.append(readiness_label)

        ttk.Label(main, text="Status:").grid(
            row=15, column=0, sticky="nw", pady=(0, 10)
        )
        status_label = ttk.Label(
            main, textvariable=self.status_var, wraplength=500
        )
        status_label.grid(row=15, column=1, columnspan=2, sticky="ew", pady=(0, 10))
        self.wrap_labels.append(status_label)

        counters_frame = ttk.LabelFrame(main, text="Category counters", padding=10)
        counters_frame.grid(
            row=16, column=0, columnspan=3, sticky="ew", pady=(0, 14)
        )
        counters_frame.columnconfigure(0, weight=1)
        ttk.Label(
            counters_frame,
            textvariable=self.counters_var,
            justify="left",
        ).grid(row=0, column=0, sticky="w")

        audit_frame = ttk.LabelFrame(
            main, text="Post-anonymization audit", padding=10
        )
        audit_frame.grid(
            row=17, column=0, columnspan=3, sticky="ew", pady=(0, 14)
        )
        audit_frame.columnconfigure(0, weight=1)
        ttk.Label(
            audit_frame,
            textvariable=self.audit_var,
            justify="left",
        ).grid(row=0, column=0, sticky="w")

        ttk.Label(main, text="Output files:").grid(
            row=18, column=0, sticky="nw", pady=(0, 10)
        )
        output_label = ttk.Label(
            main, textvariable=self.output_path_var, wraplength=500
        )
        output_label.grid(row=18, column=1, columnspan=2, sticky="ew", pady=(0, 10))
        self.wrap_labels.append(output_label)

        ttk.Label(main, text="Reports:").grid(
            row=19, column=0, sticky="nw", pady=(0, 10)
        )
        report_label = ttk.Label(
            main, textvariable=self.report_path_var, wraplength=500
        )
        report_label.grid(row=19, column=1, columnspan=2, sticky="ew", pady=(0, 10))
        self.wrap_labels.append(report_label)

        self._build_review_section(main, row=20)

        warning_label = ttk.Label(
            main,
            text=MANUAL_REVIEW_WARNING,
            foreground="#9a3412",
            wraplength=580,
        )
        warning_label.grid(row=21, column=0, columnspan=3, sticky="w", pady=(4, 0))
        self.wrap_labels.append(warning_label)

        main.bind("<Configure>", self._update_wrap_lengths, add="+")
        self._bind_mousewheel_recursively(main)
        self.refresh_llm_models()

    def _bind_mousewheel_recursively(self, widget: tk.Widget) -> None:
        widget.bind("<MouseWheel>", self._on_mousewheel, add="+")
        widget.bind("<Button-4>", self._on_mousewheel, add="+")
        widget.bind("<Button-5>", self._on_mousewheel, add="+")
        for child in widget.winfo_children():
            self._bind_mousewheel_recursively(child)

    def _on_mousewheel(self, event: tk.Event) -> str | None:
        if self.scroll_canvas is None:
            return None

        units = mousewheel_scroll_units(event)
        if units:
            self.scroll_canvas.yview_scroll(units, "units")
            return "break"
        return None

    def _update_wrap_lengths(self, event: tk.Event) -> None:
        wrap_length = max(360, int(getattr(event, "width", WINDOW_MIN_WIDTH)) - 220)
        for label in self.wrap_labels:
            label.configure(wraplength=wrap_length)

    def _reset_batch_display(self) -> None:
        self.counters_var.set(format_counters({}))
        self.audit_var.set(format_batch_audit_result(None))
        self.output_path_var.set("No outputs yet.")
        self.report_path_var.set("No reports yet.")

    def refresh_llm_models(self) -> None:
        status, models = list_installed_models()
        values, selected_model, hint = format_llm_model_selector_state(status, models)
        self.llm_model_hint_var.set(hint)

        if self.llm_model_combobox is not None:
            self.llm_model_combobox.configure(values=values)
            if values:
                self.llm_model_combobox.state(["readonly", "!disabled"])
            else:
                self.llm_model_combobox.state(["disabled"])

        current_model = self.llm_model_var.get()
        if current_model in values:
            return
        self.llm_model_var.set(selected_model)

    def _refresh_selected_files_display(self) -> None:
        self.selected_file_count_var.set(
            format_selected_file_count(len(self.selected_paths))
        )
        self.selected_path_var.set(
            format_safe_path_list(self.selected_paths, "No files selected.")
        )
        if self.selected_files_listbox is None:
            return

        self.selected_files_listbox.delete(0, tk.END)
        for path in self.selected_paths:
            self.selected_files_listbox.insert(tk.END, path.name)

    def _set_ready_status_for_selected_files(self) -> None:
        count = len(self.selected_paths)
        if count == 0:
            self.status_var.set("Add at least one input file.")
            return

        file_label = _file_word(count)
        if self.output_dir is None:
            self.status_var.set(
                f"Selected {count} {file_label}. Select an output folder next."
            )
            return

        self.status_var.set(
            f"Selected {count} {file_label}. Ready to anonymize into the output folder."
        )

    def select_file(self) -> None:
        file_paths = filedialog.askopenfilenames(
            title="Select files",
            filetypes=[
                ("Supported files", "*.txt *.docx *.pdf *.png *.jpg *.jpeg *.tif *.tiff"),
                ("TXT files", "*.txt"),
                ("DOCX files", "*.docx"),
                ("PDF files", "*.pdf"),
                ("Image files", "*.png *.jpg *.jpeg *.tif *.tiff"),
                ("All files", "*.*"),
            ],
        )
        if not file_paths:
            return

        new_paths = [Path(file_path) for file_path in file_paths]
        added_count = 0
        for path in new_paths:
            if path not in self.selected_paths:
                self.selected_paths.append(path)
                added_count += 1

        self._refresh_selected_files_display()
        self._reset_batch_display()
        total_count = len(self.selected_paths)
        added_label = _file_word(added_count)
        total_label = _file_word(total_count)
        if added_count:
            status_text = (
                f"Added {added_count} {added_label} to the GUI list. "
                f"Total selected: {total_count} {total_label}. "
                "Original files remain unchanged."
            )
        else:
            status_text = "Selected files were already in the GUI list."
        if self.output_dir is None:
            status_text += " Select an output folder next."
        else:
            status_text += " Ready to anonymize into the output folder."
        self.status_var.set(status_text)
        self._update_anonymize_button_state()

    def clear_selected_files(self) -> None:
        self.selected_paths = []
        self._refresh_selected_files_display()
        self._reset_batch_display()
        self.status_var.set(
            "Cleared the selected files from the GUI list. No files were deleted."
        )
        self._update_anonymize_button_state()

    def remove_selected_files(self) -> None:
        if self.selected_files_listbox is None:
            return

        selected_indexes = self.selected_files_listbox.curselection()
        if not selected_indexes:
            self.status_var.set("Select one or more files in the list to remove.")
            return

        removed_count = len(selected_indexes)
        self.selected_paths = remove_paths_by_indexes(
            self.selected_paths,
            tuple(int(index) for index in selected_indexes),
        )
        self._refresh_selected_files_display()
        self._reset_batch_display()
        file_label = _file_word(removed_count)
        self.status_var.set(
            f"Removed {removed_count} {file_label} from the GUI list. "
            "No files were deleted."
        )
        self._update_anonymize_button_state()

    def select_output_dir(self) -> None:
        folder_path = filedialog.askdirectory(title="Select output folder")
        if not folder_path:
            return

        self.output_dir = Path(folder_path)
        folder_name = self.output_dir.name or "selected folder"
        self.output_dir_var.set(f"Output folder selected: {folder_name}")
        self._set_ready_status_for_selected_files()
        self._update_anonymize_button_state()

    def select_sensitive_terms_file(self) -> None:
        file_path = filedialog.askopenfilename(
            title="Select sensitive terms file",
            filetypes=[
                ("TXT files", "*.txt"),
                ("All files", "*.*"),
            ],
        )
        if not file_path:
            return

        self.sensitive_terms_path = Path(file_path)
        self.sensitive_terms_var.set(
            "Dictionary status: selected; will load during anonymization"
        )
        if self.selected_paths and self.output_dir is not None:
            self.status_var.set(
                "Sensitive terms file selected. Ready to anonymize into the output folder."
            )
        elif self.selected_paths:
            self.status_var.set(
                "Sensitive terms file selected. Select an output folder next."
            )
        else:
            self.status_var.set(
                "Sensitive terms file selected. Add input files and select an output folder."
            )
        self._update_anonymize_button_state()

    def _update_anonymize_button_state(self) -> None:
        self.readiness_var.set(
            format_anonymize_readiness(
                len(self.selected_paths),
                self.output_dir is not None,
            )
        )
        if self.anonymize_button is None:
            return
        if self.selected_paths and self.output_dir is not None:
            self.anonymize_button.state(["!disabled"])
        else:
            self.anonymize_button.state(["disabled"])

    def anonymize_selected_files(self) -> None:
        if not self.selected_paths:
            self.status_var.set("Select input files before anonymizing.")
            return
        if self.output_dir is None:
            self.status_var.set("Select an output folder before anonymizing.")
            return

        file_label = _file_word(len(self.selected_paths))
        self.status_var.set(
            f"Anonymizing {len(self.selected_paths)} selected {file_label}..."
        )
        self.root.update_idletasks()

        def update_processing_status(index: int, total: int, path: Path) -> None:
            self.status_var.set(format_processing_status(index, total, path))
            self.root.update_idletasks()

        try:
            batch_result = anonymize_batch(
                self.selected_paths,
                self.output_dir,
                sensitive_terms_path=self.sensitive_terms_path,
                use_ner=self.use_ner_var.get(),
                use_llm_review=self.use_llm_review_var.get(),
                llm_model_name=self.llm_model_var.get(),
                pdf_redaction_scope=pdf_redaction_scope_from_gui_label(
                    self.pdf_redaction_scope_var.get()
                ),
                pdf_output_mode=pdf_output_mode_from_gui_label(
                    self.pdf_redaction_scope_var.get()
                ),
                progress_callback=update_processing_status,
            )
        except Exception:
            self.status_var.set(
                "Error: batch failed. Check selected files and output folder."
            )
            self.counters_var.set(format_counters({}))
            self.audit_var.set(format_batch_audit_result(None))
            self.output_path_var.set("No outputs created.")
            self.report_path_var.set("No reports created.")
            return

        output_names = [
            str(result["output_name"])
            for result in batch_result.results
            if result.get("status") == "success" and result.get("output_name")
        ]
        report_names = [
            str(result["report_name"])
            for result in batch_result.results
            if result.get("status") == "success" and result.get("report_name")
        ]
        dictionary_status = format_batch_dictionary_result(
            batch_result,
            self.sensitive_terms_path,
        )
        self.status_var.set(format_batch_status(batch_result))
        self.counters_var.set(format_counters(batch_result.counters))
        self.audit_var.set(format_batch_audit_result(batch_result))
        self.sensitive_terms_var.set(dictionary_status)
        self.output_path_var.set(
            format_safe_path_list(
                [Path(name) for name in output_names],
                "No outputs created.",
            )
        )
        reports_text = format_safe_path_list(
            [Path(name) for name in report_names],
            "No per-file reports.",
        )
        self.report_path_var.set(
            f"{reports_text}; batch summary: {batch_result.summary_path.name}; "
            f"batch review checklist: {batch_result.review_checklist_path.name}"
            if batch_result.review_checklist_path is not None
            else f"{reports_text}; batch summary: {batch_result.summary_path.name}"
        )
        self.review_dir = self.output_dir
        self.review_dir_var.set(f"Review folder selected: {self.output_dir.name}")
        self.load_review_folder()

    def _build_review_section(self, main: ttk.Frame, row: int) -> None:
        review_frame = ttk.LabelFrame(main, text="Manual review workflow", padding=10)
        review_frame.grid(row=row, column=0, columnspan=3, sticky="ew", pady=(0, 14))
        review_frame.columnconfigure(1, weight=1)

        ttk.Button(
            review_frame,
            text="Select review folder",
            command=self.select_review_output_dir,
        ).grid(row=0, column=0, sticky="w", pady=(0, 8))

        review_dir_label = ttk.Label(
            review_frame,
            textvariable=self.review_dir_var,
            wraplength=500,
        )
        review_dir_label.grid(row=0, column=1, columnspan=3, sticky="ew", pady=(0, 8))
        self.wrap_labels.append(review_dir_label)

        review_tree_frame = ttk.Frame(review_frame)
        review_tree_frame.grid(row=1, column=0, columnspan=4, sticky="ew", pady=(0, 8))
        review_tree_frame.columnconfigure(0, weight=1)
        self.review_tree = ttk.Treeview(
            review_tree_frame,
            columns=("output", "risk", "checklist", "report", "status"),
            show="headings",
            height=5,
            selectmode="extended",
        )
        review_tree_scrollbar = ttk.Scrollbar(
            review_tree_frame,
            orient="vertical",
            command=self.review_tree.yview,
        )
        self.review_tree.configure(yscrollcommand=review_tree_scrollbar.set)
        self.review_tree.heading("output", text="Output")
        self.review_tree.heading("risk", text="Risk")
        self.review_tree.heading("checklist", text="Checklist")
        self.review_tree.heading("report", text="Report")
        self.review_tree.heading("status", text="Manual status")
        self.review_tree.column("output", width=190, anchor="w")
        self.review_tree.column("risk", width=90, anchor="w")
        self.review_tree.column("checklist", width=170, anchor="w")
        self.review_tree.column("report", width=150, anchor="w")
        self.review_tree.column("status", width=120, anchor="w")
        self.review_tree.grid(row=0, column=0, sticky="ew")
        review_tree_scrollbar.grid(row=0, column=1, sticky="ns")

        ttk.Combobox(
            review_frame,
            textvariable=self.review_status_choice_var,
            values=REVIEW_STATUSES,
            state="readonly",
            width=16,
        ).grid(row=2, column=0, sticky="w", pady=(0, 8))

        ttk.Button(
            review_frame,
            text="Set selected status",
            command=self.set_selected_review_status,
        ).grid(row=2, column=1, sticky="w", padx=(8, 0), pady=(0, 8))

        ttk.Button(
            review_frame,
            text="Save review status",
            command=self.save_review_status,
        ).grid(row=2, column=2, sticky="w", padx=(8, 0), pady=(0, 8))

        ttk.Button(
            review_frame,
            text="Export approved",
            command=self.export_approved_review_files,
        ).grid(row=2, column=3, sticky="w", padx=(8, 0), pady=(0, 8))

        ttk.Button(
            review_frame,
            text="Open selected output",
            command=self.open_selected_review_output,
        ).grid(row=3, column=0, sticky="w", pady=(0, 8))

        ttk.Button(
            review_frame,
            text="Open matching report",
            command=self.open_selected_review_report,
        ).grid(row=3, column=1, sticky="w", padx=(8, 0), pady=(0, 8))

        ttk.Button(
            review_frame,
            text="Open review checklist",
            command=self.open_selected_review_checklist,
        ).grid(row=3, column=2, sticky="w", padx=(8, 0), pady=(0, 8))

        review_warning_label = ttk.Label(
            review_frame,
            text=(
                "Approved is a manual user decision; the application does not "
                "guarantee complete anonymization."
            ),
            foreground="#9a3412",
            wraplength=640,
        )
        review_warning_label.grid(
            row=4,
            column=0,
            columnspan=4,
            sticky="w",
            pady=(0, 6),
        )
        self.wrap_labels.append(review_warning_label)

        review_status_label = ttk.Label(
            review_frame,
            textvariable=self.review_status_var,
            wraplength=640,
        )
        review_status_label.grid(row=5, column=0, columnspan=4, sticky="ew")
        self.wrap_labels.append(review_status_label)

    def select_review_output_dir(self) -> None:
        folder_path = filedialog.askdirectory(title="Select output folder for review")
        if not folder_path:
            return

        self.review_dir = Path(folder_path)
        folder_name = self.review_dir.name or "selected folder"
        self.review_dir_var.set(f"Review folder selected: {folder_name}")
        self.load_review_folder()

    def load_review_folder(self) -> None:
        if self.review_dir is None:
            self.review_status_var.set("Select an output folder for review first.")
            return

        try:
            workspace = load_review_workspace(self.review_dir)
        except OSError:
            self.review_items = []
            self.review_batch_summary_names = []
            self._populate_review_tree()
            self.review_status_var.set("Could not read the selected review folder.")
            return

        self.review_items = workspace.items
        self.review_batch_summary_names = workspace.batch_summary_names
        self._populate_review_tree()
        self.review_status_var.set(
            f"Detected {len(self.review_items)} anonymized output file(s) for review."
        )

    def _populate_review_tree(self) -> None:
        if self.review_tree is None:
            return

        for item_id in self.review_tree.get_children():
            self.review_tree.delete(item_id)

        for item in self.review_items:
            self.review_tree.insert(
                "",
                "end",
                iid=item.output_name,
                values=(
                    item.output_name,
                    item.risk_level or "unknown",
                    item.checklist_name or "missing",
                    item.report_name or "missing",
                    item.status,
                ),
            )

    def set_selected_review_status(self) -> None:
        if self.review_tree is None:
            return

        selected_items = self.review_tree.selection()
        if not selected_items:
            self.review_status_var.set(
                "Select one or more review items before setting status."
            )
            return

        selected_status = self.review_status_choice_var.get()
        statuses_by_output_name = {
            str(output_name): selected_status for output_name in selected_items
        }
        try:
            self.review_items = apply_review_statuses(
                self.review_items,
                statuses_by_output_name,
            )
        except ValueError:
            self.review_status_var.set("Select a valid manual review status.")
            return

        self._populate_review_tree()
        self.review_tree.selection_set(*[str(item) for item in selected_items])
        file_label = _file_word(len(selected_items))
        self.review_status_var.set(
            f"Manual status set to {selected_status} for "
            f"{len(selected_items)} {file_label}."
        )

    def _get_single_selected_review_item(self) -> ReviewItem | None:
        if self.review_tree is None:
            return None

        selected_items = self.review_tree.selection()
        if len(selected_items) != 1:
            self.review_status_var.set(
                "Select exactly one review item before opening a file."
            )
            return None

        output_name = str(selected_items[0])
        for item in self.review_items:
            if item.output_name == output_name:
                return item

        self.review_status_var.set("Selected review item is no longer available.")
        return None

    def _open_review_file(self, file_name: str, file_label: str) -> None:
        if self.review_dir is None:
            self.review_status_var.set("Select an output folder for review first.")
            return

        safe_name = Path(file_name).name
        file_path = self.review_dir / safe_name
        if not file_path.exists():
            self.review_status_var.set(f"Missing {file_label} file: {safe_name}.")
            return

        try:
            open_path_with_default_app(file_path)
        except OSError:
            self.review_status_var.set(
                f"Could not open {file_label} file: {safe_name}."
            )
            return

        self.review_status_var.set(f"Opened {file_label} file: {safe_name}.")

    def open_selected_review_output(self) -> None:
        item = self._get_single_selected_review_item()
        if item is None:
            return

        if self.review_dir is None:
            self.review_status_var.set("Select an output folder for review first.")
            return

        preferred_path = preferred_review_output_path(self.review_dir, item.output_name)
        self._open_review_file(preferred_path.name, "anonymized output")

    def open_selected_review_report(self) -> None:
        item = self._get_single_selected_review_item()
        if item is None:
            return
        if item.report_name is None:
            self.review_status_var.set(
                f"No matching report detected for {item.output_name}."
            )
            return

        self._open_review_file(item.report_name, "report")

    def open_selected_review_checklist(self) -> None:
        item = self._get_single_selected_review_item()
        if item is None:
            return
        if item.checklist_name is None:
            self.review_status_var.set(
                f"No matching review checklist detected for {item.output_name}."
            )
            return

        self._open_review_file(item.checklist_name, "review checklist")

    def save_review_status(self) -> None:
        if self.review_dir is None:
            self.review_status_var.set("Select an output folder for review first.")
            return
        if not self.review_items:
            self.review_status_var.set("No generated _ANON files detected for review.")
            return

        try:
            save_result = save_review_files(
                self.review_dir,
                items=self.review_items,
                batch_summary_names=self.review_batch_summary_names,
            )
        except OSError:
            self.review_status_var.set("Could not save review status files.")
            return

        completed = "yes" if save_result.manual_review_completed else "no"
        self.review_status_var.set(
            f"Saved {save_result.status_path.name} and {save_result.summary_path.name}. "
            f"Manual review completed: {completed}."
        )

    def export_approved_review_files(self) -> None:
        if self.review_dir is None:
            self.review_status_var.set("Select an output folder for review first.")
            return

        try:
            export_result = export_approved_workspace(self.review_dir)
        except FileNotFoundError:
            self.review_status_var.set(
                "Missing _REVIEW_STATUS.json. "
                "Save review status before exporting approved files."
            )
            return
        except ValueError as exc:
            message = str(exc)
            if "no approved" in message:
                self.review_status_var.set("No approved files found to export.")
            else:
                self.review_status_var.set(
                    "Approved export failed safely; no source files were modified."
                )
            return
        except OSError:
            self.review_status_var.set(
                "Approved export failed safely; no source files were modified."
            )
            return

        self.review_status_var.set(
            format_approved_export_status(
                export_result.exported_output_count,
                export_result.copied_report_count,
                len(export_result.missing_report_names),
                export_result.index_path.name,
            )
        )


def start_gui() -> None:
    """Start the Tkinter desktop application."""
    root = tk.Tk()
    AnonymizerGui(root)
    root.mainloop()


def main() -> None:
    """Run the GUI when this module is executed as a script."""
    start_gui()


if __name__ == "__main__":
    main()
