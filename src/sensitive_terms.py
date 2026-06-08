"""Private sensitive terms dictionary support."""

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
import re


@dataclass(frozen=True, repr=False)
class SensitiveTerm:
    """One private exact term and its safe replacement label."""

    term: str
    label: str

    def __post_init__(self) -> None:
        if not isinstance(self.term, str):
            raise TypeError("term must be a string")
        if not isinstance(self.label, str):
            raise TypeError("label must be a string")

        term = self.term.strip()
        label = self.label.strip()
        if not term:
            raise ValueError("term must not be empty")
        if not label:
            raise ValueError("label must not be empty")
        if "[" in label or "]" in label:
            raise ValueError("label must not contain brackets")

        object.__setattr__(self, "term", term)
        object.__setattr__(self, "label", label)

    @property
    def placeholder(self) -> str:
        return f"[{self.label}]"

    def __repr__(self) -> str:
        return f"SensitiveTerm(label={self.label!r})"


def _malformed_line_error(line_number: int) -> ValueError:
    return ValueError(
        f"Malformed sensitive terms line {line_number}. "
        "Expected format: term = [LABEL]."
    )


def _parse_sensitive_term_line(line: str, line_number: int) -> SensitiveTerm | None:
    stripped = line.strip()
    if not stripped or stripped.startswith("#"):
        return None

    if "=" not in stripped:
        raise _malformed_line_error(line_number)

    term_text, label_text = stripped.split("=", 1)
    term = term_text.strip()
    label_token = label_text.strip()
    if not term:
        raise _malformed_line_error(line_number)
    if not label_token.startswith("[") or not label_token.endswith("]"):
        raise _malformed_line_error(line_number)

    label = label_token[1:-1].strip()
    if not label or "[" in label or "]" in label:
        raise _malformed_line_error(line_number)

    return SensitiveTerm(term=term, label=label)


def parse_sensitive_terms(text: str) -> list[SensitiveTerm]:
    """Parse private dictionary text without exposing source terms in errors."""
    if not isinstance(text, str):
        raise TypeError("text must be a string")

    terms: list[SensitiveTerm] = []
    seen_terms: set[str] = set()

    for line_number, line in enumerate(text.splitlines(), start=1):
        parsed = _parse_sensitive_term_line(line, line_number)
        if parsed is None:
            continue
        if parsed.term in seen_terms:
            raise ValueError(
                f"Duplicate sensitive terms line {line_number}. "
                "Each private term must be unique."
            )

        terms.append(parsed)
        seen_terms.add(parsed.term)

    return terms


def load_sensitive_terms(file_path: str | Path) -> list[SensitiveTerm]:
    """Load a private UTF-8 sensitive terms dictionary file."""
    return parse_sensitive_terms(Path(file_path).read_text(encoding="utf-8"))


def _term_regex(term: str) -> str:
    escaped = re.escape(term)
    if term[0].isalnum() or term[0] == "_":
        escaped = rf"(?<!\w){escaped}"
    if term[-1].isalnum() or term[-1] == "_":
        escaped = rf"{escaped}(?!\w)"
    return escaped


def _prepare_terms(sensitive_terms: Iterable[SensitiveTerm]) -> list[SensitiveTerm]:
    terms = list(sensitive_terms)
    seen_terms: set[str] = set()

    for term in terms:
        if not isinstance(term, SensitiveTerm):
            raise TypeError("sensitive_terms must contain SensitiveTerm items")
        if term.term in seen_terms:
            raise ValueError("sensitive_terms must not contain duplicate terms")
        seen_terms.add(term.term)

    return sorted(terms, key=lambda item: len(item.term), reverse=True)


def apply_sensitive_terms(
    text: str, sensitive_terms: Iterable[SensitiveTerm] | None
) -> tuple[str, dict[str, int]]:
    """Apply private dictionary replacements and return counters by label."""
    if not isinstance(text, str):
        raise TypeError("text must be a string")
    if sensitive_terms is None:
        return text, {}

    terms = _prepare_terms(sensitive_terms)
    if not terms:
        return text, {}

    labels_by_term = {term.term: term.label for term in terms}
    pattern = re.compile("|".join(_term_regex(term.term) for term in terms))
    counters: dict[str, int] = {}

    def replace(match: re.Match[str]) -> str:
        label = labels_by_term[match.group(0)]
        counters[label] = counters.get(label, 0) + 1
        return f"[{label}]"

    return pattern.sub(replace, text), counters
