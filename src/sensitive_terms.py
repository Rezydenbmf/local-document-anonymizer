"""Private sensitive terms dictionary support."""

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
import re


_INTERNAL_WHITESPACE_PATTERN = r"[^\S\r\n]+"
_UTF8_BOM = "\ufeff"


@dataclass(frozen=True, repr=False)
class SensitiveTerm:
    """One private dictionary alias and its safe replacement label."""

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
        "Expected format: term or alias | alias = [LABEL]."
    )


def _split_aliases(term_text: str, line_number: int) -> list[str]:
    aliases = [alias.strip() for alias in term_text.split("|")]
    if not aliases or any(not alias for alias in aliases):
        raise _malformed_line_error(line_number)
    return aliases


def _parse_sensitive_term_line(
    line: str, line_number: int
) -> list[SensitiveTerm] | None:
    stripped = line.strip()
    if not stripped or stripped.startswith("#"):
        return None

    if "=" not in stripped:
        raise _malformed_line_error(line_number)

    term_text, label_text = stripped.split("=", 1)
    aliases = _split_aliases(term_text, line_number)
    label_token = label_text.strip()
    if not label_token.startswith("[") or not label_token.endswith("]"):
        raise _malformed_line_error(line_number)

    label = label_token[1:-1].strip()
    if not label or "[" in label or "]" in label:
        raise _malformed_line_error(line_number)

    return [SensitiveTerm(term=alias, label=label) for alias in aliases]


def _normalized_term_key(term: str) -> str:
    return " ".join(term.split()).casefold()


def _duplicate_alias_error(line_number: int) -> ValueError:
    return ValueError(
        f"Duplicate sensitive terms line {line_number}. "
        "Each private alias must map to only one label."
    )


def parse_sensitive_terms(text: str) -> list[SensitiveTerm]:
    """Parse private dictionary text without exposing source terms in errors."""
    if not isinstance(text, str):
        raise TypeError("text must be a string")

    terms: list[SensitiveTerm] = []
    labels_by_key: dict[str, str] = {}

    for line_number, line in enumerate(text.splitlines(), start=1):
        if line_number == 1:
            line = line.removeprefix(_UTF8_BOM)
        parsed_terms = _parse_sensitive_term_line(line, line_number)
        if parsed_terms is None:
            continue

        for parsed in parsed_terms:
            key = _normalized_term_key(parsed.term)
            existing_label = labels_by_key.get(key)
            if existing_label == parsed.label:
                continue
            if existing_label is not None:
                raise _duplicate_alias_error(line_number)

            terms.append(parsed)
            labels_by_key[key] = parsed.label

    return terms


def load_sensitive_terms(file_path: str | Path) -> list[SensitiveTerm]:
    """Load a private UTF-8 sensitive terms dictionary file."""
    return parse_sensitive_terms(Path(file_path).read_text(encoding="utf-8"))


def _term_regex(term: str) -> str:
    parts = re.split(r"\s+", term.strip())
    escaped = _INTERNAL_WHITESPACE_PATTERN.join(re.escape(part) for part in parts)
    if term[0].isalnum() or term[0] == "_":
        escaped = rf"(?<!\w){escaped}"
    if term[-1].isalnum() or term[-1] == "_":
        escaped = rf"{escaped}(?!\w)"
    return escaped


def _prepare_terms(sensitive_terms: Iterable[SensitiveTerm]) -> list[SensitiveTerm]:
    terms = list(sensitive_terms)
    prepared_terms: list[SensitiveTerm] = []
    labels_by_key: dict[str, str] = {}

    for term in terms:
        if not isinstance(term, SensitiveTerm):
            raise TypeError("sensitive_terms must contain SensitiveTerm items")
        key = _normalized_term_key(term.term)
        existing_label = labels_by_key.get(key)
        if existing_label == term.label:
            continue
        if existing_label is not None:
            raise ValueError(
                "sensitive_terms must not contain duplicate aliases "
                "with different labels"
            )

        prepared_terms.append(term)
        labels_by_key[key] = term.label

    return sorted(
        prepared_terms,
        key=lambda item: (len(_normalized_term_key(item.term)), len(item.term)),
        reverse=True,
    )


def _compile_sensitive_terms_pattern(
    sensitive_terms: Iterable[SensitiveTerm],
) -> tuple[re.Pattern[str], dict[str, str]] | None:
    terms = _prepare_terms(sensitive_terms)
    if not terms:
        return None

    labels_by_group: dict[str, str] = {}
    pattern_parts: list[str] = []
    for index, term in enumerate(terms):
        group_name = f"term_{index}"
        pattern_parts.append(f"(?P<{group_name}>{_term_regex(term.term)})")
        labels_by_group[group_name] = term.label

    return re.compile("|".join(pattern_parts), re.IGNORECASE), labels_by_group


def count_sensitive_term_matches(
    text: str, sensitive_terms: Iterable[SensitiveTerm] | None
) -> int:
    """Count private dictionary matches without returning matched source text."""
    if not isinstance(text, str):
        raise TypeError("text must be a string")
    if sensitive_terms is None:
        return 0

    compiled = _compile_sensitive_terms_pattern(sensitive_terms)
    if compiled is None:
        return 0

    pattern, _ = compiled
    return sum(1 for _ in pattern.finditer(text))


def apply_sensitive_terms(
    text: str, sensitive_terms: Iterable[SensitiveTerm] | None
) -> tuple[str, dict[str, int]]:
    """Apply private dictionary replacements and return counters by label."""
    if not isinstance(text, str):
        raise TypeError("text must be a string")
    if sensitive_terms is None:
        return text, {}

    compiled = _compile_sensitive_terms_pattern(sensitive_terms)
    if compiled is None:
        return text, {}

    pattern, labels_by_group = compiled
    counters: dict[str, int] = {}

    def replace(match: re.Match[str]) -> str:
        if match.lastgroup is None:
            raise RuntimeError("sensitive term match has no group")
        label = labels_by_group[match.lastgroup]
        counters[label] = counters.get(label, 0) + 1
        return f"[{label}]"

    return pattern.sub(replace, text), counters
