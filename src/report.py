"""Safe anonymization report generation."""

from collections.abc import Iterable, Mapping
from pathlib import Path, PurePosixPath, PureWindowsPath


DICTIONARY_STATUS_NOT_SELECTED = "not selected"
DICTIONARY_STATUS_LOADED = "loaded"
DICTIONARY_STATUS_INVALID = "invalid"
DICTIONARY_STATUSES = (
    DICTIONARY_STATUS_NOT_SELECTED,
    DICTIONARY_STATUS_LOADED,
    DICTIONARY_STATUS_INVALID,
)
BATCH_ERROR_UNSUPPORTED_FILE_TYPE = "unsupported file type"
BATCH_ERROR_EMPTY_TEXT_PDF = "PDF has no extractable text"
BATCH_ERROR_TEXT_DECODING = "TXT file could not be decoded as UTF-8"
BATCH_ERROR_FILE_IO = "file could not be read or written"
BATCH_ERROR_MISSING_DEPENDENCY = "required local document dependency is unavailable"
BATCH_ERROR_OCR_UNAVAILABLE = "OCR unavailable for image-based input"
BATCH_ERROR_OCR_FAILED = "OCR failed for image-based input"
BATCH_ERROR_PROCESSING_FAILED = "file processing failed"
BATCH_ERROR_DESCRIPTIONS = (
    BATCH_ERROR_UNSUPPORTED_FILE_TYPE,
    BATCH_ERROR_EMPTY_TEXT_PDF,
    BATCH_ERROR_TEXT_DECODING,
    BATCH_ERROR_FILE_IO,
    BATCH_ERROR_MISSING_DEPENDENCY,
    BATCH_ERROR_OCR_UNAVAILABLE,
    BATCH_ERROR_OCR_FAILED,
    BATCH_ERROR_PROCESSING_FAILED,
)
RISK_LEVEL_OK = "ok"
RISK_LEVEL_WARNING = "warning"
RISK_LEVEL_HIGH = "high_risk"
RISK_LEVELS = (
    RISK_LEVEL_OK,
    RISK_LEVEL_WARNING,
    RISK_LEVEL_HIGH,
)
OCR_STATUSES = (
    "available",
    "unavailable",
    "dependency_missing",
    "engine_not_found",
    "unsupported_input",
    "not_used",
)
OCR_INPUT_TYPES = ("image", "pdf", "none")
OCR_WARNING_TEXTS = (
    "",
    "local OCR dependency is missing",
    "local OCR engine not found",
    "input type is not supported for OCR",
    "OCR completed but no text was extracted",
    "OCR failed safely",
)
NER_STATUSES = (
    "available",
    "unavailable",
    "dependency_missing",
    "model_missing",
    "disabled",
    "processing_error",
)
NER_LABELS = (
    "NER_PERSON",
    "NER_ORG",
    "NER_LOCATION",
    "NER_MISC",
)
NER_WARNING_TEXTS = (
    "",
    "local NER dependency is missing",
    "local NER model is missing",
    "local NER model could not be loaded",
    "local NER processing failed safely",
)
LLM_REVIEW_STATUSES = (
    "disabled",
    "available",
    "unavailable",
    "ollama_not_found",
    "service_unavailable",
    "no_model_configured",
    "model_missing",
    "timeout",
    "invalid_response",
    "processing_error",
    "completed",
)
LLM_RISK_LEVELS = (
    "ok",
    "warning",
    "high_risk",
    "unknown",
)
LLM_RESIDUAL_CATEGORIES = (
    "PERSON_LIKE",
    "ORGANIZATION_LIKE",
    "LOCATION_LIKE",
    "ADDRESS_CONTEXT",
    "CASE_REFERENCE_LIKE",
    "CONTACT_DATA_LIKE",
    "OTHER_SENSITIVE_CONTEXT",
)
LLM_WARNING_TEXTS = (
    "",
    "local Ollama command not found",
    "local Ollama check timed out",
    "local Ollama service unavailable",
    "local Ollama model list unavailable",
    "configured local Ollama model is missing",
    "local LLM review timed out",
    "local LLM review failed safely",
)
LLM_ATTEMPTED_FAILURE_STATUSES = (
    "timeout",
    "invalid_response",
    "processing_error",
)
LLM_SKIPPED_OR_UNAVAILABLE_STATUSES = (
    "disabled",
    "unavailable",
    "ollama_not_found",
    "service_unavailable",
    "no_model_configured",
    "model_missing",
)
PDF_REDACTION_STATUSES = (
    "completed",
    "completed_with_warnings",
    "no_matches",
    "skipped_ocr",
    "unavailable",
)
PDF_REDACTION_SCOPES = ("safe", "strict")
PDF_REVIEW_TYPES = ("rebuilt_from_anonymized_text", "none")
PDF_TEXT_EXTRACTION_TYPES = ("text_layer", "ocr_fallback", "ocr_forced", "")
PDF_REDACTION_COLOR_LEGEND = (
    (
        "red",
        "PESEL, NIP, REGON, ID card numbers, IBAN, postal codes, and other "
        "strong identifiers",
    ),
    ("orange", "phone numbers and conservative person-name typo matches"),
    ("blue", "email and electronic identifiers"),
    ("gray", "dates"),
    ("purple", "organizations"),
    (
        "green",
        "locations, including a town/city name next to a postal code and a "
        "street name after ul./al./pl.",
    ),
)


