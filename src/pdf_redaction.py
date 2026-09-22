"""True redaction helpers for text-based PDF outputs."""

from __future__ import annotations

import bisect
import re
import tempfile
import textwrap
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path

try:
    from .file_writers import (
        build_collision_safe_path,
        build_image_visual_pdf_path,
        build_original_redacted_pdf_path,
        build_pdf_visual_path,
        build_pdf_review_path,
    )
    from .sensitive_terms import SensitiveTerm
except ImportError:
    from file_writers import (
        build_collision_safe_path,
        build_image_visual_pdf_path,
        build_original_redacted_pdf_path,
        build_pdf_visual_path,
        build_pdf_review_path,
    )
    from sensitive_terms import SensitiveTerm


PDF_REDACTION_STATUS_COMPLETED = "completed"
PDF_REDACTION_STATUS_COMPLETED_WITH_WARNINGS = "completed_with_warnings"
PDF_REDACTION_STATUS_NO_MATCHES = "no_matches"
PDF_REDACTION_STATUS_SKIPPED_OCR = "skipped_ocr"
PDF_REDACTION_STATUS_UNAVAILABLE = "unavailable"
PDF_REDACTION_STATUSES = (
    PDF_REDACTION_STATUS_COMPLETED,
    PDF_REDACTION_STATUS_COMPLETED_WITH_WARNINGS,
    PDF_REDACTION_STATUS_NO_MATCHES,
    PDF_REDACTION_STATUS_SKIPPED_OCR,
    PDF_REDACTION_STATUS_UNAVAILABLE,
)
PDF_REVIEW_TYPE_REBUILT = "rebuilt_from_anonymized_text"
PDF_REVIEW_TYPE_NONE = "none"
PDF_VISUAL_TYPE_WORD_COORDINATES = "original_layout_word_coordinate_redaction"
PDF_VISUAL_REDACTION_MODE_WORD_COORDINATES = "word_coordinates"
PDF_TEXT_EXTRACTION_TEXT_LAYER = "text_layer"
PDF_TEXT_EXTRACTION_OCR_FALLBACK = "ocr_fallback"
PDF_REDACTION_COLORS = {
    "PESEL": (0.85, 0.12, 0.12),
    "TELEFON": (0.95, 0.45, 0.12),
    "PERSON_NAME_TYPO": (0.95, 0.45, 0.12),
    "EMAIL": (0.15, 0.35, 0.85),
    "NER_PERSON": (0.95, 0.45, 0.12),
    "NER_ORG": (0.50, 0.42, 0.70),
    "NER_LOCATION": (0.25, 0.55, 0.35),
    "NER_MISC": (0.50, 0.42, 0.70),
    "DATA": (0.45, 0.45, 0.45),
    "POSTAL_CODE": (0.85, 0.12, 0.12),
    "MIEJSCOWOSC": (0.25, 0.55, 0.35),
    "ULICA": (0.25, 0.55, 0.35),
    "NIP": (0.85, 0.12, 0.12),
    "REGON": (0.85, 0.12, 0.12),
    "NAZWA_FIRMY": (0.50, 0.42, 0.70),
    "DOWOD_OSOBISTY": (0.85, 0.12, 0.12),
    "IBAN": (0.85, 0.12, 0.12),
    "RECZNE": (0.08, 0.08, 0.08),
}
MANUAL_REDACTION_LABEL = "RECZNE"
_SAFE_WORD_PADDING = set(".,;:!?()[]{}<>\"'")
_UPPER_LETTERS = "A-ZĄĆĘŁŃÓŚŹŻ"
_LOWER_LETTERS = "A-Za-zĄĆĘŁŃÓŚŹŻąćęłńóśźż"
_NAME_TOKEN = rf"[{_UPPER_LETTERS}][{_LOWER_LETTERS}]{{2,}}"
_NAME_HYPHEN_CHAR_LIST = "-\u00ad\u2010\u2011\u2012\u2013\u2014"
_NAME_HYPHEN = rf"[{_NAME_HYPHEN_CHAR_LIST}]"
_NAME_HYPHEN_CHARS = frozenset(_NAME_HYPHEN_CHAR_LIST)
# Whitespace that can separate two words *within the same line* (space,
# tab) but never a newline. get_text("text")/word-coordinate extraction
# in this module joins separate PDF lines/table rows with a single "\n",
# so this is exactly the row/line boundary in this pipeline's own text.
# A plain \s here would happily match that "\n" too, letting a pattern
# built from multiple independent word tokens (a name plus its surname,
# a label plus its value) silently absorb the *next* line's unrelated
# first word - confirmed live on a table document: "Nagy-Kowalski" (a
# person's surname in one table row) matched all the way through to
# "Adres" (the *next* row's field label), redacting a word that was
# never a name at all. Kept as its own copy, in sync with
# anonymizer.py's identical _INLINE_WS: anonymizer.py already imports
# from this module (see build_pdf_redaction_metadata et al.), so this
# module importing back from anonymizer.py would be circular - see this
# file's own docstring/the surrounding duplicated pattern set below,
# which predates this constant and has the same constraint.
_INLINE_WS = r"[^\S\n]"
_SURNAME_LIKE_TOKEN = (
    rf"[{_UPPER_LETTERS}][{_LOWER_LETTERS}]{{2,}}"
    r"(?:ski|ska|cki|cka|dzki|dzka|ak|ek|ik|yk|uk|cz|icz|wicz|owicz|ewicz)"
)
# Kept in sync with anonymizer.py's identical _COMPANY_LEGAL_FORM_SUFFIX/
# _COMPANY_NAME_WORD/NAZWA_FIRMY_PATTERN (same circular-import constraint
# as the rest of this duplicated pattern set - see _INLINE_WS's own
# comment above). A Polish company's own legal-form suffix (Sp. z o.o.,
# S.A., ...) is a deterministic regex safety net alongside NER: spaCy's
# small model tagged only "z o.o." out of a real invoice's "Usługi
# Biurowe Testowski Sp. z o.o." and missed "Firma Wzorcowa S.A."
# entirely.
_COMPANY_LEGAL_FORM_SUFFIX = (
    rf"(?i:sp\.{_INLINE_WS}*z{_INLINE_WS}*o\.{_INLINE_WS}*o\."
    rf"|s\.a\."
    rf"|sp\.{_INLINE_WS}*[kj]\."
    rf"|s\.k\.a\."
    rf"|p\.s\.a\.)"
)
# Deliberately more permissive than the shared _NAME_TOKEN - see
# anonymizer.py's identical constant for why: a strict letters-only,
# 3+-char token left a leading brand token ("3M") or hyphenated compound
# ("Info-Tech") exposed right next to the [NAZWA_FIRMY] tag, which reads
# as fully redacted while it isn't. Local to this pattern only.
_COMPANY_NAME_WORD = rf"[{_UPPER_LETTERS}\d][{_LOWER_LETTERS}\d-]*"
NAZWA_FIRMY_PATTERN = re.compile(
    rf"""
    (?<!\w)
    {_COMPANY_NAME_WORD}
    (?:{_INLINE_WS}+{_COMPANY_NAME_WORD}){{0,5}}
    {_INLINE_WS}+
    {_COMPANY_LEGAL_FORM_SUFFIX}
    (?!\w)
    """,
    re.VERBOSE,
)
PERSON_NAME_TYPO_PATTERN = re.compile(
    rf"""
    (?<![\w\-\u00ad\u2010\u2011\u2012\u2013\u2014])
    {_NAME_TOKEN}
    {_INLINE_WS}*
    {_NAME_HYPHEN}
    {_INLINE_WS}*
    (?:
        {_SURNAME_LIKE_TOKEN}
        {_INLINE_WS}+
        {_NAME_TOKEN}
        |
        {_NAME_TOKEN}
        {_INLINE_WS}+
        {_SURNAME_LIKE_TOKEN}
    )
    (?![\w\-\u00ad\u2010\u2011\u2012\u2013\u2014])
    """,
    re.VERBOSE,
)


