"""Regex-based plain text anonymization engine."""

from collections.abc import Iterable
from pathlib import Path
import re

from audit import AUDIT_CATEGORY_ORDER, audit_text
from file_readers import (
    DOCX_EXTENSION,
    PDF_EXTENSION,
    SUPPORTED_EXTENSIONS,
    TXT_EXTENSION,
    read_docx_file,
    read_pdf_file,
    read_txt_file,
)
from file_writers import (
    build_report_path,
    save_anonymized_docx_copy,
    save_anonymized_pdf_txt_copy,
    save_anonymized_txt_copy,
)
from report import save_report_file
from sensitive_terms import SensitiveTerm, apply_sensitive_terms


SUPPORTED_LABELS = ("PESEL", "EMAIL", "TELEFON", "DATA")

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
                (?:\+48|0048)[ -]?\d{3}[ -]?\d{3}[ -]?\d{3}
                |
                \d{3}[- ]\d{3}[- ]\d{3}
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
)


def anonymize_text(
    text: str, sensitive_terms: Iterable[SensitiveTerm] | None = None
) -> tuple[str, dict[str, int]]:
    """Replace high-confidence sensitive values with category placeholders."""
    if not isinstance(text, str):
        raise TypeError("text must be a string")

    anonymized, counters = apply_sensitive_terms(text, sensitive_terms)

    for label, pattern in _PATTERNS:
        anonymized, count = pattern.subn(f"[{label}]", anonymized)
        if count:
            counters[label] = counters.get(label, 0) + count

    return anonymized, counters


def _reusable_sensitive_terms(
    sensitive_terms: Iterable[SensitiveTerm] | None,
) -> list[SensitiveTerm] | None:
    if sensitive_terms is None:
        return None
    return list(sensitive_terms)


def anonymize_txt_file(
    source_path: str | Path,
    sensitive_terms: Iterable[SensitiveTerm] | None = None,
) -> tuple[Path, dict[str, int]]:
    """Anonymize a TXT file and save output plus a safe report."""
    output_path, counters, _ = anonymize_txt_file_with_audit(
        source_path, sensitive_terms=sensitive_terms
    )
    return output_path, counters


def anonymize_txt_file_with_audit(
    source_path: str | Path,
    sensitive_terms: Iterable[SensitiveTerm] | None = None,
) -> tuple[Path, dict[str, int], dict[str, object]]:
    """Anonymize a TXT file and return safe audit metadata."""
    terms = _reusable_sensitive_terms(sensitive_terms)
    text = read_txt_file(source_path)
    anonymized, counters = anonymize_text(text, sensitive_terms=terms)
    output_path = save_anonymized_txt_copy(source_path, anonymized)
    audit_result = audit_text(anonymized, sensitive_terms=terms)
    _save_anonymization_report(source_path, output_path, counters, audit_result)
    return output_path, counters, audit_result


def anonymize_docx_file(
    source_path: str | Path,
    sensitive_terms: Iterable[SensitiveTerm] | None = None,
) -> tuple[Path, dict[str, int]]:
    """Anonymize a DOCX file and save output plus a safe report."""
    output_path, counters, _ = anonymize_docx_file_with_audit(
        source_path, sensitive_terms=sensitive_terms
    )
    return output_path, counters


def anonymize_docx_file_with_audit(
    source_path: str | Path,
    sensitive_terms: Iterable[SensitiveTerm] | None = None,
) -> tuple[Path, dict[str, int], dict[str, object]]:
    """Anonymize a DOCX file and return safe audit metadata."""
    terms = _reusable_sensitive_terms(sensitive_terms)

    def anonymize_docx_text(text: str) -> tuple[str, dict[str, int]]:
        return anonymize_text(text, sensitive_terms=terms)

    output_path, counters = save_anonymized_docx_copy(
        source_path, anonymize_docx_text
    )
    anonymized_text = read_docx_file(output_path)
    audit_result = audit_text(anonymized_text, sensitive_terms=terms)
    _save_anonymization_report(source_path, output_path, counters, audit_result)
    return output_path, counters, audit_result


def anonymize_pdf_file(
    source_path: str | Path,
    sensitive_terms: Iterable[SensitiveTerm] | None = None,
) -> tuple[Path, dict[str, int]]:
    """Anonymize text from a PDF and save TXT output plus a safe report."""
    output_path, counters, _ = anonymize_pdf_file_with_audit(
        source_path, sensitive_terms=sensitive_terms
    )
    return output_path, counters


def anonymize_pdf_file_with_audit(
    source_path: str | Path,
    sensitive_terms: Iterable[SensitiveTerm] | None = None,
) -> tuple[Path, dict[str, int], dict[str, object]]:
    """Anonymize text from a PDF and return safe audit metadata."""
    terms = _reusable_sensitive_terms(sensitive_terms)
    text = read_pdf_file(source_path)
    anonymized, counters = anonymize_text(text, sensitive_terms=terms)
    output_path = save_anonymized_pdf_txt_copy(source_path, anonymized)
    audit_result = audit_text(anonymized, sensitive_terms=terms)
    _save_anonymization_report(source_path, output_path, counters, audit_result)
    return output_path, counters, audit_result


def _save_anonymization_report(
    source_path: str | Path,
    output_path: str | Path,
    counters: dict[str, int],
    audit_result: dict[str, object],
) -> Path:
    source = Path(source_path)
    output = Path(output_path)
    report_path = build_report_path(source)
    return save_report_file(
        report_path,
        counters=counters,
        input_extension=source.suffix,
        output_extension=output.suffix,
        category_order=SUPPORTED_LABELS,
        audit_result=audit_result,
        audit_category_order=AUDIT_CATEGORY_ORDER,
    )


def anonymize_file(
    source_path: str | Path,
    sensitive_terms: Iterable[SensitiveTerm] | None = None,
) -> tuple[Path, dict[str, int]]:
    """Anonymize one supported application file using existing workflows."""
    output_path, counters, _ = anonymize_file_with_audit(
        source_path, sensitive_terms=sensitive_terms
    )
    return output_path, counters


def anonymize_file_with_audit(
    source_path: str | Path,
    sensitive_terms: Iterable[SensitiveTerm] | None = None,
) -> tuple[Path, dict[str, int], dict[str, object]]:
    """Anonymize one supported file and return safe audit metadata."""
    path = Path(source_path)

    if path.suffix.lower() == TXT_EXTENSION:
        return anonymize_txt_file_with_audit(path, sensitive_terms=sensitive_terms)
    if path.suffix.lower() == DOCX_EXTENSION:
        return anonymize_docx_file_with_audit(path, sensitive_terms=sensitive_terms)
    if path.suffix.lower() == PDF_EXTENSION:
        return anonymize_pdf_file_with_audit(path, sensitive_terms=sensitive_terms)

    suffix = path.suffix.lower() or "<none>"
    supported = ", ".join(SUPPORTED_EXTENSIONS)
    raise ValueError(
        f"Unsupported file extension for anonymize_file: {suffix}. "
        f"Only {supported} files are supported."
    )
