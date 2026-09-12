"""Small informational modals: AboutDialog ("O programie"),
SummaryDialog ("Szczegóły"), and ApprovalLockWarningDialog (the
one-time-dismissible "approving locks this file" confirmation)."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable

import customtkinter as ctk
from PIL import Image

try:
    from .gui_helpers import (
        APP_ABOUT_TEXT,
        APP_ALPHA_DISCLAIMER_TEXT,
        APP_ICON_PATH,
        APP_TITLE,
        APP_VERSION,
        APPROVAL_LOCK_HINT_ID,
        COLOR_ACCENT,
        COLOR_ACCENT_HOVER,
        COLOR_BG,
        COLOR_BORDER,
        COLOR_CARD,
        COLOR_ICON_IDLE,
        COLOR_OK,
        COLOR_TEXT,
        COLOR_TEXT_MUTED,
        COLOR_WARNING,
        COLOR_WARNING_SOFT,
        COLOR_WARNING_TEXT,
        FONT_FAMILY,
        MAGIC_PEN_HINT_ID,
        RISK_STYLES,
        RISK_SUMMARY_TEXT_PL,
        _bring_window_to_front,
        apply_subtle_scrollbar,
        category_label_pl,
        center_window_over_parent,
        dismiss_hint,
        format_approval_lock_warning_text,
        format_approval_lock_warning_title,
        risk_style_key,
    )
    from .review import ReviewItem
except ImportError:
    from gui_helpers import (
        APP_ABOUT_TEXT,
        APP_ALPHA_DISCLAIMER_TEXT,
        APP_ICON_PATH,
        APP_TITLE,
        APP_VERSION,
        APPROVAL_LOCK_HINT_ID,
        COLOR_ACCENT,
        COLOR_ACCENT_HOVER,
        COLOR_BG,
        COLOR_BORDER,
        COLOR_CARD,
        COLOR_ICON_IDLE,
        COLOR_OK,
        COLOR_TEXT,
        COLOR_TEXT_MUTED,
        COLOR_WARNING,
        COLOR_WARNING_SOFT,
        COLOR_WARNING_TEXT,
        FONT_FAMILY,
        MAGIC_PEN_HINT_ID,
        RISK_STYLES,
        RISK_SUMMARY_TEXT_PL,
        _bring_window_to_front,
        apply_subtle_scrollbar,
        category_label_pl,
        center_window_over_parent,
        dismiss_hint,
        format_approval_lock_warning_text,
        format_approval_lock_warning_title,
        risk_style_key,
    )
    from review import ReviewItem

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .gui_app import AnonymizerApp

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
        center_window_over_parent(window, app.root, 420, 430)
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

        alpha_card = ctk.CTkFrame(window, corner_radius=10, fg_color=COLOR_WARNING_SOFT)
        alpha_card.pack(fill="x", padx=20, pady=(0, 12))
        alpha_row = ctk.CTkFrame(alpha_card, fg_color="transparent")
        alpha_row.pack(fill="x", padx=14, pady=12)
        ctk.CTkLabel(
            alpha_row,
            text="\U000026a0",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13),
            text_color=COLOR_WARNING_TEXT,
        ).pack(side="left", padx=(0, 8))
        ctk.CTkLabel(
            alpha_row,
            text=APP_ALPHA_DISCLAIMER_TEXT,
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            text_color=COLOR_WARNING_TEXT,
            wraplength=310,
            justify="left",
            anchor="w",
        ).pack(side="left", fill="x", expand=True)

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
        center_window_over_parent(window, app.root, 480, 520)
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
        apply_subtle_scrollbar(chips_frame)
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


class ApprovalLockWarningDialog:
    """Confirmation shown before approving one or more review items -
    approving is a one-way action (see ComparisonWindow.locked): the
    magic pen stops accepting edits on an approved file, so
    re-anonymizing the source from scratch is the only way back. Direct
    user feedback: silently approving needs an explicit warning first,
    not just a status change - but also a "Nie pokazuj ponownie"
    checkbox that persists across restarts (see dismiss_hint /
    APPROVAL_LOCK_HINT_ID in gui_helpers.py), since a warning nobody can
    ever turn off gets clicked through on autopilot anyway. Settings >
    Ogólne can bring it back once dismissed.

    ``on_confirm`` is called (and the window destroyed) only once the
    user actually clicks "Zatwierdź" - cancelling or closing the window
    leaves the review status untouched.
    """

    def __init__(self, app: AnonymizerApp, count: int, on_confirm: Callable[[], None]) -> None:
        self.on_confirm = on_confirm
        window = ctk.CTkToplevel(app.root)
        self.window = window
        window.title(format_approval_lock_warning_title(count))
        center_window_over_parent(window, app.root, 420, 300)
        window.resizable(False, False)
        window.configure(fg_color=COLOR_BG)
        window.transient(app.root)
        window.grab_set()
        window.protocol("WM_DELETE_WINDOW", self._cancel)

        banner = ctk.CTkFrame(
            window,
            corner_radius=10,
            fg_color=COLOR_WARNING_SOFT,
            border_width=1,
            border_color=COLOR_WARNING,
        )
        banner.pack(fill="x", padx=20, pady=(20, 12))
        ctk.CTkLabel(
            banner,
            text="⚠ Zatwierdzenie jest ostateczne",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
            text_color=COLOR_WARNING_TEXT,
            anchor="w",
        ).pack(fill="x", padx=14, pady=(12, 4))
        ctk.CTkLabel(
            banner,
            text=format_approval_lock_warning_text(count),
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            text_color=COLOR_WARNING_TEXT,
            anchor="w",
            wraplength=350,
            justify="left",
        ).pack(fill="x", padx=14, pady=(0, 12))

        self.dont_show_again_var = tk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            window,
            text="Nie pokazuj ponownie",
            variable=self.dont_show_again_var,
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            text_color=COLOR_TEXT,
            fg_color=COLOR_ACCENT,
            hover_color=COLOR_ACCENT_HOVER,
        ).pack(anchor="w", padx=24, pady=(4, 4))
        ctk.CTkLabel(
            window,
            text="Możesz przywrócić to ostrzeżenie w Ustawienia > Ogólne.",
            font=ctk.CTkFont(family=FONT_FAMILY, size=10),
            text_color=COLOR_TEXT_MUTED,
            anchor="w",
        ).pack(fill="x", padx=24, pady=(0, 16))

        actions = ctk.CTkFrame(window, fg_color="transparent")
        actions.pack(fill="x", padx=20, pady=(0, 20))
        # Same packing-order-first rule this project always follows for a
        # primary action next to a secondary one: "Zatwierdź" is packed
        # before "Anuluj" so it is never the one squeezed off narrow.
        ctk.CTkButton(
            actions,
            text="Zatwierdź",
            width=120,
            height=34,
            corner_radius=8,
            fg_color=COLOR_ACCENT,
            hover_color=COLOR_ACCENT_HOVER,
            font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
            command=self._confirm,
        ).pack(side="right")
        ctk.CTkButton(
            actions,
            text="Anuluj",
            width=100,
            height=34,
            corner_radius=8,
            fg_color="transparent",
            hover_color=COLOR_ICON_IDLE,
            text_color=COLOR_TEXT_MUTED,
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            command=self._cancel,
        ).pack(side="right", padx=(0, 8))

        _bring_window_to_front(window)

    def _confirm(self) -> None:
        if self.dont_show_again_var.get():
            dismiss_hint(APPROVAL_LOCK_HINT_ID)
        self.window.destroy()
        self.on_confirm()

    def _cancel(self) -> None:
        self.window.destroy()


class MagicPenHintDialog:
    """A first-open "what can I do here" explainer for the magic pen,
    shown once (see ComparisonWindow._maybe_show_magic_pen_hint) the
    first time a comparison window with an editable (not locked) PDF
    opens - per direct user feedback that the draw/erase buttons alone
    were "too small to notice" and a first-time user would have no idea
    this editing capability even existed. Purely informational (one
    "Rozumiem" button, not a confirm/cancel choice) with the same
    persisted "Nie pokazuj ponownie" pattern as
    ApprovalLockWarningDialog - restorable from Settings > Ogólne.
    """

    def __init__(self, app: AnonymizerApp, parent_window: tk.Misc) -> None:
        # Transient to (and centered over, and refocused back onto on
        # close) parent_window - the comparison window this hint was
        # actually triggered from, *not* app.root. A real bug was found
        # and fixed here: making this transient to app.root instead let
        # Windows raise the main app window as this dialog's "owner",
        # burying the comparison window behind it - confirmed directly
        # by a user report of clicking through what they thought was an
        # unresponsive window, only to find the preview had gone behind
        # the main app.
        self.parent_window = parent_window
        window = ctk.CTkToplevel(parent_window)
        self.window = window
        window.title("Co możesz zrobić z tym dokumentem?")
        center_window_over_parent(window, parent_window, 440, 380)
        window.resizable(False, False)
        window.configure(fg_color=COLOR_BG)
        window.transient(parent_window)
        window.grab_set()
        window.protocol("WM_DELETE_WINDOW", self._close)

        ctk.CTkLabel(
            window,
            text="✏️ Ten dokument można jeszcze poprawić",
            font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"),
            text_color=COLOR_TEXT,
            wraplength=390,
            justify="left",
        ).pack(fill="x", padx=20, pady=(20, 12))

        for glyph, text in (
            (
                "✏",
                (
                    "Zaznacz i przeciągnij myszą w prawym oknie edycji, aby "
                    "ręcznie ukryć coś, co program pominął."
                ),
            ),
            (
                "🖱",
                (
                    "Kliknij prawym przyciskiem na kolorowym zaznaczeniu (albo "
                    "użyj przycisku „Usuń zaznaczenie”), aby cofnąć "
                    "automatyczną anonimizację tego fragmentu."
                ),
            ),
            (
                "✓",
                (
                    "Dopóki nie klikniesz „Zatwierdź”, dokument pozostaje "
                    "w pełni edytowalny - po zatwierdzeniu edycja nie jest już "
                    "możliwa."
                ),
            ),
        ):
            row = ctk.CTkFrame(window, fg_color="transparent")
            row.pack(fill="x", padx=20, pady=4)
            ctk.CTkLabel(
                row,
                text=glyph,
                font=ctk.CTkFont(family=FONT_FAMILY, size=14),
                text_color=COLOR_ACCENT,
                width=24,
            ).pack(side="left", anchor="n")
            ctk.CTkLabel(
                row,
                text=text,
                font=ctk.CTkFont(family=FONT_FAMILY, size=12),
                text_color=COLOR_TEXT,
                wraplength=340,
                justify="left",
                anchor="w",
            ).pack(side="left", fill="x", expand=True)

        self.dont_show_again_var = tk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            window,
            text="Nie pokazuj ponownie",
            variable=self.dont_show_again_var,
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            text_color=COLOR_TEXT,
            fg_color=COLOR_ACCENT,
            hover_color=COLOR_ACCENT_HOVER,
        ).pack(anchor="w", padx=24, pady=(12, 4))
        ctk.CTkLabel(
            window,
            text="Możesz przywrócić tę podpowiedź w Ustawienia > Ogólne.",
            font=ctk.CTkFont(family=FONT_FAMILY, size=10),
            text_color=COLOR_TEXT_MUTED,
            anchor="w",
        ).pack(fill="x", padx=24, pady=(0, 12))

        ctk.CTkButton(
            window,
            text="Rozumiem",
            width=120,
            height=34,
            corner_radius=8,
            fg_color=COLOR_ACCENT,
            hover_color=COLOR_ACCENT_HOVER,
            font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
            command=self._close,
        ).pack(pady=(0, 20))

        _bring_window_to_front(window)

    def _close(self) -> None:
        if self.dont_show_again_var.get():
            dismiss_hint(MAGIC_PEN_HINT_ID)
        self.window.destroy()
        # View must return to whatever window this hint was raised over
        # - per direct user feedback, clicking "Rozumiem" left the
        # comparison window buried behind the main app with nothing
        # visibly bringing it back.
        _bring_window_to_front(self.parent_window)