@dataclass(frozen=True)
class PdfRedactionPattern:
    """A source-text pattern that can be located in a text-based PDF."""

    label: str
    pattern: re.Pattern[str]


@dataclass(frozen=True)
class PdfRedactionSpan:
    """Detected source span in normalized PDF page text."""

    label: str
    page_number: int
    start_offset: int
    end_offset: int
    replacement_label: str
    source: str


@dataclass(frozen=True)
class PdfWord:
    """One PDF word token and its normalized text range."""

    text: str
    rect: object
    start_offset: int
    end_offset: int
    block_no: int
    line_no: int
    word_no: int


@dataclass(frozen=True)
class PdfWordPage:
    """One PDF page represented as normalized word text plus ranges."""

    page_number: int
    text: str
    words: tuple[PdfWord, ...]


PDF_REDACTION_PATTERNS: tuple[PdfRedactionPattern, ...] = (
    PdfRedactionPattern(
        "EMAIL",
        re.compile(
            r"(?<![\w.+-])[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
        ),
    ),
    PdfRedactionPattern("PESEL", re.compile(r"(?<!\w)\d{11}(?!\w)")),
    PdfRedactionPattern(
        "DOWOD_OSOBISTY",
        re.compile(r"(?<!\w)[A-Z]{3}\d{6}(?!\w)"),
    ),
    PdfRedactionPattern(
        "IBAN",
        re.compile(
            r"(?<!\w)PL\s?\d{2}(?:\s?\d{4}){6}(?!\w)",
            re.IGNORECASE,
        ),
    ),
    PdfRedactionPattern(
        "NIP",
        re.compile(
            rf"""
            (?<!\w)
            NIP
            {_INLINE_WS}*[:.-]?{_INLINE_WS}*
            \d(?:[\s-]?\d){{9}}
            (?!\w)
            """,
            re.VERBOSE | re.IGNORECASE,
        ),
    ),
    PdfRedactionPattern(
        "REGON",
        re.compile(
            rf"""
            (?<!\w)
            REGON
            {_INLINE_WS}*[:.-]?{_INLINE_WS}*
            (?:
                \d(?:[\s-]?\d){{13}}
                |
                \d(?:[\s-]?\d){{8}}
            )
            (?!\w)
            """,
            re.VERBOSE | re.IGNORECASE,
        ),
    ),
    PdfRedactionPattern(
        "NAZWA_FIRMY",
        NAZWA_FIRMY_PATTERN,
    ),
    PdfRedactionPattern(
        "TELEFON",
        re.compile(
            r"""
            (?<![\w+])
            (?:
                (?:\+48|0048)[\s-]?\d{3}[\s-]?\d{3}[\s-]?\d{3}
                |
                \d{9}
            )
            (?!\w)
            """,
            re.VERBOSE,
        ),
    ),
    PdfRedactionPattern(
        "DATA",
        re.compile(
            r"""
            (?<!\w)
            (?:
                \d{4}-(?:0[1-9]|1[0-2])-(?:0[1-9]|[12]\d|3[01])
                |
                (?:0[1-9]|[12]\d|3[01])\.(?:0[1-9]|1[0-2])\.\d{4}
                |
                (?:0[1-9]|[12]\d|3[01])-(?:0[1-9]|1[0-2])-\d{4}
                |
                (?:0[1-9]|[12]\d|3[01])/(?:0[1-9]|1[0-2])/\d{4}
                |
                (?:0?[1-9]|[12]\d|3[01])[^\S\n]+(?:stycznia|lutego|marca|kwietnia|maja|
                czerwca|lipca|sierpnia|wrze[śs]nia|pa[źz]dziernika|listopada|
                grudnia)[^\S\n]+\d{4}
            )
            (?!\w)
            """,
            re.VERBOSE | re.IGNORECASE,
        ),
    ),
    PdfRedactionPattern(
        "ULICA",
        re.compile(
            rf"""
            (?<!\w)
            (?i:ul\.?|al\.?|pl\.?|ulic[ayę]|aleja|alei|aleję|plac(?:u)?){_INLINE_WS}+
            {_NAME_TOKEN}
            (?:{_INLINE_WS}+{_NAME_TOKEN}){{0,2}}
            (?:{_INLINE_WS}+\d+[A-Za-z]?(?:/\d+)?)?
            (?!\w)
            """,
            re.VERBOSE,
        ),
    ),
    PdfRedactionPattern(
        "MIEJSCOWOSC",
        re.compile(
            rf"""
            (?<=\d{{2}}-\d{{3}}{_INLINE_WS})
            {_NAME_TOKEN}
            (?:{_NAME_HYPHEN}{_NAME_TOKEN})?
            (?:{_INLINE_WS}{_NAME_TOKEN})?
            """,
            re.VERBOSE,
        ),
    ),
    PdfRedactionPattern(
        "POSTAL_CODE",
        re.compile(r"(?<!\w)\d{2}-\d{3}(?!\w)"),
    ),
    PdfRedactionPattern(
        "PERSON_NAME_TYPO",
        PERSON_NAME_TYPO_PATTERN,
    ),
)

