"""Optional local spaCy NER support."""

from __future__ import annotations

from dataclasses import dataclass
from importlib import import_module
import re
from typing import Any


NER_STATUS_AVAILABLE = "available"
NER_STATUS_UNAVAILABLE = "unavailable"
NER_STATUS_DEPENDENCY_MISSING = "dependency_missing"
NER_STATUS_MODEL_MISSING = "model_missing"
NER_STATUS_DISABLED = "disabled"
NER_STATUS_PROCESSING_ERROR = "processing_error"
NER_STATUSES = (
    NER_STATUS_AVAILABLE,
    NER_STATUS_UNAVAILABLE,
    NER_STATUS_DEPENDENCY_MISSING,
    NER_STATUS_MODEL_MISSING,
    NER_STATUS_DISABLED,
    NER_STATUS_PROCESSING_ERROR,
)

DEFAULT_NER_MODEL = "pl_core_news_sm"
NER_LABEL_PERSON = "NER_PERSON"
NER_LABEL_ORG = "NER_ORG"
NER_LABEL_LOCATION = "NER_LOCATION"
NER_LABEL_MISC = "NER_MISC"
NER_LABELS = (
    NER_LABEL_PERSON,
    NER_LABEL_ORG,
    NER_LABEL_LOCATION,
    NER_LABEL_MISC,
)

_MODEL_LABELS = {
    "PER": NER_LABEL_PERSON,
    "PERSON": NER_LABEL_PERSON,
    "PERSNAME": NER_LABEL_PERSON,
    "PERS_NAME": NER_LABEL_PERSON,
    "ORG": NER_LABEL_ORG,
    "ORGNAME": NER_LABEL_ORG,
    "ORG_NAME": NER_LABEL_ORG,
    "LOC": NER_LABEL_LOCATION,
    "GPE": NER_LABEL_LOCATION,
    "PLACE": NER_LABEL_LOCATION,
    "PLACENAME": NER_LABEL_LOCATION,
    "PLACE_NAME": NER_LABEL_LOCATION,
    "MISC": NER_LABEL_MISC,
}

_PLACEHOLDER_PATTERN = re.compile(r"\[[A-Z0-9_ ]+\]")


@dataclass(frozen=True)
class NerContext:
    """Loaded local NER model plus safe status metadata."""

    enabled: bool
    status: str
    model_name: str
    nlp: Any | None = None
    warning: str = ""


@dataclass(frozen=True)
class NerEntity:
    """Safe entity span with only offsets and an internal label."""

    start: int
    end: int
    label: str


def _spacy_module():
    try:
        return import_module("spacy")
    except ModuleNotFoundError:
        return None


def _safe_model_name(model_name: object) -> str:
    text = str(model_name or DEFAULT_NER_MODEL).strip()
    if not text:
        return DEFAULT_NER_MODEL
    if re.fullmatch(r"[A-Za-z0-9_.-]+", text):
        return text
    return "local_model"


def build_ner_metadata(
    *,
    enabled: bool,
    used: bool,
    status: str,
    model_name: str = DEFAULT_NER_MODEL,
    counters: dict[str, int] | None = None,
    warning: str = "",
) -> dict[str, object]:
    """Build safe NER metadata for reports, summaries, and GUI status."""
    if status not in NER_STATUSES:
        status = NER_STATUS_UNAVAILABLE

    safe_counters = {label: 0 for label in NER_LABELS}
    if counters:
        for label, count in counters.items():
            if label in NER_LABELS and isinstance(count, int) and count >= 0:
                safe_counters[label] = count

    return {
        "enabled": bool(enabled),
        "used": bool(used),
        "status": status,
        "model_name": _safe_model_name(model_name),
        "counters": safe_counters,
        "warning": str(warning or ""),
    }


def build_ner_disabled_metadata(
    model_name: str = DEFAULT_NER_MODEL,
) -> dict[str, object]:
    """Return safe metadata for workflows where NER is disabled."""
    return build_ner_metadata(
        enabled=False,
        used=False,
        status=NER_STATUS_DISABLED,
        model_name=model_name,
    )


def prepare_ner_context(
    *,
    enabled: bool = False,
    model_name: str = DEFAULT_NER_MODEL,
) -> NerContext:
    """Load a local spaCy model when NER is enabled, without downloading."""
    safe_model_name = _safe_model_name(model_name)
    if not enabled:
        return NerContext(
            enabled=False,
            status=NER_STATUS_DISABLED,
            model_name=safe_model_name,
        )

    spacy_module = _spacy_module()
    if spacy_module is None:
        return NerContext(
            enabled=True,
            status=NER_STATUS_DEPENDENCY_MISSING,
            model_name=safe_model_name,
            warning="local NER dependency is missing",
        )

    try:
        nlp = spacy_module.load(safe_model_name)
    except OSError:
        return NerContext(
            enabled=True,
            status=NER_STATUS_MODEL_MISSING,
            model_name=safe_model_name,
            warning="local NER model is missing",
        )
    except Exception:
        return NerContext(
            enabled=True,
            status=NER_STATUS_UNAVAILABLE,
            model_name=safe_model_name,
            warning="local NER model could not be loaded",
        )

    return NerContext(
        enabled=True,
        status=NER_STATUS_AVAILABLE,
        model_name=safe_model_name,
        nlp=nlp,
    )