def _safe_file_type(value: str) -> str:
    text = str(value).strip()
    if not text:
        return "UNKNOWN"

    suffix = text if text.startswith(".") else Path(text).suffix
    label = (suffix or text).lstrip(".").upper()
    return label or "UNKNOWN"


def _ordered_categories(
    counters: Mapping[str, int], category_order: Iterable[str] | None
) -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()

    if category_order is not None:
        for label in category_order:
            if label not in seen:
                ordered.append(label)
                seen.add(label)

    for label in sorted(counters):
        if label not in seen:
            ordered.append(label)
            seen.add(label)

    return ordered


def _validate_count(value: int) -> None:
    if not isinstance(value, int):
        raise TypeError("counter values must be integers")
    if value < 0:
        raise ValueError("counter values must not be negative")


def _safe_filename(value: object) -> str:
    text = str(value).strip()
    if not text:
        return "unknown"

    windows_name = PureWindowsPath(text).name
    return PurePosixPath(windows_name).name or "unknown"


def _safe_batch_error(value: object) -> str:
    text = str(value).strip()
    if text in BATCH_ERROR_DESCRIPTIONS:
        return text
    return BATCH_ERROR_PROCESSING_FAILED


def _safe_risk_level(value: object, fallback_status: object = None) -> str:
    risk_level = str(value).strip()
    if risk_level in RISK_LEVELS:
        return risk_level
    if fallback_status == "ok":
        return RISK_LEVEL_OK
    return RISK_LEVEL_WARNING


def _safe_ocr_status(value: object) -> str:
    status = str(value).strip()
    if status in OCR_STATUSES:
        return status
    return "unavailable"


def _safe_ocr_input_type(value: object) -> str:
    input_type = str(value).strip()
    if input_type in OCR_INPUT_TYPES:
        return input_type
    return "none"


def _safe_ocr_warning(value: object) -> str:
    warning = str(value or "").strip()
    if warning in OCR_WARNING_TEXTS:
        return warning
    return "OCR failed safely" if warning else ""


def _safe_ner_status(value: object) -> str:
    status = str(value).strip()
    if status in NER_STATUSES:
        return status
    return "unavailable"


def _safe_ner_model_name(value: object) -> str:
    text = str(value or "").strip()
    if not text:
        return "unknown"
    if text.replace("_", "").replace(".", "").replace("-", "").isalnum():
        return text
    return "local_model"


def _safe_ner_warning(value: object) -> str:
    warning = str(value or "").strip()
    if warning in NER_WARNING_TEXTS:
        return warning
    return "local NER processing failed safely" if warning else ""


def _safe_llm_review_status(value: object) -> str:
    status = str(value).strip()
    if status in LLM_REVIEW_STATUSES:
        return status
    return "unavailable"


def _safe_llm_model_name(value: object) -> str:
    text = str(value or "").strip()
    if not text:
        return "not configured"
    normalized = (
        text.replace("_", "")
        .replace(".", "")
        .replace("-", "")
        .replace(":", "")
        .replace("/", "")
    )
    if normalized.isalnum():
        return text
    return "local_model"


def _safe_llm_risk_level(value: object) -> str:
    risk_level = str(value).strip()
    if risk_level in LLM_RISK_LEVELS:
        return risk_level
    return "unknown"


def _safe_llm_warning(value: object) -> str:
    warning = str(value or "").strip()
    if warning in LLM_WARNING_TEXTS:
        return warning
    return "local LLM review failed safely" if warning else ""


def _safe_pdf_redaction_status(value: object) -> str:
    status = str(value).strip()
    if status in PDF_REDACTION_STATUSES:
        return status
    return "unavailable"


def _safe_pdf_redaction_output_name(value: object) -> str:
    if value in (None, ""):
        return "not created"
    return _safe_filename(value)


def _safe_pdf_redaction_scope(value: object) -> str:
    scope = str(value or "").strip().lower()
    if scope in PDF_REDACTION_SCOPES:
        return scope
    return "safe"


def _safe_pdf_review_type(value: object) -> str:
    review_type = str(value or "").strip()
    if review_type in PDF_REVIEW_TYPES:
        return review_type
    return "none"


def _safe_pdf_text_extraction(value: object) -> str:
    extraction = str(value or "").strip()
    if extraction in PDF_TEXT_EXTRACTION_TYPES:
        return extraction or "unknown"
    return "unknown"