# Same fix, same reason, as anonymizer.py's identical fallback (this
# module can't import anonymizer.py's copy - the import direction
# already runs the other way, anonymizer.py imports from this module,
# so the reverse would be circular). The direct "NIP"/"REGON" entries
# above require the label and its digits on the same line - a common
# invoice-table layout (every field label grouped in one column/block,
# every value in another a few lines later) defeats that entirely,
# confirmed live on a real invoice fixture. _table_separated_label_value_spans
# pairs a label with the nearest not-yet-claimed value within
# _TABLE_LABEL_VALUE_MAX_LINES_AHEAD lines, in reading order - never
# touching the label text itself, since a field label is never PII.
_BARE_NIP_LABEL_PATTERN = re.compile(r"(?<!\w)NIP(?!\w)", re.IGNORECASE)
_BARE_REGON_LABEL_PATTERN = re.compile(r"(?<!\w)REGON(?!\w)", re.IGNORECASE)
_BARE_NIP_VALUE_PATTERN = re.compile(r"(?<!\w)\d(?:[\s-]?\d){9}(?!\w)")
_BARE_REGON_VALUE_PATTERN = re.compile(
    r"(?<!\w)(?:\d(?:[\s-]?\d){13}|\d(?:[\s-]?\d){8})(?!\w)"
)
# Kept small and close to the actually-observed real-world gap (2
# lines) rather than generous - see anonymizer.py's identical constant
# for the full reasoning (a wider window risks mispairing an unrelated
# same-length number instead of the real value).
_TABLE_LABEL_VALUE_MAX_LINES_AHEAD = 4


def _line_start_offsets(text: str) -> list[int]:
    """0-based offset each line starts at, for bisect-based line-number
    lookups - shared across both the NIP and REGON calls in the same
    page text by callers that need more than one, instead of each call
    re-scanning the same text for newlines independently."""
    line_starts = [0]
    line_starts.extend(m.end() for m in re.finditer(r"\n", text))
    return line_starts


def _table_separated_label_value_spans(
    text: str,
    label_pattern: re.Pattern[str],
    value_pattern: re.Pattern[str],
    line_starts: list[int],
) -> list[tuple[int, int]]:
    """Pair each bare ``label_pattern`` match with the nearest, not yet
    claimed ``value_pattern`` match that starts after it, within
    ``_TABLE_LABEL_VALUE_MAX_LINES_AHEAD`` lines - in reading order, so
    a block of N labels pairs with the next N values in the same
    relative order they were written in. Returns only the *value*
    spans; the caller never touches the label text. ``line_starts``
    (see _line_start_offsets) is precomputed by the caller so pairing
    NIP and REGON in the same page text doesn't rescan it for newlines
    twice."""
    label_starts = [m.start() for m in label_pattern.finditer(text)]
    if not label_starts:
        return []
    value_positions = [(m.start(), m.end()) for m in value_pattern.finditer(text)]
    if not value_positions:
        return []

    def line_number(offset: int) -> int:
        return bisect.bisect_right(line_starts, offset) - 1

    claimed: set[int] = set()
    spans: list[tuple[int, int]] = []
    search_from = 0
    for label_start in label_starts:
        label_line = line_number(label_start)
        while search_from < len(value_positions) and (
            value_positions[search_from][0] < label_start
            or search_from in claimed
        ):
            search_from += 1
        for index in range(search_from, len(value_positions)):
            if index in claimed:
                continue
            value_start, value_end = value_positions[index]
            if line_number(value_start) - label_line > _TABLE_LABEL_VALUE_MAX_LINES_AHEAD:
                break
            claimed.add(index)
            spans.append((value_start, value_end))
            break
    return spans


def _table_separated_nip_regon_matches(
    page_text: str, active_labels: frozenset[str] | None
) -> list[tuple[str, int, int]]:
    """Return ``(label, start, end)`` spans for the table-separated
    NIP/REGON fallback."""
    results: list[tuple[str, int, int]] = []
    line_starts = _line_start_offsets(page_text)
    for label_name, label_pattern, value_pattern in (
        ("NIP", _BARE_NIP_LABEL_PATTERN, _BARE_NIP_VALUE_PATTERN),
        ("REGON", _BARE_REGON_LABEL_PATTERN, _BARE_REGON_VALUE_PATTERN),
    ):
        if active_labels is not None and label_name not in active_labels:
            continue
        for start, end in _table_separated_label_value_spans(
            page_text, label_pattern, value_pattern, line_starts
        ):
            results.append((label_name, start, end))
    return results


def build_pdf_redaction_metadata(
    *,
    status: str,
    output_path: str | Path | None = None,
    redaction_count: int = 0,
    counters: dict[str, int] | None = None,
) -> dict[str, object]:
    """Return safe PDF redaction metadata for reports and summaries."""
    if status not in PDF_REDACTION_STATUSES:
        status = PDF_REDACTION_STATUS_UNAVAILABLE
    return {
        "used": status in (
            PDF_REDACTION_STATUS_COMPLETED,
            PDF_REDACTION_STATUS_COMPLETED_WITH_WARNINGS,
            PDF_REDACTION_STATUS_NO_MATCHES,
        ),
        "status": status,
        "output_name": Path(output_path).name if output_path is not None else "",
        "redaction_count": redaction_count,
        "counters": counters or {},
        "true_redaction": status in (
            PDF_REDACTION_STATUS_COMPLETED,
            PDF_REDACTION_STATUS_COMPLETED_WITH_WARNINGS,
        ),
        "review_pdf_created": False,
        "review_pdf_name": "",
        "review_pdf_type": PDF_REVIEW_TYPE_NONE,
        "text_extraction": "",
        "visual_pdf_created": False,
        "visual_pdf_name": "",
        "visual_pdf_type": "none",
        "visual_redaction_mode": "",
        "unmapped_categories": {},
        "original_layout_redaction_used": status in (
            PDF_REDACTION_STATUS_COMPLETED,
            PDF_REDACTION_STATUS_COMPLETED_WITH_WARNINGS,
            PDF_REDACTION_STATUS_NO_MATCHES,
        ),
        "original_layout_redaction_experimental": False,
        "applied_rects": [],
    }


def build_pdf_redaction_skipped_ocr_metadata() -> dict[str, object]:
    """Return metadata for PDF inputs handled through OCR text fallback."""
    return build_pdf_redaction_metadata(status=PDF_REDACTION_STATUS_SKIPPED_OCR)


def build_pdf_review_metadata(
    *,
    output_path: str | Path,
    text_extraction: str,
) -> dict[str, object]:
    """Return safe metadata for a rebuilt PDF review artifact."""
    return {
        "used": True,
        "status": PDF_REDACTION_STATUS_COMPLETED,
        "output_name": Path(output_path).name,
        "redaction_count": 0,
        "counters": {},
        "true_redaction": False,
        "review_pdf_created": True,
        "review_pdf_name": Path(output_path).name,
        "review_pdf_type": PDF_REVIEW_TYPE_REBUILT,
        "text_extraction": text_extraction,
        "visual_pdf_created": False,
        "visual_pdf_name": "",
        "visual_pdf_type": "none",
        "visual_redaction_mode": "",
        "unmapped_categories": {},
        "original_layout_redaction_used": False,
        "original_layout_redaction_experimental": False,
    }


