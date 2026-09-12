"""The main DocShield application window (AnonymizerApp): start,
history, processing, and review screens."""

import threading
import time
import tkinter as tk
import webbrowser
from datetime import datetime, timezone
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk
from PIL import Image, ImageTk
from tkinterdnd2 import DND_FILES

try:
    from .anonymizer import (
        BatchResult,
        anonymize_batch,
    )
    from .dependency_updates import (
        check_dependency_updates,
        install_package_update,
    )
    from .environment_check import (
        ENV_ITEM_NER,
        ENV_ITEM_OCR,
        INSTALL_ACTION_OPEN_URL,
        INSTALL_ACTION_SPACY_MODEL,
        INSTALL_ACTION_TESSDATA_DOWNLOAD,
        check_environment,
        install_ner_model,
        install_tesseract_language,
    )
    from .file_writers import internal_artifacts_dir
    from .gui_comparison_window import ComparisonWindow
    from .gui_dialogs import (
        AboutDialog,
        ApprovalLockWarningDialog,
        SummaryDialog,
    )
    from .gui_helpers import (
        APP_BUILD_STAGE_LABEL,
        APP_ICON_ICO_PATH,
        APP_ICON_PATH,
        APP_PERSONAL_NOTE,
        APP_SUBTITLE,
        APP_TAGLINE,
        APP_TITLE,
        APP_VERSION,
        APPROVAL_LOCK_HINT_ID,
        COLOR_ACCENT,
        COLOR_ACCENT_HOVER,
        COLOR_ACCENT_SOFT,
        COLOR_BG,
        COLOR_BORDER,
        COLOR_CARD,
        COLOR_HIGH_RISK,
        COLOR_HIGH_RISK_SOFT,
        COLOR_ICON_IDLE,
        COLOR_NEEDS_REVIEW,
        COLOR_NEEDS_REVIEW_SOFT,
        COLOR_OK,
        COLOR_OK_SOFT,
        COLOR_SIDEBAR_BG,
        COLOR_SIDEBAR_HOVER,
        COLOR_SIDEBAR_TEXT,
        COLOR_SIDEBAR_TEXT_MUTED,
        COLOR_SIDEBAR_TRUST_BG,
        COLOR_TEXT,
        COLOR_TEXT_MUTED,
        COLOR_WARNING,
        COLOR_WARNING_SOFT,
        COLOR_WARNING_TEXT,
        FILE_LIST_MAX_HEIGHT,
        FONT_FAMILY,
        HEADER_STACK_BREAKPOINT,
        LEGEND_ITEMS,
        MANUAL_REVIEW_WARNING,
        PDF_OUTPUT_LABEL_VISUAL_REDACTION,
        QUICK_SETTINGS_PANEL_WIDTH,
        RISK_STYLES,
        SCRIPT_FONT_FAMILY,
        WINDOW_DEFAULT_SIZE,
        WINDOW_MIN_HEIGHT,
        WINDOW_MIN_WIDTH,
        DnDCTk,
        IconTooltip,
        apply_subtle_scrollbar,
        default_output_directory,
        environment_status_lookup,
        file_type_badge,
        filter_supported_paths,
        format_anonymize_button_text,
        format_batch_error_items,
        format_drop_result,
        format_filename_pii_warning,
        format_processing_animation_frame,
        format_readiness_pl,
        format_recent_folder_timestamp,
        format_review_heading_subtitle,
        format_review_summary_line,
        format_short_path,
        get_file_type_icon,
        hint_is_dismissed,
        history_config_path,
        load_recent_folders,
        open_path_with_default_app,
        parse_dropped_file_paths,
        parse_report_summary,
        pdf_output_mode_from_gui_label,
        pdf_redaction_scope_from_gui_label,
        record_recent_folder,
        remove_paths_by_indexes,
        restrict_review_items_to_batch,
        review_status_label_pl,
        risk_style_key,
        save_recent_folders,
        truncate_filename_middle,
    )
    from .gui_settings_dialog import SettingsDialog
    from .output_cleanup import (
        apply_output_cleanup_plan,
        build_output_cleanup_plan,
        format_cleanup_plan_summary,
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
        BatchResult,
        anonymize_batch,
    )
    from dependency_updates import (
        check_dependency_updates,
        install_package_update,
    )
    from environment_check import (
        ENV_ITEM_NER,
        ENV_ITEM_OCR,
        INSTALL_ACTION_OPEN_URL,
        INSTALL_ACTION_SPACY_MODEL,
        INSTALL_ACTION_TESSDATA_DOWNLOAD,
        check_environment,
        install_ner_model,
        install_tesseract_language,
    )
    from file_writers import internal_artifacts_dir
    from gui_comparison_window import ComparisonWindow
    from gui_dialogs import (
        AboutDialog,
        ApprovalLockWarningDialog,
        SummaryDialog,
    )
    from gui_helpers import (
        APP_BUILD_STAGE_LABEL,
        APP_ICON_ICO_PATH,
        APP_ICON_PATH,
        APP_PERSONAL_NOTE,
        APP_SUBTITLE,
        APP_TAGLINE,
        APP_TITLE,
        APP_VERSION,
        APPROVAL_LOCK_HINT_ID,
        COLOR_ACCENT,
        COLOR_ACCENT_HOVER,
        COLOR_ACCENT_SOFT,
        COLOR_BG,
        COLOR_BORDER,
        COLOR_CARD,
        COLOR_HIGH_RISK,
        COLOR_HIGH_RISK_SOFT,
        COLOR_ICON_IDLE,
        COLOR_NEEDS_REVIEW,
        COLOR_NEEDS_REVIEW_SOFT,
        COLOR_OK,
        COLOR_OK_SOFT,
        COLOR_SIDEBAR_BG,
        COLOR_SIDEBAR_HOVER,
        COLOR_SIDEBAR_TEXT,
        COLOR_SIDEBAR_TEXT_MUTED,
        COLOR_SIDEBAR_TRUST_BG,
        COLOR_TEXT,
        COLOR_TEXT_MUTED,
        COLOR_WARNING,
        COLOR_WARNING_SOFT,
        COLOR_WARNING_TEXT,
        FILE_LIST_MAX_HEIGHT,
        FONT_FAMILY,
        HEADER_STACK_BREAKPOINT,
        LEGEND_ITEMS,
        MANUAL_REVIEW_WARNING,
        PDF_OUTPUT_LABEL_VISUAL_REDACTION,
        QUICK_SETTINGS_PANEL_WIDTH,
        RISK_STYLES,
        SCRIPT_FONT_FAMILY,
        WINDOW_DEFAULT_SIZE,
        WINDOW_MIN_HEIGHT,
        WINDOW_MIN_WIDTH,
        DnDCTk,
        IconTooltip,
        apply_subtle_scrollbar,
        default_output_directory,
        environment_status_lookup,
        file_type_badge,
        filter_supported_paths,
        format_anonymize_button_text,
        format_batch_error_items,
        format_drop_result,
        format_filename_pii_warning,
        format_processing_animation_frame,
        format_readiness_pl,
        format_recent_folder_timestamp,
        format_review_heading_subtitle,
        format_review_summary_line,
        format_short_path,
        get_file_type_icon,
        hint_is_dismissed,
        history_config_path,
        load_recent_folders,
        open_path_with_default_app,
        parse_dropped_file_paths,
        parse_report_summary,
        pdf_output_mode_from_gui_label,
        pdf_redaction_scope_from_gui_label,
        record_recent_folder,
        remove_paths_by_indexes,
        restrict_review_items_to_batch,
        review_status_label_pl,
        risk_style_key,
        save_recent_folders,
        truncate_filename_middle,
    )
    from gui_settings_dialog import SettingsDialog
    from output_cleanup import (
        apply_output_cleanup_plan,
        build_output_cleanup_plan,
        format_cleanup_plan_summary,
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
        # Collapsed to a slim rail (see _build_quick_settings_panel) once
        # the user clicks the panel's own collapse toggle - per direct
        # feedback that "Szybkie akcje" can get in the way and should be
        # hideable, with only the "Anonimizuj" button itself guaranteed
        # to stay reachable either way. A runtime-only preference (not
        # persisted to disk): unlike the one-time hints in
        # ui_hints_config_path, this is an active layout choice for the
        # current session, not a "never show me this again" warning.
        self.quick_actions_collapsed = False

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
        self.processing_animation_label: ctk.CTkLabel | None = None
        self._processing_animation_step = 0
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
        # Dark navy, not the plain white card used elsewhere - a light
        # sidebar blended into the rest of the (also light) app and was
        # easy to miss/ignore; a distinct dark panel reads as permanent
        # navigation rather than just another content card.
        sidebar = ctk.CTkFrame(
            parent, fg_color=COLOR_SIDEBAR_BG, corner_radius=0, width=208
        )
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
        brand_title_row = ctk.CTkFrame(brand_text_col, fg_color="transparent", cursor="hand2")
        brand_title_row.pack(anchor="w")
        brand_title_label = ctk.CTkLabel(
            brand_title_row,
            text=APP_TITLE,
            font=ctk.CTkFont(family=FONT_FAMILY, size=16, weight="bold"),
            text_color="#FFFFFF",
            cursor="hand2",
        )
        brand_title_label.pack(side="left")
        alpha_badge = ctk.CTkLabel(
            brand_title_row,
            text=APP_BUILD_STAGE_LABEL,
            font=ctk.CTkFont(family=FONT_FAMILY, size=9, weight="bold"),
            text_color="#FFFFFF",
            fg_color=COLOR_WARNING,
            corner_radius=4,
            width=0,
            cursor="hand2",
        )
        alpha_badge.pack(side="left", padx=(6, 0), ipadx=4, ipady=1)
        brand_clickables.append(alpha_badge)
        IconTooltip(alpha_badge, "Wersja rozwojowa - w trakcie testów")
        brand_subtitle_label = ctk.CTkLabel(
            brand_text_col,
            text="Anonimizator dokumentów",
            font=ctk.CTkFont(family=FONT_FAMILY, size=10),
            text_color=COLOR_SIDEBAR_TEXT,
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
                hover_color=COLOR_SIDEBAR_HOVER,
                text_color=COLOR_SIDEBAR_TEXT,
                font=ctk.CTkFont(family=FONT_FAMILY, size=13),
                command=command,
            )
            button.pack(fill="x", pady=(0, 4))
            if tooltip:
                IconTooltip(button, tooltip)
            self._nav_buttons[key] = button

        # Empty expanding spacer pushes the trust badge to the bottom.
        ctk.CTkFrame(sidebar, fg_color="transparent").pack(fill="both", expand=True)

        trust_card = ctk.CTkFrame(sidebar, fg_color=COLOR_SIDEBAR_TRUST_BG, corner_radius=10)
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
            text="Działa lokalnie",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
            text_color="#FFFFFF",
            anchor="w",
        ).pack(side="left")
        ctk.CTkLabel(
            trust_card,
            text="Twoje dane nie opuszczają\ntego komputera.\nBez internetu. Bez chmury.",
            font=ctk.CTkFont(family=FONT_FAMILY, size=10),
            text_color=COLOR_SIDEBAR_TEXT,
            justify="left",
            anchor="w",
        ).pack(fill="x", padx=12, pady=(0, 10))

        ctk.CTkLabel(
            sidebar,
            text=f"v{APP_VERSION}",
            font=ctk.CTkFont(family=FONT_FAMILY, size=9),
            text_color=COLOR_SIDEBAR_TEXT_MUTED,
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
                fg_color=COLOR_ACCENT if is_active else "transparent",
                text_color="#FFFFFF" if is_active else COLOR_SIDEBAR_TEXT,
                hover_color=COLOR_ACCENT_HOVER if is_active else COLOR_SIDEBAR_HOVER,
            )

    def _clear_content(self) -> None:
        self.processing_animation_label = None
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

    def _install_tesseract_language_clicked(self, lang_code: str) -> None:
        if ENV_ITEM_OCR in self.environment_installing:
            return
        self.environment_installing.add(ENV_ITEM_OCR)
        if self.active_screen == "start":
            self.show_start_screen()

        def worker() -> None:
            ok, error = install_tesseract_language(lang_code)
            self.root.after(0, lambda: self._on_tesseract_language_install_done(ok, error))

        threading.Thread(target=worker, daemon=True).start()

    def _on_tesseract_language_install_done(self, ok: bool, error: str) -> None:
        self.environment_installing.discard(ENV_ITEM_OCR)
        if not ok and error:
            messagebox.showerror("Pakiet językowy", error)
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

        # Both "something's missing" and "a library update is available"
        # use the same warning/amber treatment now - a plain blue "info"
        # card for updates read as too easy to miss/dismiss compared to
        # the OCR-style warning card, per direct user feedback comparing
        # the two side by side.
        is_warning = bool(issues)
        header_text = (
            "⚠ Niektóre funkcje mogą nie działać w pełni:"
            if is_warning
            else "⚠ Dostępne aktualizacje bibliotek:"
        )
        bg_color = COLOR_WARNING_SOFT
        border_color = COLOR_WARNING
        header_color = COLOR_WARNING_TEXT

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
            elif item.install_action == INSTALL_ACTION_TESSDATA_DOWNLOAD:
                ctk.CTkButton(
                    row,
                    text="Zainstaluj pakiet polski",
                    width=170,
                    height=26,
                    corner_radius=8,
                    fg_color=COLOR_ACCENT,
                    hover_color=COLOR_ACCENT_HOVER,
                    font=ctk.CTkFont(family=FONT_FAMILY, size=10, weight="bold"),
                    command=lambda target=item.install_target: (
                        self._install_tesseract_language_clicked(target)
                    ),
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
        """The start screen's right-hand "Szybkie akcje" (quick actions)
        card - the most-used detection settings plus, per direct user
        feedback, the output-folder picker and the "Anonimizuj" button
        itself, moved here from the bottom of the center column so that
        column can show more of the selected-file list.

        Moving the primary action button in here brought back the exact
        hazard the "pinned bottom bar" pattern in show_start_screen was
        built to prevent: the settings above (checkboxes, OCR status,
        dictionary row) can grow taller than the panel, and this panel
        is also always visible now (the old QUICK_SETTINGS_MIN_WIDTH
        hide-below-880px gate is gone, since a hidden panel would mean a
        hidden "Anonimizuj" button). So the same fix is reapplied one
        level deeper: action_bar (folder picker, status text, the
        button) is packed *first* with side="bottom" so it always claims
        its space, and everything else scrolls in the region above it -
        the button can never be pushed out of reach, on any window size.

        Deliberately only wraps settings that are real, already-wired
        toggles (self.use_ner, self.use_llm_review) - OCR has no such
        toggle in this app (it runs automatically when available, there
        is nothing to switch off), so that row stays a read-only status
        like it already is in the full Settings dialog, rather than
        adding a checkbox that would not actually control anything.

        Collapsible: a header button slides this whole card away to a
        slim rail (see _build_collapsed_quick_actions_rail) - per direct
        user feedback the panel can get in the way and should be
        hideable, with the reopen control and the "Anonimizuj" button
        itself guaranteed to stay reachable either way.
        """
        if self.quick_actions_collapsed:
            return self._build_collapsed_quick_actions_rail(parent)

        panel = ctk.CTkFrame(
            parent,
            corner_radius=12,
            fg_color=COLOR_CARD,
            border_width=1,
            border_color=COLOR_BORDER,
            width=QUICK_SETTINGS_PANEL_WIDTH,
        )
        panel.pack_propagate(False)

        action_bar = ctk.CTkFrame(panel, fg_color="transparent")
        action_bar.pack(side="bottom", fill="x", padx=14, pady=(0, 14))
        inner = ctk.CTkScrollableFrame(panel, fg_color="transparent")
        inner.pack(side="top", fill="both", expand=True, padx=14, pady=(14, 0))
        apply_subtle_scrollbar(inner)

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
            text="Szybkie akcje",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
            text_color=COLOR_TEXT,
            cursor="hand2",
        ).pack(side="left")
        collapse_button = ctk.CTkButton(
            header_row,
            text="»",
            width=22,
            height=20,
            corner_radius=6,
            fg_color="transparent",
            hover_color=COLOR_ICON_IDLE,
            text_color=COLOR_TEXT_MUTED,
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            command=self._toggle_quick_actions_collapsed,
        )
        collapse_button.pack(side="right")
        IconTooltip(collapse_button, "Ukryj szybkie akcje")

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

        # Disabled in this alpha build: local-LLM review (Ollama) exists
        # in the code but has not been tested enough to offer yet. The
        # checkbox stays visible (so it's clear the feature is coming,
        # not missing) but locked off - self.use_llm_review is never set
        # from here while it's disabled.
        llm_var = tk.BooleanVar(value=False)

        llm_label_row = ctk.CTkFrame(inner, fg_color="transparent")
        llm_label_row.pack(fill="x", pady=(0, 2))
        ctk.CTkCheckBox(
            llm_label_row,
            text="Dodatkowa kontrola wyniku (AI)",
            variable=llm_var,
            state="disabled",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            text_color=COLOR_TEXT_MUTED,
            fg_color=COLOR_ACCENT,
            hover_color=COLOR_ACCENT_HOVER,
        ).pack(side="left")
        ctk.CTkLabel(
            llm_label_row,
            text="wkrótce",
            font=ctk.CTkFont(family=FONT_FAMILY, size=10, weight="bold"),
            text_color=COLOR_ACCENT,
        ).pack(side="left", padx=(6, 0))
        ctk.CTkLabel(
            inner,
            text="Jeszcze niedostępne w tej wersji rozwojowej - w przygotowaniu",
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
        ).pack(fill="x", pady=(4, 10))

        # --- pinned action bar: folder picker + status + "Anonimizuj" ---
        # A thin top border visually separates this always-reachable
        # action area from the settings that scroll above it.
        ctk.CTkFrame(action_bar, fg_color=COLOR_BORDER, height=1).pack(
            fill="x", pady=(0, 10)
        )
        ctk.CTkLabel(
            action_bar,
            text="Folder wynikowy",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
            text_color=COLOR_TEXT,
            anchor="w",
        ).pack(fill="x", pady=(0, 4))
        path_field = ctk.CTkFrame(
            action_bar,
            corner_radius=8,
            fg_color=COLOR_BG,
            border_width=1,
            border_color=COLOR_BORDER,
        )
        path_field.pack(fill="x", pady=(0, 6))
        path_field_inner = ctk.CTkFrame(path_field, fg_color="transparent")
        path_field_inner.pack(fill="x", padx=10, pady=7)
        ctk.CTkLabel(
            path_field_inner,
            text="\U0001f4c1",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13),
        ).pack(side="left", padx=(0, 8))
        # The panel is narrow, so the path text and the "Zmień" button
        # stack instead of sitting side by side (as they did in the old
        # wide bottom_bar) - side by side here would squeeze both down
        # to the point of being unreadable/unclickable.
        self.output_dir_value_label = ctk.CTkLabel(
            path_field_inner,
            text=self._output_dir_display_text(),
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            text_color=COLOR_TEXT,
            anchor="w",
        )
        self.output_dir_value_label.pack(side="left", fill="x", expand=True)
        ctk.CTkButton(
            action_bar,
            text="Zmień",
            height=30,
            corner_radius=8,
            fg_color="transparent",
            border_width=1,
            border_color=COLOR_BORDER,
            hover_color=COLOR_ICON_IDLE,
            text_color=COLOR_TEXT,
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            command=self.pick_output_dir,
        ).pack(fill="x", pady=(0, 10))

        self.status_label = ctk.CTkLabel(
            action_bar,
            text=format_readiness_pl(
                len(self.selected_paths), self.output_dir is not None
            ),
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            text_color=COLOR_TEXT_MUTED,
        )
        self.status_label.pack(pady=(0, 8))

        self.anonymize_button = ctk.CTkButton(
            action_bar,
            text="Anonimizuj",
            height=48,
            corner_radius=10,
            fg_color=COLOR_ACCENT,
            hover_color=COLOR_ACCENT_HOVER,
            font=ctk.CTkFont(family=FONT_FAMILY, size=16, weight="bold"),
            state="disabled",
            command=self.start_anonymize,
        )
        self.anonymize_button.pack(fill="x")

        return panel

    def _toggle_quick_actions_collapsed(self) -> None:
        self.quick_actions_collapsed = not self.quick_actions_collapsed
        self.show_start_screen()

    def _build_collapsed_quick_actions_rail(self, parent: ctk.CTkFrame) -> ctk.CTkFrame:
        """The slim stand-in for _build_quick_settings_panel once
        collapsed: the "Anonimizuj" button and a reopen toggle, icon-only
        since there is no room for a label - per direct user feedback,
        the button must stay reachable even while the rest of "Szybkie
        akcje" is hidden away. self.status_label and
        self.output_dir_value_label are intentionally left unset (not
        built here) - _update_readiness and pick_output_dir already
        null-check both before touching them.

        self.anonymize_button is packed *first* here, before the reopen
        button - the same "packed first is never the one squeezed out"
        rule this project leans on everywhere else. A real bug was found
        and fixed here: the previous version packed the reopen button
        first, which could crowd the anonymize button off a short window
        instead of the other way around - exactly backwards for which of
        the two actually has to stay reachable.
        """
        panel = ctk.CTkFrame(
            parent,
            corner_radius=12,
            fg_color=COLOR_CARD,
            border_width=1,
            border_color=COLOR_BORDER,
            width=64,
        )
        panel.pack_propagate(False)
        inner = ctk.CTkFrame(panel, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=10, pady=14)

        self.status_label = None
        self.output_dir_value_label = None

        self.anonymize_button = ctk.CTkButton(
            inner,
            text="▶",
            width=36,
            height=54,
            corner_radius=10,
            fg_color=COLOR_ACCENT,
            hover_color=COLOR_ACCENT_HOVER,
            font=ctk.CTkFont(family=FONT_FAMILY, size=16, weight="bold"),
            state="disabled",
            command=self.start_anonymize,
        )
        self.anonymize_button.pack(side="bottom")
        IconTooltip(self.anonymize_button, "Anonimizuj")

        # A bigger, accent-colored, clearly-clickable control instead of
        # the small muted "«" arrow from the first version - per direct
        # feedback that arrow "looked ugly" and wasn't an obvious
        # "restore this panel" affordance. "☰" reads as "more/menu"
        # without needing a label this narrow a rail has no room for.
        reopen_button = ctk.CTkButton(
            inner,
            text="☰",
            width=40,
            height=36,
            corner_radius=8,
            fg_color=COLOR_ACCENT,
            hover_color=COLOR_ACCENT_HOVER,
            text_color="#FFFFFF",
            font=ctk.CTkFont(family=FONT_FAMILY, size=16, weight="bold"),
            command=self._toggle_quick_actions_collapsed,
        )
        reopen_button.pack(side="top")
        IconTooltip(reopen_button, "Pokaż szybkie akcje")

        return panel

    def show_start_screen(self) -> None:
        self.active_screen = "start"
        self._update_sidebar_active_state()
        self._clear_content()

        # A narrower column on the right holds the always-visible
        # "Szybkie akcje" quick-actions panel (see
        # _build_quick_settings_panel) - packed *before* the main
        # column so it claims its fixed width first. That panel now
        # also carries the output-folder picker and the "Anonimizuj"
        # button (moved out of this column per direct user feedback),
        # which is why it is no longer hidden below a minimum window
        # width the way it used to be: hiding it would have hidden the
        # button too. The freed-up main column is now pure scrollable
        # content - drop zone + file list - so more of the file list is
        # visible at once, which was the other half of that same
        # feedback.
        columns_row = ctk.CTkFrame(self.content, fg_color="transparent")
        columns_row.pack(fill="both", expand=True)
        self._build_quick_settings_panel(columns_row).pack(
            side="right", fill="y", padx=(12, 0)
        )
        main_col = ctk.CTkFrame(columns_row, fg_color="transparent")
        main_col.pack(side="left", fill="both", expand=True)

        scroll_region = ctk.CTkScrollableFrame(main_col, fg_color="transparent")
        scroll_region.pack(side="top", fill="both", expand=True)
        apply_subtle_scrollbar(scroll_region)

        self._build_header_row(scroll_region)
        self._build_resume_review_banner(scroll_region)

        self._build_status_banner(scroll_region)

        # Half the column's width, centered - a 3-column grid (weights
        # 1:2:1) rather than a fixed pixel width, so it stays exactly
        # half regardless of window size. Per direct user feedback: the
        # full-width drop zone from the mockup-matching pass looked too
        # large/heavy once the file list below it could show more items.
        drop_wrap = ctk.CTkFrame(scroll_region, fg_color="transparent")
        drop_wrap.pack(fill="x", pady=(0, 4))
        drop_wrap.grid_columnconfigure(0, weight=1)
        drop_wrap.grid_columnconfigure(1, weight=2)
        drop_wrap.grid_columnconfigure(2, weight=1)

        drop_frame = ctk.CTkFrame(
            drop_wrap,
            corner_radius=16,
            fg_color=COLOR_ACCENT_SOFT,
            border_width=2,
            border_color=COLOR_BORDER,
        )
        drop_frame.grid(row=0, column=1, sticky="ew")

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
        apply_subtle_scrollbar(self.file_card_frame)
        self._refresh_file_cards()

        # Fills the vertical space the file list left behind (per direct
        # user feedback that it looked "too bare" now) with something
        # actually useful rather than decoration: a shortcut back into
        # recently used output folders, reusing data already loaded for
        # the Historia screen instead of a second source of truth.
        self._build_recent_folders_shortcut(scroll_region)

        # Folder picker, status text and "Anonimizuj" itself now live in
        # the "Szybkie akcje" panel built above (see
        # _build_quick_settings_panel) - this just syncs their initial
        # state/text to the current selection.
        self._update_readiness()

    def _build_recent_folders_shortcut(self, parent: ctk.CTkFrame) -> None:
        """A compact "Ostatnie foldery wynikowe" card - up to 3 most
        recent entries, reusing self.recent_folders (already loaded for
        the Historia screen, see _prepare_default_output_dir/__init__)
        rather than a second read of history_config_path. Silently
        renders nothing when there is no history yet, rather than an
        empty/awkward card - a first-run window is already sparse enough
        without an extra empty box telling the user so.
        """
        if not self.recent_folders:
            return
        card = ctk.CTkFrame(
            parent,
            corner_radius=12,
            fg_color=COLOR_CARD,
            border_width=1,
            border_color=COLOR_BORDER,
        )
        card.pack(fill="x", pady=(0, 14))
        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="x", padx=16, pady=12)

        header_row = ctk.CTkFrame(inner, fg_color="transparent")
        header_row.pack(fill="x", pady=(0, 8))
        ctk.CTkLabel(
            header_row,
            text="Ostatnie foldery wynikowe",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
            text_color=COLOR_TEXT,
            anchor="w",
        ).pack(side="left")
        ctk.CTkButton(
            header_row,
            text="Zobacz wszystkie →",
            fg_color="transparent",
            hover_color=COLOR_ICON_IDLE,
            text_color=COLOR_ACCENT,
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            height=22,
            command=self.show_history_screen,
        ).pack(side="right")

        for entry in self.recent_folders[:3]:
            folder_path = entry.get("path", "")
            exists = Path(folder_path).is_dir()
            row = ctk.CTkFrame(inner, fg_color="transparent")
            row.pack(fill="x", pady=3)
            ctk.CTkLabel(
                row,
                text="\U0001f4c1",
                font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            ).pack(side="left", padx=(0, 8))
            ctk.CTkLabel(
                row,
                text=Path(folder_path).name or folder_path,
                font=ctk.CTkFont(family=FONT_FAMILY, size=11),
                text_color=COLOR_TEXT if exists else COLOR_TEXT_MUTED,
                anchor="w",
            ).pack(side="left", fill="x", expand=True)
            if exists:
                ctk.CTkButton(
                    row,
                    text="Otwórz",
                    width=70,
                    height=24,
                    corner_radius=6,
                    fg_color="transparent",
                    border_width=1,
                    border_color=COLOR_BORDER,
                    hover_color=COLOR_ICON_IDLE,
                    text_color=COLOR_TEXT,
                    font=ctk.CTkFont(family=FONT_FAMILY, size=10),
                    command=lambda p=folder_path: self.open_history_folder(p),
                ).pack(side="right")
            else:
                ctk.CTkLabel(
                    row,
                    text="nie istnieje",
                    font=ctk.CTkFont(family=FONT_FAMILY, size=10),
                    text_color=COLOR_HIGH_RISK,
                ).pack(side="right")

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
        # A file name is not touched by anonymization, yet it travels with
        # every output, the review manifest and the export - so a name
        # that itself carries a PESEL or an e-mail defeats an otherwise
        # clean run. Surfaced here, at the moment files are added, rather
        # than after processing when it is too late to rename anything.
        filename_warning = format_filename_pii_warning(
            [path.name for path in self.selected_paths]
        )
        self._update_readiness(
            status_override=filename_warning
            or format_drop_result(added, len(unsupported))
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
            if not self.quick_actions_collapsed:
                # The collapsed rail's button is icon-only ("▶", no room
                # for a label) - leave its text alone there rather than
                # overwrite it with "Anonimizuj N plików" on every
                # refresh; IconTooltip already explains what it does.
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
        apply_subtle_scrollbar(scroll)

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
            # Re-running into the same folder is the normal way people
            # work, and nothing ever removed the previous run's files -
            # so folders accumulate one numbered generation per run. An
            # audit of what the app leaves on disk flagged that directly:
            # more generations is more to look after, and an old
            # generation can be less redacted than the current one while
            # looking just as finished.
            ctk.CTkButton(
                row,
                text="Wyczyść stare",
                width=110,
                height=30,
                corner_radius=8,
                fg_color="transparent",
                border_width=1,
                border_color=COLOR_BORDER,
                hover_color=COLOR_ICON_IDLE,
                text_color=COLOR_TEXT,
                font=ctk.CTkFont(family=FONT_FAMILY, size=11),
                command=lambda p=folder_path: self.clean_output_folder(p),
            ).pack(side="right", padx=(0, 8))
        else:
            ctk.CTkLabel(
                row,
                text="folder nie istnieje",
                font=ctk.CTkFont(family=FONT_FAMILY, size=10),
                text_color=COLOR_HIGH_RISK,
            ).pack(side="right")

    def clean_output_folder(self, folder_path: str) -> None:
        """Remove superseded output generations from one folder, after
        showing exactly what would go. Never deletes without that
        confirmation, and only ever considers files this app itself wrote
        (see output_cleanup) - pointing the output at the folder the
        source documents live in is normal, and those must be safe."""
        plan = build_output_cleanup_plan(folder_path)
        summary = format_cleanup_plan_summary(plan)
        if plan.is_empty:
            messagebox.showinfo("Wyczyść stare wyniki", summary, parent=self.root)
            return
        confirmed = messagebox.askyesno(
            "Wyczyść stare wyniki",
            f"{summary}\n\nUsunąć je teraz? Tej operacji nie można cofnąć.",
            parent=self.root,
        )
        if not confirmed:
            return
        removed, failed = apply_output_cleanup_plan(plan)
        message = f"Usunięto {removed} plików."
        if failed:
            message += f" Nie udało się usunąć: {failed}."
        messagebox.showinfo("Wyczyść stare wyniki", message, parent=self.root)
        self.show_history_screen()

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

        # A small charming animation (a pencil "copying" between two
        # pages) instead of a single static document emoji - per direct
        # user feedback that the processing screen felt bare. Advanced
        # one frame per _update_processing call (see below) rather than
        # its own independent after()-rescheduled timer: anonymize_batch
        # runs synchronously on the main thread, only pumped by
        # update_idletasks() between files (not update(), which is what
        # actually processes pending after() timers) - a separate timer
        # would sit frozen for the whole batch and only catch up in one
        # stuttering burst once the blocking call finally returned.
        # Driving it from the same real per-file progress event the
        # progress bar/labels already use keeps it honestly tied to
        # actual progress instead of a fake, disconnected animation.
        self._processing_animation_step = 0
        self.processing_animation_label = ctk.CTkLabel(
            wrapper,
            text=format_processing_animation_frame(0),
            font=ctk.CTkFont(family=FONT_FAMILY, size=28),
            text_color=COLOR_ACCENT,
        )
        self.processing_animation_label.pack(pady=(0, 24))

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
        if self.processing_animation_label is not None:
            # Advanced one frame per real progress event rather than its
            # own independent timer - see the comment in
            # show_processing_screen for why a separate after()-driven
            # timer would not actually animate during the batch's
            # synchronous run.
            self._processing_animation_step += 1
            self.processing_animation_label.configure(
                text=format_processing_animation_frame(self._processing_animation_step)
            )
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
        apply_subtle_scrollbar(scroll)
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
            command=self._bulk_approve_selected,
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

    def _bulk_approve_selected(self) -> None:
        targets = [
            item
            for item in self.review_items
            if item.output_name in self.selected_review_output_names
        ]
        self._confirm_then_approve(targets)

    def _confirm_then_approve(self, items: list[ReviewItem]) -> None:
        """Approve one or more review items - unless the user has already
        dismissed ApprovalLockWarningDialog for good, show it once (even
        for a multi-file bulk approve - one dialog covering all of them,
        not one per file) before actually changing anything, since
        approving permanently locks each file's magic-pen editing (see
        ComparisonWindow.locked). Already-approved items are dropped from
        ``items`` first - re-clicking "✓" on one changes nothing, so it
        must not re-show a warning about a lock that is already in effect.
        """
        items = [item for item in items if item.status != REVIEW_STATUS_APPROVED]
        if not items:
            return
        if hint_is_dismissed(APPROVAL_LOCK_HINT_ID):
            self._approve_items_confirmed(items)
            return
        ApprovalLockWarningDialog(
            self, len(items), lambda: self._approve_items_confirmed(items)
        )

    def _approve_items_confirmed(self, items: list[ReviewItem]) -> None:
        approved_names = {item.output_name for item in items}
        for item in items:
            self.set_review_status(item, REVIEW_STATUS_APPROVED)
        # Same "clear the acted-on selection" behavior _bulk_set_status
        # already has - a no-op for the single-item card button, where
        # that item was never part of the selection in the first place.
        self.selected_review_output_names -= approved_names
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
            lambda: self._confirm_then_approve([item]),
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