def _review_checklist_section_lines(
    checklist_result: Mapping[str, object] | None,
) -> list[str]:
    created = bool(checklist_result and checklist_result.get("created", False))
    output_name = (
        _safe_filename(checklist_result.get("output_name", "not created"))
        if checklist_result
        else "not created"
    )
    return [
        "",
        "Review checklist:",
        f"Review checklist created: {'yes' if created else 'no'}",
        f"Review checklist output: {output_name if created else 'not created'}",
    ]


def _append_counter_lines(
    lines: list[str],
    title: str,
    counters: Mapping[str, int],
) -> None:
    lines.append(title)
    if counters:
        for label in sorted(counters):
            count = counters.get(label, 0)
            _validate_count(count)
            lines.append(f"* {label}: {count}")
    else:
        lines.append("* none: 0")


def _pdf_redaction_section_lines(
    pdf_redaction_result: Mapping[str, object] | None,
) -> list[str]:
    if pdf_redaction_result is None:
        return []

    used = bool(pdf_redaction_result.get("used", False))
    status = _safe_pdf_redaction_status(pdf_redaction_result.get("status"))
    output_name = _safe_pdf_redaction_output_name(
        pdf_redaction_result.get("output_name", "")
    )
    redaction_count = pdf_redaction_result.get("redaction_count", 0)
    _validate_count(redaction_count)
    true_redaction = bool(pdf_redaction_result.get("true_redaction", False))
    visual_pdf_created = bool(pdf_redaction_result.get("visual_pdf_created", False))
    visual_pdf_name = _safe_pdf_redaction_output_name(
        pdf_redaction_result.get("visual_pdf_name", "")
    )
    visual_pdf_type = str(pdf_redaction_result.get("visual_pdf_type", "none")).strip()
    visual_redaction_mode = str(
        pdf_redaction_result.get("visual_redaction_mode", "")
    ).strip()
    review_pdf_created = bool(pdf_redaction_result.get("review_pdf_created", False))
    review_pdf_name = _safe_pdf_redaction_output_name(
        pdf_redaction_result.get("review_pdf_name", "")
    )
    review_pdf_type = _safe_pdf_review_type(
        pdf_redaction_result.get("review_pdf_type", "none")
    )
    text_extraction = _safe_pdf_text_extraction(
        pdf_redaction_result.get("text_extraction", "")
    )
    original_layout_redaction_used = bool(
        pdf_redaction_result.get("original_layout_redaction_used", False)
    )
    original_layout_redaction_experimental = bool(
        pdf_redaction_result.get("original_layout_redaction_experimental", False)
    )
    raw_counters = pdf_redaction_result.get("counters", {})
    if not isinstance(raw_counters, Mapping):
        raise TypeError("PDF redaction counters must be a mapping")
    warning = str(pdf_redaction_result.get("warning", "")).strip()
    safe_scope_note = str(pdf_redaction_result.get("safe_scope_note", "")).strip()
    strict_scope_warning = str(
        pdf_redaction_result.get("strict_scope_warning", "")
    ).strip()
    scope = _safe_pdf_redaction_scope(pdf_redaction_result.get("scope", "safe"))
    detected_categories = pdf_redaction_result.get("detected_categories", {})
    txt_anonymized_categories = pdf_redaction_result.get(
        "txt_anonymized_categories", {}
    )
    pdf_redacted_categories = pdf_redaction_result.get(
        "pdf_redacted_categories",
        raw_counters,
    )
    not_redacted_categories = pdf_redaction_result.get(
        "detected_not_pdf_redacted_categories",
        {},
    )
    ner_safe_scope_skipped_categories = pdf_redaction_result.get(
        "ner_safe_scope_skipped_categories",
        {},
    )
    unmapped_categories = pdf_redaction_result.get("unmapped_categories", {})
    weak_phone_like_skipped = pdf_redaction_result.get("weak_phone_like_skipped", 0)
    _validate_count(weak_phone_like_skipped)
    for label, value in (
        ("PDF detected categories", detected_categories),
        ("TXT anonymized categories", txt_anonymized_categories),
        ("PDF redacted categories", pdf_redacted_categories),
        ("Detected but not PDF-redacted categories", not_redacted_categories),
        ("Unmapped PDF detections", unmapped_categories),
        ("NER categories not PDF-redacted by current PDF scope", ner_safe_scope_skipped_categories),
    ):
        if not isinstance(value, Mapping):
            raise TypeError(f"{label} must be a mapping")

    lines = [
        "",
        "PDF redaction:",
        f"PDF text extraction used: {text_extraction}",
        f"Visual PDF created: {'yes' if visual_pdf_created else 'no'}",
        f"Visual PDF type: {visual_pdf_type or 'none'}",
        f"Visual PDF output: {visual_pdf_name}",
        f"Redaction mapping: {visual_redaction_mode or 'none'}",
        f"Review PDF created: {'yes' if review_pdf_created else 'no'}",
        f"Review PDF type: {review_pdf_type}",
        f"Review PDF output: {review_pdf_name}",
        "Layout-preserving original redaction used: "
        f"{'yes' if original_layout_redaction_used else 'no'}",
        "Layout-preserving original redaction experimental: "
        f"{'yes' if original_layout_redaction_experimental else 'no'}",
        f"PDF redaction output created: {'yes' if used else 'no'}",
        f"PDF redaction status: {status}",
        f"PDF redaction scope: {scope}",
        f"PDF redaction output: {output_name}",
        f"PDF true redaction used: {'yes' if true_redaction else 'no'}",
        f"PDF redaction blocks: {redaction_count}",
        f"Weak phone-like numeric values skipped: {weak_phone_like_skipped}",
        "PDF redaction color legend:",
    ]
    for color, meaning in PDF_REDACTION_COLOR_LEGEND:
        lines.append(f"* {color}: {meaning}")
    if scope == "safe":
        if visual_redaction_mode == "word_coordinates":
            lines.append(
                "PDF safe scope rule: word-coordinate visual redaction maps detected "
                "full-word spans only; unmapped spans are reported by category."
            )
        else:
            lines.append(
                "PDF safe scope rule: NER_PERSON uses conservative exact-span "
                "redaction; broad NER_ORG, NER_LOCATION, and NER_MISC are not "
                "PDF-redacted by default."
            )

    _append_counter_lines(lines, "PDF detected categories:", detected_categories)
    _append_counter_lines(
        lines,
        "TXT anonymized categories:",
        txt_anonymized_categories,
    )
    _append_counter_lines(lines, "PDF redacted categories:", pdf_redacted_categories)
    _append_counter_lines(
        lines,
        "Detected but not PDF-redacted categories:",
        not_redacted_categories,
    )
    _append_counter_lines(
        lines,
        "NER categories not PDF-redacted by current PDF scope:",
        ner_safe_scope_skipped_categories,
    )
    _append_counter_lines(lines, "Unmapped PDF detections:", unmapped_categories)
    lines.append("PDF redaction categories:")
    if raw_counters:
        for label in sorted(raw_counters):
            count = raw_counters.get(label, 0)
            _validate_count(count)
            lines.append(f"* {label}: {count}")
    else:
        lines.append("* none: 0")
    if warning:
        lines.append(f"PDF redaction warning: {warning}")
    if safe_scope_note:
        lines.append(f"PDF safe scope note: {safe_scope_note}")
    if strict_scope_warning:
        lines.append(f"PDF strict scope warning: {strict_scope_warning}")
    if original_layout_redaction_experimental:
        lines.append(
            "PDF original-layout redaction warning: experimental; may under-redact "
            "or over-redact."
        )
    if review_pdf_created and review_pdf_type == "rebuilt_from_anonymized_text":
        lines.append(
            "Review PDF note: rebuilt from anonymized text and not layout-preserving."
        )
        lines.append(
            "Review PDF table-heavy note: for table-heavy or multi-column PDFs, "
            "use the review checklist and original document during manual review."
        )

    return lines