def manual_edit_span_key(
    page_number: int, label: str, rect: object
) -> tuple[int, str, float, float, float, float]:
    """Return a stable identity for one applied redaction rectangle.

    Deterministic for a given source file and detection settings, so a
    manually removed (undone) automatic redaction can be recognised again
    the next time the same source is re-scanned and skipped.
    """
    return (
        int(page_number),
        str(label),
        round(rect.x0, 2),
        round(rect.y0, 2),
        round(rect.x1, 2),
        round(rect.y1, 2),
    )


def build_pdf_visual_redaction_metadata(
    *,
    output_path: str | Path,
    redaction_count: int,
    counters: dict[str, int],
    unmapped_categories: dict[str, int],
    applied_rects: Sequence[dict[str, object]] = (),
) -> dict[str, object]:
    """Return safe metadata for word-coordinate visual PDF redaction."""
    status = (
        PDF_REDACTION_STATUS_COMPLETED_WITH_WARNINGS
        if unmapped_categories
        else PDF_REDACTION_STATUS_COMPLETED
    )
    if not counters and not unmapped_categories:
        status = PDF_REDACTION_STATUS_NO_MATCHES
    metadata = build_pdf_redaction_metadata(
        status=status,
        output_path=output_path,
        redaction_count=redaction_count,
        counters=counters,
    )
    metadata["true_redaction"] = bool(redaction_count)
    metadata["visual_pdf_created"] = True
    metadata["visual_pdf_name"] = Path(output_path).name
    metadata["visual_pdf_type"] = PDF_VISUAL_TYPE_WORD_COORDINATES
    metadata["visual_redaction_mode"] = PDF_VISUAL_REDACTION_MODE_WORD_COORDINATES
    metadata["unmapped_categories"] = unmapped_categories
    metadata["original_layout_redaction_used"] = True
    metadata["original_layout_redaction_experimental"] = False
    metadata["text_extraction"] = PDF_TEXT_EXTRACTION_TEXT_LAYER
    metadata["applied_rects"] = list(applied_rects)
    if unmapped_categories:
        metadata["warning"] = (
            "Some detected PDF spans could not be mapped to full word rectangles"
        )
    return metadata


def _load_fitz_module():
    try:
        import pymupdf as fitz
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "PDF redaction output requires PyMuPDF. "
            "Install dependencies from requirements.txt."
        ) from exc
    return fitz


def pdf_page_count(source_path: str | Path) -> int | None:
    """Return a PDF's real page count, or ``None`` if it can't be read
    (missing PyMuPDF, a corrupt/non-PDF file, ...) - never raises.

    Deliberately just opens the file and reads ``.page_count`` - no word/
    text extraction (see ``extract_pdf_word_pages`` for that) - so this
    is cheap enough to call synchronously for every PDF the GUI's file
    list gains, right at drag-and-drop time, to know each file's real
    page count before the user ever types a page range for it."""
    try:
        fitz = _load_fitz_module()
    except RuntimeError:
        return None
    try:
        with fitz.open(source_path) as document:
            return document.page_count
    except Exception:  # noqa: BLE001 - a bad/corrupt file must never crash the GUI
        return None


def pdf_has_signature_widget(
    source_path: str | Path,
    *,
    active_pages: frozenset[int] | None = None,
) -> bool:
    """Return whether a PDF has at least one *in-scope* AcroForm signature
    field (the same ``PDF_WIDGET_TYPE_SIGNATURE`` scope, and the same
    ``active_pages``/``_page_in_scope`` filtering, ``_strip_signature_widgets``
    actually removes) - never raises, ``False`` on any failure (missing
    PyMuPDF, a corrupt/non-PDF file, ...).

    Used to only show the magic-pen signature-removal toggle for
    documents that actually have a signature field the removal step
    would touch. Without the same ``active_pages`` filtering
    ``_strip_signature_widgets`` applies, a document whose Etap 5 page
    range excludes the only page carrying a signature would still show
    the toggle - and flipping it would silently do nothing, exactly the
    no-op this gate exists to prevent."""
    try:
        fitz = _load_fitz_module()
    except RuntimeError:
        return False
    try:
        with fitz.open(source_path) as document:
            if not document.is_form_pdf:
                return False
            for page_number, page in enumerate(document, start=1):
                if not _page_in_scope(page_number, active_pages):
                    continue
                for widget in page.widgets() or []:
                    if widget.field_type == fitz.PDF_WIDGET_TYPE_SIGNATURE:
                        return True
            return False
    except Exception:  # noqa: BLE001 - a bad/corrupt file must never crash the GUI
        return False


def _build_word_page(
    fitz,
    page_number: int,
    normalized_words: Sequence[
        tuple[str, tuple[float, float, float, float], int, int, int]
    ],
) -> PdfWordPage:
    """Shared text/offset reconstruction for extract_pdf_word_pages and
    word_pages_from_ocr_boxes - the exact same line-break-between-PDF-
    lines convention either way, regardless of whether the words came
    from the PDF's real text layer or from OCR.

    Keeps a line break between source lines instead of flattening the
    whole page into one run-on line: a single joined line loses the
    sentence/line context NER needs and can make a short standalone
    label word (for example "PESEL" or "Data") look like part of a
    longer proper-noun phrase to the NER model.
    """
    text_parts: list[str] = []
    words: list[PdfWord] = []
    offset = 0
    previous_block_line: tuple[int, int] | None = None
    for token, rect, block_no, line_no, word_no in normalized_words:
        if not token:
            continue
        current_block_line = (block_no, line_no)
        if text_parts:
            separator = "\n" if current_block_line != previous_block_line else " "
            text_parts.append(separator)
            offset += 1
        start = offset
        text_parts.append(token)
        offset += len(token)
        words.append(
            PdfWord(
                text=token,
                rect=fitz.Rect(rect),
                start_offset=start,
                end_offset=offset,
                block_no=block_no,
                line_no=line_no,
                word_no=word_no,
            )
        )
        previous_block_line = current_block_line
    return PdfWordPage(
        page_number=page_number, text="".join(text_parts), words=tuple(words)
    )


def extract_pdf_word_pages(source_path: str | Path) -> list[PdfWordPage]:
    """Extract normalized per-page text with word coordinate ranges."""
    fitz = _load_fitz_module()
    pages: list[PdfWordPage] = []
    with fitz.open(source_path) as document:
        for page_index, page in enumerate(document, start=1):
            raw_words = page.get_text("words") or []
            sorted_words = sorted(
                raw_words,
                key=lambda item: (int(item[5]), int(item[6]), int(item[7])),
            )
            normalized = [
                (str(word[4]), tuple(word[:4]), int(word[5]), int(word[6]), int(word[7]))
                for word in sorted_words
            ]
            pages.append(_build_word_page(fitz, page_index, normalized))
    return pages


