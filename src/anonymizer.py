"""Regex-based plain text anonymization engine."""

import bisect
import json
import re
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from pathlib import Path

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
        apply_collision_suffix,
        build_anonymized_image_txt_path,
        build_anonymized_pdf_txt_path,
        build_batch_summary_path,
        build_collision_safe_path,
        build_image_visual_pdf_path,
        build_original_redacted_pdf_path,
        build_pdf_review_path,
        build_pdf_visual_path,
        build_report_path,
        build_shared_collision_suffix,
        internal_artifacts_dir,
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
        extract_image_word_boxes,
        extract_pdf_word_boxes,
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
        save_word_coordinate_redacted_image_copy,
        save_word_coordinate_redacted_pdf_copy,
        word_pages_from_ocr_boxes,
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
        apply_collision_suffix,
        build_anonymized_image_txt_path,
        build_anonymized_pdf_txt_path,
        build_batch_summary_path,
        build_collision_safe_path,
        build_image_visual_pdf_path,
        build_original_redacted_pdf_path,
        build_pdf_review_path,
        build_pdf_visual_path,
        build_report_path,
        build_shared_collision_suffix,
        internal_artifacts_dir,
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
        extract_image_word_boxes,
        extract_pdf_word_boxes,
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
        save_word_coordinate_redacted_image_copy,
        save_word_coordinate_redacted_pdf_copy,
        word_pages_from_ocr_boxes,
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


SUPPORTED_LABELS = (
    "PESEL",
    "EMAIL",
    "TELEFON",
    "DATA",
    "PERSON_NAME_TYPO",
    "ULICA",
    "MIEJSCOWOSC",
    "POSTAL_CODE",
    "NIP",
    "REGON",
    "DOWOD_OSOBISTY",
    "IBAN",
)
REPORT_CATEGORY_ORDER = (*SUPPORTED_LABELS, *NER_LABELS)

# Etap 4: user-facing "pick what to anonymize this run" categories, each
# grouping one or more internal detection labels the user thinks of as
# one thing (e.g. "Adres" covers both the regex-detected street/city/
# postal-code labels and the AI-detected NER_LOCATION spans - a user
# unchecking "Adres" expects *no* address-shaped text left, not just
# the subset a regex happened to catch). Deliberately only 8 - not every
# internal label - per the user's own spec (2026-09-16 conversation,
# revised 2026-09-17 after live testing showed the original NER_ORG/
# NER_LOCATION-always-on split didn't match what a "Dane firmy"/"Adres"
# checkbox actually promises: deselecting everything but PESEL still
# left company names and address fragments redacted). What's left
# uncovered by any group (DOWOD_OSOBISTY, PERSON_NAME_TYPO, NER_MISC) is
# still never user-toggleable and always gets redacted regardless of
# selection - the safe default for anything with no checkbox to attach
# it to, since leaving something *out* of the checklist can only mean
# "always protected", never "silently exposed". DOWOD_OSOBISTY
# specifically must stay always-on even though it looks NIP/REGON-
# adjacent: the audit leftover-scanner's ID_LIKE_NUMBER pattern matches
# NIP/REGON *and* DOWOD_OSOBISTY/PASZPORT-shaped text under one label,
# so folding it into "Dane firmy" would risk hiding a real leftover
# ID-card/passport number alongside the NIP/REGON the user meant to
# exempt (see _AUDIT_ONLY_ADDRESS_LABELS below for the same reasoning
# applied to ULICA/MIEJSCOWOSC/POSTAL_CODE/NER_LOCATION's own
# audit-only counterparts). The dictionary (sensitive_terms.py) and
# RECZNE (magic-pen manual edits) are likewise always-on and outside
# this mechanism entirely - both are the user's own explicit, separate
# choices already.
CATEGORY_PESEL = "pesel"
CATEGORY_PERSON = "person"
CATEGORY_PHONE = "phone"
CATEGORY_EMAIL = "email"
CATEGORY_IBAN = "iban"
CATEGORY_ADDRESS = "address"
CATEGORY_COMPANY = "company"
CATEGORY_DATE = "date"
CATEGORY_GROUPS: dict[str, tuple[str, ...]] = {
    CATEGORY_PESEL: ("PESEL",),
    CATEGORY_PERSON: ("NER_PERSON",),
    CATEGORY_PHONE: ("TELEFON",),
    CATEGORY_EMAIL: ("EMAIL",),
    CATEGORY_IBAN: ("IBAN",),
    CATEGORY_ADDRESS: ("ULICA", "MIEJSCOWOSC", "POSTAL_CODE", "NER_LOCATION"),
    CATEGORY_COMPANY: ("NIP", "REGON", "NER_ORG"),
    CATEGORY_DATE: ("DATA",),
}
ALL_CATEGORIES = tuple(CATEGORY_GROUPS.keys())
_CATEGORY_CONTROLLED_LABELS = frozenset(
    label for labels in CATEGORY_GROUPS.values() for label in labels
)
# Never gated by category selection - see the module comment above.
ALWAYS_ON_LABELS = (
    frozenset(SUPPORTED_LABELS) | frozenset(NER_LABELS)
) - _CATEGORY_CONTROLLED_LABELS


