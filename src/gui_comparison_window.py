"""Side-by-side original-vs-anonymized comparison window, including
the magic pen manual redaction editor, and the document preview
rendering helpers it (and the review screen) share."""

from __future__ import annotations

import os
import sys
import tkinter as tk
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import NamedTuple

import customtkinter as ctk
from PIL import Image, ImageTk

try:
    from .file_readers import (
        read_docx_file,
        read_txt_file,
    )
    from .file_writers import internal_artifacts_dir
    from .gui_helpers import (
        COLOR_ACCENT,
        COLOR_ACCENT_HOVER,
        COLOR_BG,
        COLOR_BORDER,
        COLOR_CARD,
        COLOR_HIGH_RISK,
        COLOR_ICON_IDLE,
        COLOR_TEXT,
        COLOR_TEXT_MUTED,
        FONT_FAMILY,
        LEGEND_ITEMS,
        ZOOM_LINK_HINT_ID,
        IconTooltip,
        _bring_window_to_front,
        apply_subtle_scrollbar,
        dismiss_hint,
        hint_is_dismissed,
    )
    from .manual_redaction import (
        EMPTY_MANUAL_EDITS,
        MANUAL_REDACTION_LABEL,
        ManualEdits,
        ManualRect,
        apply_manual_redaction_count_to_report_text,
        apply_pending_overrides,
        compute_visible_redaction_rects,
        load_manual_edits,
        manual_edits_path,
        rect_info_key,
        regenerate_pdf_with_manual_overrides,
        save_manual_edits,
    )
    from .review import (
        REVIEW_STATUS_APPROVED,
        REVIEW_STATUS_NEEDS_REVIEW,
        ReviewItem,
    )
except ImportError:
    from file_readers import (
        read_docx_file,
        read_txt_file,
    )
    from file_writers import internal_artifacts_dir
    from gui_helpers import (
        COLOR_ACCENT,
        COLOR_ACCENT_HOVER,
        COLOR_BG,
        COLOR_BORDER,
        COLOR_CARD,
        COLOR_HIGH_RISK,
        COLOR_ICON_IDLE,
        COLOR_TEXT,
        COLOR_TEXT_MUTED,
        FONT_FAMILY,
        LEGEND_ITEMS,
        ZOOM_LINK_HINT_ID,
        IconTooltip,
        _bring_window_to_front,
        apply_subtle_scrollbar,
        dismiss_hint,
        hint_is_dismissed,
    )
    from manual_redaction import (
        EMPTY_MANUAL_EDITS,
        MANUAL_REDACTION_LABEL,
        ManualEdits,
        ManualRect,
        apply_manual_redaction_count_to_report_text,
        apply_pending_overrides,
        compute_visible_redaction_rects,
        load_manual_edits,
        manual_edits_path,
        rect_info_key,
        regenerate_pdf_with_manual_overrides,
        save_manual_edits,
    )
    from review import (
        REVIEW_STATUS_APPROVED,
        REVIEW_STATUS_NEEDS_REVIEW,
        ReviewItem,
    )

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .gui_app import AnonymizerApp

def pdf_page_zoom(page_width_pt: float, target_width: int) -> float:
    """Return the render zoom used to scale a PDF page to ``target_width``."""
    safe_width = max(page_width_pt, 1)
    return target_width / safe_width


def ctk_widget_scaling_factor(widget: object) -> float:
    """Return the current CustomTkinter DPI scaling factor for ``widget``.

    CTkImage applies this automatically; code that draws directly onto a
    plain Tk widget (like the magic pen's tk.Canvas) has to apply it by
    hand to render at a matching on-screen size. Always falls back to 1.0
    (no scaling) rather than raising - a display-scaling mismatch is a
    cosmetic issue, never worth crashing the preview over.
    """
    try:
        return float(ctk.ScalingTracker.get_widget_scaling(widget))
    except Exception:  # noqa: BLE001 - cosmetic fallback, must never crash
        return 1.0


def canvas_point_to_pdf_point(cx: float, cy: float, zoom: float) -> tuple[float, float]:
    """Convert a canvas pixel coordinate back to PDF point coordinates."""
    safe_zoom = zoom if zoom else 1.0
    return (cx / safe_zoom, cy / safe_zoom)


def normalize_drag_rect(
    x0: float, y0: float, x1: float, y1: float
) -> tuple[float, float, float, float]:
    """Return a rectangle with x0<=x1 and y0<=y1, regardless of drag direction."""
    return (min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1))


def is_degenerate_drag_rect(
    x0: float, y0: float, x1: float, y1: float, *, min_size: float = 4.0
) -> bool:
    """True when a dragged rectangle is too small to be an intentional selection."""
    return (x1 - x0) < min_size or (y1 - y0) < min_size


BASE_PREVIEW_WIDTH = 460
ZOOM_MIN = 0.5
ZOOM_MAX = 3.0
ZOOM_STEP = 0.1
ZOOM_DEFAULT = 1.0
ZOOM_LINK_HINT_ID = "zoom_link_toggle"


def clamp_zoom_level(
    value: float, minimum: float = ZOOM_MIN, maximum: float = ZOOM_MAX
) -> float:
    """Clamp a preview zoom multiplier to a sane, always-legible range."""
    return round(min(max(value, minimum), maximum), 2)


def zoom_percent_label(value: float) -> str:
    """Format a zoom multiplier as a whole-percent label, e.g. 1.2 -> '120%'."""
    return f"{round(value * 100)}%"


def zoom_step_from_scroll_event(event: object) -> int:
    """Return -1/0/+1 zoom-out/none/zoom-in for one Ctrl+scroll event."""
    event_num = getattr(event, "num", None)
    if event_num == 4:
        return 1
    if event_num == 5:
        return -1
    delta = int(getattr(event, "delta", 0) or 0)
    if delta > 0:
        return 1
    if delta < 0:
        return -1
    return 0


def scroll_sync_units(event: object) -> int:
    """Return the exact canvas ``yview scroll`` unit count CustomTkinter's
    own CTkScrollableFrame uses internally for one wheel event.

    Deliberately mirrors that library's private ``_mouse_wheel_all``
    formula (not the more forgiving ``mousewheel_scroll_units`` used
    elsewhere) so a linked pane scrolls in exact lockstep with the pane
    the cursor is actually over, instead of gradually drifting out of
    sync from using a different step size.
    """
    event_num = getattr(event, "num", None)
    if event_num == 4:
        return -1
    if event_num == 5:
        return 1
    delta = int(getattr(event, "delta", 0) or 0)
    if sys.platform == "darwin":
        return -delta
    return -int(delta / 6)


def zoom_link_glyph(linked: bool) -> str:
    """Return the padlock glyph for the zoom-link toggle's current state.

    A closed padlock ("locked together") for linked zoom and an open
    padlock ("free to move independently") for unlinked - the glyph itself
    should suggest the meaning without requiring a hover or prior
    knowledge of the convention.
    """
    return "🔒" if linked else "🔓"


def zoom_link_tooltip_text(linked: bool) -> str:
    """Return hover-tooltip text describing the zoom-link toggle's state
    and what clicking it will do next."""
    if linked:
        return (
            "🔒 Powiększenie połączone: oba podglądy skalują się razem. "
            "Kliknij, aby ustawiać każdy osobno."
        )
    return (
        "🔓 Powiększenie niezależne: każdy podgląd osobno. "
        "Kliknij, aby połączyć oba."
    )


def find_rect_at_point(
    rects: Sequence[Mapping[str, object]], page_number: int, x: float, y: float
) -> Mapping[str, object] | None:
    """Return the top-most rect on a page whose bounds contain the point."""
    for rect in reversed(list(rects)):
        if int(rect.get("page", -1)) != page_number:
            continue
        if (
            float(rect["x0"]) <= x <= float(rect["x1"])
            and float(rect["y0"]) <= y <= float(rect["y1"])
        ):
            return rect
    return None


def _render_text_block(parent: ctk.CTkBaseClass, text: str, zoom: float = 1.0) -> None:
    box = ctk.CTkTextbox(
        parent,
        width=int(440 * zoom),
        height=int(600 * zoom),
        wrap="word",
        fg_color=COLOR_CARD,
        text_color=COLOR_TEXT,
        font=ctk.CTkFont(family=FONT_FAMILY, size=max(1, round(11 * zoom))),
    )
    box.pack(fill="both", expand=True, padx=4, pady=4)
    box.insert("1.0", text)
    box.configure(state="disabled")


class RenderedPreview(NamedTuple):
    """What render_document_preview built: the CTkImage objects (kept
    alive by the caller), a page-number -> widget map for jump-to-page
    navigation (PDF only - a page concept genuinely doesn't apply to a
    DOCX/TXT/image preview), and the page count that map's size already
    encodes but a caller open-coding ``len(page_widgets)`` everywhere
    would be worse than just naming it once here.
    """

    images: list[ctk.CTkImage]
    page_widgets: dict[int, ctk.CTkBaseClass]
    page_count: int