def word_pages_from_ocr_boxes(
    ocr_pages: Sequence[dict[str, object]],
) -> list[PdfWordPage]:
    """Convert ocr.extract_pdf_word_boxes/extract_image_word_boxes's raw
    per-page word-box data into the same PdfWord/PdfWordPage shape
    extract_pdf_word_pages produces from a real PDF text layer - so
    every existing word-coordinate function (compute_redaction_rects,
    save_word_coordinate_redacted_pdf_copy, ...) works identically
    whether the words came from a real PDF text layer or from OCR. This
    is the piece that lets a scanned page get the same true colored
    redaction boxes a text-layer PDF already gets, instead of only ever
    falling back to a rebuilt plain-text document.
    """
    fitz = _load_fitz_module()
    pages: list[PdfWordPage] = []
    for ocr_page in ocr_pages:
        raw_words = sorted(
            ocr_page.get("words", []),
            key=lambda word: (
                int(word["block_no"]),
                int(word["line_no"]),
                int(word["word_no"]),
            ),
        )
        normalized = [
            (
                str(word["text"]),
                tuple(word["rect"]),
                int(word["block_no"]),
                int(word["line_no"]),
                int(word["word_no"]),
            )
            for word in raw_words
        ]
        pages.append(
            _build_word_page(fitz, int(ocr_page["page_number"]), normalized)
        )
    return pages


def _coerce_review_pages(
    anonymized_text: str,
    page_texts: Sequence[str] | None,
) -> list[str]:
    if page_texts:
        return [str(page_text) for page_text in page_texts] or [anonymized_text]
    return [anonymized_text]


def _add_wrapped_review_text_page(fitz, document, page_number: int, text: str) -> None:
    page = document.new_page(width=595, height=842)
    margin = 54
    y = 54
    font_size = 11
    line_height = 15
    max_chars = 88
    page.insert_text(
        (margin, y),
        f"Source page {page_number}",
        fontsize=12,
        fontname="helv",
    )
    y += 26

    for source_line in str(text).splitlines() or [""]:
        wrapped_lines = textwrap.wrap(
            source_line,
            width=max_chars,
            replace_whitespace=False,
            drop_whitespace=False,
        ) or [""]
        for line in wrapped_lines:
            if y > 790:
                page = document.new_page(width=595, height=842)
                y = 54
                page.insert_text(
                    (margin, y),
                    f"Source page {page_number} (continued)",
                    fontsize=12,
                    fontname="helv",
                )
                y += 26
            page.insert_text((margin, y), line, fontsize=font_size, fontname="helv")
            y += line_height


def save_rebuilt_review_pdf_from_text(
    source_path: str | Path,
    anonymized_text: str,
    *,
    page_texts: Sequence[str] | None = None,
    output_dir: str | Path | None = None,
    output_path: str | Path | None = None,
    text_extraction: str = PDF_TEXT_EXTRACTION_TEXT_LAYER,
) -> dict[str, object]:
    """Create a readable PDF review artifact from anonymized text only.

    ``output_path`` writes that exact path instead of picking an
    independent collision-safe name - used so every companion file of one
    run shares one number (see build_shared_collision_suffix)."""
    if not isinstance(anonymized_text, str):
        raise TypeError("anonymized_text must be a string")

    fitz = _load_fitz_module()
    source = Path(source_path)
    if output_path is not None:
        output_path = Path(output_path)
    else:
        output_path = build_collision_safe_path(
            build_pdf_review_path(source, output_dir=output_dir)
        )
    pages = _coerce_review_pages(anonymized_text, page_texts)

    document = fitz.open()
    try:
        for page_number, page_text in enumerate(pages, start=1):
            _add_wrapped_review_text_page(fitz, document, page_number, page_text)
        document.save(output_path, garbage=4, deflate=True, clean=True)
    finally:
        document.close()

    return build_pdf_review_metadata(
        output_path=output_path,
        text_extraction=text_extraction,
    )


def _search_page_for_text(page, text: str):
    flags = 0
    try:
        import pymupdf as fitz

        flags = getattr(fitz, "TEXT_DEHYPHENATE", 0)
    except ModuleNotFoundError:
        flags = 0
    return page.search_for(text, quads=False, flags=flags)


def _add_redaction(page, rect, label: str) -> None:
    fill = PDF_REDACTION_COLORS.get(label, (0.45, 0.45, 0.45))
    page.add_redact_annot(rect, fill=fill)


def _merge_rects_by_line(words: Sequence[PdfWord]):
    if not words:
        return []

    grouped: list[list[PdfWord]] = []
    for word in words:
        if (
            grouped
            and grouped[-1][-1].block_no == word.block_no
            and grouped[-1][-1].line_no == word.line_no
        ):
            grouped[-1].append(word)
        else:
            grouped.append([word])

    rects = []
    for group in grouped:
        rect = group[0].rect
        for word in group[1:]:
            rect = rect | word.rect
        rects.append(rect)
    return rects


def _padding_is_safe(text: str, *, hyphen_at_start: bool) -> bool:
    """``hyphen_at_start`` says where a hyphen would sit if this padding
    is the other half of a hyphenated compound word split by the
    detector's own span boundary: ``True`` for padding trailing *after*
    the span (e.g. "-Wojciechowski"), ``False`` for padding leading *up
    to* the span (e.g. "Zaremba-").
    """
    if all(character.isspace() or character in _SAFE_WORD_PADDING for character in text):
        return True
    # A detected span landing exactly at a hyphen inside a hyphenated
    # compound word ("Zaremba-Wojciechowski", detected by NER as just
    # "Zaremba") is still one real match that must be redacted in full -
    # confirmed live: spaCy's own span boundary lands right on the
    # hyphen (a genuine sub-word split its own tokenizer makes), and
    # without this the check above used to reject the whole span
    # outright, leaving the *entire* name completely unredacted rather
    # than at least widened to the full word - worse than a plain miss,
    # since a real, detected PII entity ended up with zero protection.
    # Deliberately narrow (hyphen immediately at the span boundary, only
    # letters/more hyphens/safe punctuation beyond it) rather than "any
    # letters are safe padding" - that broader rule would risk widening
    # into a genuinely unrelated word that just happens to start with
    # the same few letters as the detected entity, with no hyphen
    # indicating they're one compound.
    #
    # The remainder allows more hyphen-like characters (not just plain
    # letters) - code review caught the first version of this fix
    # requiring remainder.isalpha(), which still rejected the whole span
    # for a 3+-part hyphenated name when NER only tagged one end segment
    # (e.g. "Anna" out of "Anna-Maria-Zaremba" leaves a remainder of
    # "Maria-Zaremba", which itself contains a hyphen) - reproducing the
    # exact zero-protection bug this fix exists to close, just one
    # hyphen further along. Safe punctuation/whitespace is also allowed
    # in the remainder for the same reason (a trailing comma glued
    # directly onto the word with no space, e.g. "-Wojciechowski,").
    if len(text) < 2:
        return False
    hyphen_char = text[0] if hyphen_at_start else text[-1]
    remainder = text[1:] if hyphen_at_start else text[:-1]
    if hyphen_char not in _NAME_HYPHEN_CHARS:
        return False
    return all(
        character.isalpha()
        or character in _NAME_HYPHEN_CHARS
        or character.isspace()
        or character in _SAFE_WORD_PADDING
        for character in remainder
    )


