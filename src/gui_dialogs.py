"""Small informational modals: AboutDialog ("O programie") and
SummaryDialog ("Szczegóły")."""

from __future__ import annotations

import tkinter as tk

import customtkinter as ctk
from PIL import Image

try:
    from .gui_helpers import (
        APP_ABOUT_TEXT,
        APP_ICON_PATH,
        APP_TITLE,
        APP_VERSION,
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
        RISK_STYLES,
        RISK_SUMMARY_TEXT_PL,
        _bring_window_to_front,
        category_label_pl,
        risk_style_key,
    )
    from .review import ReviewItem
except ImportError:
    from gui_helpers import (
        APP_ABOUT_TEXT,
        APP_ICON_PATH,
        APP_TITLE,
        APP_VERSION,
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
        RISK_STYLES,
        RISK_SUMMARY_TEXT_PL,
        _bring_window_to_front,
        category_label_pl,
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