def resolve_active_labels(
    active_categories: Iterable[str] | None,
) -> frozenset[str] | None:
    """Return every internal detection label currently allowed to be
    redacted, given the user's category selection for this task.

    ``None`` means "no filtering" - every caller's behavior before this
    feature existed, and what every existing caller that doesn't pass
    ``active_categories`` still gets. An empty ``active_categories``
    still redacts every always-on label (see ``ALWAYS_ON_LABELS``) - it
    can narrow what the user controls, never remove the categories
    outside their control.
    """
    if active_categories is None:
        return None
    selected = frozenset(
        label
        for category in active_categories
        for label in CATEGORY_GROUPS.get(category, ())
    )
    return ALWAYS_ON_LABELS | selected


CATEGORY_SELECTION_SUFFIX = "_CATEGORY_SELECTION"
CATEGORY_SELECTION_EXTENSION = ".json"


def category_selection_path(output_pdf_path: str | Path) -> Path:
    """Return the sidecar JSON path recording which Etap 4 categories
    were active when this visual PDF/image output was first produced.

    Same hidden internal-artifacts folder and naming convention
    manual_redaction.py's manual_edits_path already uses for a related
    purpose - needed so a later magic-pen manual edit's "regenerate"
    pass (in manual_redaction.py, a separate module this one is never
    allowed to import from - it imports compute_pdf_redaction_spans
    *from here*) can re-detect using the *same* category selection the
    user originally chose, instead of silently falling back to
    redacting everything. Without this, editing an already-anonymized
    document and saving would re-add redactions for categories the user
    had deliberately excluded, changing the approved output out from
    under them.
    """
    path = Path(output_pdf_path)
    internal_dir = internal_artifacts_dir(path.parent)
    return (
        internal_dir
        / f"{path.stem}{CATEGORY_SELECTION_SUFFIX}{CATEGORY_SELECTION_EXTENSION}"
    )


def load_category_selection(path: str | Path) -> frozenset[str] | None:
    """Load the *frozen* set of detection labels that were actually
    active when this visual PDF/image output was first produced, or
    ``None`` if missing/corrupt/never written/written by an older
    version of this app.

    Deliberately not the category *names* the user picked - those are
    only meaningful through CATEGORY_GROUPS's *current* mapping, which
    can itself change between app versions (confirmed: NER_ORG/
    NER_LOCATION moved from always-on into CATEGORY_COMPANY/
    CATEGORY_ADDRESS on 2026-09-17). Re-resolving old category names
    against a *later* mapping would silently change what a magic-pen
    resave of an already-anonymized document redacts, even though the
    user never touched that document's category selection - exactly
    the kind of silent behavior change this sidecar exists to prevent.
    Freezing the resolved label set at save time makes a later mapping
    change never retroactively alter an existing document.

    A sidecar written before this field existed has no ``active_labels``
    key at all, and is treated the same as missing/corrupt: ``None``,
    which resolve_active_labels() treats as "no filtering" - the safe
    direction, since it's not possible to know what an old category
    name meant under a mapping that no longer exists, and redacting
    everything is safer than guessing and redacting less than the
    original output had.
    """
    try:
        raw_text = Path(path).read_text(encoding="utf-8")
        data = json.loads(raw_text)
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict):
        return None
    labels = data.get("active_labels")
    if not labels:
        return None
    if not isinstance(labels, list) or not all(
        isinstance(item, str) for item in labels
    ):
        return None
    return frozenset(labels)


def save_category_selection(
    path: str | Path, active_categories: Iterable[str] | None
) -> Path:
    """Write the category selection sidecar - ``None`` records "no
    filtering" explicitly (as ``null``), the same as never having one
    of the 8 categories deselected. Never raises on a write failure
    (e.g. a read-only folder) - a cosmetic-adjacent app-state file, not
    worth failing the whole anonymization run over; the caller decides
    whether to log/ignore.

    Stores both the category *names* (kept for a possible future "what
    did I pick last time" display - never read back by this app today)
    and the *resolved* label set active right now, at save time - see
    load_category_selection for why the resolved set, not the names, is
    what a later regenerate actually needs.
    """
    destination = Path(path)
    active_categories = (
        list(active_categories) if active_categories is not None else None
    )
    active_labels = resolve_active_labels(active_categories)
    payload = {
        "active_categories": active_categories,
        "active_labels": (
            sorted(active_labels) if active_labels is not None else None
        ),
    }
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return destination


# audit.py's own leftover-risk scanner has a handful of broader,
# audit-only pattern labels with no exact counterpart in
# SUPPORTED_LABELS/NER_LABELS (see its _AUDIT_PATTERNS) - deliberately
# looser catch-alls meant to flag things the real detector might have
# missed. Two of them (ADDRESS_LIKE, STREET_LIKE) are unambiguously
# address-shaped and safe to suppress whenever the user excludes the
# "address" category, same as ULICA/MIEJSCOWOSC/POSTAL_CODE themselves.
# The rest (CASE_REFERENCE, ID_LIKE_NUMBER, INITIAL_SURNAME,
# LONG_NUMBER_SEQUENCE) are deliberately left un-mappable: ID_LIKE_NUMBER
# in particular matches NIP/REGON *and* DOWOD_OSOBISTY/PASZPORT-shaped
# text under one label, and DOWOD_OSOBISTY must never be suppressible via
# the "company" category - excluding it would risk hiding a real leftover
# ID-card/passport number alongside the NIP/REGON the user actually
# meant to exempt. Left as a known, accepted gap rather than a wrong fix.
_AUDIT_ONLY_ADDRESS_LABELS = frozenset({"ADDRESS_LIKE", "STREET_LIKE"})
_ADDRESS_CATEGORY_LABELS = frozenset(CATEGORY_GROUPS[CATEGORY_ADDRESS])


