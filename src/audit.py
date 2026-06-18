"""Safe post-anonymization audit for remaining sensitive-looking patterns."""

from collections.abc import Iterable
import re

try:
    from .sensitive_terms import SensitiveTerm, count_sensitive_term_matches
except ImportError:
    from sensitive_terms import SensitiveTerm, count_sensitive_term_matches


AUDIT_STATUS_OK = "ok"
AUDIT_STATUS_WARNING = "warning"
RISK_LEVEL_OK = "ok"
RISK_LEVEL_WARNING = "warning"
RISK_LEVEL_HIGH = "high_risk"
RISK_LEVELS = (
    RISK_LEVEL_OK,
    RISK_LEVEL_WARNING,
    RISK_LEVEL_HIGH,
)
HIGH_RISK_AUDIT_CATEGORIES = (
    "EMAIL",
    "PESEL",
    "TELEFON",
    "SENSITIVE_DICTIONARY_TERM",
    "ADDRESS_LIKE",
    "ID_LIKE_NUMBER",
    "LONG_NUMBER_SEQUENCE",
)
HIGH_RISK_TOTAL_WARNING_THRESHOLD = 3
AUDIT_CATEGORY_ORDER = (
    "EMAIL",
    "PESEL",
    "TELEFON",
    "DATA",
    "SENSITIVE_DICTIONARY_TERM",
    "CASE_REFERENCE",
    "POSTAL_CODE",
    "ADDRESS_LIKE",
    "STREET_LIKE",
    "INITIAL_SURNAME",
    "ID_LIKE_NUMBER",
    "LONG_NUMBER_SEQUENCE",
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
                [A-Z]{1,4}\.\d{1,6}\.\d{2,4}
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
        "ADDRESS_LIKE",
        re.compile(
            r"""
            (?<!\w)
            (?:ul\.|al\.|pl\.|ulica|aleja|plac)\s+
            [A-Z][A-Za-z-]+
            (?:\s+[A-Z][A-Za-z-]+){0,2}
            \s+\d+[A-Za-z]?(?:/\d+)?
            (?!\w)
            """,
            re.VERBOSE,
        ),
    ),
    (
        "STREET_LIKE",
        re.compile(
            r"""
            (?<!\w)
            (?:ul\.|al\.|pl\.|ulica|aleja|plac)\s+
            [A-Z][A-Za-z-]+
            (?:\s+[A-Z][A-Za-z-]+){0,2}
            (?!\s+\d)
            (?!\w)
            """,
            re.VERBOSE,
        ),
    ),
    (
        "INITIAL_SURNAME",
        re.compile(r"(?<!\w)[A-Z]\.\s+[A-Z][A-Za-z-]{2,}(?!\w)"),
    ),
    (
        "ID_LIKE_NUMBER",
        re.compile(
            r"""
            (?<!\w)
            (?:ID|IDENTYFIKATOR|NR|NIP|REGON|KRS|PASZPORT|DOWOD)
            [:\s.-]*
            \d{4,12}
            (?!\w)
            """,
            re.VERBOSE,
        ),
    ),
    (
        "LONG_NUMBER_SEQUENCE",
        re.compile(r"(?<!\w)\d(?:[ -]?\d){11,}(?!\w)"),
    ),
)


def _count_sensitive_dictionary_terms(
    text: str, sensitive_terms: Iterable[SensitiveTerm] | None
) -> int:
    return count_sensitive_term_matches(text, sensitive_terms)


def determine_risk_level(findings: dict[str, int]) -> str:
    """Return a safe review-prioritization level for audit counters."""
    total_warnings = sum(findings.values())
    if total_warnings == 0:
        return RISK_LEVEL_OK

    has_high_risk_category = any(
        findings.get(category, 0) > 0 for category in HIGH_RISK_AUDIT_CATEGORIES
    )
    if (
        has_high_risk_category
        or total_warnings >= HIGH_RISK_TOTAL_WARNING_THRESHOLD
    ):
        return RISK_LEVEL_HIGH

    return RISK_LEVEL_WARNING


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
        "risk_level": determine_risk_level(findings),
        "findings": findings,
        "manual_review_required": True,
    }
