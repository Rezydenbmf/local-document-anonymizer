"""The Ustawienia (Settings) modal dialog."""

from __future__ import annotations

import threading
import tkinter as tk
from collections.abc import Callable
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

try:
    from .environment_check import (
        ENV_ITEM_LLM,
        ENV_ITEM_NER,
        ENV_ITEM_OCR,
        install_tesseract_language,
    )
    from .gui_helpers import (
        APPROVAL_LOCK_HINT_ID,
        COLOR_ACCENT,
        COLOR_ACCENT_HOVER,
        COLOR_ACCENT_SOFT,
        COLOR_BG,
        COLOR_BORDER,
        COLOR_CARD,
        COLOR_ICON_IDLE,
        COLOR_OK,
        COLOR_TEXT,
        COLOR_TEXT_MUTED,
        FONT_FAMILY,
        MAGIC_PEN_ACTION_LABELS_PL,
        MAGIC_PEN_BUILTIN_BINDINGS,
        MAGIC_PEN_BUTTON_LABELS_PL,
        MAGIC_PEN_BUTTONS,
        MAGIC_PEN_HINT_ID,
        MAGIC_PEN_MODE_CLASSIC,
        MAGIC_PEN_MODE_CUSTOM,
        MAGIC_PEN_MODE_DEFAULT,
        PDF_OUTPUT_SETTINGS_BY_LABEL,
        PDF_OUTPUT_SHORT_LABELS,
        IconTooltip,
        _bring_window_to_front,
        center_window_over_parent,
        environment_status_lookup,
        format_llm_model_selector_state,
        hint_is_dismissed,
        is_valid_magic_pen_bindings,
        magic_pen_bindings_description_pl,
        restore_hint,
        save_magic_pen_interaction_config,
    )
    from .llm_review import list_installed_models
    from .ocr import (
        COMMON_OCR_LANGUAGES_PL,
        list_installed_languages,
    )
except ImportError:
    from environment_check import (
        ENV_ITEM_LLM,
        ENV_ITEM_NER,
        ENV_ITEM_OCR,
        install_tesseract_language,
    )
    from gui_helpers import (
        APPROVAL_LOCK_HINT_ID,
        COLOR_ACCENT,
        COLOR_ACCENT_HOVER,
        COLOR_ACCENT_SOFT,
        COLOR_BG,
        COLOR_BORDER,
        COLOR_CARD,
        COLOR_ICON_IDLE,
        COLOR_OK,
        COLOR_TEXT,
        COLOR_TEXT_MUTED,
        FONT_FAMILY,
        MAGIC_PEN_ACTION_LABELS_PL,
        MAGIC_PEN_BUILTIN_BINDINGS,
        MAGIC_PEN_BUTTON_LABELS_PL,
        MAGIC_PEN_BUTTONS,
        MAGIC_PEN_HINT_ID,
        MAGIC_PEN_MODE_CLASSIC,
        MAGIC_PEN_MODE_CUSTOM,
        MAGIC_PEN_MODE_DEFAULT,
        PDF_OUTPUT_SETTINGS_BY_LABEL,
        PDF_OUTPUT_SHORT_LABELS,
        IconTooltip,
        _bring_window_to_front,
        center_window_over_parent,
        environment_status_lookup,
        format_llm_model_selector_state,
        hint_is_dismissed,
        is_valid_magic_pen_bindings,
        magic_pen_bindings_description_pl,
        restore_hint,
        save_magic_pen_interaction_config,
    )
    from llm_review import list_installed_models
    from ocr import (
        COMMON_OCR_LANGUAGES_PL,
        list_installed_languages,
    )

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .gui_app import AnonymizerApp