def _excluded_labels_for_audit(
    active_labels: frozenset[str] | None,
) -> frozenset[str] | None:
    """Labels the post-hoc leftover-risk scanner (audit.py) should skip,
    given the resolved active-label set - the complement of
    ``active_labels`` within every label that scan even knows about.
    ``None`` when nothing is being filtered."""
    if active_labels is None:
        return None
    excluded = (frozenset(SUPPORTED_LABELS) | frozenset(NER_LABELS)) - active_labels
    if _ADDRESS_CATEGORY_LABELS & excluded:
        excluded = excluded | _AUDIT_ONLY_ADDRESS_LABELS
    return excluded
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
# The direct "NIP"/"REGON" patterns in _PATTERNS require the label and
# its digits to sit on the same line - confirmed live on a real invoice
# fixture, a common table layout defeats that entirely: every field
# label grouped in one column/block ("NIP", "REGON"), every value
# grouped in another a few lines later ("526-000-12-46", "012345678"),
# leaving both completely undetected despite "Dane firmy" being
# selected. _replace_table_separated_nip_regon below is a fallback pass
# for exactly that shape - see its own docstring for how it pairs a
# label with a value without touching the label text itself (a field
# label is never PII, same principle as _INLINE_WS's own fix earlier
# the same session).
_BARE_NIP_LABEL_PATTERN = re.compile(r"(?<!\w)NIP(?!\w)", re.IGNORECASE)
_BARE_REGON_LABEL_PATTERN = re.compile(r"(?<!\w)REGON(?!\w)", re.IGNORECASE)
_BARE_NIP_VALUE_PATTERN = re.compile(r"(?<!\w)\d(?:[\s-]?\d){9}(?!\w)")
_BARE_REGON_VALUE_PATTERN = re.compile(
    r"(?<!\w)(?:\d(?:[\s-]?\d){13}|\d(?:[\s-]?\d){8})(?!\w)"
)
# How many lines forward of an unmatched label a value can still be
# paired with it - bounds the fallback to "the same table/block", not
# an unrelated number anywhere later in a long document. Kept small and
# close to the actually-observed real-world gap (2 lines, on the
# invoice fixture that prompted this fix: two labels then two values)
# rather than generous - the wider this window, the more exposure to
# an unrelated same-length number (an order ID, a quantity column, a
# bank fragment) sitting between the label and its real value getting
# mispaired instead, which would both over-redact the wrong number
# *and* leave the real NIP/REGON unclaimed and unredacted.
_TABLE_LABEL_VALUE_MAX_LINES_AHEAD = 4