def _ocr_section_lines(ocr_result: Mapping[str, object] | None) -> list[str]:
    if ocr_result is None:
        return []

    used = bool(ocr_result.get("used", False))
    status = _safe_ocr_status(ocr_result.get("status"))
    input_type = _safe_ocr_input_type(ocr_result.get("input_type"))
    items_processed = ocr_result.get("items_processed", 0)
    _validate_count(items_processed)
    warning = _safe_ocr_warning(ocr_result.get("warning", ""))

    lines = [
        "",
        "OCR:",
        f"OCR used: {'yes' if used else 'no'}",
        f"OCR status: {status}",
        f"OCR input type: {input_type}",
        f"OCR pages/images processed: {items_processed}",
    ]
    if warning:
        lines.append(f"OCR warning: {warning}")

    return lines


def _ner_section_lines(ner_result: Mapping[str, object] | None) -> list[str]:
    if ner_result is None:
        return []

    enabled = bool(ner_result.get("enabled", False))
    used = bool(ner_result.get("used", False))
    status = _safe_ner_status(ner_result.get("status"))
    model_name = _safe_ner_model_name(ner_result.get("model_name"))
    warning = _safe_ner_warning(ner_result.get("warning", ""))
    raw_counters = ner_result.get("counters", {})
    if not isinstance(raw_counters, Mapping):
        raise TypeError("NER counters must be a mapping")
    raw_exclusion_counters = ner_result.get("exclusion_counters", {})
    if not isinstance(raw_exclusion_counters, Mapping):
        raise TypeError("NER exclusion counters must be a mapping")
    linebreak_person_candidates = ner_result.get("linebreak_person_candidates", 0)
    _validate_count(linebreak_person_candidates)

    lines = [
        "",
        "Local NER:",
        f"NER enabled: {'yes' if enabled else 'no'}",
        f"NER used: {'yes' if used else 'no'}",
        f"NER status: {status}",
        f"NER model: {model_name}",
        "NER categories:",
    ]

    has_counter = False
    for label in NER_LABELS:
        count = raw_counters.get(label, 0)
        _validate_count(count)
        lines.append(f"* {label}: {count}")
        if count:
            has_counter = True

    if not has_counter and not NER_LABELS:
        lines.append("* none: 0")
    if warning:
        lines.append(f"NER warning: {warning}")
    lines.append("NER/PDF exclusions applied:")
    has_exclusion_counter = False
    for label in sorted(raw_exclusion_counters):
        count = raw_exclusion_counters.get(label, 0)
        _validate_count(count)
        lines.append(f"* {label}: {count}")
        if count:
            has_exclusion_counter = True
    if not raw_exclusion_counters:
        lines.append("* none: 0")
    lines.append(
        f"NER line-break person candidates handled: {linebreak_person_candidates}"
    )

    return lines


