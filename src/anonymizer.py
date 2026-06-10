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
from report import (
    DICTIONARY_STATUS_INVALID,
    DICTIONARY_STATUS_LOADED,
    DICTIONARY_STATUS_NOT_SELECTED,
    save_report_file,
)
from sensitive_terms import SensitiveTerm, apply_sensitive_terms, load_sensitive_terms


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
    anonymized, counters, _ = _anonymize_text_with_dictionary_counters(
        text, sensitive_terms=sensitive_terms
    )
    return anonymized, counters


def _anonymize_text_with_dictionary_counters(
    text: str, sensitive_terms: Iterable[SensitiveTerm] | None = None
) -> tuple[str, dict[str, int], dict[str, int]]:
    """Return anonymized text, all counters, and dictionary-label counters."""
    if not isinstance(text, str):
        raise TypeError("text must be a string")

    anonymized, counters = apply_sensitive_terms(text, sensitive_terms)
    dictionary_counters = dict(counters)

    for label, pattern in _PATTERNS:
        anonymized, count = pattern.subn(f"[{label}]", anonymized)
        if count:
            counters[label] = counters.get(label, 0) + count

    return anonymized, counters, dictionary_counters


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


def _merge_counters(target: dict[str, int], source: dict[str, int]) -> None:
    for label, count in source.items():
        target[label] = target.get(label, 0) + count


def anonymize_txt_file(
    source_path: str | Path,
    sensitive_terms: Iterable[SensitiveTerm] | None = None,
    sensitive_terms_path: str | Path | None = None,
) -> tuple[Path, dict[str, int]]:
    """Anonymize a TXT file and save output plus a safe report."""
    output_path, counters, _ = anonymize_txt_file_with_audit(
        source_path,
        sensitive_terms=sensitive_terms,
        sensitive_terms_path=sensitive_terms_path,
    )
    return output_path, counters


def anonymize_txt_file_with_audit(
    source_path: str | Path,
    sensitive_terms: Iterable[SensitiveTerm] | None = None,
    sensitive_terms_path: str | Path | None = None,
) -> tuple[Path, dict[str, int], dict[str, object]]:
    """Anonymize a TXT file and return safe audit metadata."""
    terms, dictionary_status = _prepare_workflow_dictionary(
        sensitive_terms, sensitive_terms_path
    )
    text = read_txt_file(source_path)
    anonymized, counters, dictionary_counters = (
        _anonymize_text_with_dictionary_counters(text, sensitive_terms=terms)
    )
    output_path = save_anonymized_txt_copy(source_path, anonymized)
    dictionary_result = _dictionary_result(
        status=dictionary_status,
        sensitive_terms=terms,
        label_counters=dictionary_counters,
    )
    audit_result = _attach_dictionary_result(
        audit_text(anonymized, sensitive_terms=terms),
        dictionary_result,
    )
    _save_anonymization_report(
        source_path, output_path, counters, audit_result, dictionary_result
    )
    return output_path, counters, audit_result


def anonymize_docx_file(
    source_path: str | Path,
    sensitive_terms: Iterable[SensitiveTerm] | None = None,
    sensitive_terms_path: str | Path | None = None,
) -> tuple[Path, dict[str, int]]:
    """Anonymize a DOCX file and save output plus a safe report."""
    output_path, counters, _ = anonymize_docx_file_with_audit(
        source_path,
        sensitive_terms=sensitive_terms,
        sensitive_terms_path=sensitive_terms_path,
    )
    return output_path, counters


def anonymize_docx_file_with_audit(
    source_path: str | Path,
    sensitive_terms: Iterable[SensitiveTerm] | None = None,
    sensitive_terms_path: str | Path | None = None,
) -> tuple[Path, dict[str, int], dict[str, object]]:
    """Anonymize a DOCX file and return safe audit metadata."""
    terms, dictionary_status = _prepare_workflow_dictionary(
        sensitive_terms, sensitive_terms_path
    )
    dictionary_counters: dict[str, int] = {}

    def anonymize_docx_text(text: str) -> tuple[str, dict[str, int]]:
        anonymized, counters, paragraph_dictionary_counters = (
            _anonymize_text_with_dictionary_counters(text, sensitive_terms=terms)
        )
        _merge_counters(dictionary_counters, paragraph_dictionary_counters)
        return anonymized, counters

    def anonymize_docx_run(text: str) -> tuple[str, dict[str, int]]:
        anonymized, counters, _ = _anonymize_text_with_dictionary_counters(
            text, sensitive_terms=terms
        )
        return anonymized, counters

    output_path, counters = save_anonymized_docx_copy(
        source_path,
        anonymize_docx_text,
        anonymize_run=anonymize_docx_run,
    )
    anonymized_text = read_docx_file(output_path)
    dictionary_result = _dictionary_result(
        status=dictionary_status,
        sensitive_terms=terms,
        label_counters=dictionary_counters,
    )
    audit_result = _attach_dictionary_result(
        audit_text(anonymized_text, sensitive_terms=terms),
        dictionary_result,
    )
    _save_anonymization_report(
        source_path, output_path, counters, audit_result, dictionary_result
    )
    return output_path, counters, audit_result


