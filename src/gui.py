"""Tkinter GUI for Stage 5 single-file anonymization."""

from pathlib import Path
import tkinter as tk
from tkinter import filedialog, ttk

from anonymizer import SUPPORTED_LABELS, anonymize_file


APP_TITLE = "Local Document Anonymizer"
MANUAL_REVIEW_WARNING = (
    "Manual review required before using or sharing the anonymized result."
)


def format_counters(counters: dict[str, int]) -> str:
    """Format anonymization counters without exposing source values."""
    lines = [f"{label}: {counters.get(label, 0)}" for label in SUPPORTED_LABELS]
    lines.append(f"TOTAL: {sum(counters.values())}")
    return "\n".join(lines)


class AnonymizerGui:
    """Small Tkinter application for anonymizing one selected file."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.selected_path: Path | None = None
        self.selected_path_var = tk.StringVar(value="No file selected.")
        self.status_var = tk.StringVar(value="Select a file to begin.")
        self.counters_var = tk.StringVar(value=format_counters({}))
        self.output_path_var = tk.StringVar(value="No output yet.")
        self.anonymize_button: ttk.Button | None = None

        self._build()

    def _build(self) -> None:
        self.root.title(APP_TITLE)
        self.root.minsize(640, 420)
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

        self.anonymize_button = ttk.Button(
            main,
            text="Anonymize",
            command=self.anonymize_selected_file,
            state="disabled",
        )
        self.anonymize_button.grid(row=3, column=0, sticky="w", pady=(0, 14))

        ttk.Label(main, text="Status:").grid(
            row=4, column=0, sticky="nw", pady=(0, 10)
        )
        status_label = ttk.Label(
            main, textvariable=self.status_var, wraplength=500
        )
        status_label.grid(row=4, column=1, columnspan=2, sticky="ew", pady=(0, 10))

        counters_frame = ttk.LabelFrame(main, text="Category counters", padding=10)
        counters_frame.grid(
            row=5, column=0, columnspan=3, sticky="ew", pady=(0, 14)
        )
        counters_frame.columnconfigure(0, weight=1)
        ttk.Label(
            counters_frame,
            textvariable=self.counters_var,
            justify="left",
        ).grid(row=0, column=0, sticky="w")

        ttk.Label(main, text="Output file:").grid(
            row=6, column=0, sticky="nw", pady=(0, 10)
        )
        output_label = ttk.Label(
            main, textvariable=self.output_path_var, wraplength=500
        )
        output_label.grid(row=6, column=1, columnspan=2, sticky="ew", pady=(0, 10))

        warning_label = ttk.Label(
            main,
            text=MANUAL_REVIEW_WARNING,
            foreground="#9a3412",
            wraplength=580,
        )
        warning_label.grid(row=7, column=0, columnspan=3, sticky="w", pady=(4, 0))

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
        if self.anonymize_button is not None:
            self.anonymize_button.state(["!disabled"])

    def anonymize_selected_file(self) -> None:
        if self.selected_path is None:
            self.status_var.set("Select a file before anonymizing.")
            return

        self.status_var.set("Anonymizing selected file...")
        self.root.update_idletasks()

        try:
            output_path, counters = anonymize_file(self.selected_path)
        except Exception as exc:
            self.status_var.set(f"Error: {exc}")
            self.counters_var.set(format_counters({}))
            self.output_path_var.set("No output created.")
            return

        self.status_var.set("Completed. Review the anonymized output manually.")
        self.counters_var.set(format_counters(counters))
        self.output_path_var.set(str(output_path))


def start_gui() -> None:
    """Start the Stage 5 Tkinter desktop application."""
    root = tk.Tk()
    AnonymizerGui(root)
    root.mainloop()