def _llm_review_section_lines(
    llm_review_result: Mapping[str, object] | None,
) -> list[str]:
    if llm_review_result is None:
        return []

    used = bool(llm_review_result.get("used", False))
    status = _safe_llm_review_status(llm_review_result.get("status"))
    model_name = _safe_llm_model_name(llm_review_result.get("model_name"))
    risk_level = _safe_llm_risk_level(llm_review_result.get("risk_level"))
    manual_review_required = bool(
        llm_review_result.get("manual_review_required", True)
    )
    warning = _safe_llm_warning(llm_review_result.get("warning", ""))
    raw_categories = llm_review_result.get("possible_residual_categories", [])
    if not isinstance(raw_categories, list):
        raise TypeError("LLM residual categories must be a list")

    categories = [
        category for category in raw_categories if category in LLM_RESIDUAL_CATEGORIES
    ]
    lines = [
        "",
        "Local LLM review:",
        f"LLM review used: {'yes' if used else 'no'}",
        f"LLM review status: {status}",
        f"LLM model: {model_name}",
        f"LLM risk level: {risk_level}",
        "Possible residual categories:",
    ]
    if categories:
        for category in LLM_RESIDUAL_CATEGORIES:
            if category in categories:
                lines.append(f"* {category}")
    else:
        lines.append("* none")
    lines.append(
        f"LLM manual review required: {'yes' if manual_review_required else 'no'}"
    )
    if warning:
        lines.append(f"LLM warning: {warning}")

    return lines


def _audit_section_lines(
    audit_result: Mapping[str, object] | None,
    audit_category_order: Iterable[str] | None,
) -> list[str]:
    if audit_result is None:
        return []

    status = audit_result.get("status")
    if status not in ("ok", "warning"):
        raise ValueError("audit status must be ok or warning")

    findings = audit_result.get("findings")
    if not isinstance(findings, Mapping):
        raise TypeError("audit findings must be a mapping")

    manual_review_required = audit_result.get("manual_review_required")
    if not isinstance(manual_review_required, bool):
        raise TypeError("audit manual_review_required must be a boolean")

    risk_level = _safe_risk_level(audit_result.get("risk_level"), status)
    categories = _ordered_categories(findings, audit_category_order)
    non_zero_categories: list[tuple[str, int]] = []
    for label in categories:
        count = findings.get(label, 0)
        _validate_count(count)
        if count:
            non_zero_categories.append((label, count))

    lines = [
        "",
        "Post-anonymization audit:",
        f"Status: {status}",
        f"Risk level: {risk_level}",
        "Possible remaining sensitive patterns:",
    ]
    if non_zero_categories:
        for label, count in non_zero_categories:
            lines.append(f"* {label}: {count}")
    else:
        lines.append("* none: 0")

    return lines


def _dictionary_section_lines(
    dictionary_result: Mapping[str, object] | None,
) -> list[str]:
    if dictionary_result is None:
        status = DICTIONARY_STATUS_NOT_SELECTED
        label_counters: Mapping[str, int] = {}
    else:
        status = dictionary_result.get("status")
        if status not in DICTIONARY_STATUSES:
            raise ValueError(
                "dictionary status must be not selected, loaded, or invalid"
            )

        raw_label_counters = dictionary_result.get("label_counters", {})
        if not isinstance(raw_label_counters, Mapping):
            raise TypeError("dictionary label_counters must be a mapping")
        label_counters = raw_label_counters

    dictionary_used = status == DICTIONARY_STATUS_LOADED
    has_label_match = False
    for count in label_counters.values():
        _validate_count(count)
        if count:
            has_label_match = True
    matches_found = dictionary_used and has_label_match

    lines = [
        "",
        "Dictionary:",
        f"Dictionary used: {'yes' if dictionary_used else 'no'}",
        f"Dictionary status: {status}",
        f"Dictionary matches found: {'yes' if matches_found else 'no'}",
        "Dictionary labels:",
    ]

    if label_counters:
        for label in sorted(label_counters):
            count = label_counters[label]
            lines.append(f"* {label}: {count}")
    else:
        lines.append("* none: 0")

    return lines


