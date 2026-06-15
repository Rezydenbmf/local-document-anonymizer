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
BATCH_ERROR_PROCESSING_FAILED = "file processing failed"
BATCH_ERROR_DESCRIPTIONS = (
    BATCH_ERROR_UNSUPPORTED_FILE_TYPE,
    BATCH_ERROR_EMPTY_TEXT_PDF,
    BATCH_ERROR_TEXT_DECODING,
    BATCH_ERROR_FILE_IO,
    BATCH_ERROR_MISSING_DEPENDENCY,
    BATCH_ERROR_PROCESSING_FAILED,
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
        "Possible remaining sensitive patterns:",
    ]
    if non_zero_categories:
        for label, count in non_zero_categories:
            lines.append(f"* {label}: {count}")
    else:
        lines.append("* none: 0")

    manual_review_text = "yes" if manual_review_required else "no"
    lines.append(f"Manual review required: {manual_review_text}")
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
    category_order: Iterable[str] | None = None,
    status: str = "completed",
    manual_review_required: bool = True,
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

    lines.extend(["", "Files:"])
    for result in results:
        file_status = str(result.get("status", "error"))
        input_name = _safe_filename(result.get("input_name", "unknown"))
        lines.append(f"* input: {input_name}")
        lines.append(f"  status: {file_status}")
        if file_status == "success":
            lines.append(f"  output: {_safe_filename(result.get('output_name', 'unknown'))}")
            lines.append(f"  report: {_safe_filename(result.get('report_name', 'unknown'))}")
            lines.append(f"  audit status: {result.get('audit_status', 'unknown')}")
        else:
            lines.append(f"  error: {_safe_batch_error(result.get('error', ''))}")
            lines.append("  output: not created")
            lines.append("  report: not created")

    lines.extend(
        [
            "",
            "Original sensitive values stored: no",
            "Replacement map created: no",
            "Source paths stored: no",
            "Dictionary aliases stored: no",
            "Dictionary private terms stored: no",
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
    category_order: Iterable[str] | None = None,
    status: str = "completed",
    manual_review_required: bool = True,
) -> Path:
    """Save a safe batch summary report and return its path."""
    path = Path(summary_path)
    report_text = build_batch_summary_text(
        input_count=input_count,
        success_count=success_count,
        error_count=error_count,
        counters=counters,
        audit_status_counts=audit_status_counts,
        results=results,
        category_order=category_order,
        status=status,
        manual_review_required=manual_review_required,
    )
    path.write_text(report_text, encoding="utf-8")
    return path
