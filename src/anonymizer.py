"""Regex-based plain text anonymization engine."""

from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from pathlib import Path
import re

try:
    from .checklist import (
        build_batch_review_checklist_text,
        build_review_checklist_text,
        save_batch_review_checklist_file,
        save_review_checklist_file,
    )
    from .audit import AUDIT_CATEGORY_ORDER, RISK_LEVELS, audit_text
    from .file_readers import (
        DOCX_EXTENSION,
        IMAGE_EXTENSIONS,
        PDF_EXTENSION,
        SUPPORTED_EXTENSIONS,
        TXT_EXTENSION,
        read_docx_file,
        read_pdf_file_pages,
        read_txt_file,
    )
    from .file_writers import (
        build_batch_summary_path,
        build_collision_safe_path,
        build_report_path,
        save_anonymized_docx_copy,
        save_anonymized_image_txt_copy,
        save_anonymized_pdf_txt_copy,
        save_anonymized_txt_copy,
    )
    from .ocr import (
        OCR_INPUT_TYPE_IMAGE,
        OCR_INPUT_TYPE_NONE,
        OCR_INPUT_TYPE_PDF,
        OcrUnavailableError,
        build_ocr_not_used_metadata,
        extract_text_with_ocr,
    )
    from .ner import DEFAULT_NER_MODEL, NER_LABELS, NER_STATUSES, anonymize_text_with_ner
    from .ner import build_ner_metadata, prepare_ner_context
    from .ner import detect_entities, detect_entities_with_details
    from .llm_review import (
        LLM_REVIEW_STATUSES,
        LLM_RESIDUAL_CATEGORIES,
        LLM_RISK_LEVELS,
        run_llm_review,
    )
    from .pdf_redaction import (
        PDF_REDACTION_STATUSES,
        PdfRedactionSpan,
        build_pdf_redaction_metadata,
        build_pdf_redaction_skipped_ocr_metadata,
        extract_pdf_word_pages,
        save_rebuilt_review_pdf_from_text,
        save_redacted_pdf_copy,
        save_word_coordinate_redacted_pdf_copy,
    )
    from .report import (
        BATCH_ERROR_EMPTY_TEXT_PDF,
        BATCH_ERROR_FILE_IO,
        BATCH_ERROR_MISSING_DEPENDENCY,
        BATCH_ERROR_OCR_FAILED,
        BATCH_ERROR_OCR_UNAVAILABLE,
        BATCH_ERROR_PROCESSING_FAILED,
        BATCH_ERROR_TEXT_DECODING,
        BATCH_ERROR_UNSUPPORTED_FILE_TYPE,
        DICTIONARY_STATUS_INVALID,
        DICTIONARY_STATUS_LOADED,
        DICTIONARY_STATUS_NOT_SELECTED,
        save_batch_summary_file,
        save_report_file,
    )
    from .sensitive_terms import (
        SensitiveTerm,
        apply_sensitive_terms,
        iter_sensitive_term_spans,
        load_sensitive_terms,
    )
except ImportError:
    from checklist import (
        build_batch_review_checklist_text,
        build_review_checklist_text,
        save_batch_review_checklist_file,
        save_review_checklist_file,
    )
    from audit import AUDIT_CATEGORY_ORDER, RISK_LEVELS, audit_text
    from file_readers import (
        DOCX_EXTENSION,
        IMAGE_EXTENSIONS,
        PDF_EXTENSION,
        SUPPORTED_EXTENSIONS,
        TXT_EXTENSION,
        read_docx_file,
        read_pdf_file_pages,
        read_txt_file,
    )
    from file_writers import (
        build_batch_summary_path,
        build_collision_safe_path,
        build_report_path,
        save_anonymized_docx_copy,
        save_anonymized_image_txt_copy,
        save_anonymized_pdf_txt_copy,
        save_anonymized_txt_copy,
    )
    from ocr import (
        OCR_INPUT_TYPE_IMAGE,
        OCR_INPUT_TYPE_NONE,
        OCR_INPUT_TYPE_PDF,
        OcrUnavailableError,
        build_ocr_not_used_metadata,
        extract_text_with_ocr,
    )
    from ner import DEFAULT_NER_MODEL, NER_LABELS, NER_STATUSES, anonymize_text_with_ner
    from ner import build_ner_metadata, prepare_ner_context
    from ner import detect_entities, detect_entities_with_details
    from llm_review import (
        LLM_REVIEW_STATUSES,
        LLM_RESIDUAL_CATEGORIES,
        LLM_RISK_LEVELS,
        run_llm_review,
    )
    from pdf_redaction import (
        PDF_REDACTION_STATUSES,
        PdfRedactionSpan,
        build_pdf_redaction_metadata,
        build_pdf_redaction_skipped_ocr_metadata,
        extract_pdf_word_pages,
        save_rebuilt_review_pdf_from_text,
        save_redacted_pdf_copy,
        save_word_coordinate_redacted_pdf_copy,
    )
    from report import (
        BATCH_ERROR_EMPTY_TEXT_PDF,
        BATCH_ERROR_FILE_IO,
        BATCH_ERROR_MISSING_DEPENDENCY,
        BATCH_ERROR_OCR_FAILED,
        BATCH_ERROR_OCR_UNAVAILABLE,
        BATCH_ERROR_PROCESSING_FAILED,
        BATCH_ERROR_TEXT_DECODING,
        BATCH_ERROR_UNSUPPORTED_FILE_TYPE,
        DICTIONARY_STATUS_INVALID,
        DICTIONARY_STATUS_LOADED,
        DICTIONARY_STATUS_NOT_SELECTED,
        save_batch_summary_file,
        save_report_file,
    )
    from sensitive_terms import (
        SensitiveTerm,
        apply_sensitive_terms,
        iter_sensitive_term_spans,
        load_sensitive_terms,
    )


SUPPORTED_LABELS = ("PESEL", "EMAIL", "TELEFON", "DATA", "PERSON_NAME_TYPO")
REPORT_CATEGORY_ORDER = (*SUPPORTED_LABELS, *NER_LABELS)
PDF_COVERAGE_WARNING = (
    "PDF redaction may be partial; some detected categories were not PDF-redacted"
)
PDF_SAFE_SCOPE_NOTE = (
    "Safe PDF scope redacts conservative exact NER_PERSON spans by default; "
    "NER_ORG, NER_LOCATION, and NER_MISC are detected but not PDF-redacted by "
    "default safe PDF scope."
)
PDF_STRICT_SCOPE_WARNING = "Strict PDF redaction scope was used; it may over-redact."
PDF_REDACTION_SCOPE_SAFE = "safe"
PDF_REDACTION_SCOPE_STRICT = "strict"
PDF_REDACTION_SCOPES = (PDF_REDACTION_SCOPE_SAFE, PDF_REDACTION_SCOPE_STRICT)
PDF_OUTPUT_MODE_VISUAL = "visual_redaction"
PDF_OUTPUT_MODE_REBUILT_REVIEW = "rebuilt_review"
PDF_OUTPUT_MODE_ORIGINAL_REDACTION = "original_redaction"
PDF_OUTPUT_MODES = (
    PDF_OUTPUT_MODE_VISUAL,
    PDF_OUTPUT_MODE_REBUILT_REVIEW,
    PDF_OUTPUT_MODE_ORIGINAL_REDACTION,
)
PDF_PAGE_SEPARATOR = "\n\f\n"
PDF_SAFE_SCOPE_NER_LABELS = tuple(NER_LABELS)
PDF_DEFAULT_NER_REDACTION_LABELS = ("NER_PERSON",)
PDF_VISUAL_NER_REDACTION_LABELS = ("NER_PERSON", "NER_ORG", "NER_LOCATION")
PDF_STRICT_NER_REDACTION_LABELS = (
    "NER_PERSON",
    "NER_ORG",
    "NER_LOCATION",
    "NER_MISC",
)
PDF_NER_REDACTION_MIN_TEXT_LENGTH = 4
PDF_NER_PERSON_MIN_WORDS = 2
WEAK_PHONE_LIKE_SKIPPED_LABEL = "WEAK_PHONE_LIKE_SKIPPED"
PHONE_CONTEXT_PATTERN = re.compile(
    r"(?i)(?:tel\.?|telefon|kom\.?|mobile|fax|kontakt|numer telefonu|phone)\s*[:\-]?\s*$"
)
WEAK_GROUPED_PHONE_PATTERN = re.compile(r"(?<![\w+])\d{3}[-\s]\d{3}[-\s]\d{3}(?!\w)")
_UPPER_LETTERS = "A-ZĄĆĘŁŃÓŚŹŻ"
_LOWER_LETTERS = "A-Za-zĄĆĘŁŃÓŚŹŻąćęłńóśźż"
_NAME_TOKEN = rf"[{_UPPER_LETTERS}][{_LOWER_LETTERS}]{{2,}}"
_NAME_HYPHEN = r"[-\u00ad\u2010\u2011\u2012\u2013\u2014]"
_SURNAME_LIKE_TOKEN = (
    rf"[{_UPPER_LETTERS}][{_LOWER_LETTERS}]{{2,}}"
    r"(?:ski|ska|cki|cka|dzki|dzka|ak|ek|ik|yk|uk|cz|icz|wicz|owicz|ewicz)"
)
PERSON_NAME_TYPO_PATTERN = re.compile(
    rf"""
    (?<![\w\-\u00ad\u2010\u2011\u2012\u2013\u2014])
    {_NAME_TOKEN}
    \s*
    {_NAME_HYPHEN}
    \s*
    (?:
        {_SURNAME_LIKE_TOKEN}
        \s+
        {_NAME_TOKEN}
        |
        {_NAME_TOKEN}
        \s+
        {_SURNAME_LIKE_TOKEN}
    )
    (?![\w\-\u00ad\u2010\u2011\u2012\u2013\u2014])
    """,
    re.VERBOSE,
)