def build_report_text(
    *,
    counters: Mapping[str, int],
    input_extension: str,
    output_extension: str,
    status: str = "completed",
    category_order: Iterable[str] | None = None,
    audit_result: Mapping[str, object] | None = None,
    audit_category_order: Iterable[str] | None = None,
    dictionary_result: Mapping[str, object] | None = None,
    ocr_result: Mapping[str, object] | None = None,
    ner_result: Mapping[str, object] | None = None,
    llm_review_result: Mapping[str, object] | None = None,
    pdf_redaction_result: Mapping[str, object] | None = None,
    checklist_result: Mapping[str, object] | None = None,
) -> str:
    """Build a safe text report without source values or replacement maps."""
    if not isinstance(status, str):
        raise TypeError("status must be a string")

    lines = [
        "Anonymization report",
        "",
        f"Status: {status}",
        f"Input type: {_safe_file_type(input_extension)}",
        f"Output type: {_safe_file_type(output_extension)}",
        "",
        "Detected categories:",
    ]

    categories = _ordered_categories(counters, category_order)
    if categories:
        for label in categories:
            count = counters.get(label, 0)
            _validate_count(count)
            lines.append(f"* {label}: {count}")
    else:
        lines.append("* none: 0")

    lines.extend(_dictionary_section_lines(dictionary_result))
    lines.extend(_ocr_section_lines(ocr_result))
    lines.extend(_ner_section_lines(ner_result))
    lines.extend(_llm_review_section_lines(llm_review_result))
    lines.extend(_pdf_redaction_section_lines(pdf_redaction_result))
    lines.extend(_review_checklist_section_lines(checklist_result))
    lines.extend(_audit_section_lines(audit_result, audit_category_order))

    lines.extend(
        [
            "",
            "Manual review required: yes",
            "Original sensitive values stored: no",
            "Replacement map created: no",
        ]
    )
    return "\n".join(lines) + "\n"


def save_report_file(
    report_path: str | Path,
    *,
    counters: Mapping[str, int],
    input_extension: str,
    output_extension: str,
    status: str = "completed",
    category_order: Iterable[str] | None = None,
    audit_result: Mapping[str, object] | None = None,
    audit_category_order: Iterable[str] | None = None,
    dictionary_result: Mapping[str, object] | None = None,
    ocr_result: Mapping[str, object] | None = None,
    ner_result: Mapping[str, object] | None = None,
    llm_review_result: Mapping[str, object] | None = None,
    pdf_redaction_result: Mapping[str, object] | None = None,
    checklist_result: Mapping[str, object] | None = None,
) -> Path:
    """Save a safe anonymization report and return the report path."""
    path = Path(report_path)
    report_text = build_report_text(
        counters=counters,
        input_extension=input_extension,
        output_extension=output_extension,
        status=status,
        category_order=category_order,
        audit_result=audit_result,
        audit_category_order=audit_category_order,
        dictionary_result=dictionary_result,
        ocr_result=ocr_result,
        ner_result=ner_result,
        llm_review_result=llm_review_result,
        pdf_redaction_result=pdf_redaction_result,
        checklist_result=checklist_result,
    )
    path.write_text(report_text, encoding="utf-8")
    return path