def _span_maps_to_full_words(page: PdfWordPage, span: PdfRedactionSpan) -> list:
    if span.start_offset >= span.end_offset:
        return []

    matching_words = [
        word
        for word in page.words
        if word.end_offset > span.start_offset and word.start_offset < span.end_offset
    ]
    if not matching_words:
        return []

    first = matching_words[0]
    last = matching_words[-1]
    if span.start_offset > first.start_offset:
        left_padding = page.text[first.start_offset:span.start_offset]
        if not _padding_is_safe(left_padding, hyphen_at_start=False):
            return []
    if span.end_offset < last.end_offset:
        right_padding = page.text[span.end_offset:last.end_offset]
        if not _padding_is_safe(right_padding, hyphen_at_start=True):
            return []

    for word in matching_words[1:-1]:
        if word.start_offset < span.start_offset or word.end_offset > span.end_offset:
            return []
    return _merge_rects_by_line(matching_words)


def _span_page_lookup(word_pages: Sequence[PdfWordPage]) -> dict[int, PdfWordPage]:
    return {page.page_number: page for page in word_pages}


def compute_redaction_rects(
    word_pages: Sequence[PdfWordPage],
    spans: Iterable[PdfRedactionSpan],
    *,
    removed_span_keys: object = frozenset(),
) -> tuple[list[dict[str, object]], dict[str, int], dict[str, int]]:
    """Resolve spans to concrete redaction rectangles without touching a file.

    Returns ``(applied_rects, counters, unmapped_categories)``. ``rects`` in
    ``removed_span_keys`` (as produced by :func:`manual_edit_span_key`) are
    excluded, letting a caller compute exactly what is currently visible on a
    true-redacted PDF -- including any manual "un-redact" overrides -- for
    hit-testing in a preview, without regenerating the file itself.
    """
    pages_by_number = _span_page_lookup(word_pages)
    counters: dict[str, int] = {}
    unmapped: dict[str, int] = {}
    seen: set[tuple[int, str, float, float, float, float]] = set()
    applied_rects: list[dict[str, object]] = []
    removed_keys = set(removed_span_keys)

    for span in spans:
        page_words = pages_by_number.get(span.page_number)
        if page_words is None:
            unmapped[span.label] = unmapped.get(span.label, 0) + 1
            continue
        rects = _span_maps_to_full_words(page_words, span)
        if not rects:
            unmapped[span.label] = unmapped.get(span.label, 0) + 1
            continue
        mapped_any = False
        all_removed_by_user = True
        for rect in rects:
            key = manual_edit_span_key(span.page_number, span.label, rect)
            if key in removed_keys:
                continue
            all_removed_by_user = False
            if key in seen:
                continue
            seen.add(key)
            applied_rects.append(
                {
                    "page": span.page_number,
                    "label": span.label,
                    "x0": round(rect.x0, 2),
                    "y0": round(rect.y0, 2),
                    "x1": round(rect.x1, 2),
                    "y1": round(rect.y1, 2),
                }
            )
            mapped_any = True
        if mapped_any:
            counters[span.label] = counters.get(span.label, 0) + 1
        elif not all_removed_by_user:
            unmapped[span.label] = unmapped.get(span.label, 0) + 1

    return applied_rects, counters, unmapped


def _page_in_scope(page_number: int, active_pages: frozenset[int] | None) -> bool:
    return active_pages is None or page_number in active_pages


def _strip_signature_widgets(
    fitz_module,
    document,
    *,
    active_pages: frozenset[int] | None = None,
    strip_signatures: bool = False,
) -> int:
    """Remove every AcroForm signature field (Etap 7 - a real case showed
    a digitally-signed PDF's visual "Podpisano elektronicznie przez: ..."
    box routinely names the signer, and this app's regex/NER detection
    never sees it: it lives in a form-field appearance stream, not the
    page's own text content. Deleting the widget removes its appearance
    (the visible box, whatever it renders - text, a scanned handwritten
    signature image, or both) and its value together, in one PyMuPDF
    call - no new dependency needed beyond PyMuPDF, already bundled for
    every other PDF operation in this module.

    ``strip_signatures`` defaults to ``False`` and the whole function is
    a no-op unless it is explicitly ``True`` - the user's own decision
    (2026-09-18: "usuwanie podpisu to osobna opcja - nie dziala
    automatycznie") is enforced here, inside the shared helper, rather
    than at each call site - a future third writer of a full document
    copy (see the paragraph below) then cannot forget the off-by-default
    guard by only remembering to add the call but not the gate.

    Every function in this module that writes out a full copy of the
    source document (not a synthetic from-scratch one, like the review
    PDF's blank canvas) must call this - it is not wired in centrally
    because the two current callers don't share a document-opening
    helper to hook into; a third such writer needs its own call here.

    Scope: only real AcroForm signature widgets (``field_type ==
    PDF_WIDGET_TYPE_SIGNATURE``). A signature-like image pasted onto a
    page as ordinary content (not a form field) is indistinguishable
    from any other picture without content analysis this app doesn't
    attempt - a known, documented limitation, not silently promised
    coverage.

    ``active_pages`` (Etap 5) is honored the same way every other PDF
    redaction path honors it: a page outside the chosen range is left
    completely untouched, signature fields included.

    Deliberately re-queries ``page.widgets(...)`` fresh after every
    single deletion rather than deleting from one materialized list -
    a real crash a synthetic co-signed (two widgets, one page) test
    fixture caught: PyMuPDF's own ``delete_widget`` walks the deleted
    widget's ``.next`` link to relink the remaining chain, and for a
    document opened from a file path (exactly how every caller in this
    codebase opens one - never from an in-memory stream) a second
    ``Widget`` object fetched before the first deletion had already
    gone stale by the time its own deletion ran, raising
    ``FzErrorArgument: annotation not bound to any page``. Re-fetching
    every iteration costs one extra page scan per widget removed - on
    real documents, always a small, bounded number - and is the only
    variant proven safe against a real multi-signer page."""
    if not strip_signatures or not document.is_form_pdf:
        return 0
    removed = 0
    for page_number, page in enumerate(document, start=1):
        if not _page_in_scope(page_number, active_pages):
            continue
        while True:
            target = next(
                (
                    widget
                    for widget in (page.widgets() or ())
                    if widget.field_type == fitz_module.PDF_WIDGET_TYPE_SIGNATURE
                ),
                None,
            )
            if target is None:
                break
            page.delete_widget(target)
            removed += 1
    return removed


