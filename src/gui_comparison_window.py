"""Side-by-side original-vs-anonymized comparison window, including
the magic pen manual redaction editor, and the document preview
rendering helpers it (and the review screen) share."""

from __future__ import annotations

import os
import sys
import tkinter as tk
from collections.abc import Mapping, Sequence
from pathlib import Path
from tkinter import messagebox
from types import MappingProxyType
from typing import NamedTuple

import customtkinter as ctk
from PIL import Image, ImageTk

try:
    from .anonymizer import (
        candidate_llm_review_texts,
        category_selection_path,
        compute_pdf_redaction_spans,
        load_active_pages_selection,
        load_category_selection,
        load_signature_stripping_selection,
        update_signature_stripping_selection,
    )
    from .file_readers import (
        read_docx_file,
        read_txt_file,
    )
    from .file_writers import internal_artifacts_dir
    from .gui_dialogs import MagicPenHintDialog
    from .gui_helpers import (
        APP_ICON_PATH,
        COLOR_ACCENT,
        COLOR_ACCENT_HOVER,
        COLOR_ACCENT_SOFT,
        COLOR_BG,
        COLOR_BORDER,
        COLOR_CARD,
        COLOR_HIGH_RISK,
        COLOR_HIGH_RISK_SOFT,
        COLOR_ICON_IDLE,
        COLOR_TEXT,
        COLOR_TEXT_MUTED,
        COLOR_WARNING,
        COLOR_WARNING_SOFT,
        COLOR_WARNING_TEXT,
        FLOATING_ACTIONS_HIDDEN,
        FLOATING_ACTIONS_SAVED,
        FONT_FAMILY,
        LEGEND_ITEMS,
        MAGIC_PEN_ACTION_ERASE,
        MAGIC_PEN_ACTION_LABELS_PL,
        MAGIC_PEN_ACTION_MARK,
        MAGIC_PEN_ACTION_PAN,
        MAGIC_PEN_BUTTON_LABELS_PL,
        MAGIC_PEN_BUTTON_LEFT,
        MAGIC_PEN_BUTTON_MIDDLE,
        MAGIC_PEN_BUTTON_RIGHT,
        MAGIC_PEN_BUTTONS,
        MAGIC_PEN_HINT_ID,
        ZOOM_LINK_HINT_ID,
        IconTooltip,
        _bring_window_to_front,
        apply_subtle_scrollbar,
        center_window_over_parent,
        dismiss_hint,
        floating_actions_mode,
        format_floating_actions_status,
        format_pending_edit_confirmation_title,
        format_pending_edit_summary_lines,
        format_save_button_text,
        hint_is_dismissed,
        magic_pen_bindings_description_pl,
        resolve_magic_pen_bindings,
    )
    from .llm_suggestions import (
        AI_SUGGESTION_SOURCE_NARRATIVE,
        AI_SUGGESTION_STATUS_ACCEPTED,
        AI_SUGGESTION_STATUS_PENDING,
        AI_SUGGESTION_STATUS_REJECTED,
        AiSuggestion,
        ai_suggestion_sentence_texts,
        build_ai_suggestions,
        llm_suggestions_path,
        load_llm_suggestions_sidecar,
        locate_sentence_texts,
        redactions_overlapping_area,
        save_ai_suggestion_resolutions,
        select_review_text,
    )
    from .manual_redaction import (
        AI_SUGGESTION_LABEL,
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
    from .pdf_redaction import pdf_has_signature_widget
    from .review import (
        REVIEW_STATUS_APPROVED,
        REVIEW_STATUS_NEEDS_REVIEW,
        ReviewItem,
    )
except ImportError:
    from anonymizer import (
        candidate_llm_review_texts,
        category_selection_path,
        compute_pdf_redaction_spans,
        load_active_pages_selection,
        load_category_selection,
        load_signature_stripping_selection,
        update_signature_stripping_selection,
    )
    from file_readers import (
        read_docx_file,
        read_txt_file,
    )
    from file_writers import internal_artifacts_dir
    from gui_dialogs import MagicPenHintDialog
    from gui_helpers import (
        APP_ICON_PATH,
        COLOR_ACCENT,
        COLOR_ACCENT_HOVER,
        COLOR_ACCENT_SOFT,
        COLOR_BG,
        COLOR_BORDER,
        COLOR_CARD,
        COLOR_HIGH_RISK,
        COLOR_HIGH_RISK_SOFT,
        COLOR_ICON_IDLE,
        COLOR_TEXT,
        COLOR_TEXT_MUTED,
        COLOR_WARNING,
        COLOR_WARNING_SOFT,
        COLOR_WARNING_TEXT,
        FLOATING_ACTIONS_HIDDEN,
        FLOATING_ACTIONS_SAVED,
        FONT_FAMILY,
        LEGEND_ITEMS,
        MAGIC_PEN_ACTION_ERASE,
        MAGIC_PEN_ACTION_LABELS_PL,
        MAGIC_PEN_ACTION_MARK,
        MAGIC_PEN_ACTION_PAN,
        MAGIC_PEN_BUTTON_LABELS_PL,
        MAGIC_PEN_BUTTON_LEFT,
        MAGIC_PEN_BUTTON_MIDDLE,
        MAGIC_PEN_BUTTON_RIGHT,
        MAGIC_PEN_BUTTONS,
        MAGIC_PEN_HINT_ID,
        ZOOM_LINK_HINT_ID,
        IconTooltip,
        _bring_window_to_front,
        apply_subtle_scrollbar,
        center_window_over_parent,
        dismiss_hint,
        floating_actions_mode,
        format_floating_actions_status,
        format_pending_edit_confirmation_title,
        format_pending_edit_summary_lines,
        format_save_button_text,
        hint_is_dismissed,
        magic_pen_bindings_description_pl,
        resolve_magic_pen_bindings,
    )
    from llm_suggestions import (
        AI_SUGGESTION_SOURCE_NARRATIVE,
        AI_SUGGESTION_STATUS_ACCEPTED,
        AI_SUGGESTION_STATUS_PENDING,
        AI_SUGGESTION_STATUS_REJECTED,
        AiSuggestion,
        ai_suggestion_sentence_texts,
        build_ai_suggestions,
        llm_suggestions_path,
        load_llm_suggestions_sidecar,
        locate_sentence_texts,
        redactions_overlapping_area,
        save_ai_suggestion_resolutions,
        select_review_text,
    )
    from manual_redaction import (
        AI_SUGGESTION_LABEL,
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
    from pdf_redaction import pdf_has_signature_widget
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

# Tk's own button-number convention (1=left, 2=middle, 3=right) mapped to
# the button names resolve_magic_pen_bindings works with, so the canvas
# binding loop and _button_action share one vocabulary instead of two.
_TK_BUTTON_TO_NAME = {
    1: MAGIC_PEN_BUTTON_LEFT,
    2: MAGIC_PEN_BUTTON_MIDDLE,
    3: MAGIC_PEN_BUTTON_RIGHT,
}

# Short Polish abbreviations for the mode-indicator badges (see
# _build_pen_tool_row) - MAGIC_PEN_BUTTON_LABELS_PL's "Lewy przycisk" etc.
# are meant for the settings dialog's full-width rows, not a 3-letter
# badge in a title bar.
_MAGIC_PEN_BUTTON_SHORT_PL = {
    MAGIC_PEN_BUTTON_LEFT: "LPM",
    MAGIC_PEN_BUTTON_RIGHT: "PPM",
    MAGIC_PEN_BUTTON_MIDDLE: "ŚPM",
}

# Icon + accent pair per action, so the mode-indicator badges and the
# magic-pen document cursor both give the same at-a-glance signal for
# what a button currently does - per direct feedback that neither one
# was visible/discoverable enough before.
_MAGIC_PEN_ACTION_ICON = {
    MAGIC_PEN_ACTION_MARK: "✏",
    MAGIC_PEN_ACTION_ERASE: "\U0001f9f9",
    MAGIC_PEN_ACTION_PAN: "✋",
}
_MAGIC_PEN_ACTION_COLORS = {
    MAGIC_PEN_ACTION_MARK: (COLOR_ACCENT, COLOR_ACCENT_SOFT),
    MAGIC_PEN_ACTION_ERASE: (COLOR_HIGH_RISK, COLOR_HIGH_RISK_SOFT),
    MAGIC_PEN_ACTION_PAN: (COLOR_WARNING, COLOR_WARNING_SOFT),
}
_MAGIC_PEN_CURSOR_BY_ACTION = {
    # Named Tk/X11 system cursors - the closest built-in shapes to the
    # badge emoji above ("pencil" is a real Tk cursor name, "hand2" is
    # the conventional grab/pan cursor most apps already use). Per
    # direct feedback the previous "tcross"/"fleur" pair read as generic
    # crosshair/4-way-arrow shapes with no visible connection to the
    # badges at all. There's no built-in cursor shaped like a broom
    # (the erase badge's icon) or colored to match a badge's accent -
    # that would need a custom cursor image (its own, bigger task), not
    # a name swap.
    MAGIC_PEN_ACTION_MARK: "pencil",
    MAGIC_PEN_ACTION_ERASE: "X_cursor",
    MAGIC_PEN_ACTION_PAN: "hand2",
}


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


# -- local-LLM suggestion review (PDF only) ---------------------------------

# Same turquoise as the "sugestia AI zaakceptowana" legend entry
# (gui_helpers.LEGEND_ITEMS / pdf_redaction.PDF_REDACTION_COLORS), so a
# pending suggestion's dashed outline and its burned-in result read as the
# same thing before and after saving.
AI_SUGGESTION_OUTLINE_COLOR = "#0D99A6"
# Where on screen a focused suggestion lands: a third of the way down the
# viewport, so the lines just above it (context) stay visible too.
AI_SUGGESTION_SCROLL_ANCHOR = 0.3
AI_QUOTE_MAX_CHARS = 160

_AI_CATEGORY_LABELS_PL = {
    "PERSON_LIKE": "osoba",
    "ORGANIZATION_LIKE": "organizacja",
    "LOCATION_LIKE": "miejsce",
    "ADDRESS_CONTEXT": "adres",
    "CASE_REFERENCE_LIKE": "sygnatura / numer sprawy",
    "CONTACT_DATA_LIKE": "dane kontaktowe",
    "OTHER_SENSITIVE_CONTEXT": "inne dane wrażliwe",
    "QUASI_IDENTIFIER_COMBINATION": "kombinacja szczegółów",
}
_AI_CONFIDENCE_LABELS_PL = {
    "certain": "pewne",
    "likely": "prawdopodobne",
    "uncertain": "niepewne",
}


def ai_suggestion_title_pl(suggestion: AiSuggestion) -> str:
    """One-line Polish description of what kind of suggestion this is."""
    category = _AI_CATEGORY_LABELS_PL.get(suggestion.category, suggestion.category.lower())
    if suggestion.source == AI_SUGGESTION_SOURCE_NARRATIVE:
        confidence = _AI_CONFIDENCE_LABELS_PL.get(suggestion.confidence or "", "")
        suffix = f" ({confidence})" if confidence else ""
        return f"Dane mogą razem wskazać osobę{suffix}"
    if suggestion.finding_type == "unnecessary_redaction":
        return f"Możliwa zbędna redakcja: {category}"
    return f"Możliwa pominięta dana: {category}"


def ai_quote_text(sentence_texts: Sequence[str], max_chars: int = AI_QUOTE_MAX_CHARS) -> str:
    """The locally-resolved sentence(s) a suggestion points at, shortened
    for the narrow review panel. Never model output (see llm_review.py)."""
    text = " … ".join(" ".join(sentence.split()) for sentence in sentence_texts)
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 1].rstrip() + "…"


def ai_scroll_fraction(
    widget_y: float,
    offset_px: float,
    total_height: float,
    viewport_height: float,
    anchor: float = AI_SUGGESTION_SCROLL_ANCHOR,
) -> float:
    """``yview_moveto`` fraction that puts a point ``offset_px`` below the
    top of a page widget (itself ``widget_y`` into the scrolled content)
    ``anchor`` of the way down the visible viewport - the rect-level
    counterpart of _scroll_frame_to_widget's page-level jump."""
    if total_height <= 0:
        return 0.0
    target = widget_y + offset_px - viewport_height * anchor
    return max(0.0, min(1.0, target / total_height))


class AiReviewData(NamedTuple):
    """What the comparison window needs to review one PDF's suggestions:
    the still-undecided suggestions (in reading order), each one's
    location-hint rects and locally-resolved sentence text, and whether
    the reconstructed document text matched the one the model reviewed
    (False = suggestions are shown without any location, see
    llm_suggestions.select_review_text)."""

    suggestions: list[AiSuggestion]
    location_rects: dict[str, list[dict[str, object]]]
    sentence_texts: dict[str, list[str]]
    text_matched: bool
    # Shown instead of the review panel when there is nothing to review
    # but the AI did run - see ai_review_status_note.
    status_note: str = ""


EMPTY_AI_REVIEW = AiReviewData([], {}, {}, True)


def ai_review_status_note(sidecar) -> str:
    """Why there are no AI suggestions to review, in Polish, or "" when
    the AI wasn't used for this file at all. Real user report
    (2026-09-25): both reviews had timed out, and the window looked
    exactly the same as "the AI found nothing" - the user couldn't tell
    whether the model had run."""
    statuses = [
        str(result.get("status", ""))
        for result in (sidecar.comparison_result, sidecar.narrative_result)
        if isinstance(result, dict)
    ]
    ran = [status for status in statuses if status and status != "disabled"]
    if not ran:
        return ""
    if "timeout" in ran:
        return (
            "Analiza AI nie zdążyła się zakończyć (przekroczony limit czasu) "
            "- brak sugestii do przejrzenia."
        )
    if any(status != "completed" for status in ran):
        return "Analiza AI nie powiodła się - brak sugestii do przejrzenia."
    return "AI przeanalizowało dokument i nie zgłosiło żadnych uwag."


def _ai_reading_order_key(
    suggestion: AiSuggestion, location_rects: Sequence[Mapping[str, object]]
) -> tuple[float, float]:
    page = suggestion.page
    if page is None and location_rects:
        page = int(location_rects[0]["page"])
    top = min((float(rect["y0"]) for rect in location_rects), default=0.0)
    return (float(page) if page is not None else float("inf"), top)


def prepare_ai_review(
    result_path: Path, source_path: Path, word_pages: Sequence
) -> AiReviewData:
    """Load a PDF output's suggestion sidecar and resolve every undecided
    suggestion against ``source_path``'s geometry.

    The model's sentence numbers only mean something against the exact
    text it reviewed, which the sidecar deliberately never stores - so it
    is rebuilt here (anonymizer.candidate_llm_review_texts, from the same
    ``word_pages`` the window's detection cache already holds, so OCR
    never runs twice) and checked against the stored fingerprint. On a
    mismatch every suggestion still appears (the approval gate needs a
    decision on each), just with no page, rect or quote - never a guess.
    """
    sidecar = load_llm_suggestions_sidecar(llm_suggestions_path(result_path))
    if not sidecar.unresolved_ids():
        if sidecar.resolved:
            # Everything was already decided in an earlier session - not
            # "the AI found nothing".
            return EMPTY_AI_REVIEW
        return EMPTY_AI_REVIEW._replace(status_note=ai_review_status_note(sidecar))
    try:
        candidates = candidate_llm_review_texts(source_path, word_pages)
    except Exception:  # noqa: BLE001 - pypdf's own errors aren't OSError/ValueError;
        # a source that became unreadable must degrade to "no location",
        # never stop the comparison window (and so the review) from opening.
        candidates = []
    review_text = select_review_text(candidates, sidecar.original_text_sha256)
    suggestions = build_ai_suggestions(
        review_text or "",
        comparison_result=sidecar.comparison_result,
        narrative_result=sidecar.narrative_result,
        word_pages=word_pages if review_text is not None else [],
    )
    suggestions = [s for s in suggestions if s.id not in sidecar.resolved]
    location_rects: dict[str, list[dict[str, object]]] = {}
    sentence_texts: dict[str, list[str]] = {}
    for suggestion in suggestions:
        texts = ai_suggestion_sentence_texts(review_text, suggestion) if review_text else []
        sentence_texts[suggestion.id] = texts
        if suggestion.rects:
            location_rects[suggestion.id] = [dict(rect) for rect in suggestion.rects]
        else:
            location_rects[suggestion.id] = locate_sentence_texts(texts, word_pages)
    suggestions.sort(key=lambda s: _ai_reading_order_key(s, location_rects[s.id]))
    return AiReviewData(suggestions, location_rects, sentence_texts, review_text is not None)


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

    # Local-LLM suggestion review state (see "local-LLM suggestion review"
    # below). Immutable class-level defaults, always *replaced* rather than
    # mutated in place, so a window that never loads suggestions (DOCX/TXT,
    # locked, or no sidecar) - and the bare instances the tests build
    # without __init__ - behave exactly as before this feature existed.
    ai_review: AiReviewData = EMPTY_AI_REVIEW
    _ai_current_id: str | None = None
    # The suggestion whose area the user is marking by hand ("Zmień
    # ręcznie", or accepting a suggestion with no ready rect): every rect
    # drawn meanwhile gets AI_SUGGESTION_LABEL and counts as accepting it.
    _ai_manual_id: str | None = None
    _ai_rejected: frozenset[str] = frozenset()
    # Which staged rects/removal keys came from accepting which suggestion
    # - a suggestion's status is *derived* from whether they are still
    # pending (see _ai_status), so undo/redo/cancel/erase all update it for
    # free instead of each needing its own bookkeeping.
    _ai_accepted_rects: Mapping[str, tuple[ManualRect, ...]] = MappingProxyType({})
    _ai_accepted_removals: Mapping[str, frozenset] = MappingProxyType({})
    _ai_section: ctk.CTkFrame | None = None
    _ai_title_button: ctk.CTkButton | None = None
    _ai_manual_notice: str = ""

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
        # The *resolved* Etap 4 detection-label set this document's visual
        # output was originally produced with (see
        # anonymizer.category_selection_path/load_category_selection) -
        # None if the sidecar is missing (a pre-Etap-4 output, or the
        # visual redaction step itself failed), corrupt, or written before
        # this field existed, which resolve_active_labels() correctly
        # treats as "no filtering". Frozen at save time rather than the
        # category *names* re-resolved against today's CATEGORY_GROUPS -
        # a later app update changing what a category covers must never
        # retroactively change what regenerating an *existing* document
        # does. Threaded into every detection recompute this window
        # triggers (see _cached_detection) so a manual edit's "regenerate"
        # pass never silently redacts a category the user originally
        # excluded.
        self._original_active_labels: frozenset[str] | None = (
            load_category_selection(category_selection_path(result_path))
        )
        # Sibling of _original_active_labels, same sidecar, same freeze-at-
        # save-time reasoning (see anonymizer.load_active_pages_selection) -
        # Etap 5's page-range restriction. None means "no filtering", every
        # page in scope - the sidecar's own default before Etap 5 existed.
        self._original_active_pages: frozenset[int] | None = (
            load_active_pages_selection(category_selection_path(result_path))
        )
        # Sibling of the two above, same sidecar, same freeze-at-save-time
        # reasoning (see anonymizer.load_signature_stripping_selection) -
        # Etap 7's "usuń podpisy elektroniczne" opt-in. False (never
        # None - this is a plain bool, off by default) means the choice
        # was either never made or the document predates this feature.
        self._original_strip_signatures: bool = load_signature_stripping_selection(
            category_selection_path(result_path)
        )
        # Live, user-toggleable value for this window's magic-pen
        # signature-removal checkbox (see _build_signature_removal_toggle)
        # - starts equal to the frozen original choice, and only diverges
        # once the user actually flips the checkbox. _has_pending_changes
        # compares the two to know whether the toggle itself, with zero
        # rect edits, is still a save-worthy pending change.
        self._current_strip_signatures: bool = self._original_strip_signatures
        self._images: list[ctk.CTkImage] = []
        self._tk_images: list[ImageTk.PhotoImage] = []
        self._page_canvases: dict[int, tk.Canvas] = {}
        self._page_zoom: dict[int, float] = {}
        self._overlay_ids: dict[int, list[int]] = {}
        self._drag_start: tuple[float, float] | None = None
        self._drag_rect_id: int | None = None
        self.edits: ManualEdits = EMPTY_MANUAL_EDITS
        self.visible_rects: list[dict[str, object]] = []
        # Detection (word_pages/spans) is expensive to recompute - a scan's
        # OCR alone measured ~15s for 6 pages (see docs/PROJECT_STATE.md's
        # Etap 2 timing entry) - and source_path never changes for the
        # lifetime of one comparison window, so it only needs recomputing
        # if the detection settings themselves change mid-session (NER
        # toggled in Settings while this window stays open). Keyed on
        # those settings rather than assumed stable, so a change is still
        # picked up correctly instead of silently reusing stale results.
        self._detection_cache_key: tuple | None = None
        self._detection_cache: tuple[list, list] | None = None
        self.pending_remove_keys: set = set()
        self.pending_add_rects: list[ManualRect] = []
        self.save_button: ctk.CTkButton | None = None
        self.cancel_button: ctk.CTkButton | None = None
        self.finish_button: ctk.CTkButton | None = None
        # True between a successful save and the user either leaving or
        # starting a fresh edit - see _show_saved_confirmation.
        self._edits_saved: bool = False
        self.undo_button: ctk.CTkButton | None = None
        self.redo_button: ctk.CTkButton | None = None
        self._floating_actions: ctk.CTkFrame | None = None
        self._home_icon_image: ctk.CTkImage | None = None
        self.right_container: ctk.CTkFrame | None = None
        self._edit_undo_stack: list[tuple[list[ManualRect], set, bool, frozenset]] = []
        self._edit_redo_stack: list[tuple[list[ManualRect], set, bool, frozenset]] = []
        self.pen_status_label: ctk.CTkLabel | None = None
        # Etap 3: each mouse button (left/right/middle) is independently
        # bound to one of three actions (mark/erase/pan) per
        # app.magic_pen_interaction_mode - see _button_action and
        # resolve_magic_pen_bindings in gui_helpers.py. Replaces the
        # earlier "pin LMB to draw or erase, RMB always erases" scheme:
        # with three real buttons instead of two doing double duty, that
        # pinning UI became redundant rather than complementary.
        # _active_gesture_action tracks which action the currently-held
        # button performs, so drag/release handlers (which only see the
        # event, not which button started the gesture) know what to do.
        # _erased_this_gesture de-duplicates a drag-erase: each rect the
        # cursor passes over is removed at most once per press-to-release
        # gesture, so dragging back over the same spot doesn't toggle it
        # on and off repeatedly.
        self._active_gesture_action: str | None = None
        self._erased_this_gesture: set = set()
        self.mode_indicator_frame: ctk.CTkFrame | None = None
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
        # Rebuilt fresh each time _build_signature_removal_toggle runs
        # (the sidebar itself is torn down/rebuilt on collapse toggle) -
        # kept so _cancel_pending_changes can resync the checkbox's
        # displayed state after reverting self._current_strip_signatures,
        # without the checkbox itself needing to re-read app state.
        self._strip_signatures_var: tk.BooleanVar | None = None

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
        # Etap 7 magic-pen toggle: only offer it when the *source* (not
        # the already-redacted result) actually has an in-scope signature
        # field to remove (active_pages=self._original_active_pages, the
        # same frozen page range _strip_signature_widgets itself honors -
        # a signature field outside that range can never actually be
        # removed, so offering the toggle for it would be a guaranteed
        # no-op) - avoids cluttering the sidebar with a checkbox that
        # would do nothing. Also skipped entirely for an already-approved
        # (locked) window, where the toggle could never be shown anyway.
        # Checked once here, not live, matching magic_pen_available's own
        # once-per-window-open evaluation.
        self._document_has_signature_widget = bool(
            self.magic_pen_available
            and not self.locked
            and original_path is not None
            and pdf_has_signature_widget(
                original_path, active_pages=self._original_active_pages
            )
        )

        window = ctk.CTkToplevel(app.root)
        self.window = window
        window.title(f"Porównanie - {item.output_name}")
        center_window_over_parent(window, app.root, 1120, 780)
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
        # Undo/redo for pending (unsaved) magic-pen edits - the standard
        # shortcuts, plus Ctrl+Shift+Z as the common alternate for redo.
        window.bind("<Control-z>", lambda _e: self._undo_last_edit())
        window.bind("<Control-y>", lambda _e: self._redo_last_edit())
        window.bind("<Control-Shift-Z>", lambda _e: self._redo_last_edit())
        window.protocol("WM_DELETE_WINDOW", self._close)

        # Title bar: app icon (back to the main window), file name, and -
        # for an editable PDF - the magic pen tools. The tools used to sit
        # in a row at the bottom of the window; moving them up here gives
        # that vertical space back to the document preview, which is the
        # whole point of this window, and puts them next to the page/zoom
        # controls they belong with.
        title_row = ctk.CTkFrame(window, fg_color="transparent")
        title_row.pack(fill="x", padx=20, pady=(14, 4))
        self._build_home_button(title_row)
        ctk.CTkLabel(
            title_row,
            text=item.output_name,
            font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"),
            text_color=COLOR_TEXT,
        ).pack(side="left", padx=(10, 0))
        # Packed first among the side="right" widgets, so it lands at the
        # window's outer right edge regardless of whether the magic pen
        # tools also show up here - per direct feedback there was no way
        # to reach Ustawienia from this window at all, e.g. to change
        # mode mid-edit without closing the preview first.
        self._build_settings_shortcut_button(title_row)
        if self.magic_pen_available and not self.locked:
            # Loaded before any sidebar/title widget is built, since both
            # show the suggestion count. Also warms the detection cache
            # _reload_visible_rects below reuses.
            self._load_ai_review()
            self._build_pen_tool_row(title_row)
            self._build_ai_review_title_button(title_row)

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
        # Kept for the floating edit-actions overlay: it needs a stable,
        # non-scrolling parent covering the whole result pane.
        # right_frame.master is CTkScrollableFrame's internal scrolling
        # canvas, which is the wrong thing to place an overlay into.
        self.right_container = right_container
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
            # The save/cancel pair floats over the result pane instead of
            # occupying a permanent row at the bottom of the window (see
            # _build_floating_edit_actions): the preview is what this
            # window is for, so nothing takes its vertical space unless
            # there is actually something to act on. The pen status line
            # lives in that overlay too.
            self._build_floating_edit_actions()
        elif not self.magic_pen_available:
            # No sidebar in this case (magic pen is PDF-only), so the
            # color legend still needs a home - the existing horizontal
            # row at the bottom, same as before. A locked-but-available
            # pane already has the legend in its sidebar (see
            # _build_magic_pen_sidebar), so it needs neither this row nor
            # the floating actions above.
            app._build_legend_row(window)

        window.after(700, self._maybe_show_zoom_link_hint)
        window.after(900, self._maybe_show_magic_pen_hint)
        # Opening a preview should visibly come to the front, not appear
        # behind whatever window was already open.
        _bring_window_to_front(window)

    def _close(self) -> None:
        """Close this window and bring the main app window back to front -
        matches _bring_window_to_front's rule for opening: whichever
        window the user just acted on should end up on top."""
        self.window.destroy()
        _bring_window_to_front(self.app.root)

    def _build_floating_edit_actions(self) -> None:
        """A small "you have unsaved edits" overlay in the bottom-right
        corner of the result pane: accept on top, cancel underneath, the
        pending count and save status beside them.

        Floated with place() over the pane rather than packed into a row
        of its own, for three reasons the user asked for directly: the
        preview gets all the vertical space when there is nothing to
        save, the buttons stay reachable no matter how the panes are
        resized or whether the legend sidebar is collapsed, and - unlike
        every packed control in this window - an overlay cannot be
        squeezed out of the layout at all, which is the failure mode this
        project has had to fix by hand more than once.

        Created hidden and only placed once there is something to act on
        (see _update_floating_actions_visibility).
        """
        if self.right_container is None:
            return
        container = ctk.CTkFrame(
            self.right_container,
            corner_radius=12,
            fg_color=COLOR_CARD,
            border_width=1,
            border_color=COLOR_BORDER,
        )
        self._floating_actions = container

        inner = ctk.CTkFrame(container, fg_color="transparent")
        inner.pack(padx=12, pady=10)

        self.pen_status_label = ctk.CTkLabel(
            inner,
            text="",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            text_color=COLOR_TEXT_MUTED,
        )
        self.pen_status_label.pack(pady=(0, 6))

        self.save_button = ctk.CTkButton(
            inner,
            text=format_save_button_text(0),
            width=190,
            height=34,
            corner_radius=8,
            fg_color=COLOR_ACCENT,
            hover_color=COLOR_ACCENT_HOVER,
            text_color="#FFFFFF",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
            command=self._confirm_and_save_pending_changes,
        )
        self.save_button.pack(fill="x")
        self.cancel_button = ctk.CTkButton(
            inner,
            text="Anuluj zmiany",
            width=190,
            height=28,
            corner_radius=8,
            fg_color="transparent",
            hover_color=COLOR_ICON_IDLE,
            text_color=COLOR_TEXT_MUTED,
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            command=self._cancel_pending_changes,
        )
        self.cancel_button.pack(fill="x", pady=(6, 0))
        # Replaces the two buttons above once edits are saved, so the
        # overlay that the user was just looking at turns into the way
        # out instead of vanishing (see _show_saved_confirmation).
        self.finish_button = ctk.CTkButton(
            inner,
            text="Zakończ edycję",
            width=190,
            height=34,
            corner_radius=8,
            fg_color=COLOR_ACCENT,
            hover_color=COLOR_ACCENT_HOVER,
            text_color="#FFFFFF",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
            command=self._close,
        )

    def _floating_actions_mode(self) -> str:
        return floating_actions_mode(
            has_pending_changes=self._has_pending_changes(),
            edits_saved=self._edits_saved,
        )

    def _apply_floating_actions_mode(self, mode: str) -> None:
        """Lay the overlay out for the given mode: accept/cancel while
        edits are pending, or a single "finish" button once they are
        saved. Re-packed rather than just toggled, so the order stays
        deterministic either way."""
        if (
            self.save_button is None
            or self.cancel_button is None
            or self.finish_button is None
        ):
            return
        self.save_button.pack_forget()
        self.cancel_button.pack_forget()
        self.finish_button.pack_forget()
        if mode == FLOATING_ACTIONS_SAVED:
            self.finish_button.pack(fill="x")
        else:
            self.save_button.pack(fill="x")
            self.cancel_button.pack(fill="x", pady=(6, 0))

    def _show_saved_confirmation(self) -> None:
        """Turn the overlay into a "saved - you can leave now" state.

        Before this existed, a successful save wrote "✓ Zmiany zapisane"
        into a label that _update_pending_state had *already* hidden one
        line earlier (no pending edits left -> place_forget), so the
        confirmation was never actually visible, and the user was left
        with no obvious way to finish - only the window's X, which they
        reported as unintuitive. Keeping the overlay up, in the exact
        spot they just clicked, both confirms the save and offers the
        exit; it still costs no permanent vertical space, which is why
        the old always-on "Zamknij" button was removed in the first
        place.
        """
        self._edits_saved = True
        self._update_pending_state()

    def _update_floating_actions_visibility(self) -> None:
        """Show the overlay while there is something to accept or cancel,
        or while confirming a completed save, and keep it above the
        freshly-rendered page canvases (a pane rebuild re-stacks its
        children, so it needs lifting again)."""
        container = self._floating_actions
        if container is None:
            return
        mode = self._floating_actions_mode()
        self._apply_floating_actions_mode(mode)
        if mode == FLOATING_ACTIONS_HIDDEN:
            container.place_forget()
        else:
            container.place(relx=1.0, rely=1.0, anchor="se", x=-18, y=-18)
            container.lift()

    def _build_home_button(self, parent: ctk.CTkFrame) -> None:
        """App icon in the top-left corner that closes this window and
        returns to the main one - the same "click the logo to get home"
        affordance the main window's sidebar already has, so the preview
        window does not feel like a dead end."""
        try:
            icon_image = Image.open(APP_ICON_PATH)
        except (OSError, ValueError):
            self._home_icon_image = None
        else:
            self._home_icon_image = ctk.CTkImage(light_image=icon_image, size=(22, 22))

        home_button = ctk.CTkButton(
            parent,
            text="" if self._home_icon_image is not None else "⌂",
            image=self._home_icon_image,
            width=32,
            height=32,
            corner_radius=8,
            fg_color="transparent",
            hover_color=COLOR_ICON_IDLE,
            text_color=COLOR_TEXT,
            font=ctk.CTkFont(family=FONT_FAMILY, size=15),
            command=self._close,
        )
        home_button.pack(side="left")
        IconTooltip(home_button, "Wróć do okna głównego")

    def _build_settings_shortcut_button(self, parent: ctk.CTkFrame) -> None:
        """Gear icon that opens Ustawienia > Ogólne without leaving this
        window - per direct feedback there was no way to reach Ustawienia
        from the comparison/preview window at all, e.g. to switch magic
        pen mode mid-edit. Shown even when the magic pen tools aren't
        (locked file, non-PDF), since general settings are still
        reachable regardless.
        """
        settings_button = ctk.CTkButton(
            parent,
            text="⚙",
            width=30,
            height=30,
            corner_radius=8,
            fg_color="transparent",
            hover_color=COLOR_ICON_IDLE,
            text_color=COLOR_TEXT_MUTED,
            font=ctk.CTkFont(family=FONT_FAMILY, size=15),
            command=self._open_settings_from_here,
        )
        settings_button.pack(side="right")
        IconTooltip(settings_button, "Ustawienia")

    def _open_settings_from_here(self) -> None:
        self.app.open_settings(
            initial_tab="Ogólne", on_saved=self._refresh_magic_pen_mode
        )

    def _refresh_magic_pen_mode(self) -> None:
        """Called after Ustawienia closes with unsaved-changes committed
        (see SettingsDialog's on_saved) - the interaction mode may have
        just changed, so the badges, tooltip and every open document
        canvas's idle cursor need to catch up without the user having to
        close and reopen this window.
        """
        if self.mode_indicator_frame is not None and self.mode_indicator_frame.winfo_exists():
            self._populate_mode_indicator(self.mode_indicator_frame)
        if not self.locked:
            idle_cursor = self._idle_magic_pen_cursor()
            for canvas in self._page_canvases.values():
                try:
                    canvas.configure(cursor=idle_cursor)
                except tk.TclError:
                    pass

    def _idle_magic_pen_cursor(self) -> str:
        if self.locked:
            return "arrow"
        action = self._button_action(MAGIC_PEN_BUTTON_LEFT)
        return _MAGIC_PEN_CURSOR_BY_ACTION.get(action, "tcross")

    def _build_pen_tool_row(self, parent: ctk.CTkFrame) -> None:
        """The magic pen's own controls, in the title bar rather than a
        row at the bottom of the window - the space they used to take is
        now document preview, and they sit next to the page/zoom controls
        they are conceptually part of. Packed side="right" so the file
        name keeps the left side.
        """
        self.redo_button = ctk.CTkButton(
            parent,
            text="↷",
            width=30,
            height=30,
            corner_radius=8,
            border_width=1,
            border_color=COLOR_BORDER,
            fg_color=COLOR_BG,
            hover_color=COLOR_ICON_IDLE,
            text_color=COLOR_TEXT_MUTED,
            font=ctk.CTkFont(family=FONT_FAMILY, size=14),
            state="disabled",
            command=self._redo_last_edit,
        )
        self.redo_button.pack(side="right")
        IconTooltip(self.redo_button, "Ponów cofniętą edycję (Ctrl+Y)")
        self.undo_button = ctk.CTkButton(
            parent,
            text="↶",
            width=30,
            height=30,
            corner_radius=8,
            border_width=1,
            border_color=COLOR_BORDER,
            fg_color=COLOR_BG,
            hover_color=COLOR_ICON_IDLE,
            text_color=COLOR_TEXT_MUTED,
            font=ctk.CTkFont(family=FONT_FAMILY, size=14),
            state="disabled",
            command=self._undo_last_edit,
        )
        self.undo_button.pack(side="right", padx=(0, 10))

        # 3 small colored icon badges (one per physical mouse button)
        # instead of the old plain 11px grey text - per direct feedback
        # that text was "practically invisible" ("gdybym sam nie
        # projektował ich tam to pewnie bym ich nie zauważył"). Rebuilt
        # in place by _populate_mode_indicator whenever the mode changes
        # (custom bindings, or Ustawienia opened from this window's own
        # gear button - see _refresh_magic_pen_mode).
        self.mode_indicator_frame = ctk.CTkFrame(parent, fg_color="transparent")
        self.mode_indicator_frame.pack(side="right", padx=(0, 10))
        self._populate_mode_indicator(self.mode_indicator_frame)

    def _populate_mode_indicator(self, frame: ctk.CTkFrame) -> None:
        for child in frame.winfo_children():
            child.destroy()
        bindings = self._current_bindings()
        for button in MAGIC_PEN_BUTTONS:
            action = bindings.get(button, MAGIC_PEN_ACTION_MARK)
            icon = _MAGIC_PEN_ACTION_ICON.get(action, "")
            strong_color, soft_color = _MAGIC_PEN_ACTION_COLORS.get(
                action, (COLOR_TEXT_MUTED, COLOR_ICON_IDLE)
            )
            badge = ctk.CTkFrame(
                frame,
                corner_radius=6,
                fg_color=soft_color,
                border_width=1,
                border_color=strong_color,
            )
            badge.pack(side="left", padx=(4, 0))
            badge_label = ctk.CTkLabel(
                badge,
                text=f"{_MAGIC_PEN_BUTTON_SHORT_PL[button]} {icon}",
                font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
                text_color=strong_color,
            )
            badge_label.pack(padx=6, pady=2)
            IconTooltip(
                badge_label,
                f"{MAGIC_PEN_BUTTON_LABELS_PL[button]}: "
                f"{MAGIC_PEN_ACTION_LABELS_PL.get(action, action)}. "
                "Zmień tryb w Ustawienia > Ogólne.",
            )

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
        # Digits only, at most 3 of them (no real document has 1000+
        # pages) - a soft typing affordance, not the actual page-range
        # clamp: _go_to_page_absolute still clamps against the real page
        # count regardless of what this allows someone to type.
        page_entry_validate = (
            self.window.register(self._validate_page_entry_keystroke),
            "%P",
        )
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
            validate="key",
            validatecommand=page_entry_validate,
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

    @staticmethod
    def _validate_page_entry_keystroke(proposed_value: str) -> bool:
        """Tk "key" validator for the page-number entry: allow only an
        empty field (while the user is still typing/clearing it) or up
        to 3 digits. Returning False here blocks the keystroke outright
        - Tk's own contract for a "key"-mode validatecommand."""
        return proposed_value == "" or (
            proposed_value.isdigit() and len(proposed_value) <= 3
        )

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
        (re)render. Shown whenever there is a real page count (1 or
        more) - even a single-page document shows "1 / 1" per direct
        user feedback, rather than only appearing once there is
        somewhere else to jump to; hidden only for page_count == 0
        (no PDF pages at all, e.g. a DOCX/TXT/image preview, or the
        original genuinely unavailable). The current page is preserved
        (clamped into the new range) rather than reset to 1 on every
        rebuild, so a plain zoom change does not also silently discard
        where the user was reading.
        """
        current_attr = "original_current_page" if side == "original" else "result_current_page"
        count_attr = "original_page_count" if side == "original" else "result_page_count"
        setattr(self, count_attr, page_count)
        current = getattr(self, current_attr)
        setattr(self, current_attr, min(max(current, 1), page_count) if page_count > 0 else 0)

        row = self._page_nav_rows.get(side)
        if row is None:
            return
        if page_count > 0:
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

    def _flash_page_entry(self, side: str) -> None:
        """Brief accent-colored border flash on the page entry after a
        successful jump - positive confirmation the input was actually
        processed even when the target page was already fully visible
        and scrolling had no visible effect (common on a short 1-2 page
        document that already fits the viewport), which otherwise reads
        as "typing a page number did nothing" even though it worked.
        """
        entry = self._page_entries.get(side)
        if entry is None:
            return
        entry.configure(border_color=COLOR_ACCENT, border_width=2)
        self.window.after(
            350, lambda: entry.configure(border_color=COLOR_BORDER, border_width=1)
        )

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
        self._flash_page_entry(side)
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

    def _maybe_show_magic_pen_hint(self) -> None:
        """Auto-show the "what can I do here" magic pen explainer once,
        the first time an editable (not locked) comparison window opens
        - per direct user feedback that the draw/erase controls alone,
        even made bigger, were too easy to miss as a discoverability cue
        by themselves. A modal dialog rather than a passive tooltip
        flash (see _maybe_show_zoom_link_hint) since this needs to
        actually be read once, not just glimpsed.
        """
        if not self.magic_pen_available or self.locked:
            return
        if hint_is_dismissed(MAGIC_PEN_HINT_ID):
            return
        MagicPenHintDialog(self.app, self.window, self._current_bindings())

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

    def _build_signature_removal_toggle(self, parent: ctk.CTkFrame) -> None:
        """The Etap 7 "Usuń podpisy elektroniczne" checkbox, mirrored into
        the comparison window so the choice can be revisited per document
        from inside the magic pen, not only once at pre-anonymization time
        (see gui_app.py's own copy of this card for the original). Only
        built when the caller has already confirmed
        self._document_has_signature_widget, which itself already implies
        not self.locked (see __init__).

        Its own warning-colored card, same COLOR_WARNING_SOFT/COLOR_WARNING
        framing as the pre-anonymization checkbox, for the same reason:
        this is an irreversible, structural removal, unlike anything else
        in this sidebar (the color legend below it is static, not even a
        toggle).

        CTkCheckBox has no wraplength support at all (see the same note
        on gui_app.py's category checkboxes) - a label long enough to
        explain itself inline would just overflow this 200px-wide sidebar
        column. Mirrors gui_app.py's own split here: a short bold label on
        the checkbox itself, the actual explanation in a separate wrapped
        CTkLabel underneath.
        """
        card = ctk.CTkFrame(
            parent,
            corner_radius=8,
            fg_color=COLOR_WARNING_SOFT,
            border_width=1,
            border_color=COLOR_WARNING,
        )
        card.pack(fill="x", pady=(0, 4))
        card_inner = ctk.CTkFrame(card, fg_color="transparent")
        card_inner.pack(fill="x", padx=10, pady=8)

        strip_signatures_var = tk.BooleanVar(value=self._current_strip_signatures)
        self._strip_signatures_var = strip_signatures_var

        def _on_toggle(var=strip_signatures_var) -> None:
            self._current_strip_signatures = var.get()
            self._update_pending_state()

        checkbox = ctk.CTkCheckBox(
            card_inner,
            text="Usuń podpisy elektroniczne",
            variable=strip_signatures_var,
            command=_on_toggle,
            font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
            text_color=COLOR_WARNING_TEXT,
            fg_color=COLOR_WARNING,
            hover_color=COLOR_WARNING,
        )
        checkbox.pack(anchor="w", pady=(0, 4))
        ctk.CTkLabel(
            card_inner,
            text=(
                "Nieodwracalnie usuwa pole podpisu elektronicznego z PDF-a "
                "po zaakceptowaniu edycji."
            ),
            font=ctk.CTkFont(family=FONT_FAMILY, size=10),
            text_color=COLOR_WARNING_TEXT,
            anchor="w",
            wraplength=150,
            justify="left",
        ).pack(fill="x")
        IconTooltip(
            checkbox,
            "Domyślnie zgodnie z pierwotnym wyborem sprzed anonimizacji. "
            "Gdy zaznaczone, kolejny zapis usunie z PDF-a pole podpisu "
            "elektronicznego razem z jego widoczną treścią - nieodwracalne "
            "w wyniku. Zmiana zacznie obowiązywać dopiero po zaakceptowaniu "
            "edycji.",
        )

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
        # Scrollable, not a plain CTkFrame: pack_propagate(False) above
        # protects this column's *width* on a narrow window (see the
        # docstring), but says nothing about height - shrinking the
        # window vertically used to just clip the legend with no way to
        # reach the rest of it. Same fix already proven for the "Szybkie
        # akcje" panel's own content (_build_quick_settings_panel).
        inner = ctk.CTkScrollableFrame(sidebar, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=14, pady=14)
        apply_subtle_scrollbar(inner)

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

        if not self.locked and self.ai_review.suggestions:
            self._build_ai_review_section(inner)
        elif not self.locked and self.ai_review.status_note:
            note_frame = ctk.CTkFrame(
                inner,
                corner_radius=8,
                fg_color=COLOR_BG,
                border_width=1,
                border_color=AI_SUGGESTION_OUTLINE_COLOR,
            )
            note_frame.pack(fill="x", pady=(0, 10))
            note_inner = ctk.CTkFrame(note_frame, fg_color="transparent")
            note_inner.pack(fill="x", padx=10, pady=8)
            self._ai_label(note_inner, "Sugestie AI", size=12, bold=True)
            self._ai_label(
                note_inner, self.ai_review.status_note, color=COLOR_TEXT_MUTED
            )

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
                text=self._sidebar_bindings_hint_text(),
                font=ctk.CTkFont(family=FONT_FAMILY, size=10),
                text_color=COLOR_TEXT_MUTED,
                anchor="w",
                wraplength=168,
                justify="left",
            ).pack(fill="x", pady=(0, 10))

        ctk.CTkFrame(inner, fg_color=COLOR_BORDER, height=1).pack(fill="x", pady=14)

        if self._document_has_signature_widget:
            self._build_signature_removal_toggle(inner)
            ctk.CTkFrame(inner, fg_color=COLOR_BORDER, height=1).pack(
                fill="x", pady=14
            )

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
        if not self.locked and self.ai_review.suggestions:
            # The review panel lives in the (now hidden) sidebar - keep a
            # way back to it that doesn't require finding the legend toggle.
            ai_button = ctk.CTkButton(
                rail,
                text="✨",
                width=24,
                height=24,
                corner_radius=6,
                fg_color=COLOR_BG,
                border_width=1,
                border_color=AI_SUGGESTION_OUTLINE_COLOR,
                hover_color=COLOR_ICON_IDLE,
                text_color=AI_SUGGESTION_OUTLINE_COLOR,
                font=ctk.CTkFont(family=FONT_FAMILY, size=12),
                command=self._start_ai_review,
            )
            ai_button.pack(pady=(0, 10))
            IconTooltip(ai_button, "Sugestie AI")
        return rail

    def _toggle_legend_sidebar_collapsed(self) -> None:
        self.legend_sidebar_collapsed = not self.legend_sidebar_collapsed
        if self._sidebar_widget is not None:
            self._sidebar_widget.destroy()
            self._sidebar_widget = None
        if self.content_row is not None and self.magic_pen_available:
            self._sidebar_widget = self._build_magic_pen_sidebar(self.content_row)
            self._sidebar_widget.pack(side="right", fill="y", padx=(12, 0))

    def _current_bindings(self) -> dict[str, str]:
        return resolve_magic_pen_bindings(
            self.app.magic_pen_interaction_mode, self.app.magic_pen_custom_bindings
        )

    def _current_bindings_description(self) -> str:
        return magic_pen_bindings_description_pl(self._current_bindings())

    def _button_action(self, button: str) -> str:
        return self._current_bindings().get(button, MAGIC_PEN_ACTION_MARK)

    def _sidebar_bindings_hint_text(self) -> str:
        return (
            f"{self._current_bindings_description()}. Odznaczanie: "
            "przytrzymaj i przeciągnij, by usunąć kilka naraz. Licznik "
            "zmian - na dole okna."
        )

    # -- local-LLM suggestion review ------------------------------------------
    #
    # Word-track-changes style: "Sprawdź sugestię AI" walks through the
    # suggestions one at a time, scrolling both panes to the spot, with a
    # dashed turquoise outline around what is pending and a panel in the
    # sidebar with the AI's justification plus Zatwierdź / Odrzuć / Zmień
    # ręcznie. Nothing here redacts anything by itself: accepting only
    # *stages* ordinary magic-pen edits (pending_add_rects /
    # pending_remove_keys), which still go through the same "Zapisz
    # zmiany" confirmation and regeneration as a hand-drawn edit. Decisions
    # are persisted to the suggestions sidecar on save, which is what the
    # main window's approval gate reads (count_unresolved_ai_suggestions).

    def _load_ai_review(self) -> None:
        if self.source_path is None:
            return
        try:
            word_pages, _spans = self._cached_detection()
        except (OSError, RuntimeError, ValueError):
            word_pages = []
        self.ai_review = prepare_ai_review(self.result_path, self.source_path, word_pages)

    def _ai_suggestion(self, suggestion_id: str | None) -> AiSuggestion | None:
        for suggestion in self.ai_review.suggestions:
            if suggestion.id == suggestion_id:
                return suggestion
        return None

    def _ai_status(self, suggestion_id: str) -> str:
        if suggestion_id in self._ai_rejected:
            return AI_SUGGESTION_STATUS_REJECTED
        staged_rects = self._ai_accepted_rects.get(suggestion_id, ())
        if any(rect in self.pending_add_rects for rect in staged_rects):
            return AI_SUGGESTION_STATUS_ACCEPTED
        staged_keys = self._ai_accepted_removals.get(suggestion_id, frozenset())
        if any(key in self.pending_remove_keys for key in staged_keys):
            return AI_SUGGESTION_STATUS_ACCEPTED
        return AI_SUGGESTION_STATUS_PENDING

    def _ai_pending_ids(self) -> list[str]:
        return [
            suggestion.id
            for suggestion in self.ai_review.suggestions
            if self._ai_status(suggestion.id) == AI_SUGGESTION_STATUS_PENDING
        ]

    def _ai_ready_to_apply(self) -> list[AiSuggestion]:
        """Pending suggestions with an auto-proposed rect - the only ones
        "Zastosuj wszystkie" may touch (everything else needs a human to
        say where)."""
        return [
            suggestion
            for suggestion in self.ai_review.suggestions
            if suggestion.rects
            and self._ai_status(suggestion.id) == AI_SUGGESTION_STATUS_PENDING
        ]

    def _ai_resolutions(self) -> dict[str, str]:
        """This session's decided suggestions, as the sidecar stores them."""
        resolutions: dict[str, str] = {}
        for suggestion in self.ai_review.suggestions:
            status = self._ai_status(suggestion.id)
            if status != AI_SUGGESTION_STATUS_PENDING:
                resolutions[suggestion.id] = status
        return resolutions

    def _ai_suggestion_page(self, suggestion: AiSuggestion) -> int | None:
        if suggestion.page is not None:
            return suggestion.page
        rects = self.ai_review.location_rects.get(suggestion.id, [])
        return int(rects[0]["page"]) if rects else None

    @staticmethod
    def _ai_manual_rect_from(rect_info: Mapping[str, object]) -> ManualRect:
        return ManualRect(
            page=int(rect_info["page"]),
            x0=float(rect_info["x0"]),
            y0=float(rect_info["y0"]),
            x1=float(rect_info["x1"]),
            y1=float(rect_info["y1"]),
            label=AI_SUGGESTION_LABEL,
        )

    def _stage_ai_rects(self, suggestion: AiSuggestion) -> None:
        """Stage a suggestion's proposed rect(s) as pending AI-labeled
        additions. Caller pushes the undo snapshot."""
        new_rects = tuple(self._ai_manual_rect_from(rect) for rect in suggestion.rects)
        self.pending_add_rects.extend(new_rects)
        self._ai_accepted_rects = MappingProxyType(
            {**self._ai_accepted_rects, suggestion.id: new_rects}
        )

    # -- actions --

    def _start_ai_review(self) -> None:
        if not self.ai_review.suggestions:
            return
        if self.legend_sidebar_collapsed:
            self._toggle_legend_sidebar_collapsed()
        pending = self._ai_pending_ids()
        self._focus_ai_suggestion(pending[0] if pending else self.ai_review.suggestions[0].id)

    def _focus_ai_suggestion(self, suggestion_id: str) -> None:
        if self._ai_manual_id != suggestion_id:
            self._ai_manual_id = None
        self._ai_current_id = suggestion_id
        self._refresh_ai_review_ui()
        self._scroll_to_ai_suggestion(suggestion_id)

    def _step_ai_suggestion(self, step: int) -> None:
        ids = [suggestion.id for suggestion in self.ai_review.suggestions]
        if not ids:
            return
        index = ids.index(self._ai_current_id) if self._ai_current_id in ids else -1
        self._focus_ai_suggestion(ids[(index + step) % len(ids)])

    def _advance_ai_review(self) -> None:
        """After a decision, move on to the next still-pending suggestion
        (wrapping around), or stay put once everything is decided."""
        ids = [suggestion.id for suggestion in self.ai_review.suggestions]
        pending = set(self._ai_pending_ids())
        if not pending:
            self._ai_manual_id = None
            self._refresh_ai_review_ui()
            return
        start = ids.index(self._ai_current_id) + 1 if self._ai_current_id in ids else 0
        for offset in range(len(ids)):
            candidate = ids[(start + offset) % len(ids)]
            if candidate in pending:
                self._focus_ai_suggestion(candidate)
                return

    def _accept_ai_suggestion(self) -> None:
        suggestion = self._ai_suggestion(self._ai_current_id)
        if suggestion is None:
            return
        if suggestion.finding_type == "unnecessary_redaction":
            # The model only points at a sentence: map "zbędna redakcja"
            # onto un-redacting the existing redactions inside it (agreed
            # with the user 2026-09-23), falling back to the eraser by
            # hand when nothing overlaps.
            area = self.ai_review.location_rects.get(suggestion.id, [])
            keys = frozenset(
                rect_info_key(hit)
                for hit in redactions_overlapping_area(self.visible_rects, area)
            )
            if not keys:
                self._enter_ai_manual_mode(
                    suggestion.id,
                    "Nie znaleziono redakcji w tym zdaniu. Odznacz ją ręcznie "
                    "gumką - zostanie zaliczona do tej sugestii.",
                )
                return
            self._push_undo_snapshot()
            self.pending_remove_keys |= keys
            self._ai_accepted_removals = MappingProxyType(
                {**self._ai_accepted_removals, suggestion.id: keys}
            )
        elif suggestion.rects:
            self._push_undo_snapshot()
            self._stage_ai_rects(suggestion)
        else:
            # Narrative combinations (and a missed redaction whose sentence
            # could not be located) have no ready rect: accepting always
            # means marking the area by hand, with the justification as
            # the hint.
            self._enter_ai_manual_mode(
                suggestion.id,
                "Zaznacz ręcznie, co ukryć (np. tylko wybrane słowa). "
                "Każde zaznaczenie zostanie oznaczone jako sugestia AI.",
            )
            return
        self._redraw_all_overlays()
        self._update_pending_state()
        self._advance_ai_review()

    def _reject_ai_suggestion(self) -> None:
        suggestion = self._ai_suggestion(self._ai_current_id)
        if suggestion is None:
            return
        self._push_undo_snapshot()
        self._ai_rejected = self._ai_rejected | {suggestion.id}
        if self._ai_manual_id == suggestion.id:
            self._ai_manual_id = None
        self._redraw_all_overlays()
        self._update_pending_state()
        self._advance_ai_review()

    def _edit_ai_suggestion_manually(self) -> None:
        suggestion = self._ai_suggestion(self._ai_current_id)
        if suggestion is None:
            return
        self._enter_ai_manual_mode(
            suggestion.id,
            "Zaznacz ręcznie, co ukryć - np. zawęź propozycję AI do "
            "wybranych słów. Każde zaznaczenie zostanie oznaczone jako "
            "sugestia AI.",
        )

    def _enter_ai_manual_mode(self, suggestion_id: str, notice: str) -> None:
        self._ai_manual_id = suggestion_id
        self._ai_manual_notice = notice
        self._focus_ai_suggestion(suggestion_id)

    def _exit_ai_manual_mode(self) -> None:
        self._ai_manual_id = None
        self._refresh_ai_review_ui()
        if self._ai_status(self._ai_current_id or "") != AI_SUGGESTION_STATUS_PENDING:
            self._advance_ai_review()

    def _undo_ai_decision(self) -> None:
        """Take back this one suggestion's decision (its staged rects,
        removals or rejection) without touching any other pending edit."""
        suggestion_id = self._ai_current_id
        if suggestion_id is None or self._ai_status(suggestion_id) == AI_SUGGESTION_STATUS_PENDING:
            return
        self._push_undo_snapshot()
        self._ai_rejected = self._ai_rejected - {suggestion_id}
        staged_rects = self._ai_accepted_rects.get(suggestion_id, ())
        self.pending_add_rects = [
            rect for rect in self.pending_add_rects if rect not in staged_rects
        ]
        self.pending_remove_keys = self.pending_remove_keys - set(
            self._ai_accepted_removals.get(suggestion_id, frozenset())
        )
        self._redraw_all_overlays()
        self._update_pending_state()

    def _apply_all_ai_suggestions(self) -> None:
        targets = self._ai_ready_to_apply()
        if not targets:
            return
        remaining = len(self._ai_pending_ids()) - len(targets)
        message = (
            f"Zastosować {len(targets)} sugestii AI z gotowym zaznaczeniem?\n\n"
            "AI może się mylić - zaznaczenie może objąć za dużo albo za "
            "mało. Przed zapisem każdą zmianę nadal widać na podglądzie i "
            "można ją cofnąć (Ctrl+Z) lub odznaczyć."
        )
        if remaining:
            message += (
                f"\n\nPozostałe sugestie ({remaining}) wymagają Twojej "
                "decyzji - nie zostaną zmienione."
            )
        if not messagebox.askyesno(
            "Zastosuj wszystkie sugestie AI", message, icon="warning", parent=self.window
        ):
            return
        self._push_undo_snapshot()
        for suggestion in targets:
            self._stage_ai_rects(suggestion)
        self._redraw_all_overlays()
        self._update_pending_state()
        self._advance_ai_review()

    def _close_ai_review(self) -> None:
        self._ai_current_id = None
        self._ai_manual_id = None
        self._redraw_all_overlays()
        self._refresh_ai_review_ui()

    # -- navigation --

    def _scroll_to_ai_suggestion(self, suggestion_id: str) -> None:
        suggestion = self._ai_suggestion(suggestion_id)
        if suggestion is None:
            return
        page = self._ai_suggestion_page(suggestion)
        if page is None:
            return
        page_rects = [
            rect
            for rect in self.ai_review.location_rects.get(suggestion_id, [])
            if int(rect["page"]) == page
        ]
        top = min((float(rect["y0"]) for rect in page_rects), default=0.0)
        self._scroll_panes_to_point(page, top)

    def _scroll_panes_to_point(self, page_number: int, y_pt: float) -> None:
        """Scroll the result pane so PDF point ``y_pt`` on ``page_number``
        sits near the top of the view - and, while the panes are linked,
        the "Oryginał" pane to the same relative spot on the same page
        (its page is a differently-rendered image, so the offset is
        carried over as a fraction of the page's height)."""
        canvas = self._page_canvases.get(page_number)
        if canvas is None:
            return
        offset_px = y_pt * self._page_zoom.get(page_number, 1.0)
        self._scroll_frame_to_offset(self.right_frame, canvas, offset_px)
        self.result_current_page = page_number
        original_widget = self._original_page_widgets.get(page_number)
        if self.zoom_linked and original_widget is not None:
            try:
                page_height = max(int(canvas.cget("height")), 1)
                original_offset = offset_px / page_height * original_widget.winfo_height()
            except (tk.TclError, ValueError):
                original_offset = 0.0
            self._scroll_frame_to_offset(self.left_frame, original_widget, original_offset)
            self.original_current_page = page_number
        self._refresh_page_nav_entries()

    def _scroll_frame_to_offset(
        self, frame: ctk.CTkScrollableFrame | None, widget: tk.Misc, offset_px: float
    ) -> None:
        """_scroll_frame_to_widget plus an offset into that widget - same
        private-canvas reach and same defensive no-op on any Tk error."""
        canvas = getattr(frame, "_parent_canvas", None)
        if canvas is None:
            return
        try:
            canvas.update_idletasks()
            bbox = canvas.bbox("all")
            if not bbox:
                return
            fraction = ai_scroll_fraction(
                widget.winfo_y(),
                offset_px,
                max(bbox[3] - bbox[1], 1),
                canvas.winfo_height(),
            )
            canvas.yview_moveto(fraction)
        except tk.TclError:
            pass

    # -- drawing --

    def _draw_ai_overlay(self, canvas: tk.Canvas, page_number: int, zoom: float) -> list[int]:
        """Dashed outlines for the suggestions on this page: every pending
        suggestion's auto-proposed rect, plus the focused suggestion's
        location hint (its sentence) when it has no rect of its own.
        Decided suggestions draw nothing extra - an accepted one already
        shows as its staged edit, a rejected one simply disappears."""
        drawn_ids: list[int] = []
        for suggestion in self.ai_review.suggestions:
            if self._ai_status(suggestion.id) != AI_SUGGESTION_STATUS_PENDING:
                continue
            is_current = suggestion.id == self._ai_current_id
            if not suggestion.rects and not is_current:
                continue
            dash = (4, 2) if suggestion.rects else (2, 3)
            for rect in self.ai_review.location_rects.get(suggestion.id, []):
                if int(rect["page"]) != page_number:
                    continue
                drawn_ids.append(
                    canvas.create_rectangle(
                        float(rect["x0"]) * zoom - 2,
                        float(rect["y0"]) * zoom - 2,
                        float(rect["x1"]) * zoom + 2,
                        float(rect["y1"]) * zoom + 2,
                        outline=AI_SUGGESTION_OUTLINE_COLOR,
                        width=3 if is_current else 2,
                        dash=dash,
                    )
                )
        return drawn_ids

    # -- widgets --

    def _build_ai_review_title_button(self, parent: ctk.CTkFrame) -> None:
        if not self.ai_review.suggestions:
            return
        button = ctk.CTkButton(
            parent,
            text="",
            height=30,
            corner_radius=8,
            border_width=1,
            border_color=AI_SUGGESTION_OUTLINE_COLOR,
            fg_color=COLOR_BG,
            hover_color=COLOR_ICON_IDLE,
            text_color=AI_SUGGESTION_OUTLINE_COLOR,
            font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
            command=self._start_ai_review,
        )
        button.pack(side="right", padx=(0, 10))
        IconTooltip(
            button,
            "Przejdź po kolei przez sugestie lokalnego modelu AI. Każdą "
            "trzeba zatwierdzić lub odrzucić przed zatwierdzeniem pliku.",
        )
        self._ai_title_button = button
        self._refresh_ai_title_button()

    def _refresh_ai_title_button(self) -> None:
        button = self._ai_title_button
        if button is None:
            return
        pending = len(self._ai_pending_ids())
        text = (
            f"✨ Sprawdź sugestię AI ({pending})" if pending else "✓ Sugestie AI przejrzane"
        )
        try:
            button.configure(text=text)
        except tk.TclError:
            pass

    def _build_ai_review_section(self, parent: ctk.CTkBaseClass) -> None:
        section = ctk.CTkFrame(
            parent,
            corner_radius=8,
            fg_color=COLOR_BG,
            border_width=1,
            border_color=AI_SUGGESTION_OUTLINE_COLOR,
        )
        section.pack(fill="x", pady=(0, 10))
        self._ai_section = section
        self._populate_ai_review_section()

    def _ai_label(
        self, parent: ctk.CTkBaseClass, text: str, *, size: int = 10, bold: bool = False,
        color: str = COLOR_TEXT,
    ) -> ctk.CTkLabel:
        label = ctk.CTkLabel(
            parent,
            text=text,
            font=ctk.CTkFont(family=FONT_FAMILY, size=size, weight="bold" if bold else "normal"),
            text_color=color,
            anchor="w",
            wraplength=146,
            justify="left",
        )
        label.pack(fill="x", pady=(0, 4))
        return label

    def _ai_button(
        self, parent: ctk.CTkBaseClass, text: str, command, *, primary: bool = False
    ) -> ctk.CTkButton:
        button = ctk.CTkButton(
            parent,
            text=text,
            height=28,
            corner_radius=8,
            fg_color=AI_SUGGESTION_OUTLINE_COLOR if primary else "transparent",
            hover_color=COLOR_ACCENT_HOVER if primary else COLOR_ICON_IDLE,
            border_width=0 if primary else 1,
            border_color=COLOR_BORDER,
            text_color="#FFFFFF" if primary else COLOR_TEXT,
            font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold" if primary else "normal"),
            command=command,
        )
        button.pack(fill="x", pady=(0, 4))
        return button

    def _populate_ai_review_section(self) -> None:
        section = self._ai_section
        if section is None:
            return
        try:
            if not section.winfo_exists():
                return
        except tk.TclError:
            return
        for child in section.winfo_children():
            child.destroy()
        inner = ctk.CTkFrame(section, fg_color="transparent")
        inner.pack(fill="x", padx=10, pady=8)

        suggestions = self.ai_review.suggestions
        pending_count = len(self._ai_pending_ids())
        self._ai_label(inner, "✨ Sugestie AI", size=12, bold=True)
        if not suggestions:
            self._ai_label(
                inner, "✓ Wszystkie sugestie rozstrzygnięte i zapisane.", color=COLOR_TEXT_MUTED
            )
            return
        if not self.ai_review.text_matched:
            self._ai_label(
                inner,
                "Tekst dokumentu różni się od tego, który czytało AI - "
                "sugestie nie mają wskazanego miejsca.",
                color=COLOR_WARNING_TEXT,
            )

        current = self._ai_suggestion(self._ai_current_id)
        if current is None:
            if pending_count:
                self._ai_label(
                    inner,
                    f"Do przejrzenia: {pending_count} z {len(suggestions)}. "
                    "Każdą trzeba zatwierdzić lub odrzucić przed zatwierdzeniem pliku.",
                    color=COLOR_TEXT_MUTED,
                )
                self._ai_button(inner, "Sprawdź sugestię AI", self._start_ai_review, primary=True)
            else:
                self._ai_label(
                    inner,
                    "Wszystkie sugestie rozstrzygnięte. Zapisz zmiany, by je utrwalić.",
                    color=COLOR_TEXT_MUTED,
                )
                self._ai_button(inner, "Przejrzyj ponownie", self._start_ai_review)
            self._build_ai_apply_all_button(inner)
            return

        nav = ctk.CTkFrame(inner, fg_color="transparent")
        nav.pack(fill="x", pady=(0, 6))
        position = [s.id for s in suggestions].index(current.id) + 1
        for text, step, side in (("◀", -1, "left"), ("▶", 1, "right")):
            ctk.CTkButton(
                nav,
                text=text,
                width=26,
                height=22,
                corner_radius=6,
                fg_color=COLOR_ICON_IDLE,
                hover_color=COLOR_ACCENT_HOVER,
                text_color=COLOR_TEXT,
                font=ctk.CTkFont(family=FONT_FAMILY, size=10),
                command=lambda s=step: self._step_ai_suggestion(s),
            ).pack(side=side)
        ctk.CTkLabel(
            nav,
            text=f"{position} / {len(suggestions)}",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            text_color=COLOR_TEXT_MUTED,
        ).pack(side="left", expand=True)

        self._ai_label(inner, ai_suggestion_title_pl(current), size=11, bold=True)
        quote = ai_quote_text(self.ai_review.sentence_texts.get(current.id, []))
        if quote:
            self._ai_label(inner, f"„{quote}”")
        page = self._ai_suggestion_page(current)
        self._ai_label(
            inner,
            f"Strona {page}" if page is not None
            else "Nie udało się wskazać miejsca - poszukaj go ręcznie.",
            color=COLOR_TEXT_MUTED,
        )

        status = self._ai_status(current.id)
        if self._ai_manual_id == current.id:
            self._ai_label(inner, f"✏ {self._ai_manual_notice}", color=COLOR_WARNING_TEXT)
            self._ai_button(inner, "Zakończ zaznaczanie", self._exit_ai_manual_mode, primary=True)
        elif status == AI_SUGGESTION_STATUS_PENDING:
            self._ai_button(inner, "Zatwierdź", self._accept_ai_suggestion, primary=True)
            self._ai_button(inner, "Odrzuć", self._reject_ai_suggestion)
            self._ai_button(inner, "Zmień ręcznie", self._edit_ai_suggestion_manually)
        if status != AI_SUGGESTION_STATUS_PENDING:
            self._ai_label(
                inner,
                "✓ Zaakceptowana" if status == AI_SUGGESTION_STATUS_ACCEPTED
                else "✗ Odrzucona",
                bold=True,
                color=AI_SUGGESTION_OUTLINE_COLOR
                if status == AI_SUGGESTION_STATUS_ACCEPTED
                else COLOR_HIGH_RISK,
            )
            self._ai_label(
                inner, "Zapisz zmiany, by utrwalić decyzję.", color=COLOR_TEXT_MUTED
            )
            if self._ai_manual_id != current.id:
                self._ai_button(inner, "Cofnij decyzję", self._undo_ai_decision)

        ctk.CTkFrame(inner, fg_color=COLOR_BORDER, height=1).pack(fill="x", pady=6)
        self._ai_label(inner, f"Pozostało: {pending_count}", color=COLOR_TEXT_MUTED)
        self._build_ai_apply_all_button(inner)
        self._ai_button(inner, "Zamknij przegląd", self._close_ai_review)

    def _build_ai_apply_all_button(self, parent: ctk.CTkBaseClass) -> None:
        ready = len(self._ai_ready_to_apply())
        if ready:
            self._ai_button(parent, f"Zastosuj wszystkie ({ready})", self._apply_all_ai_suggestions)

    def _refresh_ai_review_ui(self) -> None:
        # Also runs (via _update_pending_state) in windows that never had
        # suggestions - a cheap no-op there. Checks the widgets too, not
        # only the list, so the panel still updates after the last
        # suggestion has been saved and dropped from the review.
        if (
            not self.ai_review.suggestions
            and self._ai_section is None
            and self._ai_title_button is None
        ):
            return
        self._populate_ai_review_section()
        self._refresh_ai_title_button()
        self._redraw_all_overlays()

    # -- magic pen: rendering -------------------------------------------------

    def _sensitive_terms_fingerprint(self) -> object:
        """Cheap on-disk fingerprint for the dictionary file, so editing it
        in place (same path, new content) while this window stays open -
        it is deliberately non-modal, the rest of the app stays usable -
        still invalidates the detection cache the same way it always
        forced a fresh re-read before this cache existed. mtime+size is
        enough to catch a real edit without hashing the whole file on
        every reload/save."""
        path = self.app.sensitive_terms_path
        if not path:
            return None
        try:
            stat = Path(path).stat()
        except OSError:
            return None
        return (stat.st_mtime_ns, stat.st_size)

    def _cached_detection(self) -> tuple[list, list]:
        """Return this session's (word_pages, spans) for ``self.source_path``,
        computing and caching them once instead of on every reload/save.

        The cache key covers the detection settings that can actually
        change while this window stays open (NER on/off, dictionary path
        and its contents) so a mid-session Settings or dictionary-file
        change still triggers a fresh, correct recompute rather than
        reusing stale results - only the repeated, wasted recompute of
        the *same* detection is being avoided here.
        """
        key = (
            str(self.source_path),
            str(self.app.sensitive_terms_path or ""),
            self._sensitive_terms_fingerprint(),
            bool(self.app.use_ner),
        )
        if self._detection_cache is None or self._detection_cache_key != key:
            self._detection_cache = compute_pdf_redaction_spans(
                self.source_path,
                sensitive_terms_path=self.app.sensitive_terms_path,
                use_ner=self.app.use_ner,
                active_labels=self._original_active_labels,
                active_pages=self._original_active_pages,
            )
            self._detection_cache_key = key
        return self._detection_cache

    def _reload_visible_rects(self) -> None:
        if self.source_path is None:
            self.visible_rects = []
            return
        try:
            word_pages, spans = self._cached_detection()
            self.visible_rects = compute_visible_redaction_rects(
                self.source_path,
                edits=self.edits,
                sensitive_terms_path=self.app.sensitive_terms_path,
                use_ner=self.app.use_ner,
                word_pages=word_pages,
                spans=spans,
                active_labels=self._original_active_labels,
                active_pages=self._original_active_pages,
            )
        except (OSError, RuntimeError, ValueError):
            self.visible_rects = []
            self._detection_cache = None
            self._detection_cache_key = None

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
                        cursor=self._idle_magic_pen_cursor(),
                    )
                    canvas.pack(pady=6)
                    canvas.create_image(0, 0, anchor="nw", image=tk_image)
                    self._page_canvases[page_index] = canvas
                    self._page_zoom[page_index] = zoom
                    if not self.locked:
                        # Every one of the three mouse buttons is bound to
                        # whatever action self._button_action resolves it
                        # to under the current interaction mode - which
                        # button does what is data (see
                        # resolve_magic_pen_bindings), not baked into
                        # these bindings. An approved (locked) file skips
                        # every binding entirely rather than
                        # binding-then-ignoring, so the canvas genuinely
                        # behaves like a plain, non-interactive preview.
                        for tk_button_id, button_name in _TK_BUTTON_TO_NAME.items():
                            canvas.bind(
                                f"<ButtonPress-{tk_button_id}>",
                                lambda event, p=page_index, b=button_name: (
                                    self._on_pane_button_press(event, p, b)
                                ),
                            )
                            canvas.bind(
                                f"<B{tk_button_id}-Motion>",
                                lambda event, p=page_index, b=button_name: (
                                    self._on_pane_button_drag(event, p, b)
                                ),
                            )
                            canvas.bind(
                                f"<ButtonRelease-{tk_button_id}>",
                                lambda event, p=page_index, b=button_name: (
                                    self._on_pane_button_release(event, p, b)
                                ),
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
                "label": rect.label,
                "x0": rect.x0,
                "y0": rect.y0,
                "x1": rect.x1,
                "y1": rect.y1,
            }
            for rect in self.pending_add_rects
        ]
        return list(self.visible_rects) + pending

    def _on_pane_button_press(
        self, event: tk.Event, page_number: int, button: str
    ) -> None:
        """Dispatch a mouse-button press to whichever action this window's
        interaction mode currently assigns that button - mark a new
        redaction, erase an existing one, or pan the view. Which of the
        three happens is entirely data-driven (see resolve_magic_pen_bindings
        via self._button_action), not hardcoded per physical button.
        """
        action = self._button_action(button)
        self._active_gesture_action = action
        canvas = self._page_canvases.get(page_number)
        if canvas is not None:
            # Reflect the button actually pressed, not just LPM's idle
            # cursor - a PPM/MPM gesture under a mode where they do
            # something else should look like that something else while
            # held, per the same "graficznie widać co robi" feedback the
            # idle cursor and badges above are for.
            try:
                canvas.configure(
                    cursor=_MAGIC_PEN_CURSOR_BY_ACTION.get(action, "tcross")
                )
            except tk.TclError:
                pass
        if action == MAGIC_PEN_ACTION_PAN:
            target = self._pan_target(self.right_frame)
            if target is not None:
                target.scan_mark(event.x_root, event.y_root)
            return
        if action == MAGIC_PEN_ACTION_ERASE:
            self._erased_this_gesture = set()
            self._erase_at_point(event.x, event.y, page_number)
            return
        # mark: start a new redaction rectangle
        self._drag_start = (event.x, event.y)
        self._drag_rect_id = None

    def _erase_at_point(self, x: float, y: float, page_number: int) -> None:
        zoom = self._page_zoom.get(page_number, 1.0)
        px, py = canvas_point_to_pdf_point(x, y, zoom)
        hit = find_rect_at_point(self._hit_test_pool(), page_number, px, py)
        if hit is None:
            return
        key = rect_info_key(hit)
        if key in self._erased_this_gesture:
            # Already toggled off earlier in this same press-to-release
            # gesture - a drag that passes back over the same rect must
            # not toggle it a second time.
            return
        self._erased_this_gesture.add(key)
        self._toggle_pending_remove(hit)

    def _on_pane_button_drag(
        self, event: tk.Event, page_number: int, button: str
    ) -> None:
        # The action in effect for this gesture was fixed at press time,
        # not re-read from the (possibly since-changed) current mode -
        # button always means what it meant when the gesture started.
        action = self._active_gesture_action
        if action == MAGIC_PEN_ACTION_PAN:
            target = self._pan_target(self.right_frame)
            if target is None:
                return
            try:
                target.scan_dragto(event.x_root, event.y_root, gain=1)
            except TypeError:
                target.scan_dragto(event.x_root, event.y_root)
            return
        if action == MAGIC_PEN_ACTION_ERASE:
            self._erase_at_point(event.x, event.y, page_number)
            return
        if action != MAGIC_PEN_ACTION_MARK or self._drag_start is None:
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

    def _on_pane_button_release(
        self, event: tk.Event, page_number: int, button: str
    ) -> None:
        action = self._active_gesture_action
        self._active_gesture_action = None
        release_canvas = self._page_canvases.get(page_number)
        if release_canvas is not None:
            try:
                release_canvas.configure(cursor=self._idle_magic_pen_cursor())
            except tk.TclError:
                pass
        if action == MAGIC_PEN_ACTION_ERASE:
            self._erased_this_gesture = set()
            return
        if action != MAGIC_PEN_ACTION_MARK:
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
        self._push_undo_snapshot()
        manual_suggestion = self._ai_suggestion(self._ai_manual_id)
        # Only a suggestion asking for MORE redaction can be accepted by
        # drawing: for an "unnecessary redaction" one (eraser fallback), a
        # drawn box is an ordinary magic-pen rect and accepts nothing.
        manual_suggestion_id = (
            manual_suggestion.id
            if manual_suggestion is not None
            and manual_suggestion.finding_type != "unnecessary_redaction"
            else None
        )
        new_rect = ManualRect(
            page=page_number,
            x0=px0,
            y0=py0,
            x1=px1,
            y1=py1,
            label=AI_SUGGESTION_LABEL if manual_suggestion_id else MANUAL_REDACTION_LABEL,
        )
        self.pending_add_rects.append(new_rect)
        if manual_suggestion_id:
            # Marking by hand on behalf of an AI suggestion ("Zmień
            # ręcznie" / accepting one with no ready rect): the rect counts
            # as accepting that suggestion.
            self._ai_accepted_rects = MappingProxyType(
                {
                    **self._ai_accepted_rects,
                    manual_suggestion_id: (
                        *self._ai_accepted_rects.get(manual_suggestion_id, ()),
                        new_rect,
                    ),
                }
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
                    "label": rect.label,
                    "x0": rect.x0,
                    "y0": rect.y0,
                    "x1": rect.x1,
                    "y1": rect.y1,
                }
            )
            if rect_key == key:
                # A not-yet-saved manual addition: clicking it again in
                # remove mode simply cancels that pending addition.
                self._push_undo_snapshot()
                del self.pending_add_rects[index]
                self._redraw_overlay(page_number)
                self._update_pending_state()
                return
        self._push_undo_snapshot()
        if key in self.pending_remove_keys:
            # Clicking an already-staged-for-removal rect a second time
            # un-stages it, so a misclick doesn't require cancelling every
            # other pending change to undo.
            self.pending_remove_keys.discard(key)
        else:
            self.pending_remove_keys.add(key)
            manual_suggestion = self._ai_suggestion(self._ai_manual_id)
            if (
                manual_suggestion is not None
                and manual_suggestion.finding_type == "unnecessary_redaction"
            ):
                # Un-redacting by hand on behalf of an "unnecessary
                # redaction" suggestion counts as accepting it.
                self._ai_accepted_removals = MappingProxyType(
                    {
                        **self._ai_accepted_removals,
                        manual_suggestion.id: frozenset(
                            {*self._ai_accepted_removals.get(manual_suggestion.id, ()), key}
                        ),
                    }
                )
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
            # A staged rect accepted from an AI suggestion is outlined in
            # its own legend color, so it's distinguishable from a plain
            # hand-drawn one before saving too, not only after.
            outline = (
                AI_SUGGESTION_OUTLINE_COLOR if rect.label == AI_SUGGESTION_LABEL else "#dc2626"
            )
            drawn_ids.append(
                canvas.create_rectangle(
                    x0, y0, x1, y1, fill="#111827", outline=outline, width=2
                )
            )

        drawn_ids.extend(self._draw_ai_overlay(canvas, page_number, zoom))
        self._overlay_ids[page_number] = drawn_ids

    def _redraw_all_overlays(self) -> None:
        for page_number in list(self._page_canvases.keys()):
            self._redraw_overlay(page_number)

    # -- magic pen: undo/redo for pending (unsaved) edits --------------------

    def _snapshot_pending_edit_state(self) -> tuple[list[ManualRect], set, bool, frozenset]:
        # Includes the signature toggle alongside the rects it has sat next
        # to ever since _has_pending_changes/_pending_change_count started
        # treating it as a pending change too - without this, cancelling a
        # toggle-only change (or a change made alongside rect edits) then
        # pressing Ctrl+Z would leave the toggle silently un-undone even
        # though the rects came back, a real bug code review caught.
        # AI suggestion rejections ride along for the same reason: a
        # rejection is a pending decision exactly like a staged rect.
        return (
            list(self.pending_add_rects),
            set(self.pending_remove_keys),
            self._current_strip_signatures,
            self._ai_rejected,
        )

    def _restore_pending_edit_state(
        self, snapshot: tuple[list[ManualRect], set, bool, frozenset]
    ) -> None:
        (
            self.pending_add_rects,
            self.pending_remove_keys,
            strip_signatures,
            self._ai_rejected,
        ) = snapshot
        self._current_strip_signatures = strip_signatures
        if self._strip_signatures_var is not None:
            self._strip_signatures_var.set(strip_signatures)
        self._redraw_all_overlays()
        self._update_pending_state()
        self._update_undo_redo_buttons()

    def _push_undo_snapshot(self) -> None:
        """Record the pending-edit state *before* the mutation about to
        happen, so Ctrl+Z can restore it - called at the start of every
        method that mutates pending_add_rects/pending_remove_keys.
        Whole-state snapshots rather than tracking each action's inverse
        individually: simpler and much less error-prone for three
        different mutation shapes (add a rect, toggle a removal, cancel
        a pending add), and the state involved is tiny (a handful of
        rects/keys) so copying it is cheap. Clears the redo stack -
        making a new edit after undoing invalidates whatever was undone,
        the same way every standard undo/redo editor behaves.
        """
        self._edit_undo_stack.append(self._snapshot_pending_edit_state())
        self._edit_redo_stack.clear()
        self._update_undo_redo_buttons()

    def _clear_undo_redo_history(self) -> None:
        """Called after a successful save (the rect ecosystem changes
        underneath - visible_rects gets reloaded from the regenerated
        PDF, so old snapshots referencing the previous one are no longer
        meaningful) and when a fresh magic pen pane is built."""
        self._edit_undo_stack = []
        self._edit_redo_stack = []
        self._update_undo_redo_buttons()

    def _undo_last_edit(self) -> None:
        if not self._edit_undo_stack:
            return
        self._edit_redo_stack.append(self._snapshot_pending_edit_state())
        self._restore_pending_edit_state(self._edit_undo_stack.pop())

    def _redo_last_edit(self) -> None:
        if not self._edit_redo_stack:
            return
        self._edit_undo_stack.append(self._snapshot_pending_edit_state())
        self._restore_pending_edit_state(self._edit_redo_stack.pop())

    def _update_undo_redo_buttons(self) -> None:
        # Per direct feedback, these were "practically invisible" even
        # while enabled - .configure(state=...) alone never changed
        # their color, so an active Undo looked identical to a disabled
        # one (both the same muted ghost-button style). Recoloring to
        # this app's own accent scheme when there is actually something
        # to undo/redo gives them the same visual weight a clickable
        # control gets everywhere else in this app.
        if self.undo_button is not None:
            self._style_history_button(self.undo_button, bool(self._edit_undo_stack))
        if self.redo_button is not None:
            self._style_history_button(self.redo_button, bool(self._edit_redo_stack))

    @staticmethod
    def _style_history_button(button: ctk.CTkButton, enabled: bool) -> None:
        button.configure(
            state="normal" if enabled else "disabled",
            fg_color=COLOR_ACCENT_SOFT if enabled else COLOR_BG,
            border_color=COLOR_ACCENT if enabled else COLOR_BORDER,
            text_color=COLOR_ACCENT if enabled else COLOR_TEXT_MUTED,
        )

    def _signature_choice_changed(self) -> bool:
        return self._current_strip_signatures != self._original_strip_signatures

    def _has_pending_changes(self) -> bool:
        return self._has_pending_document_changes() or bool(self._ai_rejected)

    def _has_pending_document_changes(self) -> bool:
        """Pending changes that need the PDF regenerated - everything
        except AI suggestion rejections, which only touch the sidecar."""
        return (
            bool(self.pending_remove_keys)
            or bool(self.pending_add_rects)
            or self._signature_choice_changed()
        )

    def _pending_change_count(self) -> int:
        """Rect edits plus the signature toggle, the latter counted as
        one unit when changed - so every count-based label (save button,
        floating status, confirmation title) stays accurate without each
        needing its own separate "plus a signature change" branch, and a
        toggle-only change (0 rect edits) reads as "(1)" instead of a
        misleading "(0)"."""
        return (
            len(self.pending_remove_keys)
            + len(self.pending_add_rects)
            + int(self._signature_choice_changed())
            + len(self._ai_rejected)
        )

    def _update_pending_state(self) -> None:
        count = self._pending_change_count()
        mode = self._floating_actions_mode()
        if self.save_button is not None:
            # Always enabled/accent-colored: the whole overlay only exists
            # while there is something to accept, so a disabled-looking
            # button inside it would be a contradiction.
            self.save_button.configure(text=format_save_button_text(count))
        if self.pen_status_label is not None:
            self.pen_status_label.configure(
                text=format_floating_actions_status(mode, count)
            )
        self._update_floating_actions_visibility()
        self._refresh_ai_review_ui()

    def _cancel_pending_changes(self) -> None:
        self._push_undo_snapshot()
        self.pending_remove_keys = set()
        self.pending_add_rects = []
        self._ai_rejected = frozenset()
        self._ai_manual_id = None
        self._current_strip_signatures = self._original_strip_signatures
        if self._strip_signatures_var is not None:
            self._strip_signatures_var.set(self._original_strip_signatures)
        for page_number in list(self._page_canvases.keys()):
            self._redraw_overlay(page_number)
        self._update_pending_state()

    def _confirm_and_save_pending_changes(self) -> None:
        """Show a content-free summary of the pending edits (counts and
        page numbers only - never the redacted text itself, see
        format_pending_edit_summary_lines) and ask for one explicit
        confirmation before actually regenerating the PDF - per direct
        user feedback that a plain "Zapisz zmiany" undersold what
        clicking it actually does.
        """
        if not self._has_pending_changes():
            return
        added_pages = sorted({rect.page for rect in self.pending_add_rects})
        removed_pages = sorted(
            {
                int(rect_info["page"])
                for rect_info in self.visible_rects
                if rect_info_key(rect_info) in self.pending_remove_keys
            }
        )
        signature_removal_changed = self._signature_choice_changed()
        summary_lines = format_pending_edit_summary_lines(
            len(self.pending_add_rects),
            added_pages,
            len(self.pending_remove_keys),
            removed_pages,
            signature_removal_changed=signature_removal_changed,
            strip_signatures=self._current_strip_signatures,
        )
        resolutions = self._ai_resolutions()
        if resolutions:
            accepted = sum(
                1 for status in resolutions.values() if status == AI_SUGGESTION_STATUS_ACCEPTED
            )
            summary_lines.append(
                f"Sugestie AI: zaakceptowane {accepted}, "
                f"odrzucone {len(resolutions) - accepted}"
            )
        self._build_save_confirmation_dialog(summary_lines)

    def _build_save_confirmation_dialog(self, summary_lines: list[str]) -> None:
        total = self._pending_change_count()
        window = ctk.CTkToplevel(self.window)
        dialog_height = 190 + 24 * len(summary_lines)
        window.title(format_pending_edit_confirmation_title(total))
        center_window_over_parent(window, self.window, 420, dialog_height)
        window.resizable(False, False)
        window.configure(fg_color=COLOR_BG)
        window.transient(self.window)
        window.grab_set()

        ctk.CTkLabel(
            window,
            text=format_pending_edit_confirmation_title(total),
            font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"),
            text_color=COLOR_TEXT,
            wraplength=370,
            justify="left",
        ).pack(fill="x", padx=20, pady=(20, 8))

        for line in summary_lines:
            ctk.CTkLabel(
                window,
                text=f"• {line}",
                font=ctk.CTkFont(family=FONT_FAMILY, size=12),
                text_color=COLOR_TEXT,
                wraplength=370,
                justify="left",
                anchor="w",
            ).pack(fill="x", padx=24, pady=2)

        ctk.CTkLabel(
            window,
            text="Dokument zostanie od razu przebudowany z tymi zmianami.",
            font=ctk.CTkFont(family=FONT_FAMILY, size=10),
            text_color=COLOR_TEXT_MUTED,
            wraplength=370,
            justify="left",
        ).pack(fill="x", padx=24, pady=(10, 12))

        def _confirm() -> None:
            window.destroy()
            self._save_pending_changes()

        actions = ctk.CTkFrame(window, fg_color="transparent")
        actions.pack(fill="x", padx=20, pady=(0, 20))
        # Same packing-order-first rule this project always follows for a
        # primary action next to a secondary one.
        ctk.CTkButton(
            actions,
            text="Zatwierdź",
            width=120,
            height=34,
            corner_radius=8,
            fg_color=COLOR_ACCENT,
            hover_color=COLOR_ACCENT_HOVER,
            font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
            command=_confirm,
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
            command=window.destroy,
        ).pack(side="right", padx=(0, 8))

        _bring_window_to_front(window)

    def _save_pending_changes(self) -> None:
        if not self._has_pending_changes() or self.source_path is None:
            return
        # Captured before anything is cleared - statuses are derived from
        # the pending edits themselves (see _ai_status).
        ai_resolutions = self._ai_resolutions()
        document_changed = self._has_pending_document_changes()
        if document_changed and not self._regenerate_with_pending_edits():
            return
        resolutions_saved = self._persist_ai_resolutions(ai_resolutions)
        if not resolutions_saved and not document_changed:
            # Nothing was written at all - keep every pending decision so
            # the user can simply retry.
            return

        # Past this point the PDF (if anything in it changed) is already
        # rewritten with the staged edits, so they must leave the pending
        # state even if persisting the decisions failed - keeping them
        # would stage the very same rects a second time on the next save.
        self._clear_ai_decisions()
        self.pending_remove_keys = set()
        self.pending_add_rects = []
        self._clear_undo_redo_history()
        if document_changed:
            self._reload_visible_rects()
            self._reload_pdf_pane()
            self._patch_report_with_manual_count(len(self.edits.added))
            self.app.set_review_status(self.item, REVIEW_STATUS_NEEDS_REVIEW)
        self._update_pending_state()
        self._show_saved_confirmation()
        if not resolutions_saved and self.pen_status_label is not None:
            self.pen_status_label.configure(
                text="PDF zapisany, ale nie udało się zapisać decyzji o sugestiach AI."
            )

    def _persist_ai_resolutions(self, resolutions: dict[str, str]) -> bool:
        """Write the decided suggestions to the sidecar (what the main
        window's approval gate reads) and drop them from this review -
        rejected ones vanish, accepted ones now live on as ordinary
        AI_SUGGESTION_LABEL rects in the saved edits. True when there was
        nothing to write or the write succeeded."""
        if not resolutions:
            return True
        try:
            save_ai_suggestion_resolutions(llm_suggestions_path(self.result_path), resolutions)
        except OSError:
            if self.pen_status_label is not None:
                self.pen_status_label.configure(
                    text="Nie udało się zapisać decyzji o sugestiach AI."
                )
            return False
        remaining = [s for s in self.ai_review.suggestions if s.id not in resolutions]
        self.ai_review = self.ai_review._replace(suggestions=remaining)
        if self._ai_current_id in resolutions:
            self._ai_current_id = None
        return True

    def _clear_ai_decisions(self) -> None:
        self._ai_rejected = frozenset()
        self._ai_accepted_rects = MappingProxyType({})
        self._ai_accepted_removals = MappingProxyType({})
        self._ai_manual_id = None

    def _regenerate_with_pending_edits(self) -> bool:
        """Rebuild the output PDF with the staged rect/signature edits;
        True once the new file and its edits sidecar are in place."""
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
            word_pages, spans = self._cached_detection()
            regenerate_pdf_with_manual_overrides(
                self.source_path,
                output_path=staging_path,
                edits=new_edits,
                sensitive_terms_path=self.app.sensitive_terms_path,
                use_ner=self.app.use_ner,
                word_pages=word_pages,
                spans=spans,
                active_labels=self._original_active_labels,
                active_pages=self._original_active_pages,
                strip_signatures=self._current_strip_signatures,
            )
            os.replace(staging_path, self.result_path)
            save_manual_edits(manual_edits_path(self.result_path), new_edits)
        except (OSError, RuntimeError, ValueError):
            try:
                staging_path.unlink(missing_ok=True)
            except OSError:
                pass
            # Same reset _reload_visible_rects does on failure - a
            # detection error here could mean the cached pair is
            # unreliable, so the next attempt recomputes clean rather
            # than keep serving a result that just failed.
            self._detection_cache = None
            self._detection_cache_key = None
            if self.pen_status_label is not None:
                self.pen_status_label.configure(text="Nie udało się zapisać zmian.")
            return False

        if self._signature_choice_changed():
            try:
                update_signature_stripping_selection(
                    category_selection_path(self.result_path),
                    active_labels=self._original_active_labels,
                    active_pages=self._original_active_pages,
                    strip_signatures=self._current_strip_signatures,
                )
            except OSError:
                # Cosmetic-adjacent app state, not the anonymization
                # itself - see save_category_selection's docstring. The
                # regenerated PDF above already reflects the new choice
                # either way; only a *later* regenerate would silently
                # fall back to the stale sidecar value if this write
                # failed.
                pass
            self._original_strip_signatures = self._current_strip_signatures

        self.edits = new_edits
        return True

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