def build_batch_summary_text(
    *,
    input_count: int,
    success_count: int,
    error_count: int,
    counters: Mapping[str, int],
    audit_status_counts: Mapping[str, int],
    results: Iterable[Mapping[str, object]],
    risk_level_counts: Mapping[str, int] | None = None,
    audit_category_counters: Mapping[str, int] | None = None,
    ner_status_counts: Mapping[str, int] | None = None,
    ner_category_counters: Mapping[str, int] | None = None,
    llm_review_status_counts: Mapping[str, int] | None = None,
    llm_review_risk_level_counts: Mapping[str, int] | None = None,
    llm_review_category_counters: Mapping[str, int] | None = None,
    pdf_redaction_status_counts: Mapping[str, int] | None = None,
    category_order: Iterable[str] | None = None,
    audit_category_order: Iterable[str] | None = None,
    status: str = "completed",
    manual_review_required: bool = True,
    batch_review_checklist_name: str | None = None,
) -> str:
    """Build a safe batch report without paths, source values, or aliases."""
    for count in (input_count, success_count, error_count):
        _validate_count(count)
    if success_count + error_count != input_count:
        raise ValueError("success_count plus error_count must equal input_count")
    if not isinstance(manual_review_required, bool):
        raise TypeError("manual_review_required must be a boolean")

    manual_review_text = "yes" if manual_review_required else "no"
    lines = [
        "Batch summary report",
        "",
        f"Status: {status}",
        f"Input files: {input_count}",
        f"Successful files: {success_count}",
        f"Errors: {error_count}",
        f"Manual review required: {manual_review_text}",
        f"Batch review checklist: {_safe_filename(batch_review_checklist_name) if batch_review_checklist_name else 'not created'}",
        "",
        "Detected categories:",
    ]

    categories = _ordered_categories(counters, category_order)
    if categories:
        for label in categories:
            count = counters.get(label, 0)
            _validate_count(count)
            lines.append(f"* {label}: {count}")
    else:
        lines.append("* none: 0")

    lines.extend(["", "Audit statuses:"])
    for audit_status in ("ok", "warning", "not run"):
        count = audit_status_counts.get(audit_status, 0)
        _validate_count(count)
        lines.append(f"* {audit_status}: {count}")

    lines.extend(["", "Risk levels:"])
    risk_counts = risk_level_counts or {}
    for risk_level in RISK_LEVELS:
        count = risk_counts.get(risk_level, 0)
        _validate_count(count)
        lines.append(f"* {risk_level}: {count}")

    lines.extend(["", "Audit warning categories:"])
    audit_counters = audit_category_counters or {}
    audit_categories = _ordered_categories(audit_counters, audit_category_order)
    non_zero_audit_categories: list[tuple[str, int]] = []
    for label in audit_categories:
        count = audit_counters.get(label, 0)
        _validate_count(count)
        if count:
            non_zero_audit_categories.append((label, count))
    if non_zero_audit_categories:
        for label, count in non_zero_audit_categories:
            lines.append(f"* {label}: {count}")
    else:
        lines.append("* none: 0")

    ocr_used_count = 0
    ocr_unavailable_or_failed_count = 0
    materialized_results = list(results)
    for result in materialized_results:
        if result.get("ocr_used") is True:
            ocr_used_count += 1
        ocr_status = _safe_ocr_status(result.get("ocr_status", "not_used"))
        if ocr_status in ("dependency_missing", "engine_not_found", "unavailable"):
            ocr_unavailable_or_failed_count += 1

    lines.extend(
        [
            "",
            "OCR:",
            f"* files processed with OCR: {ocr_used_count}",
            f"* OCR unavailable or failed: {ocr_unavailable_or_failed_count}",
        ]
    )

    ner_used_count = 0
    ner_unavailable_or_disabled_count = 0
    for result in materialized_results:
        if result.get("ner_used") is True:
            ner_used_count += 1
        ner_status = _safe_ner_status(result.get("ner_status", "disabled"))
        if ner_status in (
            "dependency_missing",
            "model_missing",
            "disabled",
            "unavailable",
            "processing_error",
        ):
            ner_unavailable_or_disabled_count += 1

    lines.extend(
        [
            "",
            "Local NER:",
            f"* files processed with NER: {ner_used_count}",
            f"* NER unavailable or disabled: {ner_unavailable_or_disabled_count}",
            "NER statuses:",
        ]
    )
    status_counts = ner_status_counts or {}
    for status_name in NER_STATUSES:
        count = status_counts.get(status_name, 0)
        _validate_count(count)
        lines.append(f"* {status_name}: {count}")

    lines.append("NER categories:")
    category_counts = ner_category_counters or {}
    for label in NER_LABELS:
        count = category_counts.get(label, 0)
        _validate_count(count)
        lines.append(f"* {label}: {count}")

    llm_attempted_count = 0
    llm_attempt_failed_count = 0
    llm_unavailable_or_disabled_count = 0
    for result in materialized_results:
        llm_status = _safe_llm_review_status(
            result.get("llm_review_status", "disabled")
        )
        if llm_status == "completed" or llm_status in LLM_ATTEMPTED_FAILURE_STATUSES:
            llm_attempted_count += 1
        if llm_status in LLM_ATTEMPTED_FAILURE_STATUSES:
            llm_attempt_failed_count += 1
        if llm_status in LLM_SKIPPED_OR_UNAVAILABLE_STATUSES:
            llm_unavailable_or_disabled_count += 1

    lines.extend(
        [
            "",
            "Local LLM review:",
            f"* LLM review attempts: {llm_attempted_count}",
            f"* LLM attempted but failed safely: {llm_attempt_failed_count}",
            f"* LLM unavailable, disabled, or skipped: {llm_unavailable_or_disabled_count}",
            "LLM review statuses:",
        ]
    )
    llm_status_counts = llm_review_status_counts or {}
    for status_name in LLM_REVIEW_STATUSES:
        count = llm_status_counts.get(status_name, 0)
        _validate_count(count)
        lines.append(f"* {status_name}: {count}")

    lines.append("LLM risk levels:")
    llm_risk_counts = llm_review_risk_level_counts or {}
    for risk_level in LLM_RISK_LEVELS:
        count = llm_risk_counts.get(risk_level, 0)
        _validate_count(count)
        lines.append(f"* {risk_level}: {count}")

    lines.append("LLM residual categories:")
    llm_category_counts = llm_review_category_counters or {}
    has_llm_category = False
    for category in LLM_RESIDUAL_CATEGORIES:
        count = llm_category_counts.get(category, 0)
        _validate_count(count)
        if count:
            has_llm_category = True
        lines.append(f"* {category}: {count}")
    if not has_llm_category and not LLM_RESIDUAL_CATEGORIES:
        lines.append("* none: 0")

    pdf_redaction_created_count = 0
    pdf_redaction_skipped_count = 0
    for result in materialized_results:
        pdf_redaction_status = _safe_pdf_redaction_status(
            result.get("pdf_redaction_status", "unavailable")
        )
        if result.get("pdf_redaction_output_created") is True:
            pdf_redaction_created_count += 1
        if pdf_redaction_status in ("skipped_ocr", "unavailable"):
            pdf_redaction_skipped_count += 1

    lines.extend(
        [
            "",
            "PDF redaction:",
            f"* PDF redaction outputs created: {pdf_redaction_created_count}",
            f"* PDF redaction skipped or unavailable: {pdf_redaction_skipped_count}",
            "PDF redaction statuses:",
        ]
    )
    pdf_redaction_counts = pdf_redaction_status_counts or {}
    for status_name in PDF_REDACTION_STATUSES:
        count = pdf_redaction_counts.get(status_name, 0)
        _validate_count(count)
        lines.append(f"* {status_name}: {count}")

    lines.extend(["", "Files:"])
    for result in materialized_results:
        file_status = str(result.get("status", "error"))
        input_name = _safe_filename(result.get("input_name", "unknown"))
        lines.append(f"* input: {input_name}")
        lines.append(f"  status: {file_status}")
        if file_status == "success":
            lines.append(f"  output: {_safe_filename(result.get('output_name', 'unknown'))}")
            lines.append(f"  report: {_safe_filename(result.get('report_name', 'unknown'))}")
            lines.append(
                f"  checklist: {_safe_filename(result.get('checklist_name', 'unknown'))}"
            )
            lines.append(f"  audit status: {result.get('audit_status', 'unknown')}")
            lines.append(
                f"  risk level: "
                f"{_safe_risk_level(result.get('risk_level'), result.get('audit_status'))}"
            )
        else:
            lines.append(f"  error: {_safe_batch_error(result.get('error', ''))}")
            lines.append("  output: not created")
            lines.append("  report: not created")
            lines.append("  checklist: not created")
        if "ocr_status" in result:
            lines.append(f"  OCR used: {'yes' if result.get('ocr_used') is True else 'no'}")
            lines.append(f"  OCR status: {_safe_ocr_status(result.get('ocr_status'))}")
        if "ner_status" in result:
            lines.append(f"  NER used: {'yes' if result.get('ner_used') is True else 'no'}")
            lines.append(f"  NER status: {_safe_ner_status(result.get('ner_status'))}")
        if "llm_review_status" in result:
            lines.append(
                f"  LLM review used: "
                f"{'yes' if result.get('llm_review_used') is True else 'no'}"
            )
            lines.append(
                f"  LLM review status: "
                f"{_safe_llm_review_status(result.get('llm_review_status'))}"
            )
            lines.append(
                f"  LLM risk level: "
                f"{_safe_llm_risk_level(result.get('llm_risk_level'))}"
            )
        if "pdf_redaction_status" in result:
            lines.append(
                f"  PDF redaction output: "
                f"{_safe_pdf_redaction_output_name(result.get('pdf_redaction_output_name'))}"
            )
            lines.append(
                f"  PDF redaction status: "
                f"{_safe_pdf_redaction_status(result.get('pdf_redaction_status'))}"
            )
            pdf_redaction_warning = str(
                result.get("pdf_redaction_warning", "")
            ).strip()
            if pdf_redaction_warning:
                lines.append(f"  PDF redaction warning: {pdf_redaction_warning}")

    lines.extend(
        [
            "",
            "Original sensitive values stored: no",
            "Replacement map created: no",
            "Source paths stored: no",
            "Dictionary aliases stored: no",
            "Dictionary private terms stored: no",
            "LLM prompts stored: no",
            "Raw LLM responses stored: no",
            "Document snippets stored: no",
        ]
    )
    return "\n".join(lines) + "\n"


