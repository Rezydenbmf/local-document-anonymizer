"""True redaction helpers for text-based PDF outputs."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
import re

try:
    from .file_writers import build_anonymized_pdf_path, build_collision_safe_path
    from .sensitive_terms import SensitiveTerm
except ImportError:
    from file_writers import build_anonymized_pdf_path, build_collision_safe_path
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
PDF_REDACTION_COLORS = {
    "PESEL": (0.85, 0.12, 0.12),
    "TELEFON": (0.95, 0.45, 0.12),
    "PERSON_NAME_TYPO": (0.95, 0.45, 0.12),
    "EMAIL": (0.15, 0.35, 0.85),
    "NER_ORG": (0.50, 0.42, 0.70),
    "NER_LOCATION": (0.50, 0.42, 0.70),
    "NER_MISC": (0.50, 0.42, 0.70),
    "POSTAL_CODE": (0.85, 0.12, 0.12),
    "ADDRESS_LIKE": (0.95, 0.45, 0.12),
    "DATA": (0.45, 0.45, 0.45),
}
@dataclass(frozen=True)
class PdfRedactionPattern:
    """A source-text pattern that can be located in a text-based PDF."""

    label: str
    pattern: re.Pattern[str]


PDF_REDACTION_PATTERNS: tuple[PdfRedactionPattern, ...] = (
    PdfRedactionPattern(
        "EMAIL",
        re.compile(
            r"(?<![\w.+-])[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
        ),
    ),
    PdfRedactionPattern("PESEL", re.compile(r"(?<!\w)\d{11}(?!\w)")),
    PdfRedactionPattern(
        "TELEFON",
        re.compile(
            r"""
            (?<![\w+])
            (?:
                (?:\+48|0048)[ -]?\d{3}[ -]?\d{3}[ -]?\d{3}
                |
                \d{3}[- ]\d{3}[- ]\d{3}
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
            )
            (?!\w)
            """,
            re.VERBOSE,
        ),
    ),
    PdfRedactionPattern(
        "POSTAL_CODE",
        re.compile(r"(?<!\w)\d{2}-\d{3}(?!\w)"),
    ),
    PdfRedactionPattern(
        "ADDRESS_LIKE",
        re.compile(
            r"""
            (?<!\w)
            (?:Address|Adres):
            \s+
            [A-Z][A-Za-z]{2,}
            (?:\s+\d+[A-Za-z]?(?:/\d+)?)?
            (?:,\s+\d{2}-\d{3}\s+[A-Z][A-Za-z]{2,})?
            (?!\w)
            """,
            re.VERBOSE,
        ),
    ),
    PdfRedactionPattern(
        "PERSON_NAME_TYPO",
        re.compile(
            r"""
            (?<![\w-])
            [A-Z][A-Za-z]{2,}
            -
            (?P<surname>[A-Z][A-Za-z]{2,})
            \s+
            (?P=surname)
            (?![\w-])
            """,
            re.VERBOSE,
        ),
    ),
)


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
    }


def build_pdf_redaction_skipped_ocr_metadata() -> dict[str, object]:
    """Return metadata for PDF inputs handled through OCR text fallback."""
    return build_pdf_redaction_metadata(status=PDF_REDACTION_STATUS_SKIPPED_OCR)


def _load_fitz_module():
    try:
        import fitz
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "PDF redaction output requires PyMuPDF. "
            "Install dependencies from requirements.txt."
        ) from exc
    return fitz


def _search_page_for_text(page, text: str):
    flags = 0
    try:
        import fitz

        flags = getattr(fitz, "TEXT_DEHYPHENATE", 0)
    except ModuleNotFoundError:
        flags = 0
    return page.search_for(text, quads=False, flags=flags)


def _add_redaction(page, rect, label: str) -> None:
    fill = PDF_REDACTION_COLORS.get(label, (0.45, 0.45, 0.45))
    page.add_redact_annot(rect, fill=fill)


def _redact_pattern_matches(page, page_text: str) -> dict[str, int]:
    counters: dict[str, int] = {}
    seen_locations: set[tuple[str, float, float, float, float]] = set()
    for item in PDF_REDACTION_PATTERNS:
        for match in item.pattern.finditer(page_text):
            matched_text = match.group(0)
            for rect in _search_page_for_text(page, matched_text):
                key = (
                    item.label,
                    round(rect.x0, 2),
                    round(rect.y0, 2),
                    round(rect.x1, 2),
                    round(rect.y1, 2),
                )
                if key in seen_locations:
                    continue
                seen_locations.add(key)
                _add_redaction(page, rect, item.label)
                counters[item.label] = counters.get(item.label, 0) + 1
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
    terms = [
        (str(label), str(text).strip())
        for label, text in redaction_terms
        if str(label).strip() and str(text).strip()
    ]
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
) -> dict[str, object]:
    """Create a true-redacted PDF copy and return safe metadata."""
    fitz = _load_fitz_module()
    source = Path(source_path)
    output_path = build_collision_safe_path(
        build_anonymized_pdf_path(source, output_dir=output_dir)
    )
    counters: dict[str, int] = {}

    with fitz.open(source) as document:
        for page in document:
            page_text = page.get_text("text") or ""
            _merge_counters(counters, _redact_pattern_matches(page, page_text))
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
    return build_pdf_redaction_metadata(
        status=status,
        output_path=output_path,
        redaction_count=redaction_count,
        counters=counters,
    )
