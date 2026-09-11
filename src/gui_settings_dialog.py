"""The Ustawienia (Settings) modal dialog."""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog

import customtkinter as ctk

try:
    from .environment_check import (
        ENV_ITEM_LLM,
        ENV_ITEM_NER,
        ENV_ITEM_OCR,
    )
    from .gui_helpers import (
        COLOR_ACCENT,
        COLOR_ACCENT_HOVER,
        COLOR_BG,
        COLOR_BORDER,
        COLOR_CARD,
        COLOR_ICON_IDLE,
        COLOR_OK,
        COLOR_TEXT,
        COLOR_TEXT_MUTED,
        FONT_FAMILY,
        PDF_OUTPUT_SETTINGS_BY_LABEL,
        PDF_OUTPUT_SHORT_LABELS,
        IconTooltip,
        _bring_window_to_front,
        environment_status_lookup,
        format_llm_model_selector_state,
    )
    from .llm_review import list_installed_models
except ImportError:
    from environment_check import (
        ENV_ITEM_LLM,
        ENV_ITEM_NER,
        ENV_ITEM_OCR,
    )
    from gui_helpers import (
        COLOR_ACCENT,
        COLOR_ACCENT_HOVER,
        COLOR_BG,
        COLOR_BORDER,
        COLOR_CARD,
        COLOR_ICON_IDLE,
        COLOR_OK,
        COLOR_TEXT,
        COLOR_TEXT_MUTED,
        FONT_FAMILY,
        PDF_OUTPUT_SETTINGS_BY_LABEL,
        PDF_OUTPUT_SHORT_LABELS,
        IconTooltip,
        _bring_window_to_front,
        environment_status_lookup,
        format_llm_model_selector_state,
    )
    from llm_review import list_installed_models

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .gui_app import AnonymizerApp

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


