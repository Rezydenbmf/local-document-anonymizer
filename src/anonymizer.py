"""Regex-based plain text anonymization engine."""

from pathlib import Path
import re

from file_readers import (
    DOCX_EXTENSION,
    PDF_EXTENSION,
    SUPPORTED_EXTENSIONS,
    TXT_EXTENSION,
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


def anonymize_text(text: str) -> tuple[str, dict[str, int]]:
    """Replace high-confidence sensitive values with category placeholders."""
    if not isinstance(text, str):
        raise TypeError("text must be a string")

    anonymized = text
    counters: dict[str, int] = {}

    for label, pattern in _PATTERNS:
        anonymized, count = pattern.subn(f"[{label}]", anonymized)
        if count:
            counters[label] = count

    return anonymized, counters


def anonymize_txt_file(source_path: str | Path) -> tuple[Path, dict[str, int]]:
    """Anonymize a TXT file and save output plus a safe report."""
    text = read_txt_file(source_path)
    anonymized, counters = anonymize_text(text)
    output_path = save_anonymized_txt_copy(source_path, anonymized)
    _save_anonymization_report(source_path, output_path, counters)
    return output_path, counters


def anonymize_docx_file(source_path: str | Path) -> tuple[Path, dict[str, int]]:
    """Anonymize a DOCX file and save output plus a safe report."""
    output_path, counters = save_anonymized_docx_copy(source_path, anonymize_text)
    _save_anonymization_report(source_path, output_path, counters)
    return output_path, counters


def anonymize_pdf_file(source_path: str | Path) -> tuple[Path, dict[str, int]]:
    """Anonymize text from a PDF and save TXT output plus a safe report."""
    text = read_pdf_file(source_path)
    anonymized, counters = anonymize_text(text)
    output_path = save_anonymized_pdf_txt_copy(source_path, anonymized)
    _save_anonymization_report(source_path, output_path, counters)
    return output_path, counters


def _save_anonymization_report(
    source_path: str | Path, output_path: str | Path, counters: dict[str, int]
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
    )


def anonymize_file(source_path: str | Path) -> tuple[Path, dict[str, int]]:
    """Anonymize one supported application file using existing workflows."""
    path = Path(source_path)

    if path.suffix.lower() == TXT_EXTENSION:
        return anonymize_txt_file(path)
    if path.suffix.lower() == DOCX_EXTENSION:
        return anonymize_docx_file(path)
    if path.suffix.lower() == PDF_EXTENSION:
        return anonymize_pdf_file(path)

    suffix = path.suffix.lower() or "<none>"
    supported = ", ".join(SUPPORTED_EXTENSIONS)
    raise ValueError(
        f"Unsupported file extension for anonymize_file: {suffix}. "
        f"Only {supported} files are supported."
    )