def save_word_coordinate_redacted_pdf_copy(
    source_path: str | Path,
    *,
    word_pages: Sequence[PdfWordPage],
    spans: Iterable[PdfRedactionSpan],
    output_dir: str | Path | None = None,
    output_path: str | Path | None = None,
    removed_span_keys: object = frozenset(),
    extra_redaction_rects: Iterable[tuple[int, object]] = (),
    active_pages: frozenset[int] | None = None,
    strip_signatures: bool = False,
) -> dict[str, object]:
    """Create an original-layout true-redacted PDF from word-coordinate spans.

    ``removed_span_keys`` (as produced by :func:`manual_edit_span_key`) lets a
    caller exclude specific auto-detected rectangles that a user manually
    un-redacted; ``extra_redaction_rects`` (an iterable of
    ``(page_number, rect)`` pairs, in PDF point coordinates) lets a caller add
    manually drawn redaction rectangles that were not detected automatically.
    Both are optional and default to a no-op, so existing callers behave
    exactly as before. When ``output_path`` is given, that exact path is
    (over)written instead of picking a fresh collision-safe name — used to
    regenerate an existing visual PDF in place after manual edits.
    ``strip_signatures`` (Etap 7) is ``False`` by default - a deliberate
    per-task opt-in, not automatic - and ``active_pages`` (Etap 5)
    additionally scopes it when it is on - see
    ``_strip_signature_widgets``.
    """
    fitz = _load_fitz_module()
    source = Path(source_path)
    if output_path is not None:
        resolved_output_path = Path(output_path)
    else:
        resolved_output_path = build_collision_safe_path(
            build_pdf_visual_path(source, output_dir=output_dir)
        )
    applied_rects, counters, unmapped = compute_redaction_rects(
        word_pages, spans, removed_span_keys=removed_span_keys
    )
    seen = {
        (rect["page"], rect["label"], rect["x0"], rect["y0"], rect["x1"], rect["y1"])
        for rect in applied_rects
    }

    with fitz.open(source) as document:
        signature_fields_removed = _strip_signature_widgets(
            fitz,
            document,
            active_pages=active_pages,
            strip_signatures=strip_signatures,
        )
        for rect_info in applied_rects:
            page = document[int(rect_info["page"]) - 1]
            rect = fitz.Rect(
                rect_info["x0"], rect_info["y0"], rect_info["x1"], rect_info["y1"]
            )
            _add_redaction(page, rect, str(rect_info["label"]))

        for page_number, raw_rect in extra_redaction_rects:
            if page_number < 1 or page_number > len(document):
                continue
            rect = raw_rect if isinstance(raw_rect, fitz.Rect) else fitz.Rect(raw_rect)
            key = manual_edit_span_key(page_number, MANUAL_REDACTION_LABEL, rect)
            if key in seen:
                continue
            seen.add(key)
            page = document[page_number - 1]
            _add_redaction(page, rect, MANUAL_REDACTION_LABEL)
            applied_rects.append(
                {
                    "page": page_number,
                    "label": MANUAL_REDACTION_LABEL,
                    "x0": round(rect.x0, 2),
                    "y0": round(rect.y0, 2),
                    "x1": round(rect.x1, 2),
                    "y1": round(rect.y1, 2),
                }
            )
            counters[MANUAL_REDACTION_LABEL] = counters.get(MANUAL_REDACTION_LABEL, 0) + 1

        for page in document:
            page.apply_redactions()
        document.save(resolved_output_path, garbage=4, deflate=True, clean=True)

    metadata = build_pdf_visual_redaction_metadata(
        output_path=resolved_output_path,
        redaction_count=len(applied_rects),
        counters=counters,
        unmapped_categories=unmapped,
        applied_rects=applied_rects,
    )
    metadata["signature_fields_removed"] = signature_fields_removed
    return metadata


def save_word_coordinate_redacted_image_copy(
    source_path: str | Path,
    *,
    word_pages: Sequence[PdfWordPage],
    spans: Iterable[PdfRedactionSpan],
    output_dir: str | Path | None = None,
    output_path: str | Path | None = None,
    removed_span_keys: object = frozenset(),
    extra_redaction_rects: Iterable[tuple[int, object]] = (),
) -> dict[str, object]:
    """Create a true-redacted, colored visual PDF for a standalone
    scanned image - the image-source counterpart to
    save_word_coordinate_redacted_pdf_copy, reusing it entirely rather
    than reimplementing redaction.

    Wraps the source image in a synthetic one-page PDF sized at the
    image's own pixel dimensions (so 1 pixel == 1 PDF point, matching
    how ocr.extract_image_word_boxes already measured its OCR word boxes
    with zoom=1.0 - no extra scaling needed anywhere in between), then
    calls the exact same word-coordinate redaction function a scanned
    PDF page already uses - including PyMuPDF's redaction blanking out
    the *image* pixels under a redaction rect (images=2, its own
    default), not just text, which is what actually makes this work for
    a page that is nothing but a picture. The synthetic PDF is a
    temporary implementation detail, cleaned up regardless of outcome -
    only the real output (or, on failure, nothing) is left behind.
    """
    fitz = _load_fitz_module()
    source = Path(source_path)
    if output_path is not None:
        resolved_output_path = Path(output_path)
    else:
        resolved_output_path = build_collision_safe_path(
            build_image_visual_pdf_path(source, output_dir=output_dir)
        )

    probe_pixmap = fitz.Pixmap(str(source))
    width, height = probe_pixmap.width, probe_pixmap.height
    probe_pixmap = None  # release before insert_image reopens the same file

    with tempfile.TemporaryDirectory() as staging_dir:
        synthetic_path = Path(staging_dir) / "synthetic_source.pdf"
        with fitz.open() as synthetic_document:
            page = synthetic_document.new_page(width=width, height=height)
            page.insert_image(fitz.Rect(0, 0, width, height), filename=str(source))
            synthetic_document.save(synthetic_path)

        return save_word_coordinate_redacted_pdf_copy(
            synthetic_path,
            word_pages=word_pages,
            spans=spans,
            output_path=resolved_output_path,
            removed_span_keys=removed_span_keys,
            extra_redaction_rects=extra_redaction_rects,
        )