def detect_ner_support(
    *,
    enabled: bool = True,
    model_name: str = DEFAULT_NER_MODEL,
) -> dict[str, object]:
    """Detect local NER availability without raising on absence."""
    context = prepare_ner_context(enabled=enabled, model_name=model_name)
    return build_ner_metadata(
        enabled=context.enabled,
        used=False,
        status=context.status,
        model_name=context.model_name,
        warning=context.warning,
    )


def _internal_label(model_label: object) -> str | None:
    normalized = str(model_label or "").strip().replace("-", "_").upper()
    return _MODEL_LABELS.get(normalized)


def _placeholder_ranges(text: str) -> list[tuple[int, int]]:
    return [(match.start(), match.end()) for match in _PLACEHOLDER_PATTERN.finditer(text)]


def _overlaps_any(start: int, end: int, ranges: list[tuple[int, int]]) -> bool:
    return any(start < range_end and end > range_start for range_start, range_end in ranges)


def _letter_token_starting_at(text: str, start: int, end: int) -> str:
    cursor = start
    while cursor < end and text[cursor].isalpha():
        cursor += 1
    return text[start:cursor]


def _is_simple_capitalized_word(token: str) -> bool:
    return (
        len(token) >= 2
        and token.isalpha()
        and token[0].isupper()
        and token[1:].islower()
    )


def _expand_person_start_left(
    text: str,
    start: int,
    end: int,
    placeholder_ranges: list[tuple[int, int]],
) -> int:
    if start <= 0:
        return start

    entity_token = _letter_token_starting_at(text, start, end)
    if not _is_simple_capitalized_word(entity_token):
        return start

    cursor = start - 1
    if text[cursor] not in (" ", "\t"):
        return start
    while cursor >= 0 and text[cursor] in (" ", "\t"):
        cursor -= 1
    if cursor < 0 or text[cursor] == "\n":
        return start

    previous_end = cursor + 1
    while cursor >= 0 and text[cursor].isalpha():
        cursor -= 1
    previous_start = cursor + 1
    previous_token = text[previous_start:previous_end]
    if not _is_simple_capitalized_word(previous_token):
        return start
    if any(char not in (" ", "\t") for char in text[previous_end:start]):
        return start
    if _overlaps_any(previous_start, start, placeholder_ranges):
        return start
    return previous_start


def detect_entities(text: str, context: NerContext) -> tuple[list[NerEntity], dict[str, int]]:
    """Detect supported entities and return safe spans plus counters only."""
    if not isinstance(text, str):
        raise TypeError("text must be a string")
    if context.status != NER_STATUS_AVAILABLE or context.nlp is None:
        return [], {label: 0 for label in NER_LABELS}

    doc = context.nlp(text)
    occupied_ranges = _placeholder_ranges(text)
    accepted_ranges: list[tuple[int, int]] = []
    entities: list[NerEntity] = []
    counters = {label: 0 for label in NER_LABELS}

    for entity in getattr(doc, "ents", ()):
        label = _internal_label(getattr(entity, "label_", ""))
        if label is None:
            continue
        start = getattr(entity, "start_char", None)
        end = getattr(entity, "end_char", None)
        if not isinstance(start, int) or not isinstance(end, int):
            continue
        if start < 0 or end <= start or end > len(text):
            continue
        if not text[start:end].strip():
            continue
        if label == NER_LABEL_PERSON:
            start = _expand_person_start_left(text, start, end, occupied_ranges)
        if _overlaps_any(start, end, occupied_ranges):
            continue
        if _overlaps_any(start, end, accepted_ranges):
            continue
        accepted_ranges.append((start, end))
        entities.append(NerEntity(start=start, end=end, label=label))
        counters[label] += 1

    return entities, counters


def anonymize_entities(text: str, entities: list[NerEntity]) -> str:
    """Replace safe entity spans with internal placeholders."""
    if not entities:
        return text

    parts: list[str] = []
    cursor = 0
    for entity in sorted(entities, key=lambda item: item.start):
        parts.append(text[cursor:entity.start])
        parts.append(f"[{entity.label}]")
        cursor = entity.end
    parts.append(text[cursor:])
    return "".join(parts)


def anonymize_text_with_ner(
    text: str,
    context: NerContext,
) -> tuple[str, dict[str, int], dict[str, object]]:
    """Apply local NER if available and return safe metadata."""
    if context.status != NER_STATUS_AVAILABLE:
        return (
            text,
            {},
            build_ner_metadata(
                enabled=context.enabled,
                used=False,
                status=context.status,
                model_name=context.model_name,
                warning=context.warning,
            ),
        )

    try:
        entities, counters = detect_entities(text, context)
    except Exception:
        return (
            text,
            {},
            build_ner_metadata(
                enabled=context.enabled,
                used=False,
                status=NER_STATUS_PROCESSING_ERROR,
                model_name=context.model_name,
                warning="local NER processing failed safely",
            ),
        )

    anonymized = anonymize_entities(text, entities)
    active_counters = {label: count for label, count in counters.items() if count}
    return (
        anonymized,
        active_counters,
        build_ner_metadata(
            enabled=context.enabled,
            used=True,
            status=NER_STATUS_AVAILABLE,
            model_name=context.model_name,
            counters=counters,
        ),
    )