def render_document_preview(
    parent: ctk.CTkBaseClass, path: Path, target_width: int = BASE_PREVIEW_WIDTH
) -> RenderedPreview:
    """Render a document's pages/content into the given scrollable frame.

    ``target_width`` also scales DOCX/TXT text-block previews (relative to
    ``BASE_PREVIEW_WIDTH``), so the same zoom control works for every
    supported preview type.

    Returns the CTkImage objects created so the caller can keep a strong
    reference alive for the window's lifetime (Tk drops images that are
    only referenced by the widget itself once the local variable is gone),
    plus the per-page widgets a page-navigation control can scroll to.
    """
    images: list[ctk.CTkImage] = []
    page_widgets: dict[int, ctk.CTkBaseClass] = {}
    suffix = path.suffix.lower()
    text_zoom = target_width / BASE_PREVIEW_WIDTH
    try:
        if suffix == ".pdf":
            import pymupdf as fitz

            with fitz.open(path) as document:
                for page_index, page in enumerate(document, start=1):
                    page_width = max(page.rect.width, 1)
                    zoom = target_width / page_width
                    pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom))
                    pil_image = Image.frombytes(
                        "RGB", (pix.width, pix.height), pix.samples
                    )
                    ctk_image = ctk.CTkImage(
                        light_image=pil_image,
                        size=(pix.width, pix.height),
                    )
                    images.append(ctk_image)
                    label = ctk.CTkLabel(parent, image=ctk_image, text="")
                    label.pack(pady=6)
                    page_widgets[page_index] = label
        elif suffix in (".png", ".jpg", ".jpeg", ".tif", ".tiff"):
            pil_image = Image.open(path)
            pil_image.thumbnail((target_width, 3000))
            ctk_image = ctk.CTkImage(
                light_image=pil_image, size=pil_image.size
            )
            images.append(ctk_image)
            ctk.CTkLabel(parent, image=ctk_image, text="").pack(pady=6)
        elif suffix == ".docx":
            _render_text_block(parent, read_docx_file(path), zoom=text_zoom)
        elif suffix == ".txt":
            _render_text_block(parent, read_txt_file(path), zoom=text_zoom)
        else:
            ctk.CTkLabel(
                parent,
                text=f"Brak podglądu dla typu pliku: {suffix or 'nieznany'}",
                text_color=COLOR_TEXT_MUTED,
            ).pack(pady=30)
    except Exception:  # noqa: BLE001 - preview must never crash the app
        ctk.CTkLabel(
            parent,
            text="Nie udało się wczytać podglądu tego pliku.",
            text_color=COLOR_HIGH_RISK,
            wraplength=380,
            justify="left",
        ).pack(pady=30, padx=16)
        page_widgets = {}
    return RenderedPreview(images, page_widgets, len(page_widgets))


