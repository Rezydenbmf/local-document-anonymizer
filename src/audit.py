"""Safe post-anonymization audit for remaining sensitive-looking patterns."""

from collections.abc import Iterable
import re

from sensitive_terms import SensitiveTerm


AUDIT_STATUS_OK = "ok"
AUDIT_STATUS_WARNING = "warning"
AUDIT_CATEGORY_ORDER = (
    "EMAIL",
    "PESEL",
    "TELEFON",
    "DATA",
    "SENSITIVE_DICTIONARY_TERM",
    "CASE_REFERENCE",
    "POSTAL_CODE",
    "ADDRESS",
)

_AUDIT_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
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
    (
        "CASE_REFERENCE",
        re.compile(
            r"""
            (?<!\w)
            (?:
                [A-Z]{1,4}\s*/\s*\d{1,6}\s*/\s*(?:\d{2}|\d{4})
                |
                (?:REF|CASE|SPRAWA)[- ]\d{2,4}[-/]\d{1,6}
            )
            (?!\w)
            """,
            re.VERBOSE,
        ),
    ),
    ("POSTAL_CODE", re.compile(r"(?<!\w)\d{2}-\d{3}(?!\w)")),
    (
        "ADDRESS",
        re.compile(
            r"""
            (?<!\w)
            (?:ul\.|al\.|pl\.)\s+
            [A-Z][A-Za-z-]+
            (?:\s+\d+[A-Za-z]?)?
            (?!\w)
            """,
            re.VERBOSE,
        ),
    ),
)


def _term_regex(term: str) -> str:
    escaped = re.escape(term)
    if term[0].isalnum() or term[0] == "_":
        escaped = rf"(?<!\w){escaped}"
    if term[-1].isalnum() or term[-1] == "_":
        escaped = rf"{escaped}(?!\w)"
    return escaped


def _prepare_sensitive_terms(
    sensitive_terms: Iterable[SensitiveTerm] | None,
) -> list[SensitiveTerm]:
    if sensitive_terms is None:
        return []

    terms = list(sensitive_terms)
    seen_terms: set[str] = set()
    for term in terms:
        if not isinstance(term, SensitiveTerm):
            raise TypeError("sensitive_terms must contain SensitiveTerm items")
        if term.term in seen_terms:
            raise ValueError("sensitive_terms must not contain duplicate terms")
        seen_terms.add(term.term)

    return sorted(terms, key=lambda item: len(item.term), reverse=True)


def _count_sensitive_dictionary_terms(
    text: str, sensitive_terms: Iterable[SensitiveTerm] | None
) -> int:
    terms = _prepare_sensitive_terms(sensitive_terms)
    if not terms:
        return 0

    pattern = re.compile("|".join(_term_regex(term.term) for term in terms))
    return sum(1 for _ in pattern.finditer(text))


def audit_text(
    text: str, sensitive_terms: Iterable[SensitiveTerm] | None = None
) -> dict[str, object]:
    """Return safe audit metadata for suspicious text left after anonymization."""
    if not isinstance(text, str):
        raise TypeError("text must be a string")

    findings = {
        label: sum(1 for _ in pattern.finditer(text))
        for label, pattern in _AUDIT_PATTERNS
    }
    findings["SENSITIVE_DICTIONARY_TERM"] = _count_sensitive_dictionary_terms(
        text, sensitive_terms
    )
    findings = {
        label: findings.get(label, 0)
        for label in AUDIT_CATEGORY_ORDER
    }

    status = (
        AUDIT_STATUS_WARNING
        if any(count > 0 for count in findings.values())
        else AUDIT_STATUS_OK
    )

    return {
        "status": status,
        "findings": findings,
        "manual_review_required": True,
    }