@dataclass(frozen=True)
class FileWorkflowResult:
    """Internal single-file workflow result including safe output paths."""

    output_path: Path
    report_path: Path
    checklist_path: Path
    counters: dict[str, int]
    audit_result: dict[str, object]
    ocr_result: dict[str, object]
    ner_result: dict[str, object]
    llm_review_result: dict[str, object]
    pdf_redaction_result: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class BatchResult:
    """Public batch workflow result with paths plus safe summary metadata."""

    summary_path: Path
    input_count: int
    success_count: int
    error_count: int
    counters: dict[str, int]
    audit_status_counts: dict[str, int]
    risk_level_counts: dict[str, int]
    audit_category_counters: dict[str, int]
    results: list[dict[str, object]]
    ner_status_counts: dict[str, int] = field(default_factory=dict)
    ner_category_counters: dict[str, int] = field(default_factory=dict)
    llm_review_status_counts: dict[str, int] = field(default_factory=dict)
    llm_review_risk_level_counts: dict[str, int] = field(default_factory=dict)
    llm_review_category_counters: dict[str, int] = field(default_factory=dict)
    pdf_redaction_status_counts: dict[str, int] = field(default_factory=dict)
    review_checklist_path: Path | None = None

_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "EMAIL",
        re.compile(
            r"(?<![\w.+-])[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
        ),
    ),
    ("PESEL", re.compile(r"(?<!\w)\d{11}(?!\w)")),
    (
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
    (
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
    (
        "PERSON_NAME_TYPO",
        PERSON_NAME_TYPO_PATTERN,
    ),
)


def anonymize_text(
    text: str,
    sensitive_terms: Iterable[SensitiveTerm] | None = None,
    *,
    use_ner: bool = False,
    ner_model_name: str = DEFAULT_NER_MODEL,
) -> tuple[str, dict[str, int]]:
    """Replace high-confidence sensitive values with category placeholders."""
    ner_context = prepare_ner_context(enabled=use_ner, model_name=ner_model_name)
    anonymized, counters, _, _ = _anonymize_text_with_dictionary_counters(
        text,
        sensitive_terms=sensitive_terms,
        ner_context=ner_context,
    )
    return anonymized, counters


def _anonymize_text_with_dictionary_counters(
    text: str,
    sensitive_terms: Iterable[SensitiveTerm] | None = None,
    ner_context=None,
) -> tuple[str, dict[str, int], dict[str, int], dict[str, object]]:
    """Return anonymized text, counters, dictionary counters, and NER metadata."""
    if not isinstance(text, str):
        raise TypeError("text must be a string")

    anonymized, counters, dictionary_counters = _apply_dictionary_and_regex(
        text,
        sensitive_terms=sensitive_terms,
    )

    if ner_context is None:
        ner_result = build_ner_metadata(
            enabled=False,
            used=False,
            status="disabled",
            model_name=DEFAULT_NER_MODEL,
        )
    else:
        anonymized, ner_counters, ner_result = anonymize_text_with_ner(
            anonymized, ner_context
        )
        _merge_counters(counters, ner_counters)

    return anonymized, counters, dictionary_counters, ner_result


def _apply_dictionary_and_regex(
    text: str,
    sensitive_terms: Iterable[SensitiveTerm] | None = None,
) -> tuple[str, dict[str, int], dict[str, int]]:
    """Apply deterministic replacements before optional NER."""
    anonymized, counters = apply_sensitive_terms(text, sensitive_terms)
    dictionary_counters = dict(counters)

    for label, pattern in _PATTERNS:
        anonymized, count = pattern.subn(f"[{label}]", anonymized)
        if count:
            counters[label] = counters.get(label, 0) + count
    anonymized, weak_phone_count = _replace_contextual_weak_phone_numbers(
        anonymized
    )
    if weak_phone_count:
        counters["TELEFON"] = counters.get("TELEFON", 0) + weak_phone_count

    return anonymized, counters, dictionary_counters


def _has_phone_context(text: str, start: int) -> bool:
    left_context = text[max(0, start - 32):start]
    return bool(PHONE_CONTEXT_PATTERN.search(left_context))


def _replace_contextual_weak_phone_numbers(text: str) -> tuple[str, int]:
    parts: list[str] = []
    cursor = 0
    count = 0
    for match in WEAK_GROUPED_PHONE_PATTERN.finditer(text):
        if not _has_phone_context(text, match.start()):
            continue
        parts.append(text[cursor:match.start()])
        parts.append("[TELEFON]")
        cursor = match.end()
        count += 1
    if not count:
        return text, 0
    parts.append(text[cursor:])
    return "".join(parts), count


def _weak_phone_like_without_context_count(text: str) -> int:
    return sum(
        1
        for match in WEAK_GROUPED_PHONE_PATTERN.finditer(text)
        if not _has_phone_context(text, match.start())
    )


def _pdf_ner_redaction_terms(
    pre_ner_text: str,
    ner_context,
    *,
    allowed_labels: Iterable[str] = PDF_DEFAULT_NER_REDACTION_LABELS,
) -> list[tuple[str, str]]:
    """Return exact NER spans allowed by the default safe PDF scope."""
    allowed = {str(label) for label in allowed_labels}
    if not allowed:
        return []

    try:
        entities, _ = detect_entities(pre_ner_text, ner_context)
    except Exception:
        return []

    redaction_terms: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for entity in entities:
        if entity.label not in allowed:
            continue
        value = pre_ner_text[entity.start:entity.end].strip()
        key = (entity.label, value)
        if (
            len(value) >= PDF_NER_REDACTION_MIN_TEXT_LENGTH
            and "[" not in value
            and "]" not in value
            and any(character.isalnum() for character in value)
            and key not in seen
        ):
            seen.add(key)
            redaction_terms.append((entity.label, value))
    return redaction_terms


def _ner_redaction_word_count(value: str) -> int:
    return len(re.findall(r"\w+", value, flags=re.UNICODE))


def _is_safe_pdf_ner_redaction_value(label: str, value: str) -> bool:
    if len(value) < PDF_NER_REDACTION_MIN_TEXT_LENGTH:
        return False
    if "[" in value or "]" in value:
        return False
    if not any(character.isalnum() for character in value):
        return False
    if label == "NER_PERSON":
        return _ner_redaction_word_count(value) >= PDF_NER_PERSON_MIN_WORDS
    return True


def _pdf_ner_redaction_plan(
    pre_ner_text: str,
    ner_context,
    *,
    allowed_labels: Iterable[str],
) -> tuple[list[tuple[str, str]], dict[str, int]]:
    """Return safe NER PDF redaction terms plus label-only skipped counters."""
    allowed = {str(label) for label in allowed_labels}
    if not allowed:
        return [], {}

    try:
        entities, _, _, _ = detect_entities_with_details(pre_ner_text, ner_context)
    except Exception:
        return [], {}

    redaction_terms: list[tuple[str, str]] = []
    skipped_counters: dict[str, int] = {}
    seen: set[tuple[str, str]] = set()
    for entity in entities:
        if entity.label not in allowed:
            continue
        value = pre_ner_text[entity.start:entity.end].strip()
        if not _is_safe_pdf_ner_redaction_value(entity.label, value):
            skipped_counters[entity.label] = skipped_counters.get(entity.label, 0) + 1
            continue
        key = (entity.label, value)
        if key in seen:
            continue
        seen.add(key)
        redaction_terms.append(key)
    return redaction_terms, skipped_counters


def _normalize_pdf_redaction_scope(scope: str) -> str:
    value = str(scope or "").strip().lower()
    if value in PDF_REDACTION_SCOPES:
        return value
    return PDF_REDACTION_SCOPE_SAFE


def _normalize_pdf_output_mode(mode: str) -> str:
    value = str(mode or "").strip().lower()
    if value in PDF_OUTPUT_MODES:
        return value
    return PDF_OUTPUT_MODE_VISUAL


def _split_anonymized_pdf_pages(anonymized_text: str, page_count: int) -> list[str]:
    if page_count <= 0:
        return [anonymized_text]
    pages = anonymized_text.split(PDF_PAGE_SEPARATOR)
    if len(pages) == page_count:
        return pages
    return [anonymized_text]


def _pdf_ner_allowed_labels_for_scope(scope: str) -> tuple[str, ...]:
    normalized = _normalize_pdf_redaction_scope(scope)
    if normalized == PDF_REDACTION_SCOPE_STRICT:
        return PDF_STRICT_NER_REDACTION_LABELS
    return PDF_DEFAULT_NER_REDACTION_LABELS


def _ranges_overlap(first: tuple[int, int], second: tuple[int, int]) -> bool:
    return first[0] < second[1] and second[0] < first[1]


def _span_overlaps_existing(
    start: int,
    end: int,
    occupied_ranges: list[tuple[int, int]],
) -> bool:
    return any(_ranges_overlap((start, end), existing) for existing in occupied_ranges)


def _add_pdf_span(
    spans: list[PdfRedactionSpan],
    occupied_ranges: list[tuple[int, int]],
    *,
    label: str,
    page_number: int,
    start: int,
    end: int,
    source: str,
) -> None:
    if start >= end:
        return
    if _span_overlaps_existing(start, end, occupied_ranges):
        return
    spans.append(
        PdfRedactionSpan(
            label=label,
            page_number=page_number,
            start_offset=start,
            end_offset=end,
            replacement_label=f"[{label}]",
            source=source,
        )
    )
    occupied_ranges.append((start, end))


def _regex_pdf_spans_for_page(
    page_text: str,
    page_number: int,
    occupied_ranges: list[tuple[int, int]],
) -> list[PdfRedactionSpan]:
    spans: list[PdfRedactionSpan] = []
    for label, pattern in _PATTERNS:
        for match in pattern.finditer(page_text):
            _add_pdf_span(
                spans,
                occupied_ranges,
                label=label,
                page_number=page_number,
                start=match.start(),
                end=match.end(),
                source="regex",
            )
    for match in WEAK_GROUPED_PHONE_PATTERN.finditer(page_text):
        if not _has_phone_context(page_text, match.start()):
            continue
        _add_pdf_span(
            spans,
            occupied_ranges,
            label="TELEFON",
            page_number=page_number,
            start=match.start(),
            end=match.end(),
            source="regex",
        )
    return spans


def _dictionary_pdf_spans_for_page(
    page_text: str,
    page_number: int,
    occupied_ranges: list[tuple[int, int]],
    sensitive_terms: Iterable[SensitiveTerm] | None,
) -> list[PdfRedactionSpan]:
    spans: list[PdfRedactionSpan] = []
    for label, start, end in iter_sensitive_term_spans(page_text, sensitive_terms):
        _add_pdf_span(
            spans,
            occupied_ranges,
            label=label,
            page_number=page_number,
            start=start,
            end=end,
            source="dictionary",
        )
    return spans


def _ner_pdf_spans_for_page(
    page_text: str,
    page_number: int,
    occupied_ranges: list[tuple[int, int]],
    ner_context,
) -> list[PdfRedactionSpan]:
    if ner_context is None or not getattr(ner_context, "enabled", False):
        return []
    try:
        entities, _, _, _ = detect_entities_with_details(page_text, ner_context)
    except Exception:
        return []

    spans: list[PdfRedactionSpan] = []
    for entity in entities:
        if entity.label not in PDF_VISUAL_NER_REDACTION_LABELS:
            continue
        _add_pdf_span(
            spans,
            occupied_ranges,
            label=entity.label,
            page_number=page_number,
            start=entity.start,
            end=entity.end,
            source="ner",
        )
    return spans


def _pdf_detection_spans_for_word_pages(
    word_pages,
    *,
    sensitive_terms: Iterable[SensitiveTerm] | None,
    ner_context,
) -> list[PdfRedactionSpan]:
    spans: list[PdfRedactionSpan] = []
    for page in word_pages:
        occupied_ranges: list[tuple[int, int]] = []
        spans.extend(
            _dictionary_pdf_spans_for_page(
                page.text,
                page.page_number,
                occupied_ranges,
                sensitive_terms,
            )
        )
        spans.extend(
            _regex_pdf_spans_for_page(page.text, page.page_number, occupied_ranges)
        )
        spans.extend(
            _ner_pdf_spans_for_page(
                page.text,
                page.page_number,
                occupied_ranges,
                ner_context,
            )
        )
    return spans


def _positive_counts(source: object) -> dict[str, int]:
    if not isinstance(source, dict):
        return {}
    return {
        str(label): count
        for label, count in source.items()
        if isinstance(count, int) and count > 0
    }


def _build_pdf_detected_categories(
    counters: dict[str, int],
    audit_result: dict[str, object],
    ner_result: dict[str, object],
) -> dict[str, int]:
    detected: dict[str, int] = {}
    _merge_counters(detected, _positive_counts(counters))
    _merge_counters(detected, _positive_counts(audit_result.get("findings")))
    for label, count in _positive_counts(ner_result.get("counters")).items():
        detected[label] = max(detected.get(label, 0), count)
    return detected


def _attach_pdf_coverage_metadata(
    pdf_redaction_result: dict[str, object],
    *,
    counters: dict[str, int],
    audit_result: dict[str, object],
    ner_result: dict[str, object],
    pdf_redaction_scope: str = PDF_REDACTION_SCOPE_SAFE,
    ner_pdf_redaction_skipped_categories: dict[str, int] | None = None,
) -> dict[str, object]:
    metadata = dict(pdf_redaction_result)
    scope = _normalize_pdf_redaction_scope(pdf_redaction_scope)
    detected = _build_pdf_detected_categories(counters, audit_result, ner_result)
    txt_anonymized = _positive_counts(counters)
    pdf_redacted = _positive_counts(metadata.get("counters"))
    not_redacted = {
        label: count
        for label, count in detected.items()
        if pdf_redacted.get(label, 0) <= 0
    }
    default_pdf_labels = (
        PDF_VISUAL_NER_REDACTION_LABELS
        if metadata.get("visual_redaction_mode") == "word_coordinates"
        else PDF_DEFAULT_NER_REDACTION_LABELS
    )
    ner_safe_scope_skipped = {
        label: count
        for label, count in _positive_counts(ner_result.get("counters")).items()
        if (
            label in PDF_SAFE_SCOPE_NER_LABELS
            and (
                label not in default_pdf_labels
                or pdf_redacted.get(label, 0) <= 0
            )
        )
    }
    _merge_counters(
        ner_safe_scope_skipped,
        _positive_counts(ner_pdf_redaction_skipped_categories),
    )

    metadata["detected_categories"] = detected
    metadata["txt_anonymized_categories"] = txt_anonymized
    metadata["pdf_redacted_categories"] = pdf_redacted
    metadata["detected_not_pdf_redacted_categories"] = not_redacted
    metadata["scope"] = scope
    if ner_safe_scope_skipped and scope == PDF_REDACTION_SCOPE_SAFE:
        metadata["ner_safe_scope_skipped_categories"] = ner_safe_scope_skipped
        metadata["safe_scope_note"] = PDF_SAFE_SCOPE_NOTE
    if scope == PDF_REDACTION_SCOPE_STRICT:
        metadata["strict_scope_warning"] = PDF_STRICT_SCOPE_WARNING
    if not_redacted:
        metadata["warning"] = PDF_COVERAGE_WARNING
        if metadata.get("status") in ("completed", "no_matches"):
            metadata["status"] = "completed_with_warnings"
            metadata["used"] = True
            metadata["true_redaction"] = bool(metadata.get("redaction_count", 0))
    return metadata


def _attach_auxiliary_review_pdf_metadata(
    pdf_redaction_result: dict[str, object],
    review_pdf_result: dict[str, object],
) -> dict[str, object]:
    metadata = dict(pdf_redaction_result)
    for key in ("review_pdf_created", "review_pdf_name", "review_pdf_type"):
        metadata[key] = review_pdf_result.get(key, metadata.get(key))
    if not metadata.get("text_extraction"):
        metadata["text_extraction"] = review_pdf_result.get("text_extraction", "")
    return metadata


def _reusable_sensitive_terms(
    sensitive_terms: Iterable[SensitiveTerm] | None,
) -> list[SensitiveTerm] | None:
    if sensitive_terms is None:
        return None
    return list(sensitive_terms)


def _dictionary_result(
    *,
    status: str,
    sensitive_terms: Iterable[SensitiveTerm] | None = None,
    label_counters: dict[str, int] | None = None,
) -> dict[str, object]:
    counters_by_label: dict[str, int] = {}
    if sensitive_terms is not None:
        for term in sensitive_terms:
            if not isinstance(term, SensitiveTerm):
                raise TypeError("sensitive_terms must contain SensitiveTerm items")
            counters_by_label.setdefault(term.label, 0)

    if label_counters is not None:
        for label, count in label_counters.items():
            counters_by_label[label] = count

    return {
        "status": status,
        "label_counters": counters_by_label,
    }


def _prepare_workflow_dictionary(
    sensitive_terms: Iterable[SensitiveTerm] | None,
    sensitive_terms_path: str | Path | None,
) -> tuple[list[SensitiveTerm] | None, str]:
    if sensitive_terms is not None and sensitive_terms_path is not None:
        raise ValueError(
            "Provide either sensitive_terms or sensitive_terms_path, not both."
        )

    if sensitive_terms_path is not None:
        try:
            return load_sensitive_terms(sensitive_terms_path), DICTIONARY_STATUS_LOADED
        except (OSError, UnicodeDecodeError, ValueError):
            return None, DICTIONARY_STATUS_INVALID

    if sensitive_terms is None:
        return None, DICTIONARY_STATUS_NOT_SELECTED

    terms = _reusable_sensitive_terms(sensitive_terms)
    return terms, DICTIONARY_STATUS_LOADED


def _attach_dictionary_result(
    audit_result: dict[str, object],
    dictionary_result: dict[str, object],
) -> dict[str, object]:
    audit_with_dictionary = dict(audit_result)
    audit_with_dictionary["dictionary"] = dictionary_result
    return audit_with_dictionary


def _attach_ner_result(
    audit_result: dict[str, object],
    ner_result: dict[str, object],
) -> dict[str, object]:
    audit_with_ner = dict(audit_result)
    audit_with_ner["ner"] = ner_result
    return audit_with_ner


def _run_optional_llm_review(
    anonymized_text: str,
    *,
    use_llm_review: bool,
    llm_model_name: str,
) -> dict[str, object]:
    return run_llm_review(
        anonymized_text,
        enabled=use_llm_review,
        model_name=llm_model_name,
    )


def _merge_counters(target: dict[str, int], source: dict[str, int]) -> None:
    for label, count in source.items():
        target[label] = target.get(label, 0) + count


def anonymize_txt_file(
    source_path: str | Path,
    sensitive_terms: Iterable[SensitiveTerm] | None = None,
    sensitive_terms_path: str | Path | None = None,
    output_dir: str | Path | None = None,
    *,
    use_ner: bool = False,
    ner_model_name: str = DEFAULT_NER_MODEL,
    use_llm_review: bool = False,
    llm_model_name: str = "",
) -> tuple[Path, dict[str, int]]:
    """Anonymize a TXT file and save output plus a safe report."""
    output_path, counters, _ = anonymize_txt_file_with_audit(
        source_path,
        sensitive_terms=sensitive_terms,
        sensitive_terms_path=sensitive_terms_path,
        output_dir=output_dir,
        use_ner=use_ner,
        ner_model_name=ner_model_name,
        use_llm_review=use_llm_review,
        llm_model_name=llm_model_name,
    )
    return output_path, counters


def anonymize_txt_file_with_audit(
    source_path: str | Path,
    sensitive_terms: Iterable[SensitiveTerm] | None = None,
    sensitive_terms_path: str | Path | None = None,
    output_dir: str | Path | None = None,
    *,
    use_ner: bool = False,
    ner_model_name: str = DEFAULT_NER_MODEL,
    use_llm_review: bool = False,
    llm_model_name: str = "",
) -> tuple[Path, dict[str, int], dict[str, object]]:
    """Anonymize a TXT file and return safe audit metadata."""
    result = _anonymize_txt_file_result(
        source_path,
        sensitive_terms=sensitive_terms,
        sensitive_terms_path=sensitive_terms_path,
        output_dir=output_dir,
        use_ner=use_ner,
        ner_model_name=ner_model_name,
        use_llm_review=use_llm_review,
        llm_model_name=llm_model_name,
    )
    return result.output_path, result.counters, result.audit_result


def _anonymize_txt_file_result(
    source_path: str | Path,
    sensitive_terms: Iterable[SensitiveTerm] | None = None,
    sensitive_terms_path: str | Path | None = None,
    output_dir: str | Path | None = None,
    *,
    use_ner: bool = False,
    ner_model_name: str = DEFAULT_NER_MODEL,
    use_llm_review: bool = False,
    llm_model_name: str = "",
) -> FileWorkflowResult:
    """Anonymize a TXT file and return paths needed by batch processing."""
    terms, dictionary_status = _prepare_workflow_dictionary(
        sensitive_terms, sensitive_terms_path
    )
    ner_context = prepare_ner_context(enabled=use_ner, model_name=ner_model_name)
    text = read_txt_file(source_path)
    anonymized, counters, dictionary_counters, ner_result = (
        _anonymize_text_with_dictionary_counters(
            text,
            sensitive_terms=terms,
            ner_context=ner_context,
        )
    )
    output_path = save_anonymized_txt_copy(
        source_path, anonymized, output_dir=output_dir
    )
    llm_review_result = _run_optional_llm_review(
        anonymized,
        use_llm_review=use_llm_review,
        llm_model_name=llm_model_name,
    )
    dictionary_result = _dictionary_result(
        status=dictionary_status,
        sensitive_terms=terms,
        label_counters=dictionary_counters,
    )
    audit_result = _attach_dictionary_result(
        audit_text(anonymized, sensitive_terms=terms),
        dictionary_result,
    )
    audit_result = _attach_ner_result(audit_result, ner_result)
    ocr_result = build_ocr_not_used_metadata(OCR_INPUT_TYPE_NONE)
    report_path = _build_anonymization_report_path(source_path, output_dir=output_dir)
    checklist_path = _save_review_checklist(
        source_path,
        output_path,
        report_path,
        counters,
        audit_result,
        ocr_result,
        ner_result,
        llm_review_result,
        anonymized,
        output_dir=output_dir,
    )
    report_path = _save_anonymization_report(
        source_path,
        output_path,
        counters,
        audit_result,
        dictionary_result,
        ocr_result,
        ner_result,
        llm_review_result,
        output_dir=output_dir,
        report_path=report_path,
        checklist_result={"created": True, "output_name": checklist_path.name},
    )
    return FileWorkflowResult(
        output_path,
        report_path,
        checklist_path,
        counters,
        audit_result,
        ocr_result,
        ner_result,
        llm_review_result,
    )


def anonymize_docx_file(
    source_path: str | Path,
    sensitive_terms: Iterable[SensitiveTerm] | None = None,
    sensitive_terms_path: str | Path | None = None,
    output_dir: str | Path | None = None,
    *,
    use_ner: bool = False,
    ner_model_name: str = DEFAULT_NER_MODEL,
    use_llm_review: bool = False,
    llm_model_name: str = "",
) -> tuple[Path, dict[str, int]]:
    """Anonymize a DOCX file and save output plus a safe report."""
    output_path, counters, _ = anonymize_docx_file_with_audit(
        source_path,
        sensitive_terms=sensitive_terms,
        sensitive_terms_path=sensitive_terms_path,
        output_dir=output_dir,
        use_ner=use_ner,
        ner_model_name=ner_model_name,
        use_llm_review=use_llm_review,
        llm_model_name=llm_model_name,
    )
    return output_path, counters


def anonymize_docx_file_with_audit(
    source_path: str | Path,
    sensitive_terms: Iterable[SensitiveTerm] | None = None,
    sensitive_terms_path: str | Path | None = None,
    output_dir: str | Path | None = None,
    *,
    use_ner: bool = False,
    ner_model_name: str = DEFAULT_NER_MODEL,
    use_llm_review: bool = False,
    llm_model_name: str = "",
) -> tuple[Path, dict[str, int], dict[str, object]]:
    """Anonymize a DOCX file and return safe audit metadata."""
    result = _anonymize_docx_file_result(
        source_path,
        sensitive_terms=sensitive_terms,
        sensitive_terms_path=sensitive_terms_path,
        output_dir=output_dir,
        use_ner=use_ner,
        ner_model_name=ner_model_name,
        use_llm_review=use_llm_review,
        llm_model_name=llm_model_name,
    )
    return result.output_path, result.counters, result.audit_result


def _anonymize_docx_file_result(
    source_path: str | Path,
    sensitive_terms: Iterable[SensitiveTerm] | None = None,
    sensitive_terms_path: str | Path | None = None,
    output_dir: str | Path | None = None,
    *,
    use_ner: bool = False,
    ner_model_name: str = DEFAULT_NER_MODEL,
    use_llm_review: bool = False,
    llm_model_name: str = "",
) -> FileWorkflowResult:
    """Anonymize a DOCX file and return paths needed by batch processing."""
    terms, dictionary_status = _prepare_workflow_dictionary(
        sensitive_terms, sensitive_terms_path
    )
    ner_context = prepare_ner_context(enabled=use_ner, model_name=ner_model_name)
    dictionary_counters: dict[str, int] = {}
    ner_counters: dict[str, int] = {}
    ner_status = build_ner_metadata(
        enabled=ner_context.enabled,
        used=False,
        status=ner_context.status,
        model_name=ner_context.model_name,
        warning=ner_context.warning,
    )

    def anonymize_docx_text(text: str) -> tuple[str, dict[str, int]]:
        nonlocal ner_status
        paragraph_result = _anonymize_text_with_dictionary_counters(
            text,
            sensitive_terms=terms,
            ner_context=ner_context,
        )
        anonymized, counters, paragraph_dictionary_counters, paragraph_ner_result = (
            paragraph_result
        )
        _merge_counters(dictionary_counters, paragraph_dictionary_counters)
        paragraph_ner_counters = paragraph_ner_result.get("counters", {})
        if isinstance(paragraph_ner_counters, dict):
            _merge_counters(
                ner_counters,
                {
                    label: count
                    for label, count in paragraph_ner_counters.items()
                    if isinstance(count, int)
                },
            )
        ner_status = paragraph_ner_result
        return anonymized, counters

    def anonymize_docx_run(text: str) -> tuple[str, dict[str, int]]:
        anonymized, counters, _, _ = _anonymize_text_with_dictionary_counters(
            text, sensitive_terms=terms
        )
        return anonymized, counters

    output_path, counters = save_anonymized_docx_copy(
        source_path,
        anonymize_docx_text,
        anonymize_run=anonymize_docx_run,
        output_dir=output_dir,
    )
    anonymized_text = read_docx_file(output_path)
    llm_review_result = _run_optional_llm_review(
        anonymized_text,
        use_llm_review=use_llm_review,
        llm_model_name=llm_model_name,
    )
    dictionary_result = _dictionary_result(
        status=dictionary_status,
        sensitive_terms=terms,
        label_counters=dictionary_counters,
    )
    ner_result = dict(ner_status)
    if ner_counters:
        ner_result["used"] = True
        ner_result["counters"] = {
            label: ner_counters.get(label, 0)
            for label in NER_LABELS
        }
    audit_result = _attach_dictionary_result(
        audit_text(anonymized_text, sensitive_terms=terms),
        dictionary_result,
    )
    audit_result = _attach_ner_result(audit_result, ner_result)
    ocr_result = build_ocr_not_used_metadata(OCR_INPUT_TYPE_NONE)
    report_path = _build_anonymization_report_path(source_path, output_dir=output_dir)
    checklist_path = _save_review_checklist(
        source_path,
        output_path,
        report_path,
        counters,
        audit_result,
        ocr_result,
        ner_result,
        llm_review_result,
        anonymized_text,
        sections=anonymized_text.splitlines(),
        section_label="Paragraph",
        output_dir=output_dir,
    )
    report_path = _save_anonymization_report(
        source_path,
        output_path,
        counters,
        audit_result,
        dictionary_result,
        ocr_result,
        ner_result,
        llm_review_result,
        output_dir=output_dir,
        report_path=report_path,
        checklist_result={"created": True, "output_name": checklist_path.name},
    )
    return FileWorkflowResult(
        output_path,
        report_path,
        checklist_path,
        counters,
        audit_result,
        ocr_result,
        ner_result,
        llm_review_result,
    )


def anonymize_pdf_file(
    source_path: str | Path,
    sensitive_terms: Iterable[SensitiveTerm] | None = None,
    sensitive_terms_path: str | Path | None = None,
    output_dir: str | Path | None = None,
    *,
    use_ner: bool = False,
    ner_model_name: str = DEFAULT_NER_MODEL,
    use_llm_review: bool = False,
    llm_model_name: str = "",
    pdf_redaction_scope: str = PDF_REDACTION_SCOPE_SAFE,
    pdf_output_mode: str = PDF_OUTPUT_MODE_VISUAL,
) -> tuple[Path, dict[str, int]]:
    """Anonymize text from a PDF and save TXT output plus a safe report."""
    output_path, counters, _ = anonymize_pdf_file_with_audit(
        source_path,
        sensitive_terms=sensitive_terms,
        sensitive_terms_path=sensitive_terms_path,
        output_dir=output_dir,
        use_ner=use_ner,
        ner_model_name=ner_model_name,
        use_llm_review=use_llm_review,
        llm_model_name=llm_model_name,
        pdf_redaction_scope=pdf_redaction_scope,
        pdf_output_mode=pdf_output_mode,
    )
    return output_path, counters


def anonymize_pdf_file_with_audit(
    source_path: str | Path,
    sensitive_terms: Iterable[SensitiveTerm] | None = None,
    sensitive_terms_path: str | Path | None = None,
    output_dir: str | Path | None = None,
    *,
    use_ner: bool = False,
    ner_model_name: str = DEFAULT_NER_MODEL,
    use_llm_review: bool = False,
    llm_model_name: str = "",
    pdf_redaction_scope: str = PDF_REDACTION_SCOPE_SAFE,
    pdf_output_mode: str = PDF_OUTPUT_MODE_VISUAL,
) -> tuple[Path, dict[str, int], dict[str, object]]:
    """Anonymize text from a PDF and return safe audit metadata."""
    result = _anonymize_pdf_file_result(
        source_path,
        sensitive_terms=sensitive_terms,
        sensitive_terms_path=sensitive_terms_path,
        output_dir=output_dir,
        use_ner=use_ner,
        ner_model_name=ner_model_name,
        use_llm_review=use_llm_review,
        llm_model_name=llm_model_name,
        pdf_redaction_scope=pdf_redaction_scope,
        pdf_output_mode=pdf_output_mode,
    )
    return result.output_path, result.counters, result.audit_result


def _anonymize_pdf_file_result(
    source_path: str | Path,
    sensitive_terms: Iterable[SensitiveTerm] | None = None,
    sensitive_terms_path: str | Path | None = None,
    output_dir: str | Path | None = None,
    *,
    use_ner: bool = False,
    ner_model_name: str = DEFAULT_NER_MODEL,
    use_llm_review: bool = False,
    llm_model_name: str = "",
    pdf_redaction_scope: str = PDF_REDACTION_SCOPE_SAFE,
    pdf_output_mode: str = PDF_OUTPUT_MODE_VISUAL,
) -> FileWorkflowResult:
    """Anonymize a PDF file and return paths needed by batch processing."""
    terms, dictionary_status = _prepare_workflow_dictionary(
        sensitive_terms, sensitive_terms_path
    )
    ner_context = prepare_ner_context(enabled=use_ner, model_name=ner_model_name)
    text_based_pdf = False
    word_pages = []
    try:
        word_pages = extract_pdf_word_pages(source_path)
        source_page_texts = read_pdf_file_pages(source_path)
        if not any(page_text.strip() for page_text in source_page_texts):
            raise ValueError("PDF has no extractable text")
        text = PDF_PAGE_SEPARATOR.join(source_page_texts)
        ocr_result = build_ocr_not_used_metadata(OCR_INPUT_TYPE_PDF)
        text_based_pdf = True
    except ValueError as error:
        if "no extractable text" not in str(error):
            raise
        extraction = extract_text_with_ocr(source_path)
        text = extraction.text
        source_page_texts = []
        ocr_result = extraction.metadata
        pdf_redaction_result = build_pdf_redaction_skipped_ocr_metadata()
    pdf_detection_spans = (
        _pdf_detection_spans_for_word_pages(
            word_pages,
            sensitive_terms=terms,
            ner_context=ner_context,
        )
        if text_based_pdf
        else []
    )
    weak_phone_like_skipped_count = (
        sum(_weak_phone_like_without_context_count(page.text) for page in word_pages)
        if text_based_pdf
        else 0
    )
    pre_ner_text, counters, dictionary_counters = _apply_dictionary_and_regex(
        text,
        sensitive_terms=terms,
    )
    normalized_pdf_scope = _normalize_pdf_redaction_scope(pdf_redaction_scope)
    pdf_ner_redaction_terms, pdf_ner_skipped_categories = _pdf_ner_redaction_plan(
        pre_ner_text,
        ner_context,
        allowed_labels=_pdf_ner_allowed_labels_for_scope(normalized_pdf_scope),
    )
    if ner_context is None:
        anonymized = pre_ner_text
        ner_result = build_ner_metadata(
            enabled=False,
            used=False,
            status="disabled",
            model_name=DEFAULT_NER_MODEL,
        )
    else:
        anonymized, ner_counters, ner_result = anonymize_text_with_ner(
            pre_ner_text,
            ner_context,
        )
        _merge_counters(counters, ner_counters)

    normalized_pdf_output_mode = _normalize_pdf_output_mode(pdf_output_mode)
    anonymized_pages = _split_anonymized_pdf_pages(
        anonymized,
        len(source_page_texts) if text_based_pdf else 0,
    )
    anonymized_output_text = "\n\n".join(anonymized_pages)

    if normalized_pdf_output_mode == PDF_OUTPUT_MODE_VISUAL and text_based_pdf:
        try:
            pdf_redaction_result = save_word_coordinate_redacted_pdf_copy(
                source_path,
                word_pages=word_pages,
                spans=pdf_detection_spans,
                output_dir=output_dir,
            )
        except RuntimeError:
            pdf_redaction_result = build_pdf_redaction_metadata(status="unavailable")
            pdf_redaction_result["text_extraction"] = "text_layer"
        try:
            review_pdf_result = save_rebuilt_review_pdf_from_text(
                source_path,
                anonymized_output_text,
                page_texts=anonymized_pages,
                output_dir=output_dir,
                text_extraction="text_layer",
            )
            pdf_redaction_result = _attach_auxiliary_review_pdf_metadata(
                pdf_redaction_result,
                review_pdf_result,
            )
        except RuntimeError:
            pass
    elif normalized_pdf_output_mode == PDF_OUTPUT_MODE_REBUILT_REVIEW:
        try:
            pdf_redaction_result = save_rebuilt_review_pdf_from_text(
                source_path,
                anonymized_output_text,
                page_texts=anonymized_pages if text_based_pdf else None,
                output_dir=output_dir,
                text_extraction="text_layer" if text_based_pdf else "ocr_fallback",
            )
        except RuntimeError:
            pdf_redaction_result = build_pdf_redaction_metadata(status="unavailable")
            pdf_redaction_result["text_extraction"] = (
                "text_layer" if text_based_pdf else "ocr_fallback"
            )
    elif text_based_pdf:
        try:
            pdf_redaction_result = save_redacted_pdf_copy(
                source_path,
                sensitive_terms=terms,
                extra_redaction_terms=pdf_ner_redaction_terms,
                output_dir=output_dir,
            )
        except RuntimeError:
            pdf_redaction_result = build_pdf_redaction_metadata(status="unavailable")
    else:
        pdf_redaction_result = build_pdf_redaction_skipped_ocr_metadata()
        if normalized_pdf_output_mode == PDF_OUTPUT_MODE_VISUAL:
            try:
                review_pdf_result = save_rebuilt_review_pdf_from_text(
                    source_path,
                    anonymized_output_text,
                    page_texts=None,
                    output_dir=output_dir,
                    text_extraction="ocr_fallback",
                )
                pdf_redaction_result = _attach_auxiliary_review_pdf_metadata(
                    pdf_redaction_result,
                    review_pdf_result,
                )
            except RuntimeError:
                pass
    if weak_phone_like_skipped_count:
        pdf_redaction_result["weak_phone_like_skipped"] = (
            weak_phone_like_skipped_count
        )
    output_path = save_anonymized_pdf_txt_copy(
        source_path, anonymized_output_text, output_dir=output_dir
    )
    llm_review_result = _run_optional_llm_review(
        anonymized_output_text,
        use_llm_review=use_llm_review,
        llm_model_name=llm_model_name,
    )
    dictionary_result = _dictionary_result(
        status=dictionary_status,
        sensitive_terms=terms,
        label_counters=dictionary_counters,
    )
    audit_result = _attach_dictionary_result(
        audit_text(anonymized_output_text, sensitive_terms=terms),
        dictionary_result,
    )
    audit_result = _attach_ner_result(audit_result, ner_result)
    pdf_redaction_result = _attach_pdf_coverage_metadata(
        pdf_redaction_result,
        counters=counters,
        audit_result=audit_result,
        ner_result=ner_result,
        pdf_redaction_scope=normalized_pdf_scope,
        ner_pdf_redaction_skipped_categories=pdf_ner_skipped_categories,
    )
    report_path = _build_anonymization_report_path(source_path, output_dir=output_dir)
    checklist_path = _save_review_checklist(
        source_path,
        output_path,
        report_path,
        counters,
        audit_result,
        ocr_result,
        ner_result,
        llm_review_result,
        anonymized_output_text,
        sections=anonymized_pages if text_based_pdf else None,
        section_label="Source page",
        pdf_redaction_result=pdf_redaction_result,
        output_dir=output_dir,
    )
    report_path = _save_anonymization_report(
        source_path,
        output_path,
        counters,
        audit_result,
        dictionary_result,
        ocr_result,
        ner_result,
        llm_review_result,
        pdf_redaction_result,
        output_dir=output_dir,
        report_path=report_path,
        checklist_result={"created": True, "output_name": checklist_path.name},
    )
    return FileWorkflowResult(
        output_path,
        report_path,
        checklist_path,
        counters,
        audit_result,
        ocr_result,
        ner_result,
        llm_review_result,
        pdf_redaction_result,
    )


def anonymize_image_file(
    source_path: str | Path,
    sensitive_terms: Iterable[SensitiveTerm] | None = None,
    sensitive_terms_path: str | Path | None = None,
    output_dir: str | Path | None = None,
    *,
    use_ner: bool = False,
    ner_model_name: str = DEFAULT_NER_MODEL,
    use_llm_review: bool = False,
    llm_model_name: str = "",
) -> tuple[Path, dict[str, int]]:
    """Anonymize OCR text from an image and save TXT output plus a safe report."""
    output_path, counters, _ = anonymize_image_file_with_audit(
        source_path,
        sensitive_terms=sensitive_terms,
        sensitive_terms_path=sensitive_terms_path,
        output_dir=output_dir,
        use_ner=use_ner,
        ner_model_name=ner_model_name,
        use_llm_review=use_llm_review,
        llm_model_name=llm_model_name,
    )
    return output_path, counters


def anonymize_image_file_with_audit(
    source_path: str | Path,
    sensitive_terms: Iterable[SensitiveTerm] | None = None,
    sensitive_terms_path: str | Path | None = None,
    output_dir: str | Path | None = None,
    *,
    use_ner: bool = False,
    ner_model_name: str = DEFAULT_NER_MODEL,
    use_llm_review: bool = False,
    llm_model_name: str = "",
) -> tuple[Path, dict[str, int], dict[str, object]]:
    """Anonymize OCR text from an image and return safe audit metadata."""
    result = _anonymize_image_file_result(
        source_path,
        sensitive_terms=sensitive_terms,
        sensitive_terms_path=sensitive_terms_path,
        output_dir=output_dir,
        use_ner=use_ner,
        ner_model_name=ner_model_name,
        use_llm_review=use_llm_review,
        llm_model_name=llm_model_name,
    )
    return result.output_path, result.counters, result.audit_result


def _anonymize_image_file_result(
    source_path: str | Path,
    sensitive_terms: Iterable[SensitiveTerm] | None = None,
    sensitive_terms_path: str | Path | None = None,
    output_dir: str | Path | None = None,
    *,
    use_ner: bool = False,
    ner_model_name: str = DEFAULT_NER_MODEL,
    use_llm_review: bool = False,
    llm_model_name: str = "",
) -> FileWorkflowResult:
    """Anonymize OCR text from an image and return paths for batch processing."""
    terms, dictionary_status = _prepare_workflow_dictionary(
        sensitive_terms, sensitive_terms_path
    )
    ner_context = prepare_ner_context(enabled=use_ner, model_name=ner_model_name)
    extraction = extract_text_with_ocr(source_path)
    anonymized, counters, dictionary_counters, ner_result = (
        _anonymize_text_with_dictionary_counters(
            extraction.text,
            sensitive_terms=terms,
            ner_context=ner_context,
        )
    )
    output_path = save_anonymized_image_txt_copy(
        source_path, anonymized, output_dir=output_dir
    )
    llm_review_result = _run_optional_llm_review(
        anonymized,
        use_llm_review=use_llm_review,
        llm_model_name=llm_model_name,
    )
    dictionary_result = _dictionary_result(
        status=dictionary_status,
        sensitive_terms=terms,
        label_counters=dictionary_counters,
    )
    audit_result = _attach_dictionary_result(
        audit_text(anonymized, sensitive_terms=terms),
        dictionary_result,
    )
    audit_result = _attach_ner_result(audit_result, ner_result)
    report_path = _build_anonymization_report_path(source_path, output_dir=output_dir)
    checklist_path = _save_review_checklist(
        source_path,
        output_path,
        report_path,
        counters,
        audit_result,
        extraction.metadata,
        ner_result,
        llm_review_result,
        anonymized,
        output_dir=output_dir,
    )
    report_path = _save_anonymization_report(
        source_path,
        output_path,
        counters,
        audit_result,
        dictionary_result,
        extraction.metadata,
        ner_result,
        llm_review_result,
        output_dir=output_dir,
        report_path=report_path,
        checklist_result={"created": True, "output_name": checklist_path.name},
    )
    return FileWorkflowResult(
        output_path,
        report_path,
        checklist_path,
        counters,
        audit_result,
        extraction.metadata,
        ner_result,
        llm_review_result,
    )


def _build_anonymization_report_path(
    source_path: str | Path,
    *,
    output_dir: str | Path | None = None,
) -> Path:
    return build_collision_safe_path(
        build_report_path(source_path, output_dir=output_dir)
    )


def _output_names_for_checklist(
    output_path: str | Path,
    pdf_redaction_result: dict[str, object] | None = None,
) -> list[str]:
    output_names = [Path(output_path).name]
    if pdf_redaction_result is None:
        return output_names

    visual_name = str(pdf_redaction_result.get("visual_pdf_name", "")).strip()
    if visual_name and visual_name not in output_names:
        output_names.append(Path(visual_name).name)
    for key in ("review_pdf_name", "output_name"):
        name = str(pdf_redaction_result.get(key, "")).strip()
        if name and name not in output_names:
            output_names.append(Path(name).name)
    return output_names


def _save_review_checklist(
    source_path: str | Path,
    output_path: str | Path,
    report_path: str | Path,
    counters: dict[str, int],
    audit_result: dict[str, object],
    ocr_result: dict[str, object],
    ner_result: dict[str, object],
    llm_review_result: dict[str, object],
    anonymized_text: str,
    *,
    sections: list[str] | None = None,
    section_label: str = "Line",
    pdf_redaction_result: dict[str, object] | None = None,
    output_dir: str | Path | None = None,
) -> Path:
    checklist_text = build_review_checklist_text(
        source_name=Path(source_path).name,
        input_extension=Path(source_path).suffix,
        output_names=_output_names_for_checklist(output_path, pdf_redaction_result),
        report_name=Path(report_path).name,
        counters=counters,
        audit_result=audit_result,
        ocr_result=ocr_result,
        ner_result=ner_result,
        llm_review_result=llm_review_result,
        anonymized_text=anonymized_text,
        sections=sections,
        section_label=section_label,
        pdf_redaction_result=pdf_redaction_result,
    )
    return save_review_checklist_file(
        source_path,
        output_dir=output_dir,
        text=checklist_text,
    )


def _save_anonymization_report(
    source_path: str | Path,
    output_path: str | Path,
    counters: dict[str, int],
    audit_result: dict[str, object],
    dictionary_result: dict[str, object],
    ocr_result: dict[str, object],
    ner_result: dict[str, object],
    llm_review_result: dict[str, object],
    pdf_redaction_result: dict[str, object] | None = None,
    output_dir: str | Path | None = None,
    report_path: str | Path | None = None,
    checklist_result: dict[str, object] | None = None,
) -> Path:
    source = Path(source_path)
    output = Path(output_path)
    final_report_path = (
        Path(report_path)
        if report_path is not None
        else _build_anonymization_report_path(source, output_dir=output_dir)
    )
    return save_report_file(
        final_report_path,
        counters=counters,
        input_extension=source.suffix,
        output_extension=output.suffix,
        category_order=REPORT_CATEGORY_ORDER,
        audit_result=audit_result,
        audit_category_order=AUDIT_CATEGORY_ORDER,
        dictionary_result=dictionary_result,
        ocr_result=ocr_result,
        ner_result=ner_result,
        llm_review_result=llm_review_result,
        pdf_redaction_result=pdf_redaction_result,
        checklist_result=checklist_result,
    )


def anonymize_file(
    source_path: str | Path,
    sensitive_terms: Iterable[SensitiveTerm] | None = None,
    sensitive_terms_path: str | Path | None = None,
    output_dir: str | Path | None = None,
    *,
    use_ner: bool = False,
    ner_model_name: str = DEFAULT_NER_MODEL,
    use_llm_review: bool = False,
    llm_model_name: str = "",
    pdf_redaction_scope: str = PDF_REDACTION_SCOPE_SAFE,
    pdf_output_mode: str = PDF_OUTPUT_MODE_VISUAL,
) -> tuple[Path, dict[str, int]]:
    """Anonymize one supported application file using existing workflows."""
    output_path, counters, _ = anonymize_file_with_audit(
        source_path,
        sensitive_terms=sensitive_terms,
        sensitive_terms_path=sensitive_terms_path,
        output_dir=output_dir,
        use_ner=use_ner,
        ner_model_name=ner_model_name,
        use_llm_review=use_llm_review,
        llm_model_name=llm_model_name,
        pdf_redaction_scope=pdf_redaction_scope,
        pdf_output_mode=pdf_output_mode,
    )
    return output_path, counters


def anonymize_file_with_audit(
    source_path: str | Path,
    sensitive_terms: Iterable[SensitiveTerm] | None = None,
    sensitive_terms_path: str | Path | None = None,
    output_dir: str | Path | None = None,
    *,
    use_ner: bool = False,
    ner_model_name: str = DEFAULT_NER_MODEL,
    use_llm_review: bool = False,
    llm_model_name: str = "",
    pdf_redaction_scope: str = PDF_REDACTION_SCOPE_SAFE,
    pdf_output_mode: str = PDF_OUTPUT_MODE_VISUAL,
) -> tuple[Path, dict[str, int], dict[str, object]]:
    """Anonymize one supported file and return safe audit metadata."""
    result = _anonymize_file_result(
        source_path,
        sensitive_terms=sensitive_terms,
        sensitive_terms_path=sensitive_terms_path,
        output_dir=output_dir,
        use_ner=use_ner,
        ner_model_name=ner_model_name,
        use_llm_review=use_llm_review,
        llm_model_name=llm_model_name,
        pdf_redaction_scope=pdf_redaction_scope,
        pdf_output_mode=pdf_output_mode,
    )
    return result.output_path, result.counters, result.audit_result


def _anonymize_file_result(
    source_path: str | Path,
    sensitive_terms: Iterable[SensitiveTerm] | None = None,
    sensitive_terms_path: str | Path | None = None,
    output_dir: str | Path | None = None,
    *,
    use_ner: bool = False,
    ner_model_name: str = DEFAULT_NER_MODEL,
    use_llm_review: bool = False,
    llm_model_name: str = "",
    pdf_redaction_scope: str = PDF_REDACTION_SCOPE_SAFE,
    pdf_output_mode: str = PDF_OUTPUT_MODE_VISUAL,
) -> FileWorkflowResult:
    """Anonymize one supported file and return paths needed by batch processing."""
    path = Path(source_path)

    if path.suffix.lower() == TXT_EXTENSION:
        return _anonymize_txt_file_result(
            path,
            sensitive_terms=sensitive_terms,
            sensitive_terms_path=sensitive_terms_path,
            output_dir=output_dir,
            use_ner=use_ner,
            ner_model_name=ner_model_name,
            use_llm_review=use_llm_review,
            llm_model_name=llm_model_name,
        )
    if path.suffix.lower() == DOCX_EXTENSION:
        return _anonymize_docx_file_result(
            path,
            sensitive_terms=sensitive_terms,
            sensitive_terms_path=sensitive_terms_path,
            output_dir=output_dir,
            use_ner=use_ner,
            ner_model_name=ner_model_name,
            use_llm_review=use_llm_review,
            llm_model_name=llm_model_name,
        )
    if path.suffix.lower() == PDF_EXTENSION:
        return _anonymize_pdf_file_result(
            path,
            sensitive_terms=sensitive_terms,
            sensitive_terms_path=sensitive_terms_path,
            output_dir=output_dir,
            use_ner=use_ner,
            ner_model_name=ner_model_name,
            use_llm_review=use_llm_review,
            llm_model_name=llm_model_name,
            pdf_redaction_scope=pdf_redaction_scope,
            pdf_output_mode=pdf_output_mode,
        )
    if path.suffix.lower() in IMAGE_EXTENSIONS:
        return _anonymize_image_file_result(
            path,
            sensitive_terms=sensitive_terms,
            sensitive_terms_path=sensitive_terms_path,
            output_dir=output_dir,
            use_ner=use_ner,
            ner_model_name=ner_model_name,
            use_llm_review=use_llm_review,
            llm_model_name=llm_model_name,
        )

    suffix = path.suffix.lower() or "<none>"
    supported = ", ".join(SUPPORTED_EXTENSIONS)
    raise ValueError(
        f"Unsupported file extension for anonymize_file: {suffix}. "
        f"Only {supported} files are supported."
    )


def _safe_batch_error_description(error: Exception) -> str:
    if isinstance(error, OcrUnavailableError):
        if error.status in ("dependency_missing", "engine_not_found"):
            return BATCH_ERROR_OCR_UNAVAILABLE
        return BATCH_ERROR_OCR_FAILED
    if isinstance(error, UnicodeDecodeError):
        return BATCH_ERROR_TEXT_DECODING
    if isinstance(error, ValueError) and "no extractable text" in str(error):
        return BATCH_ERROR_EMPTY_TEXT_PDF
    if isinstance(error, OSError):
        return BATCH_ERROR_FILE_IO
    if isinstance(error, RuntimeError):
        return BATCH_ERROR_MISSING_DEPENDENCY
    return BATCH_ERROR_PROCESSING_FAILED


def _merge_audit_status_count(
    audit_status_counts: dict[str, int],
    audit_result: dict[str, object],
) -> None:
    status = audit_result.get("status")
    if status not in ("ok", "warning"):
        status = "not run"
    audit_status_counts[str(status)] = audit_status_counts.get(str(status), 0) + 1


def _merge_risk_level_count(
    risk_level_counts: dict[str, int],
    audit_result: dict[str, object],
) -> None:
    risk_level = audit_result.get("risk_level")
    if risk_level in RISK_LEVELS:
        risk_level_counts[str(risk_level)] = risk_level_counts.get(str(risk_level), 0) + 1


def _merge_audit_findings(
    audit_category_counters: dict[str, int],
    audit_result: dict[str, object],
) -> None:
    findings = audit_result.get("findings")
    if not isinstance(findings, dict):
        return

    for label in AUDIT_CATEGORY_ORDER:
        count = findings.get(label, 0)
        if isinstance(count, int):
            audit_category_counters[label] = (
                audit_category_counters.get(label, 0) + count
            )


def anonymize_batch(
    source_paths: Iterable[str | Path],
    output_dir: str | Path,
    sensitive_terms: Iterable[SensitiveTerm] | None = None,
    sensitive_terms_path: str | Path | None = None,
    *,
    use_ner: bool = False,
    ner_model_name: str = DEFAULT_NER_MODEL,
    use_llm_review: bool = False,
    llm_model_name: str = "",
    pdf_redaction_scope: str = PDF_REDACTION_SCOPE_SAFE,
    pdf_output_mode: str = PDF_OUTPUT_MODE_VISUAL,
    progress_callback: Callable[[int, int, Path], None] | None = None,
) -> BatchResult:
    """Anonymize supported files sequentially into one output workspace."""
    if sensitive_terms is not None and sensitive_terms_path is not None:
        raise ValueError(
            "Provide either sensitive_terms or sensitive_terms_path, not both."
        )

    paths = [Path(path) for path in source_paths]
    reusable_terms = _reusable_sensitive_terms(sensitive_terms)
    aggregate_counters: dict[str, int] = {}
    audit_status_counts = {"ok": 0, "warning": 0, "not run": 0}
    risk_level_counts = {risk_level: 0 for risk_level in RISK_LEVELS}
    audit_category_counters = {category: 0 for category in AUDIT_CATEGORY_ORDER}
    ner_status_counts = {status: 0 for status in NER_STATUSES}
    ner_category_counters = {label: 0 for label in NER_LABELS}
    llm_review_status_counts = {status: 0 for status in LLM_REVIEW_STATUSES}
    llm_review_risk_level_counts = {risk: 0 for risk in LLM_RISK_LEVELS}
    llm_review_category_counters = {category: 0 for category in LLM_RESIDUAL_CATEGORIES}
    pdf_redaction_status_counts = {status: 0 for status in PDF_REDACTION_STATUSES}
    results: list[dict[str, object]] = []
    success_count = 0
    error_count = 0

    total_paths = len(paths)
    for index, path in enumerate(paths, start=1):
        if progress_callback is not None:
            progress_callback(index, total_paths, path)

        if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            error_count += 1
            audit_status_counts["not run"] += 1
            results.append(
                {
                    "input_name": path.name,
                    "status": "error",
                    "error": BATCH_ERROR_UNSUPPORTED_FILE_TYPE,
                }
            )
            continue

        try:
            result = _anonymize_file_result(
                path,
                sensitive_terms=reusable_terms,
                sensitive_terms_path=sensitive_terms_path,
                output_dir=output_dir,
                use_ner=use_ner,
                ner_model_name=ner_model_name,
                use_llm_review=use_llm_review,
                llm_model_name=llm_model_name,
                pdf_redaction_scope=pdf_redaction_scope,
                pdf_output_mode=pdf_output_mode,
            )
        except Exception as error:
            error_count += 1
            audit_status_counts["not run"] += 1
            error_result = {
                "input_name": path.name,
                "status": "error",
                "error": _safe_batch_error_description(error),
            }
            if isinstance(error, OcrUnavailableError):
                error_result["ocr_used"] = False
                error_result["ocr_status"] = error.status
            results.append(
                error_result
            )
            continue

        success_count += 1
        _merge_counters(aggregate_counters, result.counters)
        _merge_audit_status_count(audit_status_counts, result.audit_result)
        _merge_risk_level_count(risk_level_counts, result.audit_result)
        _merge_audit_findings(audit_category_counters, result.audit_result)
        ner_status = str(result.ner_result.get("status", "unavailable"))
        if ner_status not in ner_status_counts:
            ner_status = "unavailable"
        ner_status_counts[ner_status] = ner_status_counts.get(ner_status, 0) + 1
        ner_result_counters = result.ner_result.get("counters", {})
        if isinstance(ner_result_counters, dict):
            for label in NER_LABELS:
                count = ner_result_counters.get(label, 0)
                if isinstance(count, int):
                    ner_category_counters[label] = (
                        ner_category_counters.get(label, 0) + count
                    )
        llm_status = str(result.llm_review_result.get("status", "disabled"))
        if llm_status not in llm_review_status_counts:
            llm_status = "unavailable"
        llm_review_status_counts[llm_status] = (
            llm_review_status_counts.get(llm_status, 0) + 1
        )
        llm_risk_level = str(result.llm_review_result.get("risk_level", "unknown"))
        if llm_risk_level not in llm_review_risk_level_counts:
            llm_risk_level = "unknown"
        llm_review_risk_level_counts[llm_risk_level] = (
            llm_review_risk_level_counts.get(llm_risk_level, 0) + 1
        )
        llm_categories = result.llm_review_result.get("possible_residual_categories", [])
        if isinstance(llm_categories, list):
            for category in llm_categories:
                if category in llm_review_category_counters:
                    llm_review_category_counters[category] = (
                        llm_review_category_counters.get(category, 0) + 1
                    )
        if result.pdf_redaction_result:
            pdf_redaction_status = str(
                result.pdf_redaction_result.get("status", "unavailable")
            )
            if pdf_redaction_status not in pdf_redaction_status_counts:
                pdf_redaction_status = "unavailable"
            pdf_redaction_status_counts[pdf_redaction_status] = (
                pdf_redaction_status_counts.get(pdf_redaction_status, 0) + 1
            )
        dictionary_result = result.audit_result.get("dictionary", {})
        dictionary_status = (
            dictionary_result.get("status")
            if isinstance(dictionary_result, dict)
            else "unknown"
        )
        success_result = {
            "input_name": path.name,
            "status": "success",
            "output_name": result.output_path.name,
            "report_name": result.report_path.name,
            "checklist_name": result.checklist_path.name,
            "audit_status": result.audit_result.get("status", "unknown"),
            "risk_level": result.audit_result.get("risk_level", "unknown"),
            "dictionary_status": dictionary_status,
            "ocr_used": result.ocr_result.get("used", False),
            "ocr_status": result.ocr_result.get("status", "not_used"),
            "ner_used": result.ner_result.get("used", False),
            "ner_status": result.ner_result.get("status", "unavailable"),
            "llm_review_used": result.llm_review_result.get("used", False),
            "llm_review_status": result.llm_review_result.get("status", "disabled"),
            "llm_risk_level": result.llm_review_result.get("risk_level", "unknown"),
        }
        if result.pdf_redaction_result:
            success_result.update(
                {
                    "pdf_redaction_output_created": result.pdf_redaction_result.get(
                        "used", False
                    ),
                    "pdf_redaction_output_name": result.pdf_redaction_result.get(
                        "output_name", ""
                    ),
                    "pdf_redaction_status": result.pdf_redaction_result.get(
                        "status", "unavailable"
                    ),
                    "pdf_redaction_warning": result.pdf_redaction_result.get(
                        "warning", ""
                    ),
                }
            )
        results.append(success_result)

    batch_review_checklist_text = build_batch_review_checklist_text(
        input_count=len(paths),
        success_count=success_count,
        error_count=error_count,
        counters=aggregate_counters,
        results=results,
    )
    batch_review_checklist_path = save_batch_review_checklist_file(
        output_dir,
        text=batch_review_checklist_text,
    )
    summary_path = build_collision_safe_path(build_batch_summary_path(output_dir))
    save_batch_summary_file(
        summary_path,
        input_count=len(paths),
        success_count=success_count,
        error_count=error_count,
        counters=aggregate_counters,
        audit_status_counts=audit_status_counts,
        risk_level_counts=risk_level_counts,
        audit_category_counters=audit_category_counters,
        ner_status_counts=ner_status_counts,
        ner_category_counters=ner_category_counters,
        llm_review_status_counts=llm_review_status_counts,
        llm_review_risk_level_counts=llm_review_risk_level_counts,
        llm_review_category_counters=llm_review_category_counters,
        pdf_redaction_status_counts=pdf_redaction_status_counts,
        results=results,
        category_order=REPORT_CATEGORY_ORDER,
        audit_category_order=AUDIT_CATEGORY_ORDER,
        manual_review_required=True,
        batch_review_checklist_name=batch_review_checklist_path.name,
    )

    return BatchResult(
        summary_path=summary_path,
        input_count=len(paths),
        success_count=success_count,
        error_count=error_count,
        counters=aggregate_counters,
        audit_status_counts=audit_status_counts,
        risk_level_counts=risk_level_counts,
        audit_category_counters=audit_category_counters,
        results=results,
        ner_status_counts=ner_status_counts,
        ner_category_counters=ner_category_counters,
        llm_review_status_counts=llm_review_status_counts,
        llm_review_risk_level_counts=llm_review_risk_level_counts,
        llm_review_category_counters=llm_review_category_counters,
        pdf_redaction_status_counts=pdf_redaction_status_counts,
        review_checklist_path=batch_review_checklist_path,
    )