def anonymize_pdf_file(
    source_path: str | Path,
    sensitive_terms: Iterable[SensitiveTerm] | None = None,
    sensitive_terms_path: str | Path | None = None,
) -> tuple[Path, dict[str, int]]:
    """Anonymize text from a PDF and save TXT output plus a safe report."""
    output_path, counters, _ = anonymize_pdf_file_with_audit(
        source_path,
        sensitive_terms=sensitive_terms,
        sensitive_terms_path=sensitive_terms_path,
    )
    return output_path, counters


def anonymize_pdf_file_with_audit(
    source_path: str | Path,
    sensitive_terms: Iterable[SensitiveTerm] | None = None,
    sensitive_terms_path: str | Path | None = None,
) -> tuple[Path, dict[str, int], dict[str, object]]:
    """Anonymize text from a PDF and return safe audit metadata."""
    terms, dictionary_status = _prepare_workflow_dictionary(
        sensitive_terms, sensitive_terms_path
    )
    text = read_pdf_file(source_path)
    anonymized, counters, dictionary_counters = (
        _anonymize_text_with_dictionary_counters(text, sensitive_terms=terms)
    )
    output_path = save_anonymized_pdf_txt_copy(source_path, anonymized)
    dictionary_result = _dictionary_result(
        status=dictionary_status,
        sensitive_terms=terms,
        label_counters=dictionary_counters,
    )
    audit_result = _attach_dictionary_result(
        audit_text(anonymized, sensitive_terms=terms),
        dictionary_result,
    )
    _save_anonymization_report(
        source_path, output_path, counters, audit_result, dictionary_result
    )
    return output_path, counters, audit_result


def _save_anonymization_report(
    source_path: str | Path,
    output_path: str | Path,
    counters: dict[str, int],
    audit_result: dict[str, object],
    dictionary_result: dict[str, object],
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
        dictionary_result=dictionary_result,
    )


def anonymize_file(
    source_path: str | Path,
    sensitive_terms: Iterable[SensitiveTerm] | None = None,
    sensitive_terms_path: str | Path | None = None,
) -> tuple[Path, dict[str, int]]:
    """Anonymize one supported application file using existing workflows."""
    output_path, counters, _ = anonymize_file_with_audit(
        source_path,
        sensitive_terms=sensitive_terms,
        sensitive_terms_path=sensitive_terms_path,
    )
    return output_path, counters


def anonymize_file_with_audit(
    source_path: str | Path,
    sensitive_terms: Iterable[SensitiveTerm] | None = None,
    sensitive_terms_path: str | Path | None = None,
) -> tuple[Path, dict[str, int], dict[str, object]]:
    """Anonymize one supported file and return safe audit metadata."""
    path = Path(source_path)

    if path.suffix.lower() == TXT_EXTENSION:
        return anonymize_txt_file_with_audit(
            path,
            sensitive_terms=sensitive_terms,
            sensitive_terms_path=sensitive_terms_path,
        )
    if path.suffix.lower() == DOCX_EXTENSION:
        return anonymize_docx_file_with_audit(
            path,
            sensitive_terms=sensitive_terms,
            sensitive_terms_path=sensitive_terms_path,
        )
    if path.suffix.lower() == PDF_EXTENSION:
        return anonymize_pdf_file_with_audit(
            path,
            sensitive_terms=sensitive_terms,
            sensitive_terms_path=sensitive_terms_path,
        )

    suffix = path.suffix.lower() or "<none>"
    supported = ", ".join(SUPPORTED_EXTENSIONS)
    raise ValueError(
        f"Unsupported file extension for anonymize_file: {suffix}. "
        f"Only {supported} files are supported."
    )
