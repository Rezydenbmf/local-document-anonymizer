"""Tkinter GUI for batch anonymization."""

from collections.abc import Mapping
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, ttk

from audit import AUDIT_CATEGORY_ORDER
from anonymizer import SUPPORTED_LABELS, BatchResult, anonymize_batch
from report import (
    DICTIONARY_STATUS_INVALID,
    DICTIONARY_STATUS_LOADED,
    DICTIONARY_STATUS_NOT_SELECTED,
)


APP_TITLE = "Local Document Anonymizer"
MANUAL_REVIEW_WARNING = (
    "Manual review required before using or sharing the anonymized result."
)


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
    return "\n".join(
        [
            "Audit statuses:",
            f"OK: {counts.get('ok', 0)}",
            f"WARNING: {counts.get('warning', 0)}",
            f"Not run: {counts.get('not run', 0)}",
        ]
    )


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
        self.output_dir_var = tk.StringVar(value="No output folder selected.")
        self.sensitive_terms_var = tk.StringVar(value=format_dictionary_result(None))
        self.status_var = tk.StringVar(
            value="Select input files and an output folder to begin."
        )
        self.counters_var = tk.StringVar(value=format_counters({}))
        self.audit_var = tk.StringVar(value=format_batch_audit_result(None))
        self.output_path_var = tk.StringVar(value="No outputs yet.")
        self.report_path_var = tk.StringVar(value="No reports yet.")
        self.anonymize_button: ttk.Button | None = None

        self._build()

    def _build(self) -> None:
        self.root.title(APP_TITLE)
        self.root.minsize(680, 620)
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        main = ttk.Frame(self.root, padding=16)
        main.grid(row=0, column=0, sticky="nsew")
        main.columnconfigure(1, weight=1)

        title = ttk.Label(main, text=APP_TITLE, font=("Segoe UI", 14, "bold"))
        title.grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 14))

        select_button = ttk.Button(
            main, text="Select files", command=self.select_file
        )
        select_button.grid(row=1, column=0, sticky="w", pady=(0, 10))

        ttk.Label(main, text="Selected files:").grid(
            row=2, column=0, sticky="nw", pady=(0, 10)
        )
        selected_label = ttk.Label(
            main, textvariable=self.selected_path_var, wraplength=500
        )
        selected_label.grid(row=2, column=1, columnspan=2, sticky="ew", pady=(0, 10))

        output_dir_button = ttk.Button(
            main, text="Select output folder", command=self.select_output_dir
        )
        output_dir_button.grid(row=3, column=0, sticky="w", pady=(0, 10))

        ttk.Label(main, text="Output folder:").grid(
            row=4, column=0, sticky="nw", pady=(0, 10)
        )
        output_dir_label = ttk.Label(
            main, textvariable=self.output_dir_var, wraplength=500
        )
        output_dir_label.grid(row=4, column=1, columnspan=2, sticky="ew", pady=(0, 10))

        terms_button = ttk.Button(
            main,
            text="Select sensitive terms file",
            command=self.select_sensitive_terms_file,
        )
        terms_button.grid(row=5, column=0, sticky="w", pady=(0, 10))

        ttk.Label(main, text="Sensitive terms:").grid(
            row=6, column=0, sticky="nw", pady=(0, 10)
        )
        terms_label = ttk.Label(
            main, textvariable=self.sensitive_terms_var, wraplength=500
        )
        terms_label.grid(row=6, column=1, columnspan=2, sticky="ew", pady=(0, 10))

        self.anonymize_button = ttk.Button(
            main,
            text="Anonymize batch",
            command=self.anonymize_selected_files,
            state="disabled",
        )
        self.anonymize_button.grid(row=7, column=0, sticky="w", pady=(0, 14))

        ttk.Label(main, text="Status:").grid(
            row=8, column=0, sticky="nw", pady=(0, 10)
        )
        status_label = ttk.Label(
            main, textvariable=self.status_var, wraplength=500
        )
        status_label.grid(row=8, column=1, columnspan=2, sticky="ew", pady=(0, 10))

        counters_frame = ttk.LabelFrame(main, text="Category counters", padding=10)
        counters_frame.grid(
            row=9, column=0, columnspan=3, sticky="ew", pady=(0, 14)
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
            row=10, column=0, columnspan=3, sticky="ew", pady=(0, 14)
        )
        audit_frame.columnconfigure(0, weight=1)
        ttk.Label(
            audit_frame,
            textvariable=self.audit_var,
            justify="left",
        ).grid(row=0, column=0, sticky="w")

        ttk.Label(main, text="Output files:").grid(
            row=11, column=0, sticky="nw", pady=(0, 10)
        )
        output_label = ttk.Label(
            main, textvariable=self.output_path_var, wraplength=500
        )
        output_label.grid(row=11, column=1, columnspan=2, sticky="ew", pady=(0, 10))

        ttk.Label(main, text="Reports:").grid(
            row=12, column=0, sticky="nw", pady=(0, 10)
        )
        report_label = ttk.Label(
            main, textvariable=self.report_path_var, wraplength=500
        )
        report_label.grid(row=12, column=1, columnspan=2, sticky="ew", pady=(0, 10))

        warning_label = ttk.Label(
            main,
            text=MANUAL_REVIEW_WARNING,
            foreground="#9a3412",
            wraplength=580,
        )
        warning_label.grid(row=13, column=0, columnspan=3, sticky="w", pady=(4, 0))

    def select_file(self) -> None:
        file_paths = filedialog.askopenfilenames(
            title="Select files",
            filetypes=[
                ("Supported files", "*.txt *.docx *.pdf"),
                ("TXT files", "*.txt"),
                ("DOCX files", "*.docx"),
                ("PDF files", "*.pdf"),
                ("All files", "*.*"),
            ],
        )
        if not file_paths:
            return

        self.selected_paths = [Path(file_path) for file_path in file_paths]
        self.selected_path_var.set(
            format_safe_path_list(self.selected_paths, "No files selected.")
        )
        self.status_var.set("Ready to anonymize selected files.")
        self.counters_var.set(format_counters({}))
        self.audit_var.set(format_batch_audit_result(None))
        self.output_path_var.set("No outputs yet.")
        self.report_path_var.set("No reports yet.")
        self._update_anonymize_button_state()

    def select_output_dir(self) -> None:
        folder_path = filedialog.askdirectory(title="Select output folder")
        if not folder_path:
            return

        self.output_dir = Path(folder_path)
        folder_name = self.output_dir.name or "selected folder"
        self.output_dir_var.set(f"Output folder selected: {folder_name}")
        self.status_var.set("Ready to anonymize into selected output folder.")
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
        self.status_var.set("Ready to anonymize with selected sensitive terms file.")

    def _update_anonymize_button_state(self) -> None:
        if self.anonymize_button is None:
            return
        if self.selected_paths and self.output_dir is not None:
            self.anonymize_button.state(["!disabled"])
        else:
            self.anonymize_button.state(["disabled"])

    def anonymize_selected_file(self) -> None:
        self.anonymize_selected_files()

    def anonymize_selected_files(self) -> None:
        if not self.selected_paths:
            self.status_var.set("Select input files before anonymizing.")
            return
        if self.output_dir is None:
            self.status_var.set("Select an output folder before anonymizing.")
            return

        self.status_var.set("Anonymizing selected files...")
        self.root.update_idletasks()

        try:
            batch_result = anonymize_batch(
                self.selected_paths,
                self.output_dir,
                sensitive_terms_path=self.sensitive_terms_path,
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
        self.status_var.set(
            f"Completed. Files: {batch_result.input_count}; "
            f"success: {batch_result.success_count}; "
            f"errors: {batch_result.error_count}. "
            f"Batch summary: {batch_result.summary_path.name}. "
            "Review the anonymized output manually."
        )
        self.counters_var.set(format_counters(batch_result.counters))
        self.audit_var.set(format_batch_audit_result(batch_result))
        self.sensitive_terms_var.set(dictionary_status)
        self.output_path_var.set(
            ", ".join(output_names) if output_names else "No outputs created."
        )
        reports_text = ", ".join(report_names) if report_names else "No per-file reports."
        self.report_path_var.set(
            f"{reports_text}; batch summary: {batch_result.summary_path.name}"
        )


def start_gui() -> None:
    """Start the Tkinter desktop application."""
    root = tk.Tk()
    AnonymizerGui(root)
    root.mainloop()