def save_batch_summary_file(
    summary_path: str | Path,
    *,
    input_count: int,
    success_count: int,
    error_count: int,
    counters: Mapping[str, int],
    audit_status_counts: Mapping[str, int],
    results: Iterable[Mapping[str, object]],
    risk_level_counts: Mapping[str, int] | None = None,
    audit_category_counters: Mapping[str, int] | None = None,
    ner_status_counts: Mapping[str, int] | None = None,
    ner_category_counters: Mapping[str, int] | None = None,
    llm_review_status_counts: Mapping[str, int] | None = None,
    llm_review_risk_level_counts: Mapping[str, int] | None = None,
    llm_review_category_counters: Mapping[str, int] | None = None,
    pdf_redaction_status_counts: Mapping[str, int] | None = None,
    category_order: Iterable[str] | None = None,
    audit_category_order: Iterable[str] | None = None,
    status: str = "completed",
    manual_review_required: bool = True,
    batch_review_checklist_name: str | None = None,
) -> Path:
    """Save a safe batch summary report and return its path."""
    path = Path(summary_path)
    report_text = build_batch_summary_text(
        input_count=input_count,
        success_count=success_count,
        error_count=error_count,
        counters=counters,
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
        category_order=category_order,
        audit_category_order=audit_category_order,
        status=status,
        manual_review_required=manual_review_required,
        batch_review_checklist_name=batch_review_checklist_name,
    )
    path.write_text(report_text, encoding="utf-8")
    return path