class SettingsDialog:
    """Modal settings window for advanced anonymization options."""

    def __init__(
        self,
        app: AnonymizerApp,
        initial_tab: str | None = None,
        on_saved: Callable[[], None] | None = None,
    ) -> None:
        self.app = app
        # Lets a caller outside the main window (e.g. the comparison
        # window's own gear-icon shortcut, see ComparisonWindow) react
        # once a setting that affects it - the magic pen mode, right
        # now - actually changed, without this dialog needing to know
        # anything about who opened it.
        self._on_saved = on_saved
        self.window = ctk.CTkToplevel(app.root)
        self.window.title("Ustawienia")
        center_window_over_parent(self.window, app.root, 560, 700)
        # A real, reported bug: nothing stopped this window shrinking
        # below the height its own content needs, and "Zapisz i
        # zamknij" - packed last, sharing space with the expanding
        # tabview instead of a protected footer - was the one thing
        # that got squeezed off screen. minsize is a floor; the footer
        # restructure below (packed before the tabview, side="bottom")
        # is the real fix, matching this app's own established rule
        # that whatever must always stay reachable gets packed first.
        self.window.minsize(480, 520)
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
        # Cached on the app (not recomputed fresh on every dialog open) -
        # real user report: this used to shell out to Tesseract every
        # single time Settings opened, adding a visible 3-5s stall on the
        # main thread. Refreshed for real after a language pack install
        # actually changes what's installed (see
        # _on_ocr_language_install_done).
        if app._installed_ocr_languages_cache is None:
            app._installed_ocr_languages_cache = list_installed_languages()
        self.installed_ocr_languages = app._installed_ocr_languages_cache
        self.ocr_language_installing = False
        self.ocr_language_status_label: ctk.CTkLabel | None = None
        self.ocr_language_add_var: tk.StringVar | None = None
        self.ocr_language_add_button: ctk.CTkButton | None = None
        self.detection_tab: ctk.CTkFrame | None = None
        self._ocr_language_code_by_label: dict[str, str] = {}
        self.approval_warning_status_label: ctk.CTkLabel | None = None
        self.magic_pen_hint_status_label: ctk.CTkLabel | None = None

        self.magic_pen_mode_var = tk.StringVar(value=app.magic_pen_interaction_mode)
        # A working copy, edited live by the custom-mode dropdowns and only
        # written back to app.magic_pen_custom_bindings on save - always a
        # valid button->action bijection (see is_valid_magic_pen_bindings),
        # seeded from the app's saved mapping when that's itself valid,
        # otherwise from the default mode so the custom editor never opens
        # on a broken assignment.
        self._custom_bindings: dict[str, str] = (
            dict(app.magic_pen_custom_bindings)
            if is_valid_magic_pen_bindings(app.magic_pen_custom_bindings)
            else dict(MAGIC_PEN_BUILTIN_BINDINGS[MAGIC_PEN_MODE_DEFAULT])
        )
        self._custom_binding_option_vars: dict[str, tk.StringVar] = {}
        self._custom_bindings_frame: ctk.CTkFrame | None = None

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

        # Packed before the tabview and pinned to the bottom, so it
        # always claims its own space and can never be squeezed off a
        # short window - the same "protected footer" pattern this app
        # already uses for the main screen's "Anonimizuj" action bar.
        ctk.CTkButton(
            self.window,
            text="Zapisz i zamknij",
            height=42,
            corner_radius=8,
            fg_color=COLOR_ACCENT,
            hover_color=COLOR_ACCENT_HOVER,
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
            command=self._save_and_close,
        ).pack(side="bottom", fill="x", padx=20, pady=16)

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

        self.detection_tab = tabview.add("Wykrywanie danych")
        self._build_detection_tab(self.detection_tab)
        self._build_pdf_tab(tabview.add("Dokumenty PDF"))
        self._build_dictionary_tab(tabview.add("Słownik"))
        self._build_general_tab(tabview.add("Ogólne"))
        if initial_tab is not None:
            try:
                tabview.set(initial_tab)
            except ValueError:
                pass

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
            disabled=True,
            disabled_note="Jeszcze niedostępne w tej wersji rozwojowej - w przygotowaniu",
        )
        self._build_ocr_language_section(tab)

    def _refresh_detection_tab(self) -> None:
        """Rebuild the "Wykrywanie danych" tab in place after a language
        pack finishes installing, so the status dot and the "Dograj"
        dropdown reflect what's actually installed now rather than what
        was true when the dialog first opened."""
        if self.detection_tab is None or not self.detection_tab.winfo_exists():
            return
        for widget in self.detection_tab.winfo_children():
            widget.destroy()
        self._build_detection_tab(self.detection_tab)

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
        self._build_magic_pen_mode_section(tab)
        self.approval_warning_status_label = self._build_hint_restore_row(
            tab,
            title="Ostrzeżenie przy zatwierdzaniu",
            hint_id=APPROVAL_LOCK_HINT_ID,
            shown_text="Widoczne przy każdym zatwierdzaniu",
        )
        self.magic_pen_hint_status_label = self._build_hint_restore_row(
            tab,
            title="Podpowiedź o edycji dokumentu",
            hint_id=MAGIC_PEN_HINT_ID,
            shown_text="Widoczna przy pierwszym otwarciu edytowalnego dokumentu",
        )

    def _build_magic_pen_mode_section(self, parent: ctk.CTkFrame) -> None:
        """Tryb interakcji magic pena: which mouse button marks, erases,
        or pans - "Domyślny" gives each action its own button, "Klasyczny"
        keeps this app's original LPM=mark/PPM=erase scheme and only adds
        middle=pan, "Niestandardowy" lets the user assign the three
        themselves via the dropdowns _build_custom_bindings_rows reveals
        below the radio buttons.
        """
        # A highlighted card, not the plain _section_frame every toggle
        # around it uses - per direct feedback this section "blended in
        # too much" with simple on/off settings, even though it is a
        # 3-way mode picker with its own sub-rows. Same accent-card
        # treatment as the comparison window's category picker
        # (gui_app.py's "Kategorie do anonimizacji").
        section = ctk.CTkFrame(
            parent,
            corner_radius=10,
            fg_color=COLOR_ACCENT_SOFT,
            border_width=1,
            border_color=COLOR_ACCENT,
        )
        section.pack(fill="x", pady=6)
        inner = ctk.CTkFrame(section, fg_color="transparent")
        inner.pack(fill="x", padx=14, pady=12)
        ctk.CTkLabel(
            inner,
            text="🖱 Tryb interakcji magic pena",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
            text_color=COLOR_TEXT,
            anchor="w",
        ).pack(fill="x", pady=(0, 2))
        ctk.CTkLabel(
            inner,
            text="Co robi lewy, prawy i środkowy przycisk myszy w oknie edycji",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            text_color=COLOR_TEXT_MUTED,
            anchor="w",
        ).pack(fill="x", pady=(0, 8))

        mode_options = (
            (MAGIC_PEN_MODE_DEFAULT, "Domyślny", MAGIC_PEN_BUILTIN_BINDINGS[MAGIC_PEN_MODE_DEFAULT]),
            (MAGIC_PEN_MODE_CLASSIC, "Klasyczny", MAGIC_PEN_BUILTIN_BINDINGS[MAGIC_PEN_MODE_CLASSIC]),
            (MAGIC_PEN_MODE_CUSTOM, "Niestandardowy", None),
        )
        for mode_value, mode_label, bindings in mode_options:
            row = ctk.CTkFrame(inner, fg_color="transparent")
            row.pack(fill="x", pady=2)
            ctk.CTkRadioButton(
                row,
                text=mode_label,
                value=mode_value,
                variable=self.magic_pen_mode_var,
                font=ctk.CTkFont(family=FONT_FAMILY, size=11),
                text_color=COLOR_TEXT,
                command=self._on_magic_pen_mode_changed,
            ).pack(side="left")
            if bindings is not None:
                ctk.CTkLabel(
                    row,
                    text=magic_pen_bindings_description_pl(bindings),
                    font=ctk.CTkFont(family=FONT_FAMILY, size=10),
                    text_color=COLOR_TEXT_MUTED,
                    anchor="w",
                ).pack(side="left", padx=(10, 0))

        self._custom_bindings_frame = ctk.CTkFrame(inner, fg_color="transparent")
        self._build_custom_bindings_rows(self._custom_bindings_frame)
        self._update_custom_bindings_visibility()

    def _build_custom_bindings_rows(self, parent: ctk.CTkFrame) -> None:
        self._custom_binding_option_vars = {}
        action_labels = list(MAGIC_PEN_ACTION_LABELS_PL.values())
        label_to_action = {label: action for action, label in MAGIC_PEN_ACTION_LABELS_PL.items()}
        for button in MAGIC_PEN_BUTTONS:
            row = ctk.CTkFrame(parent, fg_color="transparent")
            row.pack(fill="x", pady=3)
            ctk.CTkLabel(
                row,
                text=MAGIC_PEN_BUTTON_LABELS_PL[button],
                font=ctk.CTkFont(family=FONT_FAMILY, size=11),
                text_color=COLOR_TEXT,
                width=110,
                anchor="w",
            ).pack(side="left")
            current_action = self._custom_bindings[button]
            option_var = tk.StringVar(value=MAGIC_PEN_ACTION_LABELS_PL[current_action])
            self._custom_binding_option_vars[button] = option_var
            ctk.CTkOptionMenu(
                row,
                values=action_labels,
                variable=option_var,
                fg_color=COLOR_BG,
                button_color=COLOR_ACCENT,
                button_hover_color=COLOR_ACCENT_HOVER,
                text_color=COLOR_TEXT,
                font=ctk.CTkFont(family=FONT_FAMILY, size=11),
                command=lambda label, b=button: self._on_custom_binding_changed(
                    b, label_to_action[label]
                ),
            ).pack(side="left")

    def _on_custom_binding_changed(self, button: str, new_action: str) -> None:
        """Keep self._custom_bindings a valid bijection: giving ``button``
        an action some other button already has swaps the two, rather
        than leaving that other action with no button (or two buttons
        sharing one action) - so the mapping never needs an explicit
        "invalid, fix it" error state.
        """
        old_action = self._custom_bindings[button]
        if new_action == old_action:
            return
        other_button = next(
            b for b, a in self._custom_bindings.items() if a == new_action
        )
        self._custom_bindings[button] = new_action
        self._custom_bindings[other_button] = old_action
        self._custom_binding_option_vars[other_button].set(
            MAGIC_PEN_ACTION_LABELS_PL[old_action]
        )

    def _on_magic_pen_mode_changed(self) -> None:
        self._update_custom_bindings_visibility()

    def _update_custom_bindings_visibility(self) -> None:
        if self._custom_bindings_frame is None:
            return
        if self.magic_pen_mode_var.get() == MAGIC_PEN_MODE_CUSTOM:
            self._custom_bindings_frame.pack(fill="x", pady=(4, 0))
        else:
            self._custom_bindings_frame.pack_forget()

    def _build_hint_restore_row(
        self, parent: ctk.CTkFrame, *, title: str, hint_id: str, shown_text: str
    ) -> ctk.CTkLabel:
        """A "bring it back" row for a one-time hint/warning dismissed via
        its own "Nie pokazuj ponownie" checkbox - that checkbox has no
        other way to be undone, per direct user feedback that a
        permanently dismissible one-way hint still needs a way back.
        Shared by every such hint in the app (see APPROVAL_LOCK_HINT_ID,
        MAGIC_PEN_HINT_ID in gui_helpers.py) instead of one copy-pasted
        section per hint. Returns the status label so a later refresh
        (see _restore_hint) has something to update.
        """
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
        status_label = ctk.CTkLabel(
            text_col,
            text=self._hint_restore_status_text(hint_id, shown_text),
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            text_color=COLOR_TEXT_MUTED,
            anchor="w",
        )
        status_label.pack(fill="x")
        ctk.CTkButton(
            row,
            text="Przywróć",
            width=90,
            height=28,
            corner_radius=8,
            fg_color="transparent",
            border_width=1,
            border_color=COLOR_BORDER,
            hover_color=COLOR_ICON_IDLE,
            text_color=COLOR_TEXT,
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            command=lambda: self._restore_hint(hint_id, shown_text, status_label),
        ).pack(side="right")
        return status_label

    @staticmethod
    def _hint_restore_status_text(hint_id: str, shown_text: str) -> str:
        if hint_is_dismissed(hint_id):
            return "Ukryte (zaznaczono \"Nie pokazuj ponownie\")"
        return shown_text

    def _restore_hint(
        self, hint_id: str, shown_text: str, status_label: ctk.CTkLabel
    ) -> None:
        restore_hint(hint_id)
        status_label.configure(text=self._hint_restore_status_text(hint_id, shown_text))

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
        disabled: bool = False,
        disabled_note: str | None = None,
    ) -> None:
        """``disabled`` locks the switch off (the variable already holds
        ``False`` for anything built this way) for a feature that exists
        in the code but has not been tested enough to offer yet - e.g.
        the alpha build's local-LLM review. ``disabled_note`` replaces
        the subtitle with a short explanation instead of the normal
        description, so it reads as "not yet" rather than "broken"."""
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
            text_color=COLOR_TEXT_MUTED if disabled else COLOR_TEXT,
            anchor="w",
        ).pack(side="left", fill="x")
        if disabled:
            ctk.CTkLabel(
                title_row,
                text="wkrótce",
                font=ctk.CTkFont(family=FONT_FAMILY, size=10, weight="bold"),
                text_color=COLOR_ACCENT,
                anchor="w",
            ).pack(side="left", padx=(8, 0))
        ctk.CTkLabel(
            text_col,
            text=disabled_note if disabled and disabled_note else subtitle,
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            text_color=COLOR_TEXT_MUTED,
            anchor="w",
        ).pack(fill="x")
        ctk.CTkSwitch(
            row,
            text="",
            variable=variable,
            progress_color=COLOR_ACCENT,
            state="disabled" if disabled else "normal",
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

    def _installed_ocr_language_names(self) -> str:
        if not self.installed_ocr_languages:
            return "Nie wykryto żadnego zainstalowanego języka."
        names = ", ".join(
            COMMON_OCR_LANGUAGES_PL.get(code, code)
            for code in self.installed_ocr_languages
        )
        return f"Aktualnie obsługiwane języki: {names}."

    def _build_ocr_language_section(self, parent: ctk.CTkFrame) -> None:
        """OCR status plus language-pack management - polski is this
        app's baseline OCR language (see ocr.PRIMARY_OCR_LANGUAGE); this
        section shows what's actually installed and lets the user add
        another language pack without leaving the app, since silently
        missing the Polish pack is exactly what produced garbled OCR
        text before this was surfaced anywhere.
        """
        status_ok = self.environment_status.get(ENV_ITEM_OCR)
        frame = self._section_frame(parent)
        row = ctk.CTkFrame(frame, fg_color="transparent")
        row.pack(fill="x", padx=14, pady=12)
        text_col = ctk.CTkFrame(row, fg_color="transparent")
        text_col.pack(fill="x")
        title_row = ctk.CTkFrame(text_col, fg_color="transparent")
        title_row.pack(fill="x")
        self._build_status_dot(title_row, status_ok)
        ctk.CTkLabel(
            title_row,
            text="OCR (skany, obrazy)",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
            text_color=COLOR_TEXT,
            anchor="w",
        ).pack(side="left", fill="x")
        ctk.CTkLabel(
            text_col,
            text="Automatyczne, wymaga lokalnego Tesseracta. Polski jest "
            "językiem podstawowym, angielski dodatkowym.",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            text_color=COLOR_TEXT_MUTED,
            anchor="w",
            wraplength=460,
            justify="left",
        ).pack(fill="x", pady=(0, 6))

        self.ocr_language_status_label = ctk.CTkLabel(
            text_col,
            text=self._installed_ocr_language_names(),
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            text_color=COLOR_TEXT,
            anchor="w",
            wraplength=460,
            justify="left",
        )
        self.ocr_language_status_label.pack(fill="x", pady=(0, 8))

        addable = {
            code: label
            for code, label in COMMON_OCR_LANGUAGES_PL.items()
            if code not in self.installed_ocr_languages
        }
        if not addable:
            return

        add_row = ctk.CTkFrame(text_col, fg_color="transparent")
        add_row.pack(fill="x")
        ctk.CTkLabel(
            add_row,
            text="Dograj pakiet językowy:",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            text_color=COLOR_TEXT_MUTED,
        ).pack(side="left", padx=(0, 8))
        sorted_addable = dict(sorted(addable.items(), key=lambda pair: pair[1]))
        # The variable holds the OptionMenu's selected *label* (what the
        # widget actually shows/sets), not a language code - initializing
        # it to a code here silently broke "Dograj" (the code lookup by
        # label always missed, so the click did nothing at all).
        self.ocr_language_add_var = tk.StringVar(value=next(iter(sorted_addable.values())))
        ctk.CTkOptionMenu(
            add_row,
            values=list(sorted_addable.values()),
            variable=self.ocr_language_add_var,
            width=140,
            height=28,
            fg_color=COLOR_ICON_IDLE,
            button_color=COLOR_BORDER,
            button_hover_color=COLOR_BORDER,
            text_color=COLOR_TEXT,
            dropdown_fg_color=COLOR_CARD,
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
        ).pack(side="left", padx=(0, 8))
        self._ocr_language_code_by_label = {v: k for k, v in sorted_addable.items()}
        self.ocr_language_add_button = ctk.CTkButton(
            add_row,
            text="Dograj",
            width=80,
            height=28,
            corner_radius=8,
            fg_color=COLOR_ACCENT,
            hover_color=COLOR_ACCENT_HOVER,
            font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
            command=self._add_ocr_language_clicked,
        )
        self.ocr_language_add_button.pack(side="left")

    def _add_ocr_language_clicked(self) -> None:
        if self.ocr_language_installing or self.ocr_language_add_var is None:
            return
        label = self.ocr_language_add_var.get()
        lang_code = self._ocr_language_code_by_label.get(label)
        if not lang_code:
            return
        self.ocr_language_installing = True
        if self.ocr_language_add_button is not None:
            self.ocr_language_add_button.configure(state="disabled", text="Dograję...")

        def worker() -> None:
            ok, error = install_tesseract_language(lang_code)
            self.window.after(0, lambda: self._on_ocr_language_install_done(ok, error))

        threading.Thread(target=worker, daemon=True).start()

    def _on_ocr_language_install_done(self, ok: bool, error: str) -> None:
        self.ocr_language_installing = False
        if not self.window.winfo_exists():
            return
        if not ok:
            messagebox.showerror(
                "Pakiet językowy", error or "Nie udało się dograć pakietu językowego."
            )
            if self.ocr_language_add_button is not None:
                self.ocr_language_add_button.configure(state="normal", text="Dograj")
            return
        # Refresh the installed-language list from the real, current state
        # rather than assuming success - confirms the file actually landed
        # somewhere Tesseract will read it from. Also updates the app-level
        # cache above, so a later Settings open sees the new language too
        # instead of serving the stale pre-install list.
        self.installed_ocr_languages = list_installed_languages()
        self.app._installed_ocr_languages_cache = self.installed_ocr_languages
        self.environment_status[ENV_ITEM_OCR] = True
        if self.ocr_language_status_label is not None:
            self.ocr_language_status_label.configure(
                text=self._installed_ocr_language_names()
            )
        # Rebuild the tab so the "Dograj" row drops the language that is
        # now installed and the status dot turns green.
        self._refresh_detection_tab()

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
        # LLM review is disabled in this alpha build (untested) - forced
        # off regardless of the switch state as a second guarantee on top
        # of the disabled control itself.
        self.app.use_llm_review = False
        self.app.pdf_output_label = self.pdf_mode_var.get()
        self.app.auto_open_on_approve = self.auto_open_var.get()
        self.app.show_usage_hints = self.show_hints_var.get()
        self.app.sensitive_terms_path = self.sensitive_terms_path
        self.app.magic_pen_interaction_mode = self.magic_pen_mode_var.get()
        self.app.magic_pen_custom_bindings = dict(self._custom_bindings)
        try:
            save_magic_pen_interaction_config(
                self.app.magic_pen_interaction_config_path,
                self.app.magic_pen_interaction_mode,
                self.app.magic_pen_custom_bindings,
            )
        except OSError:
            # A cosmetic preference, same as the hint-dismissal writes
            # elsewhere - never worth failing the whole save over a
            # read-only home folder.
            pass
        if self.app.use_llm_review and not self.app.llm_model_name:
            status, models = list_installed_models()
            _values, selected_model, _hint = format_llm_model_selector_state(
                status, models
            )
            self.app.llm_model_name = selected_model
        self.window.destroy()
        if self._on_saved is not None:
            self._on_saved()