def _line_start_offsets(text: str) -> list[int]:
    """0-based offset each line starts at, for bisect-based line-number
    lookups - shared across both the NIP and REGON calls in the same
    document/page by callers that need more than one, instead of each
    call re-scanning the same text for newlines independently."""
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
    relative order they were written in, the same way a person reading
    the table would. Returns only the *value* spans; the caller never
    touches the label text. ``line_starts`` (see _line_start_offsets)
    is precomputed by the caller so pairing NIP and REGON in the same
    text doesn't rescan it for newlines twice.
    """
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


def _table_separated_nip_regon_pdf_spans(
    text: str, active_labels: frozenset[str] | None
) -> list[tuple[str, int, int]]:
    """Fallback for the table layout _PATTERNS' direct NIP/REGON entries
    can't handle - see the module comment above ``_BARE_NIP_LABEL_PATTERN``.
    Returns ``(label, start, end)`` spans; ``_replace_table_separated_nip_regon``
    below builds on this directly rather than re-walking the same pairing
    logic a second time."""
    results: list[tuple[str, int, int]] = []
    line_starts = _line_start_offsets(text)
    for label_name, label_pattern, value_pattern in (
        ("NIP", _BARE_NIP_LABEL_PATTERN, _BARE_NIP_VALUE_PATTERN),
        ("REGON", _BARE_REGON_LABEL_PATTERN, _BARE_REGON_VALUE_PATTERN),
    ):
        if active_labels is not None and label_name not in active_labels:
            continue
        for start, end in _table_separated_label_value_spans(
            text, label_pattern, value_pattern, line_starts
        ):
            results.append((label_name, start, end))
    return results


def _replace_table_separated_nip_regon(
    text: str, active_labels: frozenset[str] | None
) -> tuple[str, dict[str, int]]:
    """Text-substitution counterpart of _table_separated_nip_regon_pdf_spans,
    for the plain TXT/DOCX path (not word-coordinate PDF, which needs the
    spans themselves to map back to a rectangle rather than a replaced
    string)."""
    replacements = sorted(
        (start, end, label_name)
        for label_name, start, end in _table_separated_nip_regon_pdf_spans(
            text, active_labels
        )
    )
    if not replacements:
        return text, {}

    counters: dict[str, int] = {}
    parts: list[str] = []
    cursor = 0
    for start, end, label_name in replacements:
        parts.append(text[cursor:start])
        parts.append(f"[{label_name}]")
        cursor = end
        counters[label_name] = counters.get(label_name, 0) + 1
    parts.append(text[cursor:])
    return "".join(parts), counters
_UPPER_LETTERS = "A-ZĄĆĘŁŃÓŚŹŻ"
_LOWER_LETTERS = "A-Za-zĄĆĘŁŃÓŚŹŻąćęłńóśźż"
_NAME_TOKEN = rf"[{_UPPER_LETTERS}][{_LOWER_LETTERS}]{{2,}}"
_NAME_HYPHEN = r"[-\u00ad\u2010\u2011\u2012\u2013\u2014]"
# Whitespace that can separate two words *within the same line* (space,
# tab) but never a newline - word_pages_for_redaction_geometry joins each
# extracted PDF line/table row with a single "\n", so this is exactly the
# row/line boundary in this pipeline's own text. A plain \s here would
# happily match that "\n" too, letting a pattern built from multiple
# independent word tokens (a name plus its surname, a city plus a
# trailing word) silently absorb the *next* line's unrelated first word -
# confirmed live on a table document: "Nagy-Kowalski" (a person's surname
# in one table row) matched all the way through to "Adres" (the *next*
# row's field label), redacting a word that was never a name at all.
_INLINE_WS = r"[^\S\n]"
_SURNAME_LIKE_TOKEN = (
    rf"[{_UPPER_LETTERS}][{_LOWER_LETTERS}]{{2,}}"
    r"(?:ski|ska|cki|cka|dzki|dzka|ak|ek|ik|yk|uk|cz|icz|wicz|owicz|ewicz)"
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
        "DOWOD_OSOBISTY",
        re.compile(r"(?<!\w)[A-Z]{3}\d{6}(?!\w)"),
    ),
    (
        "IBAN",
        re.compile(
            r"(?<!\w)PL\s?\d{2}(?:\s?\d{4}){6}(?!\w)",
            re.IGNORECASE,
        ),
    ),
    (
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
    (
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
    (
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
    (
        # Must run before "POSTAL_CODE" below: this pattern's lookbehind
        # needs the raw "dd-ddd " postal code digits still present in the
        # text, and _apply_dictionary_and_regex applies _PATTERNS in order,
        # replacing matches as it goes.
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
    (
        "POSTAL_CODE",
        re.compile(r"(?<!\w)\d{2}-\d{3}(?!\w)"),
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
    *,
    active_labels: frozenset[str] | None = None,
) -> tuple[str, dict[str, int], dict[str, int], dict[str, object]]:
    """Return anonymized text, counters, dictionary counters, and NER metadata."""
    if not isinstance(text, str):
        raise TypeError("text must be a string")

    anonymized, counters, dictionary_counters = _apply_dictionary_and_regex(
        text,
        sensitive_terms=sensitive_terms,
        active_labels=active_labels,
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
            anonymized, ner_context, allowed_labels=active_labels
        )
        _merge_counters(counters, ner_counters)

    return anonymized, counters, dictionary_counters, ner_result


def _apply_dictionary_and_regex(
    text: str,
    sensitive_terms: Iterable[SensitiveTerm] | None = None,
    *,
    active_labels: frozenset[str] | None = None,
) -> tuple[str, dict[str, int], dict[str, int]]:
    """Apply deterministic replacements before optional NER.

    ``active_labels`` (see ``resolve_active_labels``) skips a pattern's
    substitution entirely rather than substituting-then-discarding, so
    excluded values are never touched in the output text at all - not
    just left out of the counters. ``None`` (the default) redacts every
    label, exactly as before this parameter existed. The dictionary pass
    above is never filtered - it is always the user's own explicit,
    separate choice.
    """
    anonymized, counters = apply_sensitive_terms(text, sensitive_terms)
    dictionary_counters = dict(counters)

    for label, pattern in _PATTERNS:
        if active_labels is None or label in active_labels:
            anonymized, count = pattern.subn(f"[{label}]", anonymized)
            if count:
                counters[label] = counters.get(label, 0) + count
        # Right after REGON's own direct (same-line) pattern gets its
        # shot, and *before* TELEFON's turn a few iterations later:
        # TELEFON's own bare "\d{9}" fallback (a deliberately permissive
        # match for a plain Polish mobile number with no separators)
        # would otherwise claim a disconnected 9-digit REGON value
        # first, since REGON's short form is exactly 9 digits too. This
        # only ever sees labels the direct NIP/REGON patterns above
        # didn't already consume (a same-line "NIP: 123..." is long
        # gone by now, untouched), so the existing adjacent-case
        # behavior is unaffected - this purely adds the previously-
        # impossible disconnected case, still ahead of TELEFON in the
        # same "first claim wins" precedence every other _PATTERNS
        # entry relies on. Deliberately checked as a plain `if`, not
        # `continue`d away above when REGON itself is excluded: a real
        # bug code-review caught - selecting only "NIP" (without
        # "REGON") used to skip this whole block, since it only ever
        # ran from the REGON iteration, silently losing table-separated
        # NIP detection too. Currently unreachable through the GUI
        # (CATEGORY_COMPANY always bundles NIP+REGON together) but a
        # real trap for any future caller that splits them.
        if label == "REGON" and (
            active_labels is None
            or "NIP" in active_labels
            or "REGON" in active_labels
        ):
            anonymized, table_counts = _replace_table_separated_nip_regon(
                anonymized, active_labels
            )
            for table_label, table_count in table_counts.items():
                counters[table_label] = counters.get(table_label, 0) + table_count
    if active_labels is None or "TELEFON" in active_labels:
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
    *,
    active_labels: frozenset[str] | None = None,
) -> list[PdfRedactionSpan]:
    """``active_labels`` must be applied *before* a span is added, not
    filtered out of the result afterward - _add_pdf_span reserves
    ``occupied_ranges`` as a side effect, and NER (source="ner") runs
    after this in _pdf_detection_spans_for_word_pages. A category
    excluded here still reserving its range would silently block an
    always-on NER span (e.g. NER_PERSON) that overlaps the same text
    from ever being added, leaving that PII completely unredacted -
    exactly the bug a post-hoc-only filter caused.
    """
    spans: list[PdfRedactionSpan] = []
    for label, pattern in _PATTERNS:
        if active_labels is None or label in active_labels:
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
        # Right after REGON's own direct (same-line) pattern above, and
        # before TELEFON's turn a few iterations later: see
        # _apply_dictionary_and_regex's identical ordering note.
        # _add_pdf_span's own occupied_ranges overlap check means this
        # must run after the direct NIP/REGON patterns' own matches
        # already reserved their ranges, exactly like the text-
        # substitution path - otherwise this fallback would win a
        # same-line "NIP: 123..." case it was never meant to handle,
        # narrowing that redaction box to just the digits and silently
        # blocking the direct pattern's own wider span. Deliberately a
        # plain `if`, not `continue`d away above when REGON itself is
        # excluded - see _apply_dictionary_and_regex's identical note
        # on the real bug that caused.
        if label == "REGON" and (
            active_labels is None
            or "NIP" in active_labels
            or "REGON" in active_labels
        ):
            for table_label, start, end in _table_separated_nip_regon_pdf_spans(
                page_text, active_labels
            ):
                _add_pdf_span(
                    spans,
                    occupied_ranges,
                    label=table_label,
                    page_number=page_number,
                    start=start,
                    end=end,
                    source="regex",
                )
    if active_labels is None or "TELEFON" in active_labels:
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
    *,
    active_labels: frozenset[str] | None = None,
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
        if active_labels is not None and entity.label not in active_labels:
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
    active_labels: frozenset[str] | None = None,
) -> list[PdfRedactionSpan]:
    """Detect spans in dictionary -> regex -> NER order, same as always -
    but with Etap 4's category selection applied *before* each span is
    added, not filtered out of the result afterward. This matters
    because of a real bug a post-hoc-only filter had: _add_pdf_span
    reserves the character range in occupied_ranges as a side effect of
    being *called*, regardless of whether its span survives to the
    return value. An excluded regex label (e.g. ULICA, filtered out
    post-hoc) would still have reserved its range, silently blocking the
    always-on NER span for the same text (e.g. a person's name inside an
    address) from ever being added by the later NER pass -  leaving that
    PII completely unredacted in both categories. Filtering before
    reservation, in every one of the three per-page helpers below,
    closes that gap. Dictionary spans are never filtered - always the
    user's own explicit, separate choice.
    """
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
            _regex_pdf_spans_for_page(
                page.text,
                page.page_number,
                occupied_ranges,
                active_labels=active_labels,
            )
        )
        spans.extend(
            _ner_pdf_spans_for_page(
                page.text,
                page.page_number,
                occupied_ranges,
                ner_context,
                active_labels=active_labels,
            )
        )
    return spans


def word_pages_for_redaction_geometry(source_path: str | Path) -> list:
    """Return the word rectangles a redaction pass can draw boxes onto,
    from whichever source actually has them: a PDF's own text layer, or -
    when it has none, i.e. a scan - word-level OCR of the rendered pages.
    An image source goes straight to OCR.

    This exists because getting that choice wrong silently *removes*
    protection rather than failing loudly. A real, reported bug:
    compute_pdf_redaction_spans used extract_pdf_word_pages alone, so for
    a scanned PDF it found zero words, therefore zero automatic
    detections - and the magic pen's "save" path, which regenerates the
    output from the original through exactly that function, rebuilt the
    file with *only* the user's hand-drawn rectangle on it. Every
    automatically redacted PESEL, name and address came back visible in
    the output the moment someone made one manual edit. The batch
    pipeline had the text-layer-then-OCR fallback; this path never got
    it, and the two drifted apart unnoticed.
    """
    path = Path(source_path)
    if path.suffix.lower() in IMAGE_EXTENSIONS:
        try:
            extraction = extract_image_word_boxes(path)
        except OcrUnavailableError:
            return []
        return word_pages_from_ocr_boxes(extraction.pages)

    word_pages = extract_pdf_word_pages(path)
    if any(page.words for page in word_pages):
        return word_pages
    # No text layer - a scan. Same word-box OCR the batch pipeline falls
    # back to, so both produce identical geometry for the same file.
    try:
        extraction = extract_pdf_word_boxes(path)
    except OcrUnavailableError:
        return word_pages
    return word_pages_from_ocr_boxes(extraction.pages)


def compute_pdf_redaction_spans(
    source_path: str | Path,
    *,
    sensitive_terms: Iterable[SensitiveTerm] | None = None,
    sensitive_terms_path: str | Path | None = None,
    use_ner: bool = False,
    ner_model_name: str = DEFAULT_NER_MODEL,
    active_categories: Iterable[str] | None = None,
    active_labels: frozenset[str] | None = None,
) -> tuple[list, list[PdfRedactionSpan]]:
    """Recompute word pages and detection spans for a source document.

    Reruns the same dictionary/regex/NER detection used by the normal batch
    workflow, without producing any output file. Used to regenerate a
    true-redacted visual PDF (for example after manual "magic pen" edits)
    without re-running the full ``anonymize_batch`` pipeline.

    ``active_labels`` - an already-resolved label set - takes precedence
    when given: this is what the magic-pen "regenerate" path should pass,
    loaded from the document's own category-selection sidecar (see
    category_selection_path/load_category_selection), frozen to the
    label set active when that document was first produced rather than
    resolved fresh against whatever CATEGORY_GROUPS means *today* - a
    later app update can change what a category covers without
    retroactively changing what regenerating an *existing* document
    does. ``active_categories`` (raw category names, resolved fresh via
    resolve_active_labels) is for a live/current selection with no
    prior sidecar to freeze from. ``None`` for both (the default)
    redacts everything, exactly as before either parameter existed.
    """
    terms, _dictionary_status = _prepare_workflow_dictionary(
        sensitive_terms, sensitive_terms_path
    )
    ner_context = prepare_ner_context(enabled=use_ner, model_name=ner_model_name)
    if active_labels is None:
        active_labels = resolve_active_labels(active_categories)
    word_pages = word_pages_for_redaction_geometry(source_path)
    spans = _pdf_detection_spans_for_word_pages(
        word_pages,
        sensitive_terms=terms,
        ner_context=ner_context,
        active_labels=active_labels,
    )
    return word_pages, spans


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
    active_labels: frozenset[str] | None = None,
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
        # A category the user deliberately excluded (Etap 4) isn't a PDF
        # redaction *gap* - the coverage warning below exists to catch
        # cases where redaction unexpectedly failed, not to second-guess
        # an intentional choice already surfaced elsewhere in the report.
        and (active_labels is None or label in active_labels)
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
    active_categories: Iterable[str] | None = None,
) -> FileWorkflowResult:
    """Anonymize a TXT file and return paths needed by batch processing."""
    terms, dictionary_status = _prepare_workflow_dictionary(
        sensitive_terms, sensitive_terms_path
    )
    ner_context = prepare_ner_context(enabled=use_ner, model_name=ner_model_name)
    active_labels = resolve_active_labels(active_categories)
    text = read_txt_file(source_path)
    anonymized, counters, dictionary_counters, ner_result = (
        _anonymize_text_with_dictionary_counters(
            text,
            sensitive_terms=terms,
            ner_context=ner_context,
            active_labels=active_labels,
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
        audit_text(
            anonymized,
            sensitive_terms=terms,
            excluded_labels=_excluded_labels_for_audit(active_labels),
        ),
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
    active_categories: Iterable[str] | None = None,
) -> FileWorkflowResult:
    """Anonymize a DOCX file and return paths needed by batch processing."""
    terms, dictionary_status = _prepare_workflow_dictionary(
        sensitive_terms, sensitive_terms_path
    )
    ner_context = prepare_ner_context(enabled=use_ner, model_name=ner_model_name)
    active_labels = resolve_active_labels(active_categories)
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
            active_labels=active_labels,
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
            text, sensitive_terms=terms, active_labels=active_labels
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
        audit_text(
            anonymized_text,
            sensitive_terms=terms,
            excluded_labels=_excluded_labels_for_audit(active_labels),
        ),
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
    active_categories: Iterable[str] | None = None,
) -> FileWorkflowResult:
    """Anonymize a PDF file and return paths needed by batch processing."""
    terms, dictionary_status = _prepare_workflow_dictionary(
        sensitive_terms, sensitive_terms_path
    )
    ner_context = prepare_ner_context(enabled=use_ner, model_name=ner_model_name)
    active_labels = resolve_active_labels(active_categories)
    text_based_pdf = False
    word_pages = []
    ocr_word_pages: list = []
    word_box_fallback_reason: str | None = None
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
        # Try OCR *with* word-level positions first - it produces the same
        # text a plain OCR pass would (see word_pages_from_ocr_boxes), plus
        # the coordinates needed for true colored visual redaction on a
        # scanned page instead of only ever falling back to a rebuilt
        # plain-text document. Falls back to the original plain-text-only
        # OCR path unchanged when word-level OCR itself is unavailable
        # (e.g. no Tesseract) - never a second, redundant OCR pass either
        # way.
        try:
            word_box_extraction = extract_pdf_word_boxes(source_path)
            ocr_word_pages = word_pages_from_ocr_boxes(word_box_extraction.pages)
            text = PDF_PAGE_SEPARATOR.join(page.text for page in ocr_word_pages)
            ocr_result = word_box_extraction.metadata
        except OcrUnavailableError as word_box_error:
            # Recorded (status code only - no paths, no OCR text) so a
            # scan that silently fell back to the old placeholder-text
            # style, rather than getting colored visual redaction, is
            # actually diagnosable afterwards from the developer report
            # instead of only ever guessed at - this exact gap made a
            # real user report ("skan znowu nie ma kolorami anonimizacji")
            # impossible to root-cause without the original file.
            word_box_fallback_reason = word_box_error.status
            extraction = extract_text_with_ocr(source_path)
            text = extraction.text
            ocr_result = extraction.metadata
        source_page_texts = []
        pdf_redaction_result = build_pdf_redaction_skipped_ocr_metadata()
    active_word_pages = word_pages if text_based_pdf else ocr_word_pages
    pdf_detection_spans = (
        _pdf_detection_spans_for_word_pages(
            active_word_pages,
            sensitive_terms=terms,
            ner_context=ner_context,
            active_labels=active_labels,
        )
        if active_word_pages
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
        active_labels=active_labels,
    )
    normalized_pdf_scope = _normalize_pdf_redaction_scope(pdf_redaction_scope)
    scope_ner_labels = _pdf_ner_allowed_labels_for_scope(normalized_pdf_scope)
    if active_labels is not None:
        # The "original_redaction" text-search fallback path's NER terms
        # must respect Etap 4's category selection too, same as every
        # other redaction path - intersect rather than replace, so the
        # existing safe/strict scope restriction still applies on top.
        scope_ner_labels = tuple(
            label for label in scope_ner_labels if label in active_labels
        )
    pdf_ner_redaction_terms, pdf_ner_skipped_categories = _pdf_ner_redaction_plan(
        pre_ner_text,
        ner_context,
        allowed_labels=scope_ner_labels,
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
            allowed_labels=active_labels,
        )
        _merge_counters(counters, ner_counters)

    normalized_pdf_output_mode = _normalize_pdf_output_mode(pdf_output_mode)
    # ocr_word_pages joins its page texts with the same PDF_PAGE_SEPARATOR
    # a real text layer uses (see above) - passing 0 here like the old
    # OCR-without-coordinates path did would leave those raw separator
    # markers embedded as literal text in the saved TXT output instead of
    # splitting them back into real pages.
    if text_based_pdf:
        page_count_for_split = len(source_page_texts)
    elif ocr_word_pages:
        page_count_for_split = len(ocr_word_pages)
    else:
        page_count_for_split = 0
    anonymized_pages = _split_anonymized_pdf_pages(anonymized, page_count_for_split)
    anonymized_output_text = "\n\n".join(anonymized_pages)

    # One number for every companion file this run writes, instead of each
    # writer picking its own. review.preferred_review_output_path - how the
    # comparison window decides what to show - looks for the visual PDF
    # whose number matches the TXT's; numbering them independently let
    # those drift apart permanently the moment one run produced a
    # different set of files than another (e.g. a run from before visual
    # output existed, or one where the visual step failed). From then on
    # the lookup missed and every later run silently showed the rebuilt
    # text PDF instead of the colored one - a real, reproduced bug behind
    # a repeated "the scan lost its colors again" report.
    pdf_output_suffix = build_shared_collision_suffix(
        [
            build_anonymized_pdf_txt_path(source_path, output_dir=output_dir),
            build_pdf_visual_path(source_path, output_dir=output_dir),
            build_pdf_review_path(source_path, output_dir=output_dir),
            build_original_redacted_pdf_path(source_path, output_dir=output_dir),
        ]
    )
    pdf_txt_output_path = apply_collision_suffix(
        build_anonymized_pdf_txt_path(source_path, output_dir=output_dir),
        pdf_output_suffix,
    )
    pdf_visual_output_path = apply_collision_suffix(
        build_pdf_visual_path(source_path, output_dir=output_dir), pdf_output_suffix
    )
    pdf_review_output_path = apply_collision_suffix(
        build_pdf_review_path(source_path, output_dir=output_dir), pdf_output_suffix
    )
    pdf_original_redacted_output_path = apply_collision_suffix(
        build_original_redacted_pdf_path(source_path, output_dir=output_dir),
        pdf_output_suffix,
    )

    if normalized_pdf_output_mode == PDF_OUTPUT_MODE_VISUAL and active_word_pages:
        text_extraction_label = "text_layer" if text_based_pdf else "ocr_word_coordinates"
        try:
            pdf_redaction_result = save_word_coordinate_redacted_pdf_copy(
                source_path,
                word_pages=active_word_pages,
                spans=pdf_detection_spans,
                output_path=pdf_visual_output_path,
            )
            pdf_redaction_result["text_extraction"] = text_extraction_label
            try:
                save_category_selection(
                    category_selection_path(pdf_visual_output_path),
                    active_categories,
                )
            except OSError:
                # Cosmetic-adjacent app state, not the anonymization
                # itself - see save_category_selection's docstring.
                pass
        except Exception as visual_redaction_error:  # noqa: BLE001
            # Deliberately broad, not just RuntimeError: this step draws
            # on PyMuPDF internals (page.apply_redactions(), a malformed
            # rect, ...) that can fail in ways this project does not
            # control the exception type of. A failure here must never
            # take down the whole file - the plain-text-anonymized
            # output a few lines below, and the rebuilt review PDF right
            # after this block, both still work independently; only the
            # colored-box presentation is lost, not the anonymization
            # itself. Recorded as the exception's class name only (never
            # str(error), which could echo a path or other detail back)
            # so a real occurrence is finally diagnosable from the
            # developer report instead of only ever guessed at - this
            # exact gap made a real, repeated user report impossible to
            # root-cause without the original file.
            pdf_redaction_result = build_pdf_redaction_metadata(status="unavailable")
            pdf_redaction_result["text_extraction"] = text_extraction_label
            pdf_redaction_result["visual_redaction_fallback_reason"] = type(
                visual_redaction_error
            ).__name__
        try:
            review_pdf_result = save_rebuilt_review_pdf_from_text(
                source_path,
                anonymized_output_text,
                page_texts=anonymized_pages if text_based_pdf else None,
                output_path=pdf_review_output_path,
                text_extraction=text_extraction_label,
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
                output_path=pdf_review_output_path,
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
                output_path=pdf_original_redacted_output_path,
                active_labels=active_labels,
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
                    output_path=pdf_review_output_path,
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
    if word_box_fallback_reason is not None:
        # Status-code only (see OcrUnavailableError) - lets a developer
        # report distinguish *why* a scan fell back to the old
        # placeholder-text style instead of colored visual redaction,
        # instead of that being unanswerable after the fact. setdefault,
        # not a plain assignment: active_word_pages is empty whenever
        # this is set (word-box OCR itself failed), so the visual-mode
        # branch above never runs and never sets its own reason for the
        # same file in practice - but if that assumption ever changes,
        # the earlier, more specific reason should win rather than be
        # silently overwritten.
        pdf_redaction_result.setdefault(
            "visual_redaction_fallback_reason", word_box_fallback_reason
        )
    output_path = save_anonymized_pdf_txt_copy(
        source_path, anonymized_output_text, output_path=pdf_txt_output_path
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
        audit_text(
            anonymized_output_text,
            sensitive_terms=terms,
            excluded_labels=_excluded_labels_for_audit(active_labels),
        ),
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
        active_labels=active_labels,
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
    active_categories: Iterable[str] | None = None,
) -> FileWorkflowResult:
    """Anonymize OCR text from an image and return paths for batch processing."""
    terms, dictionary_status = _prepare_workflow_dictionary(
        sensitive_terms, sensitive_terms_path
    )
    ner_context = prepare_ner_context(enabled=use_ner, model_name=ner_model_name)
    active_labels = resolve_active_labels(active_categories)
    # Try OCR *with* word-level positions first - same reasoning as the PDF
    # path: it produces the same text a plain OCR pass would, plus the
    # coordinates needed for a true colored-redaction visual PDF alongside
    # the existing plain-text output, in one OCR pass rather than two.
    # Falls back to the original plain-text-only OCR path unchanged when
    # word-level OCR itself is unavailable.
    ocr_word_pages: list = []
    try:
        word_box_extraction = extract_image_word_boxes(source_path)
        ocr_word_pages = word_pages_from_ocr_boxes(word_box_extraction.pages)
        ocr_text = ocr_word_pages[0].text if ocr_word_pages else ""
        ocr_metadata = word_box_extraction.metadata
    except OcrUnavailableError:
        extraction = extract_text_with_ocr(source_path)
        ocr_text = extraction.text
        ocr_metadata = extraction.metadata

    anonymized, counters, dictionary_counters, ner_result = (
        _anonymize_text_with_dictionary_counters(
            ocr_text,
            sensitive_terms=terms,
            ner_context=ner_context,
            active_labels=active_labels,
        )
    )
    # Same shared-number rule the PDF path above follows, for the same
    # reason: the comparison window finds an image's visual PDF by the
    # TXT's number, so the two must never drift apart.
    image_output_suffix = build_shared_collision_suffix(
        [
            build_anonymized_image_txt_path(source_path, output_dir=output_dir),
            build_image_visual_pdf_path(source_path, output_dir=output_dir),
        ]
    )
    output_path = save_anonymized_image_txt_copy(
        source_path,
        anonymized,
        output_path=apply_collision_suffix(
            build_anonymized_image_txt_path(source_path, output_dir=output_dir),
            image_output_suffix,
        ),
    )

    pdf_redaction_result: dict[str, object] = {}
    if ocr_word_pages:
        image_detection_spans = _pdf_detection_spans_for_word_pages(
            ocr_word_pages,
            sensitive_terms=terms,
            ner_context=ner_context,
            active_labels=active_labels,
        )
        image_visual_output_path = apply_collision_suffix(
            build_image_visual_pdf_path(source_path, output_dir=output_dir),
            image_output_suffix,
        )
        try:
            pdf_redaction_result = save_word_coordinate_redacted_image_copy(
                source_path,
                word_pages=ocr_word_pages,
                spans=image_detection_spans,
                output_path=image_visual_output_path,
            )
            pdf_redaction_result["text_extraction"] = "ocr_word_coordinates"
            try:
                save_category_selection(
                    category_selection_path(image_visual_output_path),
                    active_categories,
                )
            except OSError:
                pass
        except RuntimeError:
            pdf_redaction_result = build_pdf_redaction_metadata(status="unavailable")
            pdf_redaction_result["text_extraction"] = "ocr_word_coordinates"

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
        audit_text(
            anonymized,
            sensitive_terms=terms,
            excluded_labels=_excluded_labels_for_audit(active_labels),
        ),
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
        ocr_metadata,
        ner_result,
        llm_review_result,
        anonymized,
        pdf_redaction_result=pdf_redaction_result,
        output_dir=output_dir,
    )
    report_path = _save_anonymization_report(
        source_path,
        output_path,
        counters,
        audit_result,
        dictionary_result,
        ocr_metadata,
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
        ocr_metadata,
        ner_result,
        llm_review_result,
        pdf_redaction_result,
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
    active_categories: Iterable[str] | None = None,
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
            active_categories=active_categories,
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
            active_categories=active_categories,
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
            active_categories=active_categories,
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
            active_categories=active_categories,
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
    active_categories: Iterable[str] | None = None,
    progress_callback: Callable[[int, int, Path], None] | None = None,
) -> BatchResult:
    """Anonymize supported files sequentially into one output workspace.

    ``active_categories`` (Etap 4) restricts redaction, for every file in
    this batch, to the given user-facing categories (see
    ``CATEGORY_GROUPS`` - "Adres"/"Dane firmy" each cover both their
    regex-detected fields and their AI-detected NER_LOCATION/NER_ORG
    counterpart) plus everything never under the user's control
    (``ALWAYS_ON_LABELS``: the dictionary, DOWOD_OSOBISTY,
    PERSON_NAME_TYPO, NER_MISC) - those are always redacted regardless.
    ``None`` (the default) redacts everything, exactly as before this
    parameter existed.
    """
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
                active_categories=active_categories,
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
