"""Regex-based plain text anonymization engine."""

from pathlib import Path
import re

from file_readers import read_pdf_file, read_txt_file
from file_writers import (
    save_anonymized_docx_copy,
    save_anonymized_pdf_txt_copy,
    save_anonymized_txt_copy,
)


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
    """Anonymize a TXT file and save a separate Stage 2 output copy."""
    text = read_txt_file(source_path)
    anonymized, counters = anonymize_text(text)
    output_path = save_anonymized_txt_copy(source_path, anonymized)
    return output_path, counters


def anonymize_docx_file(source_path: str | Path) -> tuple[Path, dict[str, int]]:
    """Anonymize a DOCX file and save a separate Stage 3 output copy."""
    return save_anonymized_docx_copy(source_path, anonymize_text)


def anonymize_pdf_file(source_path: str | Path) -> tuple[Path, dict[str, int]]:
    """Anonymize text from a PDF and save a separate Stage 4 TXT output copy."""
    text = read_pdf_file(source_path)
    anonymized, counters = anonymize_text(text)
    output_path = save_anonymized_pdf_txt_copy(source_path, anonymized)
    return output_path, counters