class ComparisonWindow:
    """Side-by-side original-vs-anonymized preview.

    For PDF outputs with a known original from the current session, the
    right pane ("Po anonimizacji") also offers the magic pen: manually hide
    a piece of text automatic detection missed, or undo a specific
    automatically detected rectangle. Every edit is staged locally and only
    takes effect on "Zapisz zmiany", which regenerates the true-redacted PDF
    from the original source file (see manual_redaction.py) — never by
    drawing over the already redacted output.
    """

    def __init__(
        self,
        app: AnonymizerApp,
        item: ReviewItem,
        original_path: Path | None,
        result_path: Path,
    ) -> None:
        self.app = app
        self.item = item
        self.source_path = original_path
        self.original_path = original_path
        self.result_path = result_path
        self._images: list[ctk.CTkImage] = []
        self._tk_images: list[ImageTk.PhotoImage] = []
        self._page_canvases: dict[int, tk.Canvas] = {}
        self._page_zoom: dict[int, float] = {}
        self._overlay_ids: dict[int, list[int]] = {}
        self._drag_start: tuple[float, float] | None = None
        self._drag_rect_id: int | None = None
        self.edits: ManualEdits = EMPTY_MANUAL_EDITS
        self.visible_rects: list[dict[str, object]] = []
        self.pending_remove_keys: set = set()
        self.pending_add_rects: list[ManualRect] = []
        self.save_button: ctk.CTkButton | None = None
        self.cancel_button: ctk.CTkButton | None = None
        self.pen_status_label: ctk.CTkLabel | None = None
        # Manual-mode tool pinning: None means the modeless default (LMB
        # draws, RMB always erases). Pinning to "draw" or "erase" locks
        # LMB to that one action - RMB keeps working as erase regardless,
        # so pinning never takes away the existing shortcut, only adds a
        # single-button way to work for anyone who'd rather pick a tool
        # explicitly. _transient_tool tracks a chip lighting up because
        # its action is actually happening right now (independent of
        # pinning), cleared the moment that press/click ends.
        self.pinned_tool: str | None = None
        self._transient_tool: str | None = None
        self._tool_chips: dict[str, ctk.CTkButton] = {}
        self.left_frame: ctk.CTkScrollableFrame | None = None
        self.right_frame: ctk.CTkScrollableFrame | None = None
        self.original_zoom = ZOOM_DEFAULT
        self.result_zoom = ZOOM_DEFAULT
        self.zoom_linked = True
        self.original_zoom_label: ctk.CTkEntry | None = None
        self.result_zoom_label: ctk.CTkEntry | None = None
        self._link_buttons: list[ctk.CTkButton] = []
        self._link_tooltips: list[IconTooltip] = []
        # "Łapka" (hand/pan) and "lupa" (zoom-on-scroll) are one shared
        # tool state for the whole window, not per-pane - toggle buttons
        # exist in both pane headers for convenience, kept in sync via
        # these lists, matching the existing zoom-link button pattern.
        self.active_pointer_tool: str | None = None
        self._hand_buttons: list[ctk.CTkButton] = []
        self._zoom_tool_buttons: list[ctk.CTkButton] = []
        # Page navigation ("skocz do strony X/N", per direct user
        # feedback): page-number -> widget maps to scroll to (the
        # "Oryginał" pane's CTkLabel widgets from render_document_preview,
        # or - on the magic-pen result pane - self._page_canvases, which
        # already serves that exact purpose), plus the nav row widgets
        # themselves so _update_page_nav_controls can show/hide/update
        # them after every (re)render.
        self._original_page_widgets: dict[int, ctk.CTkBaseClass] = {}
        self._result_page_widgets: dict[int, ctk.CTkBaseClass] = {}
        self.original_page_count = 0
        self.result_page_count = 0
        self.original_current_page = 0
        self.result_current_page = 0
        self._page_nav_rows: dict[str, ctk.CTkFrame] = {}
        self._page_entries: dict[str, ctk.CTkEntry] = {}
        self._page_total_labels: dict[str, ctk.CTkLabel] = {}
        # Legend/tool-chip sidebar collapse (see _build_magic_pen_sidebar)
        # - per-window, resets to expanded each time a comparison window
        # opens, the same way zoom/pan state already does.
        self.legend_sidebar_collapsed = False
        self.content_row: ctk.CTkFrame | None = None
        self._sidebar_widget: ctk.CTkFrame | None = None

        self.magic_pen_available = bool(
            original_path is not None
            and original_path.exists()
            and result_path.exists()
            and result_path.suffix.lower() == ".pdf"
        )
        # Editable (auto-detected redactions can be un-redacted, new ones
        # drawn) right up until the file is approved - approving is a
        # deliberate, one-way "this is final" action per direct user
        # feedback (see ApprovalLockWarningDialog, shown before the app
        # ever sets this status), so once item.status is already
        # REVIEW_STATUS_APPROVED at the moment this window opens, the
        # magic pen renders read-only instead of interactive. Evaluated
        # once here from the snapshot passed in, not re-checked live
        # against self.app.review_items while the window stays open.
        self.locked = item.status == REVIEW_STATUS_APPROVED

        window = ctk.CTkToplevel(app.root)
        self.window = window
        window.title(f"Porównanie - {item.output_name}")
        window.geometry("1120x780")
        window.minsize(760, 520)
        window.resizable(True, True)
        window.configure(fg_color=COLOR_BG)
        # Deliberately NOT window.transient(app.root): on Windows, a
        # transient window is treated as a dialog of its parent and loses
        # the native maximize button even with resizable(True, True) set -
        # this window needs to behave like a normal, fully maximizable
        # window so the magic pen has room to work precisely.
        window.bind("<Control-MouseWheel>", self._on_ctrl_scroll)
        window.bind("<Control-Button-4>", self._on_ctrl_scroll)
        window.bind("<Control-Button-5>", self._on_ctrl_scroll)
        # Plain (no Ctrl) scroll: while panes are locked together, mirror
        # it onto the other pane too, so scrolling either one moves both -
        # each CTkScrollableFrame already scrolls itself via its own
        # internal bind_all, this only adds the *other* pane's half.
        window.bind("<MouseWheel>", self._on_scroll_sync)
        window.bind("<Button-4>", self._on_scroll_sync)
        window.bind("<Button-5>", self._on_scroll_sync)
        window.bind("<Escape>", self._clear_pointer_tool)
        window.protocol("WM_DELETE_WINDOW", self._close)

        ctk.CTkLabel(
            window,
            text=item.output_name,
            font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"),
            text_color=COLOR_TEXT,
        ).pack(anchor="w", padx=20, pady=(16, 4))

        # content_row holds the draggable original/result split on the
        # left and, for PDFs, the fixed-width magic pen sidebar
        # ("Korekta anonimizacji" + color legend) on the right - a
        # standalone column beside both panes rather than a toolbar row
        # above one of them, so both pane headers stay identical and
        # naturally start at the same height with no special-casing
        # needed (the toolbar-above-header/matching-spacer trick from
        # earlier the same day is retired along with the toolbar itself).
        content_row = ctk.CTkFrame(window, fg_color="transparent")
        content_row.pack(fill="both", expand=True, padx=20, pady=(4, 8))
        self.content_row = content_row

        # Packed *before* the paned splitter below, on purpose: Tk's
        # pack() hands out space in packing order, not visual order (the
        # same rule this project's other fixed-width panels already lean
        # on) - packing this fixed-width sidebar first guarantees it
        # keeps its own width and is never the one silently clipped on a
        # narrow window, which is exactly what used to happen when it was
        # packed after the splitter (confirmed as a real bug: the legend
        # and tool chips could get cut off entirely). It is still visually
        # the right-hand column, since side="right" reserves its space
        # from the row's right edge regardless of packing order.
        if self.magic_pen_available:
            self._sidebar_widget = self._build_magic_pen_sidebar(content_row)
            self._sidebar_widget.pack(side="right", fill="y", padx=(12, 0))

        # A real draggable splitter (tk.PanedWindow) instead of a fixed
        # 50/50 grid: dragging the sash resizes one side and shrinks the
        # other, like a normal split view.
        paned = tk.PanedWindow(
            content_row,
            orient=tk.HORIZONTAL,
            sashwidth=6,
            sashrelief="flat",
            bg=COLOR_BORDER,
            bd=0,
            showhandle=False,
        )
        paned.pack(side="left", fill="both", expand=True)

        left_container = ctk.CTkFrame(paned, fg_color="transparent")
        right_container = ctk.CTkFrame(paned, fg_color="transparent")
        paned.add(left_container, minsize=280, width=530, stretch="always")
        paned.add(right_container, minsize=280, width=530, stretch="always")

        self._build_pane_header(left_container, "Oryginał", "original").pack(
            fill="x", pady=(0, 6)
        )
        self._build_pane_header(right_container, "Po anonimizacji", "result").pack(
            fill="x", pady=(0, 6)
        )

        left_frame = ctk.CTkScrollableFrame(
            left_container, fg_color=COLOR_CARD, corner_radius=10, label_text=""
        )
        left_frame.pack(fill="both", expand=True)
        apply_subtle_scrollbar(left_frame)
        self.left_frame = left_frame
        right_frame = ctk.CTkScrollableFrame(
            right_container, fg_color=COLOR_CARD, corner_radius=10, label_text=""
        )
        right_frame.pack(fill="both", expand=True)
        apply_subtle_scrollbar(right_frame)
        self.right_frame = right_frame

        self._rebuild_original_pane()

        if self.magic_pen_available:
            self.edits = load_manual_edits(manual_edits_path(result_path))
            self._reload_visible_rects()
            self._build_magic_pen_pane(right_frame)
        else:
            self._rebuild_result_pane()

        if self.magic_pen_available and not self.locked:
            # Tk's pack() hands out space in the order widgets are
            # packed, not visual order - whatever is packed first gets
            # first claim on the row's width, and whatever is packed
            # last is the first to be squeezed out when the window gets
            # narrow. "Zapisz zmiany" is packed before "Anuluj zmiany"
            # for exactly that reason: it must never be the one that
            # disappears when the window is shrunk (confirmed as a real
            # bug earlier the same day, in the toolbar this replaces).
            bottom_actions = ctk.CTkFrame(window, fg_color="transparent")
            bottom_actions.pack(fill="x", padx=20, pady=(0, 8))

            # Tool "lamps" - per direct user feedback, moved out of the
            # (collapsible) legend sidebar into this always-visible row,
            # so they stay usable even while that sidebar is hidden.
            # Packed in their own sub-row above save/cancel, same
            # click-to-pin behavior as before (see _toggle_pinned_tool).
            tool_row = ctk.CTkFrame(bottom_actions, fg_color="transparent")
            tool_row.pack(fill="x", pady=(0, 6))
            self._tool_chips["draw"] = self._build_tool_chip(
                tool_row, "✏", "Dodaj zaznaczenie", "draw"
            )
            self._tool_chips["erase"] = self._build_tool_chip(
                tool_row, "🧹", "Usuń zaznaczenie", "erase"
            )
            self.pen_status_label = ctk.CTkLabel(
                tool_row,
                text="",
                font=ctk.CTkFont(family=FONT_FAMILY, size=11),
                text_color=COLOR_TEXT_MUTED,
            )
            self.pen_status_label.pack(side="left", padx=(8, 0))
            self._refresh_tool_chip_visuals()

            self.save_button = ctk.CTkButton(
                bottom_actions,
                text="Zapisz zmiany",
                width=140,
                height=32,
                corner_radius=8,
                fg_color=COLOR_ICON_IDLE,
                hover_color=COLOR_ACCENT_HOVER,
                text_color=COLOR_TEXT_MUTED,
                font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
                state="disabled",
                command=self._save_pending_changes,
            )
            self.save_button.pack(side="right")
            self.cancel_button = ctk.CTkButton(
                bottom_actions,
                text="Anuluj zmiany",
                width=130,
                height=32,
                corner_radius=8,
                fg_color="transparent",
                hover_color=COLOR_ICON_IDLE,
                text_color=COLOR_TEXT_MUTED,
                font=ctk.CTkFont(family=FONT_FAMILY, size=12),
                state="disabled",
                command=self._cancel_pending_changes,
            )
            self.cancel_button.pack(side="right", padx=(0, 8))
        elif not self.magic_pen_available:
            # No sidebar in this case (magic pen is PDF-only), so the
            # color legend still needs a home - the existing horizontal
            # row at the bottom, same as before. A locked-but-available
            # pane already has the legend in its sidebar (see
            # _build_magic_pen_sidebar), so it needs neither this row nor
            # the save/cancel row above.
            app._build_legend_row(window)

        ctk.CTkButton(
            window,
            text="Zamknij",
            width=140,
            height=36,
            corner_radius=8,
            fg_color=COLOR_ACCENT,
            hover_color=COLOR_ACCENT_HOVER,
            command=self._close,
        ).pack(pady=(0, 16))

        window.after(700, self._maybe_show_zoom_link_hint)
        # Opening a preview should visibly come to the front, not appear
        # behind whatever window was already open.
        _bring_window_to_front(window)

    def _close(self) -> None:
        """Close this window and bring the main app window back to front -
        matches _bring_window_to_front's rule for opening: whichever
        window the user just acted on should end up on top."""
        self.window.destroy()
        _bring_window_to_front(self.app.root)

    # -- zoom: independent or linked, like a dual-zone climate control ------

    def _build_pane_header(
        self, parent: ctk.CTkFrame, title: str, side: str
    ) -> ctk.CTkFrame:
        header = ctk.CTkFrame(parent, fg_color="transparent")
        ctk.CTkLabel(
            header,
            text=title,
            font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
            text_color=COLOR_TEXT_MUTED,
        ).pack(side="left")

        zoom_row = ctk.CTkFrame(header, fg_color="transparent")
        zoom_row.pack(side="right")
        ctk.CTkButton(
            zoom_row,
            text="－",
            width=24,
            height=22,
            corner_radius=6,
            fg_color=COLOR_ICON_IDLE,
            hover_color=COLOR_ACCENT_HOVER,
            text_color=COLOR_TEXT,
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            command=lambda: self._adjust_zoom(side, -1),
        ).pack(side="left", padx=(0, 2))
        zoom_label = ctk.CTkEntry(
            zoom_row,
            width=42,
            height=22,
            justify="center",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            text_color=COLOR_TEXT_MUTED,
            fg_color=COLOR_CARD,
            border_width=1,
            border_color=COLOR_BORDER,
        )
        zoom_label.insert(0, zoom_percent_label(ZOOM_DEFAULT))
        zoom_label.bind(
            "<Return>", lambda _e, s=side: self._commit_zoom_entry(s)
        )
        zoom_label.bind(
            "<FocusOut>", lambda _e, s=side: self._commit_zoom_entry(s)
        )
        zoom_label.pack(side="left")
        IconTooltip(
            zoom_label,
            "Wpisz wartość i naciśnij Enter, by ustawić powiększenie ręcznie.",
            enabled=self.app.show_usage_hints,
        )
        ctk.CTkButton(
            zoom_row,
            text="＋",
            width=24,
            height=22,
            corner_radius=6,
            fg_color=COLOR_ICON_IDLE,
            hover_color=COLOR_ACCENT_HOVER,
            text_color=COLOR_TEXT,
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            command=lambda: self._adjust_zoom(side, 1),
        ).pack(side="left", padx=(2, 6))

        hand_button = ctk.CTkButton(
            zoom_row,
            text="\U0001f590",
            width=26,
            height=22,
            corner_radius=6,
            fg_color=COLOR_ICON_IDLE,
            hover_color=COLOR_ACCENT_HOVER,
            text_color=COLOR_TEXT,
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            command=lambda: self._toggle_pointer_tool("hand"),
        )
        hand_button.pack(side="left", padx=(0, 2))
        self._hand_buttons.append(hand_button)
        IconTooltip(
            hand_button,
            "Łapka: przeciągnij, by przesunąć widok bez użycia scrolla. "
            "Kliknij ponownie lub Esc, by wyłączyć.",
            enabled=self.app.show_usage_hints,
        )
        zoom_tool_button = ctk.CTkButton(
            zoom_row,
            text="\U0001f50d",
            width=26,
            height=22,
            corner_radius=6,
            fg_color=COLOR_ICON_IDLE,
            hover_color=COLOR_ACCENT_HOVER,
            text_color=COLOR_TEXT,
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            command=lambda: self._toggle_pointer_tool("zoom"),
        )
        zoom_tool_button.pack(side="left", padx=(0, 6))
        self._zoom_tool_buttons.append(zoom_tool_button)
        IconTooltip(
            zoom_tool_button,
            "Lupa: przewiń, by powiększać/pomniejszać bez Ctrl. "
            "Wskazówka: Ctrl + scroll działa zawsze, nawet bez lupy. "
            "Kliknij ponownie lub Esc, by wyłączyć.",
            enabled=self.app.show_usage_hints,
        )

        link_button = ctk.CTkButton(
            zoom_row,
            text=zoom_link_glyph(self.zoom_linked),
            width=26,
            height=22,
            corner_radius=6,
            fg_color=COLOR_ACCENT,
            hover_color=COLOR_ACCENT_HOVER,
            text_color="#FFFFFF",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            command=self._toggle_zoom_link,
        )
        link_button.pack(side="left")
        self._link_buttons.append(link_button)
        self._link_tooltips.append(
            IconTooltip(
                link_button,
                zoom_link_tooltip_text(self.zoom_linked),
                enabled=self.app.show_usage_hints,
            )
        )
        if side == "original":
            self.original_zoom_label = zoom_label
        else:
            self.result_zoom_label = zoom_label

        # Page navigation ("skocz do strony X/N") - built now but not
        # packed yet, since the page count isn't known until the pane's
        # first render; _update_page_nav_controls packs/unpacks and
        # refreshes it from there on, for every (re)build of this pane.
        page_nav_row = ctk.CTkFrame(header, fg_color="transparent")
        self._page_nav_rows[side] = page_nav_row
        ctk.CTkButton(
            page_nav_row,
            text="◀",
            width=22,
            height=20,
            corner_radius=6,
            fg_color=COLOR_ICON_IDLE,
            hover_color=COLOR_ACCENT_HOVER,
            text_color=COLOR_TEXT,
            font=ctk.CTkFont(family=FONT_FAMILY, size=10),
            command=lambda: self._go_to_page(side, -1),
        ).pack(side="left", padx=(0, 4))
        ctk.CTkLabel(
            page_nav_row,
            text="Strona",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            text_color=COLOR_TEXT_MUTED,
        ).pack(side="left", padx=(0, 4))
        page_entry = ctk.CTkEntry(
            page_nav_row,
            width=36,
            height=20,
            justify="center",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            text_color=COLOR_TEXT_MUTED,
            fg_color=COLOR_CARD,
            border_width=1,
            border_color=COLOR_BORDER,
        )
        page_entry.bind("<Return>", lambda _e, s=side: self._commit_page_entry(s))
        page_entry.bind("<FocusOut>", lambda _e, s=side: self._commit_page_entry(s))
        page_entry.pack(side="left")
        self._page_entries[side] = page_entry
        IconTooltip(
            page_entry,
            "Wpisz numer strony i naciśnij Enter, by tam przeskoczyć.",
            enabled=self.app.show_usage_hints,
        )
        page_total_label = ctk.CTkLabel(
            page_nav_row,
            text="/ 1",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            text_color=COLOR_TEXT_MUTED,
        )
        page_total_label.pack(side="left", padx=(2, 4))
        self._page_total_labels[side] = page_total_label
        ctk.CTkButton(
            page_nav_row,
            text="▶",
            width=22,
            height=20,
            corner_radius=6,
            fg_color=COLOR_ICON_IDLE,
            hover_color=COLOR_ACCENT_HOVER,
            text_color=COLOR_TEXT,
            font=ctk.CTkFont(family=FONT_FAMILY, size=10),
            command=lambda: self._go_to_page(side, 1),
        ).pack(side="left")

        return header

    def _on_ctrl_scroll(self, event: object) -> None:
        widget = self.window.winfo_containing(event.x_root, event.y_root)
        side = self._pane_side_for_widget(widget)
        if side is None:
            return
        self._adjust_zoom(side, zoom_step_from_scroll_event(event))

    def _on_scroll_sync(self, event: object) -> None:
        """Mirror plain (no Ctrl) scrolling onto the other pane while the
        two are locked together. The pane under the cursor already scrolls
        itself via CTkScrollableFrame's own internal binding - this only
        scrolls the *other* one, by the same amount, so both move as one.
        A no-op once unlinked: each pane is then free to scroll on its own.
        """
        widget = self.window.winfo_containing(event.x_root, event.y_root)
        side = self._pane_side_for_widget(widget)
        if side is None:
            return
        if self.active_pointer_tool == "zoom":
            # "Lupa" active: plain scroll zooms, same as if Ctrl were
            # held - Ctrl+scroll itself keeps working too either way.
            self._adjust_zoom(side, zoom_step_from_scroll_event(event))
            return
        if not self.zoom_linked:
            return
        other_frame = self.right_frame if side == "original" else self.left_frame
        self._scroll_pane_by(other_frame, scroll_sync_units(event))

    @staticmethod
    def _find_textbox_in(frame: ctk.CTkScrollableFrame) -> ctk.CTkTextbox | None:
        for widget in frame.winfo_children():
            if isinstance(widget, ctk.CTkTextbox):
                return widget
        return None

    def _scroll_pane_by(self, frame: ctk.CTkScrollableFrame | None, units: int) -> None:
        """Scroll one pane by ``units``.

        A DOCX/TXT pane's only child is one fixed-height CTkTextbox (see
        _render_text_block) - scrolling through a document longer than
        that box is the textbox's *own* internal yview, not a move of the
        outer CTkScrollableFrame's canvas (which barely has anything else
        to scroll), so mirroring has to target the textbox directly or a
        long document's sync is invisible even though this method runs.
        A PDF/image pane has no such textbox, so it falls back to the
        outer canvas as before. Reaches into private
        CTkTextbox._textbox/CTkScrollableFrame._parent_canvas - there is
        no public API for programmatic scrolling - so this stays
        defensive and silently does nothing on any error rather than risk
        crashing the preview over a cosmetic scroll-sync feature.
        """
        if frame is None or units == 0:
            return
        textbox = self._find_textbox_in(frame)
        if textbox is not None:
            try:
                textbox._textbox.yview_scroll(units, "units")
            except tk.TclError:
                pass
            return
        canvas = getattr(frame, "_parent_canvas", None)
        if canvas is None:
            return
        try:
            if canvas.yview() != (0.0, 1.0):
                canvas.yview_scroll(units, "units")
        except tk.TclError:
            pass

    def _scroll_pane_to_top(self, frame: ctk.CTkScrollableFrame | None) -> None:
        if frame is None:
            return
        textbox = self._find_textbox_in(frame)
        if textbox is not None:
            try:
                textbox._textbox.yview_moveto(0.0)
            except tk.TclError:
                pass
        canvas = getattr(frame, "_parent_canvas", None)
        if canvas is None:
            return
        try:
            canvas.yview_moveto(0.0)
        except tk.TclError:
            pass

    def _pane_side_for_widget(self, widget: object) -> str | None:
        """Identify which pane (if either) a widget belongs to.

        CTkScrollableFrame embeds its actual content Frame *inside* an
        internal scrolling Canvas (via ``canvas.create_window``), not the
        other way around - so ``self.left_frame`` never appears in that
        canvas's own ``.master`` chain. Without also matching its private
        ``_parent_canvas``/``_parent_frame``, a cursor sitting over blank
        canvas space rather than directly over rendered page content (e.g.
        past the bottom of a short page, or in the padding around it)
        would resolve to neither pane and silently do nothing.
        """
        left_widgets = {
            self.left_frame,
            getattr(self.left_frame, "_parent_canvas", None),
            getattr(self.left_frame, "_parent_frame", None),
        }
        right_widgets = {
            self.right_frame,
            getattr(self.right_frame, "_parent_canvas", None),
            getattr(self.right_frame, "_parent_frame", None),
        }
        node = widget
        while node is not None:
            if node in left_widgets:
                return "original"
            if node in right_widgets:
                return "result"
            node = getattr(node, "master", None)
        return None

    def _toggle_zoom_link(self) -> None:
        self.zoom_linked = not self.zoom_linked
        if self.zoom_linked:
            # Re-locking is a full reset to the default view for both
            # panes - not just syncing to whatever zoom/scroll position
            # the left pane happened to be at - so "back to automatic"
            # is one predictable state every time, not a moving target.
            self.original_zoom = ZOOM_DEFAULT
            self.result_zoom = ZOOM_DEFAULT
            self._rebuild_original_pane()
            self._rebuild_result_pane()
            self._scroll_pane_to_top(self.left_frame)
            self._scroll_pane_to_top(self.right_frame)
        self._update_zoom_controls()

    def _adjust_zoom(self, side: str, step: int) -> None:
        if step == 0:
            return
        delta = step * ZOOM_STEP
        if self.zoom_linked:
            new_value = clamp_zoom_level(self.original_zoom + delta)
            changed = new_value != self.original_zoom or new_value != self.result_zoom
            self.original_zoom = new_value
            self.result_zoom = new_value
            if changed:
                self._rebuild_original_pane()
                self._rebuild_result_pane()
        elif side == "original":
            new_value = clamp_zoom_level(self.original_zoom + delta)
            if new_value != self.original_zoom:
                self.original_zoom = new_value
                self._rebuild_original_pane()
        else:
            new_value = clamp_zoom_level(self.result_zoom + delta)
            if new_value != self.result_zoom:
                self.result_zoom = new_value
                self._rebuild_result_pane()
        self._update_zoom_controls()

    @staticmethod
    def _set_entry_text(entry: ctk.CTkEntry, text: str) -> None:
        entry.delete(0, "end")
        entry.insert(0, text)

    def _update_zoom_controls(self) -> None:
        if self.original_zoom_label is not None:
            self._set_entry_text(
                self.original_zoom_label, zoom_percent_label(self.original_zoom)
            )
        if self.result_zoom_label is not None:
            self._set_entry_text(
                self.result_zoom_label, zoom_percent_label(self.result_zoom)
            )
        glyph = zoom_link_glyph(self.zoom_linked)
        tooltip_text = zoom_link_tooltip_text(self.zoom_linked)
        for button, tooltip in zip(self._link_buttons, self._link_tooltips):
            button.configure(
                text=glyph,
                fg_color=COLOR_ACCENT if self.zoom_linked else COLOR_ICON_IDLE,
                text_color="#FFFFFF" if self.zoom_linked else COLOR_TEXT_MUTED,
            )
            tooltip.set_text(tooltip_text)

    def _commit_zoom_entry(self, side: str) -> None:
        """Apply a manually-typed zoom percentage (e.g. "150" or "150%")
        from the entry for ``side``, clamped to the normal zoom range -
        invalid text just resets the entry back to the current zoom
        rather than raising or silently doing nothing.
        """
        entry = self.original_zoom_label if side == "original" else self.result_zoom_label
        current = self.original_zoom if side == "original" else self.result_zoom
        if entry is None:
            return
        raw = entry.get().strip().rstrip("%")
        try:
            percent = float(raw)
        except ValueError:
            self._set_entry_text(entry, zoom_percent_label(current))
            return
        new_value = clamp_zoom_level(percent / 100)
        if self.zoom_linked:
            self.original_zoom = new_value
            self.result_zoom = new_value
            self._rebuild_original_pane()
            self._rebuild_result_pane()
        elif side == "original":
            self.original_zoom = new_value
            self._rebuild_original_pane()
        else:
            self.result_zoom = new_value
            self._rebuild_result_pane()
        self._update_zoom_controls()

    # -- page navigation ("skocz do strony X/N") -----------------------------

    def _result_page_widget(self, page_number: int) -> tk.Misc | None:
        """The result pane's page N widget, whichever rendering path built
        it - self._page_canvases (magic pen) or self._result_page_widgets
        (plain render_document_preview, e.g. a locked/approved file)."""
        if self.magic_pen_available:
            return self._page_canvases.get(page_number)
        return self._result_page_widgets.get(page_number)

    def _update_page_nav_controls(self, side: str, page_count: int) -> None:
        """Show/hide and refresh the page-nav row for ``side`` after a
        (re)render - hidden entirely for a 0-or-1-page document (nothing
        to navigate to), matching every other conditionally-shown control
        in this window. The current page is preserved (clamped into the
        new range) rather than reset to 1 on every rebuild, so a plain
        zoom change does not also silently discard where the user was
        reading.
        """
        current_attr = "original_current_page" if side == "original" else "result_current_page"
        count_attr = "original_page_count" if side == "original" else "result_page_count"
        setattr(self, count_attr, page_count)
        current = getattr(self, current_attr)
        setattr(self, current_attr, min(max(current, 1), page_count) if page_count > 0 else 0)

        row = self._page_nav_rows.get(side)
        if row is None:
            return
        if page_count > 1:
            row.pack(fill="x", pady=(4, 0))
        else:
            row.pack_forget()
        self._refresh_page_nav_entries()

    def _refresh_page_nav_entries(self) -> None:
        for side in ("original", "result"):
            entry = self._page_entries.get(side)
            total_label = self._page_total_labels.get(side)
            count = self.original_page_count if side == "original" else self.result_page_count
            current = self.original_current_page if side == "original" else self.result_current_page
            if entry is not None:
                self._set_entry_text(entry, str(max(current, 1)))
            if total_label is not None:
                total_label.configure(text=f"/ {count}")

    def _scroll_frame_to_widget(
        self, frame: ctk.CTkScrollableFrame | None, widget: tk.Misc | None
    ) -> None:
        """Scroll ``frame`` so ``widget`` (one page's label/canvas) sits at
        the top - an approximate "jump to page", the same anchor-scroll
        approach a browser uses, not pixel-perfect but close enough to
        actually land on the right page. Reaches into the private
        _parent_canvas the same way every other scroll-control method in
        this window already does (no public CTkScrollableFrame API for
        this exists), so this stays defensive and silently does nothing
        on any error rather than risk crashing the preview over it.
        """
        if frame is None or widget is None:
            return
        canvas = getattr(frame, "_parent_canvas", None)
        if canvas is None:
            return
        try:
            canvas.update_idletasks()
            bbox = canvas.bbox("all")
            if not bbox:
                return
            total_height = max(bbox[3] - bbox[1], 1)
            fraction = max(0.0, min(1.0, widget.winfo_y() / total_height))
            canvas.yview_moveto(fraction)
        except tk.TclError:
            pass

    def _go_to_page_absolute(self, side: str, page_number: int, *, mirror: bool = True) -> None:
        count = self.original_page_count if side == "original" else self.result_page_count
        if count <= 0:
            return
        page_number = min(max(page_number, 1), count)
        if side == "original":
            self.original_current_page = page_number
            self._scroll_frame_to_widget(
                self.left_frame, self._original_page_widgets.get(page_number)
            )
        else:
            self.result_current_page = page_number
            self._scroll_frame_to_widget(self.right_frame, self._result_page_widget(page_number))
        self._refresh_page_nav_entries()
        # Mirrors the same page number onto the other pane while the two
        # are locked together - same "sync unless the link is off" rule
        # _on_scroll_sync already applies to plain scrolling, reused here
        # per direct user feedback ("klikając w strzałkę synchronicznie,
        # lub nie jak wyłączę synchronizację"). mirror=False on the
        # recursive call stops this from bouncing back and forth forever.
        if mirror and self.zoom_linked:
            other_side = "result" if side == "original" else "original"
            other_count = self.result_page_count if side == "original" else self.original_page_count
            if other_count > 0:
                self._go_to_page_absolute(other_side, page_number, mirror=False)

    def _go_to_page(self, side: str, step: int) -> None:
        current = self.original_current_page if side == "original" else self.result_current_page
        self._go_to_page_absolute(side, current + step)

    def _commit_page_entry(self, side: str) -> None:
        """Apply a manually-typed page number from the entry for ``side``,
        clamped into range - invalid text just resets the entry back to
        the current page rather than raising or silently doing nothing,
        matching _commit_zoom_entry's exact handling of the same failure
        mode for the zoom entry right next to it.
        """
        entry = self._page_entries.get(side)
        current = self.original_current_page if side == "original" else self.result_current_page
        if entry is None:
            return
        raw = entry.get().strip()
        try:
            page_number = int(raw)
        except ValueError:
            self._set_entry_text(entry, str(max(current, 1)))
            return
        self._go_to_page_absolute(side, page_number)

    def _toggle_pointer_tool(self, tool: str) -> None:
        """Toggle the shared hand/zoom pointer tool - clicking the
        already-active tool's button turns it back off (modeless
        default: plain scroll pans linked panes, Ctrl+scroll zooms)."""
        self.active_pointer_tool = None if self.active_pointer_tool == tool else tool
        self._refresh_pointer_tool_visuals()

    def _clear_pointer_tool(self, _event: object = None) -> None:
        """Esc cancels whichever pointer tool is active, if any."""
        if self.active_pointer_tool is not None:
            self.active_pointer_tool = None
            self._refresh_pointer_tool_visuals()

    def _refresh_pointer_tool_visuals(self) -> None:
        hand_active = self.active_pointer_tool == "hand"
        zoom_active = self.active_pointer_tool == "zoom"
        for button in self._hand_buttons:
            button.configure(
                fg_color=COLOR_ACCENT if hand_active else COLOR_ICON_IDLE,
                text_color="#FFFFFF" if hand_active else COLOR_TEXT,
            )
        for button in self._zoom_tool_buttons:
            button.configure(
                fg_color=COLOR_ACCENT if zoom_active else COLOR_ICON_IDLE,
                text_color="#FFFFFF" if zoom_active else COLOR_TEXT,
            )
        cursor = "fleur" if hand_active else ("sizing" if zoom_active else "arrow")
        for frame in (self.left_frame, self.right_frame):
            canvas = getattr(frame, "_parent_canvas", None)
            if canvas is not None:
                try:
                    canvas.configure(cursor=cursor)
                except tk.TclError:
                    pass

    def _pan_target(self, frame: ctk.CTkScrollableFrame) -> tk.Misc | None:
        """The widget hand-tool panning should actually scan_mark/
        scan_dragto for this pane - the same textbox-vs-canvas choice
        _scroll_pane_by makes for plain scroll sync, and for the same
        reason: a DOCX/TXT pane's real scrollable content is the inner
        CTkTextbox's own view, not the outer CTkScrollableFrame canvas
        (which has little to no scroll range of its own around one
        fixed-height textbox). Panning the outer canvas there would
        silently do nothing.
        """
        textbox = self._find_textbox_in(frame)
        if textbox is not None:
            return textbox._textbox
        return getattr(frame, "_parent_canvas", None)

    def _bind_pane_panning(self, widget: tk.Misc, frame: ctk.CTkScrollableFrame) -> None:
        """Recursively wire hand-tool drag-to-pan onto every descendant of
        a freshly-rendered pane, forwarding to whatever _pan_target
        resolves to via scan_mark/scan_dragto (the standard Tk pattern
        for this). A no-op whenever the hand tool isn't active, so this
        never interferes with normal clicking/scrolling. Bound with
        add="+" so it only ever adds to, never replaces, any existing
        binding on the same widget. Skips CTkScrollbar descendants so
        the hand tool never fights a scrollbar's own native drag.
        """
        if not isinstance(widget, ctk.CTkScrollbar):
            widget.bind(
                "<ButtonPress-1>",
                lambda e, f=frame: self._on_pan_press(e, f),
                add="+",
            )
            widget.bind(
                "<B1-Motion>", lambda e, f=frame: self._on_pan_drag(e, f), add="+"
            )
        for child in widget.winfo_children():
            self._bind_pane_panning(child, frame)

    def _on_pan_press(self, event: object, frame: ctk.CTkScrollableFrame) -> None:
        if self.active_pointer_tool != "hand":
            return
        target = self._pan_target(frame)
        if target is not None:
            target.scan_mark(event.x_root, event.y_root)

    def _on_pan_drag(self, event: object, frame: ctk.CTkScrollableFrame) -> None:
        if self.active_pointer_tool != "hand":
            return
        target = self._pan_target(frame)
        if target is None:
            return
        # tkinter.Canvas.scan_dragto takes an optional gain (used here for
        # a direct, 1:1 drag instead of Tk's own fast default); plain
        # tkinter.Text.scan_dragto - the inner textbox on a DOCX/TXT pane -
        # takes no such argument at all and raises TypeError if given one.
        try:
            target.scan_dragto(event.x_root, event.y_root, gain=1)
        except TypeError:
            target.scan_dragto(event.x_root, event.y_root)

    def _maybe_show_zoom_link_hint(self) -> None:
        """Auto-show the link-toggle tooltip once, the first time this
        window is ever opened, instead of relying only on discovering it
        by hovering - a lightweight, one-time onboarding hint."""
        if not self._link_tooltips:
            return
        if hint_is_dismissed(ZOOM_LINK_HINT_ID):
            return
        self._link_tooltips[-1].flash(4500)
        dismiss_hint(ZOOM_LINK_HINT_ID)

    def _rebuild_original_pane(self) -> None:
        if self.left_frame is None:
            return
        for widget in self.left_frame.winfo_children():
            widget.destroy()
        self._original_page_widgets = {}
        if self.original_path is not None and self.original_path.exists():
            preview = render_document_preview(
                self.left_frame,
                self.original_path,
                target_width=int(BASE_PREVIEW_WIDTH * self.original_zoom),
            )
            self._images.extend(preview.images)
            self._original_page_widgets = preview.page_widgets
        else:
            ctk.CTkLabel(
                self.left_frame,
                text=(
                    "Oryginał niedostępny - ten folder nie pochodzi z "
                    "bieżącej sesji przetwarzania."
                ),
                text_color=COLOR_TEXT_MUTED,
                wraplength=380,
                justify="left",
            ).pack(pady=30, padx=16)
        self._bind_pane_panning(self.left_frame, self.left_frame)
        self._update_page_nav_controls("original", len(self._original_page_widgets))

    def _rebuild_result_pane(self) -> None:
        if self.right_frame is None:
            return
        if self.magic_pen_available:
            self._reload_pdf_pane()
            return
        for widget in self.right_frame.winfo_children():
            widget.destroy()
        self._result_page_widgets = {}
        if self.result_path.exists():
            preview = render_document_preview(
                self.right_frame,
                self.result_path,
                target_width=int(BASE_PREVIEW_WIDTH * self.result_zoom),
            )
            self._images.extend(preview.images)
            self._result_page_widgets = preview.page_widgets
        else:
            ctk.CTkLabel(
                self.right_frame,
                text="Plik wynikowy nie został znaleziony.",
                text_color=COLOR_TEXT_MUTED,
            ).pack(pady=30)
        self._bind_pane_panning(self.right_frame, self.right_frame)
        self._update_page_nav_controls("result", len(self._result_page_widgets))

    # -- magic pen: toolbar -------------------------------------------------

    def _build_magic_pen_sidebar(self, parent: ctk.CTkFrame) -> ctk.CTkFrame:
        """The right-hand "Korekta anonimizacji" panel: the lock notice
        (approved files) or a short reminder of how the pen works, plus
        the color legend - a fixed-width column standing beside both
        preview panes rather than a toolbar row above one of them.

        Collapsible (see _toggle_legend_sidebar_collapsed): on a narrow
        window this fixed-width column used to simply get clipped by
        Tk's pack() ordering - fixed now by packing it before the paned
        splitter (see __init__) - but a narrow window still has less
        room to spare overall, so a header toggle lets the user
        deliberately trade the legend away for more document space
        instead of the window doing it to them.

        The draw/erase tool chips used to live here too, but per direct
        user feedback they need to stay reachable even while this panel
        is collapsed - they now live in the always-visible bottom action
        bar instead (see __init__'s bottom_actions), which also means
        this sidebar's own content is legend-only content now.
        """
        if self.legend_sidebar_collapsed:
            return self._build_collapsed_legend_rail(parent)

        sidebar = ctk.CTkFrame(
            parent,
            fg_color=COLOR_CARD,
            corner_radius=10,
            border_width=1,
            border_color=COLOR_BORDER,
            width=200,
        )
        sidebar.pack_propagate(False)
        inner = ctk.CTkFrame(sidebar, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=14, pady=14)

        header_row = ctk.CTkFrame(inner, fg_color="transparent")
        header_row.pack(fill="x", pady=(0, 10))
        ctk.CTkLabel(
            header_row,
            text="Korekta anonimizacji",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
            text_color=COLOR_TEXT,
            anchor="w",
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
            command=self._toggle_legend_sidebar_collapsed,
        )
        collapse_button.pack(side="right")
        IconTooltip(collapse_button, "Ukryj legendę")

        if self.locked:
            # Approved files render read-only: no tool chips, no drag/
            # click bindings on the canvas (see _build_magic_pen_pane) -
            # approving is a deliberate one-way "this is final" action
            # (ApprovalLockWarningDialog warns about exactly this before
            # the app ever sets the status), so the editor must actually
            # honor that once it happens, not just warn about it.
            lock_card = ctk.CTkFrame(inner, fg_color=COLOR_BG, corner_radius=8)
            lock_card.pack(fill="x", pady=(0, 10))
            ctk.CTkLabel(
                lock_card,
                text="🔒 Plik zatwierdzony",
                font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
                text_color=COLOR_TEXT,
                anchor="w",
            ).pack(fill="x", padx=10, pady=(8, 2))
            ctk.CTkLabel(
                lock_card,
                text=(
                    "Edycja niedostępna. Aby wprowadzić zmiany, uruchom "
                    "anonimizację tego pliku ponownie."
                ),
                font=ctk.CTkFont(family=FONT_FAMILY, size=10),
                text_color=COLOR_TEXT_MUTED,
                anchor="w",
                wraplength=168,
                justify="left",
            ).pack(fill="x", padx=10, pady=(0, 8))
        else:
            ctk.CTkLabel(
                inner,
                text=(
                    "LPM: nowe zaznaczenie. PPM: usuń istniejące. "
                    "Narzędzia i licznik zmian - na dole okna."
                ),
                font=ctk.CTkFont(family=FONT_FAMILY, size=10),
                text_color=COLOR_TEXT_MUTED,
                anchor="w",
                wraplength=168,
                justify="left",
            ).pack(fill="x", pady=(0, 10))

        ctk.CTkFrame(inner, fg_color=COLOR_BORDER, height=1).pack(fill="x", pady=14)

        ctk.CTkLabel(
            inner,
            text="Kategorie danych",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
            text_color=COLOR_TEXT,
            anchor="w",
        ).pack(fill="x", pady=(0, 8))
        for color, text in LEGEND_ITEMS:
            row = ctk.CTkFrame(inner, fg_color="transparent")
            row.pack(fill="x", pady=3)
            ctk.CTkLabel(
                row,
                text="●",
                text_color=color,
                font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"),
                width=16,
            ).pack(side="left")
            ctk.CTkLabel(
                row,
                text=text,
                text_color=COLOR_TEXT,
                font=ctk.CTkFont(family=FONT_FAMILY, size=10),
                anchor="w",
                wraplength=150,
                justify="left",
            ).pack(side="left", fill="x", expand=True)

        return sidebar

    def _build_collapsed_legend_rail(self, parent: ctk.CTkFrame) -> ctk.CTkFrame:
        """The slim stand-in for _build_magic_pen_sidebar once collapsed -
        just a reopen toggle. Safe to hide everything else: the tool
        chips and pen-status label live in the always-visible bottom
        action bar regardless (see __init__), not here, so nothing
        functional is lost by collapsing this panel - only the legend
        and the lock notice, which is exactly the trade the user asked
        for (more document space, legend hidden until wanted back).
        """
        rail = ctk.CTkFrame(
            parent,
            fg_color=COLOR_CARD,
            corner_radius=10,
            border_width=1,
            border_color=COLOR_BORDER,
            width=36,
        )
        rail.pack_propagate(False)
        reopen_button = ctk.CTkButton(
            rail,
            text="«",
            width=24,
            height=24,
            corner_radius=6,
            fg_color=COLOR_ICON_IDLE,
            hover_color=COLOR_ACCENT_HOVER,
            text_color=COLOR_TEXT,
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            command=self._toggle_legend_sidebar_collapsed,
        )
        reopen_button.pack(pady=10)
        IconTooltip(reopen_button, "Pokaż legendę")
        return rail

    def _toggle_legend_sidebar_collapsed(self) -> None:
        self.legend_sidebar_collapsed = not self.legend_sidebar_collapsed
        if self._sidebar_widget is not None:
            self._sidebar_widget.destroy()
            self._sidebar_widget = None
        if self.content_row is not None and self.magic_pen_available:
            self._sidebar_widget = self._build_magic_pen_sidebar(self.content_row)
            self._sidebar_widget.pack(side="right", fill="y", padx=(12, 0))

    def _build_tool_chip(
        self, parent: ctk.CTkFrame, glyph: str, label: str, tool: str
    ) -> ctk.CTkButton:
        # A compact single button rather than the wider vertical card
        # this used when it lived in the (now-collapsible) sidebar - it
        # sits in a horizontal bottom row now, next to its sibling and
        # the save/cancel buttons, so it needs to stay narrow.
        chip = ctk.CTkButton(
            parent,
            text=f"{glyph} {label}",
            height=28,
            corner_radius=8,
            fg_color=COLOR_BG,
            hover_color=COLOR_ICON_IDLE,
            text_color=COLOR_TEXT_MUTED,
            font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
            command=lambda t=tool: self._toggle_pinned_tool(t),
        )
        chip.pack(side="left", padx=(0, 8))
        IconTooltip(
            chip,
            "Kliknij, aby przypisać LPM tylko do tego narzędzia (tryb ręczny). "
            "PPM zawsze usuwa zaznaczenie, niezależnie od wybranego trybu. "
            "Kliknij ponownie, aby wrócić do trybu automatycznego.",
        )
        return chip

    def _toggle_pinned_tool(self, tool: str) -> None:
        self.pinned_tool = None if self.pinned_tool == tool else tool
        self._refresh_tool_chip_visuals()

    def _flash_tool_chip(self, tool: str) -> None:
        """Briefly light up a chip for a one-shot action (a right-click has
        no natural "held" duration the way a LMB drag does)."""
        self._transient_tool = tool
        self._refresh_tool_chip_visuals()
        self.window.after(250, self._clear_transient_tool)

    def _clear_transient_tool(self) -> None:
        self._transient_tool = None
        self._refresh_tool_chip_visuals()

    def _refresh_tool_chip_visuals(self) -> None:
        for tool, chip in self._tool_chips.items():
            self._set_tool_chip_active(
                chip,
                active=(self.pinned_tool == tool or self._transient_tool == tool),
            )

    def _set_tool_chip_active(self, chip: ctk.CTkButton, *, active: bool) -> None:
        if active:
            chip.configure(fg_color=COLOR_ACCENT, text_color="#FFFFFF")
        else:
            chip.configure(fg_color=COLOR_BG, text_color=COLOR_TEXT_MUTED)

    # -- magic pen: rendering -------------------------------------------------

    def _reload_visible_rects(self) -> None:
        if self.source_path is None:
            self.visible_rects = []
            return
        try:
            self.visible_rects = compute_visible_redaction_rects(
                self.source_path,
                edits=self.edits,
                sensitive_terms_path=self.app.sensitive_terms_path,
                use_ner=self.app.use_ner,
            )
        except (OSError, RuntimeError, ValueError):
            self.visible_rects = []

    def _build_magic_pen_pane(self, parent: ctk.CTkBaseClass) -> None:
        target_width = int(BASE_PREVIEW_WIDTH * self.result_zoom)
        # The "Oryginał" pane renders through CTkImage, which silently
        # scales by the display's DPI factor (customtkinter's own
        # get_widget_scaling) so it looks crisp on a scaled display. This
        # pane draws straight onto a plain tk.Canvas for the magic pen's
        # click/drag overlay, which has no such awareness - without
        # matching that factor here, the two pages visibly render at
        # different sizes on any non-100% display (confirmed: 125% on the
        # pilot machine). Multiplying it into the render zoom, and storing
        # that same effective zoom in self._page_zoom, keeps every later
        # coordinate conversion (click/drag/overlay) correctly aligned
        # without touching any of that code.
        dpi_scale = ctk_widget_scaling_factor(parent)
        try:
            import pymupdf as fitz

            with fitz.open(self.result_path) as document:
                for page_index, page in enumerate(document, start=1):
                    zoom = pdf_page_zoom(max(page.rect.width, 1), target_width) * dpi_scale
                    pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom))
                    pil_image = Image.frombytes(
                        "RGB", (pix.width, pix.height), pix.samples
                    )
                    tk_image = ImageTk.PhotoImage(pil_image)
                    self._tk_images.append(tk_image)
                    canvas = tk.Canvas(
                        parent,
                        width=pix.width,
                        height=pix.height,
                        highlightthickness=0,
                        bg="#FFFFFF",
                        cursor="arrow" if self.locked else "tcross",
                    )
                    canvas.pack(pady=6)
                    canvas.create_image(0, 0, anchor="nw", image=tk_image)
                    self._page_canvases[page_index] = canvas
                    self._page_zoom[page_index] = zoom
                    if not self.locked:
                        # Modeless: left button always draws a new
                        # redaction, right button always toggles an
                        # existing one - no mode to switch first. An
                        # approved (locked) file skips all four bindings
                        # entirely rather than binding-then-ignoring, so
                        # the canvas genuinely behaves like a plain,
                        # non-interactive preview.
                        canvas.bind(
                            "<ButtonPress-1>",
                            lambda event, p=page_index: self._on_pane_press(event, p),
                        )
                        canvas.bind(
                            "<B1-Motion>",
                            lambda event, p=page_index: self._on_pane_drag(event, p),
                        )
                        canvas.bind(
                            "<ButtonRelease-1>",
                            lambda event, p=page_index: self._on_pane_release(event, p),
                        )
                        canvas.bind(
                            "<ButtonPress-3>",
                            lambda event, p=page_index: self._on_pane_right_click(event, p),
                        )
        except Exception:  # noqa: BLE001 - preview must never crash the app
            ctk.CTkLabel(
                parent,
                text="Nie udało się wczytać podglądu tego pliku.",
                text_color=COLOR_HIGH_RISK,
                wraplength=380,
                justify="left",
            ).pack(pady=30, padx=16)
            self.magic_pen_available = False
        self._update_page_nav_controls("result", len(self._page_canvases))

    def _reload_pdf_pane(self) -> None:
        if self.right_frame is None:
            return
        for canvas in self._page_canvases.values():
            canvas.destroy()
        self._page_canvases = {}
        self._page_zoom = {}
        self._overlay_ids = {}
        self._tk_images = []
        self._build_magic_pen_pane(self.right_frame)
        # A rebuild also happens on a plain zoom change (not just after a
        # save, which already cleared pending state) - repaint any
        # still-pending overlay so an in-progress selection is not visually
        # lost just because the page was rescaled and its canvas recreated.
        for page_number in self._page_canvases:
            self._redraw_overlay(page_number)

    # -- magic pen: interaction -------------------------------------------------

    def _hit_test_pool(self) -> list[dict[str, object]]:
        """Every rect a "remove" click can target: staged-for-removal rects
        stay in this pool (still shown, still clickable) so clicking one a
        second time can toggle the pending removal back off."""
        pending = [
            {
                "page": rect.page,
                "label": MANUAL_REDACTION_LABEL,
                "x0": rect.x0,
                "y0": rect.y0,
                "x1": rect.x1,
                "y1": rect.y1,
            }
            for rect in self.pending_add_rects
        ]
        return list(self.visible_rects) + pending

    def _on_pane_press(self, event: tk.Event, page_number: int) -> None:
        """LMB draws a new redaction by default; pinned to "erase" it
        instead toggles the rectangle under the cursor immediately, the
        same one-click action RMB always performs. Either way, the
        matching tool chip lights up for as long as the button is held.
        """
        active_tool = self.pinned_tool or "draw"
        self._transient_tool = active_tool
        self._refresh_tool_chip_visuals()
        if active_tool == "erase":
            self._erase_at_point(event.x, event.y, page_number)
            return
        self._drag_start = (event.x, event.y)
        self._drag_rect_id = None

    def _on_pane_right_click(self, event: tk.Event, page_number: int) -> None:
        """Right button always toggles the rectangle under the cursor,
        regardless of the pinned tool - pinning to "draw" only locks in
        what LMB does, it never takes this shortcut away."""
        self._flash_tool_chip("erase")
        self._erase_at_point(event.x, event.y, page_number)

    def _erase_at_point(self, x: float, y: float, page_number: int) -> None:
        zoom = self._page_zoom.get(page_number, 1.0)
        px, py = canvas_point_to_pdf_point(x, y, zoom)
        hit = find_rect_at_point(self._hit_test_pool(), page_number, px, py)
        if hit is not None:
            self._toggle_pending_remove(hit)

    def _on_pane_drag(self, event: tk.Event, page_number: int) -> None:
        if self.pinned_tool == "erase":
            return
        if self._drag_start is None:
            return
        canvas = self._page_canvases.get(page_number)
        if canvas is None:
            return
        if self._drag_rect_id is not None:
            canvas.delete(self._drag_rect_id)
        x0, y0 = self._drag_start
        self._drag_rect_id = canvas.create_rectangle(
            x0, y0, event.x, event.y, outline="#dc2626", width=2, dash=(4, 2)
        )

    def _on_pane_release(self, event: tk.Event, page_number: int) -> None:
        self._transient_tool = None
        self._refresh_tool_chip_visuals()
        if self.pinned_tool == "erase":
            return
        if self._drag_start is None:
            return
        canvas = self._page_canvases.get(page_number)
        x0, y0 = self._drag_start
        self._drag_start = None
        if canvas is not None and self._drag_rect_id is not None:
            canvas.delete(self._drag_rect_id)
        self._drag_rect_id = None

        cx0, cy0, cx1, cy1 = normalize_drag_rect(x0, y0, event.x, event.y)
        if is_degenerate_drag_rect(cx0, cy0, cx1, cy1):
            return
        zoom = self._page_zoom.get(page_number, 1.0)
        px0, py0 = canvas_point_to_pdf_point(cx0, cy0, zoom)
        px1, py1 = canvas_point_to_pdf_point(cx1, cy1, zoom)
        self.pending_add_rects.append(
            ManualRect(page=page_number, x0=px0, y0=py0, x1=px1, y1=py1)
        )
        self._redraw_overlay(page_number)
        self._update_pending_state()

    def _toggle_pending_remove(self, hit: Mapping[str, object]) -> None:
        key = rect_info_key(hit)
        page_number = int(hit["page"])
        for index, rect in enumerate(self.pending_add_rects):
            rect_key = rect_info_key(
                {
                    "page": rect.page,
                    "label": MANUAL_REDACTION_LABEL,
                    "x0": rect.x0,
                    "y0": rect.y0,
                    "x1": rect.x1,
                    "y1": rect.y1,
                }
            )
            if rect_key == key:
                # A not-yet-saved manual addition: clicking it again in
                # remove mode simply cancels that pending addition.
                del self.pending_add_rects[index]
                self._redraw_overlay(page_number)
                self._update_pending_state()
                return
        if key in self.pending_remove_keys:
            # Clicking an already-staged-for-removal rect a second time
            # un-stages it, so a misclick doesn't require cancelling every
            # other pending change to undo.
            self.pending_remove_keys.discard(key)
        else:
            self.pending_remove_keys.add(key)
        self._redraw_overlay(page_number)
        self._update_pending_state()

    def _redraw_overlay(self, page_number: int) -> None:
        canvas = self._page_canvases.get(page_number)
        if canvas is None:
            return
        for item_id in self._overlay_ids.get(page_number, []):
            canvas.delete(item_id)
        zoom = self._page_zoom.get(page_number, 1.0)
        drawn_ids: list[int] = []

        for key in self.pending_remove_keys:
            for rect_info in self.visible_rects:
                if int(rect_info["page"]) != page_number:
                    continue
                if rect_info_key(rect_info) != key:
                    continue
                x0 = float(rect_info["x0"]) * zoom
                y0 = float(rect_info["y0"]) * zoom
                x1 = float(rect_info["x1"]) * zoom
                y1 = float(rect_info["y1"]) * zoom
                drawn_ids.append(
                    canvas.create_rectangle(x0, y0, x1, y1, outline="#16a34a", width=3)
                )
                break

        for rect in self.pending_add_rects:
            if rect.page != page_number:
                continue
            x0, y0, x1, y1 = rect.x0 * zoom, rect.y0 * zoom, rect.x1 * zoom, rect.y1 * zoom
            drawn_ids.append(
                canvas.create_rectangle(
                    x0, y0, x1, y1, fill="#111827", outline="#dc2626", width=2
                )
            )

        self._overlay_ids[page_number] = drawn_ids

    def _has_pending_changes(self) -> bool:
        return bool(self.pending_remove_keys) or bool(self.pending_add_rects)

    def _update_pending_state(self) -> None:
        has_pending = self._has_pending_changes()
        if self.save_button is not None:
            self.save_button.configure(
                state="normal" if has_pending else "disabled",
                fg_color=COLOR_ACCENT if has_pending else COLOR_ICON_IDLE,
                text_color="#FFFFFF" if has_pending else COLOR_TEXT_MUTED,
            )
        if self.cancel_button is not None:
            self.cancel_button.configure(state="normal" if has_pending else "disabled")
        if self.pen_status_label is not None:
            count = len(self.pending_remove_keys) + len(self.pending_add_rects)
            self.pen_status_label.configure(
                text=f"Niezapisane zmiany: {count}" if has_pending else ""
            )

    def _cancel_pending_changes(self) -> None:
        self.pending_remove_keys = set()
        self.pending_add_rects = []
        for page_number in list(self._page_canvases.keys()):
            self._redraw_overlay(page_number)
        self._update_pending_state()

    def _save_pending_changes(self) -> None:
        if not self._has_pending_changes() or self.source_path is None:
            return
        new_edits = apply_pending_overrides(
            self.edits, self.visible_rects, self.pending_remove_keys, self.pending_add_rects
        )
        if self.pen_status_label is not None:
            self.pen_status_label.configure(text="Zapisywanie...")
            self.window.update_idletasks()

        # Regenerate to a staging file first and only replace the live
        # output once that fully succeeds, so an interrupted or failed
        # regeneration (disk full, process killed) can never truncate or
        # corrupt the existing good output. The sidecar is written last,
        # after the real file is already safely in place, since it is the
        # smallest and least failure-prone step of the three.
        staging_path = self.result_path.with_name(
            f"{self.result_path.stem}.tmp{self.result_path.suffix}"
        )
        try:
            regenerate_pdf_with_manual_overrides(
                self.source_path,
                output_path=staging_path,
                edits=new_edits,
                sensitive_terms_path=self.app.sensitive_terms_path,
                use_ner=self.app.use_ner,
            )
            os.replace(staging_path, self.result_path)
            save_manual_edits(manual_edits_path(self.result_path), new_edits)
        except (OSError, RuntimeError, ValueError):
            try:
                staging_path.unlink(missing_ok=True)
            except OSError:
                pass
            if self.pen_status_label is not None:
                self.pen_status_label.configure(text="Nie udało się zapisać zmian.")
            return

        self.edits = new_edits
        self.pending_remove_keys = set()
        self.pending_add_rects = []
        self._reload_visible_rects()
        self._reload_pdf_pane()
        self._patch_report_with_manual_count(len(new_edits.added))
        self.app.set_review_status(self.item, REVIEW_STATUS_NEEDS_REVIEW)
        self._update_pending_state()
        if self.pen_status_label is not None:
            self.pen_status_label.configure(text="✓ Zmiany zapisane")

    def _patch_report_with_manual_count(self, manual_count: int) -> None:
        if self.app.review_dir is None or self.item.report_name is None:
            return
        report_path = (
            internal_artifacts_dir(self.app.review_dir) / Path(self.item.report_name).name
        )
        try:
            report_text = report_path.read_text(encoding="utf-8")
            report_path.write_text(
                apply_manual_redaction_count_to_report_text(report_text, manual_count),
                encoding="utf-8",
            )
        except OSError:
            pass