def _redact_pattern_matches(
    page, page_text: str, *, active_labels: frozenset[str] | None = None
) -> dict[str, int]:
    counters: dict[str, int] = {}
    seen_locations: set[tuple[str, float, float, float, float]] = set()
    # Tracks each match's *offset range* in page_text once it has
    # actually redacted something, so a later, looser pattern (TELEFON's
    # bare "\d{9}" fallback) can't also claim the same digits under a
    # second label, and the table-separated NIP/REGON fallback below
    # can't re-claim a value its own direct, same-line pattern already
    # consumed as part of a wider "NIP: 123..." match - this function
    # has no other general cross-label "already redacted this range"
    # tracking the way the word-coordinate path's occupied_ranges does.
    claimed_ranges: list[tuple[int, int]] = []

    def _redact_offset_match(label: str, start: int, end: int, matched_text: str) -> None:
        if any(start < c_end and c_start < end for c_start, c_end in claimed_ranges):
            return
        redacted_here = False
        for rect in _search_page_for_text(page, matched_text):
            key = (
                label,
                round(rect.x0, 2),
                round(rect.y0, 2),
                round(rect.x1, 2),
                round(rect.y1, 2),
            )
            if key in seen_locations:
                continue
            seen_locations.add(key)
            _add_redaction(page, rect, label)
            counters[label] = counters.get(label, 0) + 1
            redacted_here = True
        if redacted_here:
            claimed_ranges.append((start, end))

    for item in PDF_REDACTION_PATTERNS:
        if active_labels is None or item.label in active_labels:
            for match in item.pattern.finditer(page_text):
                _redact_offset_match(
                    item.label, match.start(), match.end(), match.group(0)
                )
        # Right after REGON's own direct (same-line) pattern above, and
        # before TELEFON's turn a few iterations later in this same
        # loop - see _apply_dictionary_and_regex's identical ordering
        # note in anonymizer.py. Deliberately a plain `if`, not
        # `continue`d away above when REGON itself is excluded - see
        # that same note for the real bug that caused.
        if item.label == "REGON" and (
            active_labels is None
            or "NIP" in active_labels
            or "REGON" in active_labels
        ):
            for label, start, end in _table_separated_nip_regon_matches(
                page_text, active_labels
            ):
                _redact_offset_match(label, start, end, page_text[start:end])
    return counters


def _redact_dictionary_matches(
    page,
    sensitive_terms: Iterable[SensitiveTerm] | None,
) -> dict[str, int]:
    if sensitive_terms is None:
        return {}

    counters: dict[str, int] = {}
    seen_locations: set[tuple[str, float, float, float, float]] = set()
    for term in sorted(sensitive_terms, key=lambda item: len(item.term), reverse=True):
        for rect in _search_page_for_text(page, term.term):
            key = (
                term.label,
                round(rect.x0, 2),
                round(rect.y0, 2),
                round(rect.x1, 2),
                round(rect.y1, 2),
            )
            if key in seen_locations:
                continue
            seen_locations.add(key)
            _add_redaction(page, rect, term.label)
            counters[term.label] = counters.get(term.label, 0) + 1
    return counters


def _redact_exact_text_matches(
    page,
    redaction_terms: Iterable[tuple[str, str]] | None,
) -> dict[str, int]:
    if redaction_terms is None:
        return {}

    counters: dict[str, int] = {}
    seen_locations: set[tuple[str, float, float, float, float]] = set()
    terms: list[tuple[str, str]] = []
    seen_terms: set[tuple[str, str]] = set()
    for label, text in redaction_terms:
        normalized = (str(label).strip(), str(text).strip())
        if not normalized[0] or not normalized[1] or normalized in seen_terms:
            continue
        seen_terms.add(normalized)
        terms.append(normalized)
    for label, text in sorted(terms, key=lambda item: len(item[1]), reverse=True):
        for rect in _search_page_for_text(page, text):
            key = (
                label,
                round(rect.x0, 2),
                round(rect.y0, 2),
                round(rect.x1, 2),
                round(rect.y1, 2),
            )
            if key in seen_locations:
                continue
            seen_locations.add(key)
            _add_redaction(page, rect, label)
            counters[label] = counters.get(label, 0) + 1
    return counters


def _merge_counters(target: dict[str, int], source: dict[str, int]) -> None:
    for label, count in source.items():
        target[label] = target.get(label, 0) + count


def save_redacted_pdf_copy(
    source_path: str | Path,
    *,
    sensitive_terms: Iterable[SensitiveTerm] | None = None,
    extra_redaction_terms: Iterable[tuple[str, str]] | None = None,
    output_dir: str | Path | None = None,
    output_path: str | Path | None = None,
    active_labels: frozenset[str] | None = None,
    active_pages: frozenset[int] | None = None,
    strip_signatures: bool = False,
) -> dict[str, object]:
    """Create a true-redacted PDF copy and return safe metadata.

    ``output_path`` writes that exact path instead of picking an
    independent collision-safe name - used so every companion file of one
    run shares one number (see build_shared_collision_suffix).
    ``active_labels`` (Etap 4 category selection) restricts which regex
    patterns get redacted here - the dictionary pass and
    ``extra_redaction_terms`` (already filtered by the caller, if at
    all) are unaffected, matching every other redaction path's rule that
    the user's own dictionary is always-on. ``active_pages`` (Etap 5)
    skips an out-of-scope page entirely, dictionary included - a real
    gap code review caught: this "experimental original-layout
    redaction" output mode is a separate code path from the default
    visual-redaction one and was burning PII out of every page
    regardless of the user's chosen page range. ``strip_signatures``
    (Etap 7) is ``False`` by default - a deliberate per-task opt-in,
    never automatic - see ``_strip_signature_widgets``."""
    fitz = _load_fitz_module()
    source = Path(source_path)
    if output_path is not None:
        output_path = Path(output_path)
    else:
        output_path = build_collision_safe_path(
            build_original_redacted_pdf_path(source, output_dir=output_dir)
        )
    counters: dict[str, int] = {}

    with fitz.open(source) as document:
        signature_fields_removed = _strip_signature_widgets(
            fitz,
            document,
            active_pages=active_pages,
            strip_signatures=strip_signatures,
        )
        for page_number, page in enumerate(document, start=1):
            if not _page_in_scope(page_number, active_pages):
                continue
            page_text = page.get_text("text") or ""
            _merge_counters(
                counters,
                _redact_pattern_matches(
                    page, page_text, active_labels=active_labels
                ),
            )
            _merge_counters(counters, _redact_dictionary_matches(page, sensitive_terms))
            _merge_counters(counters, _redact_exact_text_matches(page, extra_redaction_terms))
            page.apply_redactions()

        document.save(output_path, garbage=4, deflate=True, clean=True)

    redaction_count = sum(counters.values())
    status = (
        PDF_REDACTION_STATUS_COMPLETED
        if redaction_count
        else PDF_REDACTION_STATUS_NO_MATCHES
    )
    metadata = build_pdf_redaction_metadata(
        status=status,
        output_path=output_path,
        redaction_count=redaction_count,
        counters=counters,
    )
    metadata["original_layout_redaction_used"] = True
    metadata["original_layout_redaction_experimental"] = True
    metadata["text_extraction"] = PDF_TEXT_EXTRACTION_TEXT_LAYER
    metadata["signature_fields_removed"] = signature_fields_removed
    return metadata
