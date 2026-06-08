"""Tkinter GUI for single-file anonymization."""

from pathlib import Path
import tkinter as tk
from tkinter import filedialog, ttk

from anonymizer import SUPPORTED_LABELS, anonymize_file
from file_writers import build_report_path
from sensitive_terms import SensitiveTerm, load_sensitive_terms


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


class AnonymizerGui:
    """Small Tkinter application for anonymizing one selected file."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.selected_path: Path | None = None
        self.sensitive_terms: list[SensitiveTerm] | None = None
        self.selected_path_var = tk.StringVar(value="No file selected.")
        self.sensitive_terms_var = tk.StringVar(
            value="No sensitive terms file selected."
        )
        self.status_var = tk.StringVar(value="Select a file to begin.")
        self.counters_var = tk.StringVar(value=format_counters({}))
        self.output_path_var = tk.StringVar(value="No output yet.")
        self.report_path_var = tk.StringVar(value="No report yet.")
        self.anonymize_button: ttk.Button | None = None

        self._build()

    def _build(self) -> None:
        self.root.title(APP_TITLE)
        self.root.minsize(640, 520)
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        main = ttk.Frame(self.root, padding=16)
        main.grid(row=0, column=0, sticky="nsew")
        main.columnconfigure(1, weight=1)

        title = ttk.Label(main, text=APP_TITLE, font=("Segoe UI", 14, "bold"))
        title.grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 14))

        select_button = ttk.Button(
            main, text="Select file", command=self.select_file
        )
        select_button.grid(row=1, column=0, sticky="w", pady=(0, 10))

        ttk.Label(main, text="Selected file:").grid(
            row=2, column=0, sticky="nw", pady=(0, 10)
        )
        selected_label = ttk.Label(
            main, textvariable=self.selected_path_var, wraplength=500
        )
        selected_label.grid(row=2, column=1, columnspan=2, sticky="ew", pady=(0, 10))

        terms_button = ttk.Button(
            main,
            text="Select sensitive terms file",
            command=self.select_sensitive_terms_file,
        )
        terms_button.grid(row=3, column=0, sticky="w", pady=(0, 10))

        ttk.Label(main, text="Sensitive terms:").grid(
            row=4, column=0, sticky="nw", pady=(0, 10)
        )
        terms_label = ttk.Label(
            main, textvariable=self.sensitive_terms_var, wraplength=500
        )
        terms_label.grid(row=4, column=1, columnspan=2, sticky="ew", pady=(0, 10))

        self.anonymize_button = ttk.Button(
            main,
            text="Anonymize",
            command=self.anonymize_selected_file,
            state="disabled",
        )
        self.anonymize_button.grid(row=5, column=0, sticky="w", pady=(0, 14))

        ttk.Label(main, text="Status:").grid(
            row=6, column=0, sticky="nw", pady=(0, 10)
        )
        status_label = ttk.Label(
            main, textvariable=self.status_var, wraplength=500
        )
        status_label.grid(row=6, column=1, columnspan=2, sticky="ew", pady=(0, 10))

        counters_frame = ttk.LabelFrame(main, text="Category counters", padding=10)
        counters_frame.grid(
            row=7, column=0, columnspan=3, sticky="ew", pady=(0, 14)
        )
        counters_frame.columnconfigure(0, weight=1)
        ttk.Label(
            counters_frame,
            textvariable=self.counters_var,
            justify="left",
        ).grid(row=0, column=0, sticky="w")

        ttk.Label(main, text="Output file:").grid(
            row=8, column=0, sticky="nw", pady=(0, 10)
        )
        output_label = ttk.Label(
            main, textvariable=self.output_path_var, wraplength=500
        )
        output_label.grid(row=8, column=1, columnspan=2, sticky="ew", pady=(0, 10))

        ttk.Label(main, text="Report file:").grid(
            row=9, column=0, sticky="nw", pady=(0, 10)
        )
        report_label = ttk.Label(
            main, textvariable=self.report_path_var, wraplength=500
        )
        report_label.grid(row=9, column=1, columnspan=2, sticky="ew", pady=(0, 10))

        warning_label = ttk.Label(
            main,
            text=MANUAL_REVIEW_WARNING,
            foreground="#9a3412",
            wraplength=580,
        )
        warning_label.grid(row=10, column=0, columnspan=3, sticky="w", pady=(4, 0))

    def select_file(self) -> None:
        file_path = filedialog.askopenfilename(
            title="Select file",
            filetypes=[
                ("Supported files", "*.txt *.docx *.pdf"),
                ("TXT files", "*.txt"),
                ("DOCX files", "*.docx"),
                ("PDF files", "*.pdf"),
                ("All files", "*.*"),
            ],
        )
        if not file_path:
            return

        self.selected_path = Path(file_path)
        self.selected_path_var.set(str(self.selected_path))
        self.status_var.set("Ready to anonymize selected file.")
        self.counters_var.set(format_counters({}))
        self.output_path_var.set("No output yet.")
        self.report_path_var.set("No report yet.")
        if self.anonymize_button is not None:
            self.anonymize_button.state(["!disabled"])

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

        try:
            self.sensitive_terms = load_sensitive_terms(file_path)
        except ValueError as exc:
            self.sensitive_terms = None
            self.sensitive_terms_var.set("No valid sensitive terms file selected.")
            self.status_var.set(f"Sensitive terms file error: {exc}")
            return
        except Exception:
            self.sensitive_terms = None
            self.sensitive_terms_var.set("No valid sensitive terms file selected.")
            self.status_var.set("Sensitive terms file error: could not load file.")
            return

        self.sensitive_terms_var.set("Sensitive terms file selected.")
        self.status_var.set("Ready to anonymize with selected sensitive terms file.")

    def anonymize_selected_file(self) -> None:
        if self.selected_path is None:
            self.status_var.set("Select a file before anonymizing.")
            return

        self.status_var.set("Anonymizing selected file...")
        self.root.update_idletasks()

        try:
            output_path, counters = anonymize_file(
                self.selected_path, sensitive_terms=self.sensitive_terms
            )
        except Exception as exc:
            self.status_var.set(f"Error: {exc}")
            self.counters_var.set(format_counters({}))
            self.output_path_var.set("No output created.")
            self.report_path_var.set("No report created.")
            return

        self.status_var.set("Completed. Review the anonymized output manually.")
        self.counters_var.set(format_counters(counters))
        self.output_path_var.set(str(output_path))
        self.report_path_var.set(str(build_report_path(self.selected_path)))


def start_gui() -> None:
    """Start the Tkinter desktop application."""
    root = tk.Tk()
    AnonymizerGui(root)
    root.mainloop()
