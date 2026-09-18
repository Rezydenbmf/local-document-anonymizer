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
NER_EXCLUSION_PUBLIC_INSTITUTION = "PUBLIC_INSTITUTION_PHRASE"
NER_EXCLUSION_VERSION_LIKE = "VERSION_LIKE"
NER_EXCLUSION_SCIENTIFIC_NAME = "SCIENTIFIC_NAME"
NER_EXCLUSION_ORDINARY_WORD = "ORDINARY_WORD"
NER_EXCLUSION_SINGLE_TOKEN_PERSON = "SINGLE_TOKEN_PERSON_SKIPPED"
NER_EXCLUSION_LINEBREAK_NON_PERSON = "LINEBREAK_NON_PERSON_SKIPPED"
NER_EXCLUSION_CATEGORIES = (
    NER_EXCLUSION_PUBLIC_INSTITUTION,
    NER_EXCLUSION_VERSION_LIKE,
    NER_EXCLUSION_SCIENTIFIC_NAME,
    NER_EXCLUSION_ORDINARY_WORD,
    NER_EXCLUSION_SINGLE_TOKEN_PERSON,
    NER_EXCLUSION_LINEBREAK_NON_PERSON,
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
_VERSION_LIKE_PATTERN = re.compile(
    r"(?i)\b(?:version|wersja)\s+\d+(?:\.\d+)+(?:\s*,\s*\d{4})?\b"
)
_DASH_CHARS = {
    "\u00ad",
    "\u2010",
    "\u2011",
    "\u2012",
    "\u2013",
    "\u2014",
    "\u2212",
}
_DASH_TRANSLATION = str.maketrans(
    {
        "\u00ad": "-",
        "\u2010": "-",
        "\u2011": "-",
        "\u2012": "-",
        "\u2013": "-",
        "\u2014": "-",
        "\u2212": "-",
    }
)
_PUBLIC_INSTITUTION_PHRASES = {
    "rozporządzenie ministra zdrowia",
    "rozporządzenia ministra zdrowia",
    "ministra zdrowia",
    "minister zdrowia",
    "ministerstwo zdrowia",
}
_SCIENTIFIC_NAME_PHRASES = {
    "streptococcus pneumoniae",
    "neisseria meningitidis",
    "salmonella enteritidis",
    "escherichia coli",
    "pseudomonas aeruginosa",
    "haemophilus influenzae",
}
_ORDINARY_WORD_PHRASES = {
    "epidemiologicznej",
    "publicznej",
    "wiotkie",
    "\u017cywno\u015bci\u0105",
    "pesel",
    "nip",
    "regon",
}
_PUBLIC_INSTITUTION_PHRASES.update(
    {
        "ecdc",
        "gus",
        "minister zdrowia",
        "ministerstwo zdrowia",
        "ministra zdrowia",
        "pa\u0144stwowa inspekcja sanitarna",
        "pa\u0144stwow\u0105 inspekcj\u0105 sanitarn\u0105",
        "pa\u0144stwow\u0105 inspekcj\u0119 sanitarn\u0105",
        "pa\u0144stwowej inspekcji sanitarnej",
        "pa\u0144stwowy powiatowy inspektor sanitarny",
        "pa\u0144stwowego powiatowego inspektora sanitarnego",
        "powiatowej stacji",
        "powiatowa stacja sanitarno-epidemiologiczna",
        "powiatowej stacji sanitarno-epidemiologicznej",
        "rozporz\u0105dzenie ministra zdrowia",
        "rozporz\u0105dzenia ministra zdrowia",
        "stanu sanitarnego powiatu",
        "\u015bwiatowa organizacja zdrowia",
        "\u015bwiatow\u0105 organizacj\u0119 zdrowia",
        "urz\u0105d statystyczny",
        "urz\u0119dem statystycznym",
        "urz\u0119dem statystycznym w krakowie",
        "ojew\u00f3dzkiej stacji sanitarno-epidemiologicznej",
        "wojew\u00f3dzka stacja sanitarno-epidemiologiczna",
        "wojew\u00f3dzkiej stacji sanitarno-epidemiologicznej",
        "who",
    }
)
_SCIENTIFIC_NAME_PHRASES.update(
    {
        "b\u0142onica",
        "b\u0142onica-t\u0119\u017cec-krztusiec",
        "clostridium perfringens",
        "e. coli",
        "enterica",
        "enteritidis",
        "gru\u017alica",
        "haemophilus",
        "haemophilus influenzae",
        "krztusiec",
        "neisseria",
        "neisseria meningitidis",
        "odra",
        "ospa",
        "polio",
        "pseudomonas aeruginosa",
        "p\u0142onica",
        "r\u00f3\u017ca",
        "r\u00f3\u017cyczka",
        "salmonella",
        "salmonella enterica",
        "salmonella enteritidis",
        "salmoneloza",
        "salmoneloz\u0119",
        "streptococcus",
        "t\u0119\u017cec",
        "t\u0119\u017cec-b\u0142onica",
        "wzw b",
        "zaka\u017cenia neisseria",
        "\u015bwinka",
    }
)
_PERSON_TITLE_CONTEXT_PATTERN = re.compile(
    r"(?i)(?:^|[\s(])(?:mgr(?:\s+in\u017c\.?|\s+inz\.?)?|dr|lek\.?|prof\.?|pan|pani)\.?\s*$"
)
_LATIN_BINOMIAL_PATTERN = re.compile(r"^[A-Z][A-Za-z-]+\s+[a-z][a-z-]+$")


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


# Loading a spaCy pipeline from disk costs 1-3+ seconds - real, measured
# latency (see docs/PROJECT_STATE.md's Etap 2 timing entry), and a loaded
# pipeline is safe to reuse across calls (spaCy's own documented usage
# pattern: load once, call nlp(text) many times). Without this cache,
# prepare_ner_context() paid that cost on every single PDF in a batch and
# again on every magic-pen manual-edit save. Keyed on (spacy module
# object, model name) rather than just the model name - see
# prepare_ner_context for why the module identity matters too.
_LOADED_NLP_CACHE: dict[tuple[Any, str], Any] = {}


def check_ner_model_installed(model_name: str = DEFAULT_NER_MODEL) -> str:
    """Cheaply report NER availability without loading the model.

    Unlike prepare_ner_context() (which actually loads the spaCy pipeline
    into memory - real, non-trivial latency), this only checks whether the
    spaCy library and the model package are importable, via
    importlib.util.find_spec. Safe to call on every app startup.
    """
    if _spacy_module() is None:
        return NER_STATUS_DEPENDENCY_MISSING
    safe_model_name = _safe_model_name(model_name)
    try:
        import importlib.util

        found = importlib.util.find_spec(safe_model_name) is not None
    except (ImportError, ValueError, ModuleNotFoundError):
        found = False
    return NER_STATUS_AVAILABLE if found else NER_STATUS_MODEL_MISSING


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
    exclusion_counters: dict[str, int] | None = None,
    linebreak_person_candidates: int = 0,
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

    safe_exclusion_counters = {category: 0 for category in NER_EXCLUSION_CATEGORIES}
    if exclusion_counters:
        for category, count in exclusion_counters.items():
            if (
                category in NER_EXCLUSION_CATEGORIES
                and isinstance(count, int)
                and count >= 0
            ):
                safe_exclusion_counters[category] = count

    safe_linebreak_count = (
        linebreak_person_candidates
        if isinstance(linebreak_person_candidates, int)
        and linebreak_person_candidates >= 0
        else 0
    )

    return {
        "enabled": bool(enabled),
        "used": bool(used),
        "status": status,
        "model_name": _safe_model_name(model_name),
        "counters": safe_counters,
        "exclusion_counters": safe_exclusion_counters,
        "linebreak_person_candidates": safe_linebreak_count,
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

    # Keyed on the spaCy module object itself (not just the model name),
    # so a test double patched in via _spacy_module() (a fresh fake object
    # per test) never collides with a real load cached under the same
    # default model name from an earlier call. Using the object itself
    # rather than id() also means the cache holds a strong reference to
    # it, so a garbage-collected-and-reused id can never cause a false
    # collision either.
    cache_key = (spacy_module, safe_model_name)
    nlp = _LOADED_NLP_CACHE.get(cache_key)
    if nlp is None:
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
        _LOADED_NLP_CACHE[cache_key] = nlp

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


def _space_normalized(text: str) -> str:
    normalized = str(text or "").translate(_DASH_TRANSLATION)
    normalized = re.sub(r"\s*-\s*", "-", normalized)
    return " ".join(normalized.split()).strip().casefold()


def _normalized_phrase_set(values: set[str]) -> set[str]:
    return {_space_normalized(value) for value in values if _space_normalized(value)}


_PUBLIC_INSTITUTION_NORMALIZED = _normalized_phrase_set(_PUBLIC_INSTITUTION_PHRASES)
_SCIENTIFIC_NAME_NORMALIZED = _normalized_phrase_set(_SCIENTIFIC_NAME_PHRASES)
_ORDINARY_WORD_NORMALIZED = _normalized_phrase_set(_ORDINARY_WORD_PHRASES)


def _contains_normalized_phrase(normalized_value: str, normalized_phrase: str) -> bool:
    if not normalized_phrase:
        return False
    if normalized_value == normalized_phrase:
        return True
    if _word_count(normalized_phrase) < 2:
        return False
    pattern = r"(?<!\w)" + re.escape(normalized_phrase) + r"(?!\w)"
    return bool(re.search(pattern, normalized_value, flags=re.UNICODE))


def _matches_normalized_allowlist(
    normalized_value: str,
    normalized_phrases: set[str],
) -> bool:
    if normalized_value in normalized_phrases:
        return True
    return any(
        _contains_normalized_phrase(normalized_value, phrase)
        for phrase in normalized_phrases
    )


def _word_count(value: str) -> int:
    return len(re.findall(r"\w+", value, flags=re.UNICODE))


def _has_person_title_context(text: str, start: int) -> bool:
    left_context = text[max(0, start - 24):start]
    return bool(_PERSON_TITLE_CONTEXT_PATTERN.search(left_context))


def _is_latin_binomial(value: str) -> bool:
    return bool(_LATIN_BINOMIAL_PATTERN.fullmatch(" ".join(value.split())))


def _ner_exclusion_category(value: str, label: str) -> str | None:
    normalized = _space_normalized(value)
    if not normalized:
        return None
    if _VERSION_LIKE_PATTERN.fullmatch(" ".join(str(value or "").split())):
        return NER_EXCLUSION_VERSION_LIKE
    if normalized in _ORDINARY_WORD_NORMALIZED:
        return NER_EXCLUSION_ORDINARY_WORD
    if _matches_normalized_allowlist(normalized, _PUBLIC_INSTITUTION_NORMALIZED):
        return NER_EXCLUSION_PUBLIC_INSTITUTION
    if _matches_normalized_allowlist(normalized, _SCIENTIFIC_NAME_NORMALIZED):
        return NER_EXCLUSION_SCIENTIFIC_NAME
    if label == NER_LABEL_PERSON and _is_latin_binomial(value):
        return NER_EXCLUSION_SCIENTIFIC_NAME
    return None


def _person_single_token_exclusion(text: str, start: int, end: int) -> bool:
    value = text[start:end].strip()
    return _word_count(value) < 2 and not _has_person_title_context(text, start)


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


def _previous_alpha_token(text: str, index: int) -> str:
    cursor = index - 1
    while cursor >= 0 and text[cursor] in (" ", "\t", "\r"):
        cursor -= 1
    end = cursor + 1
    while cursor >= 0 and text[cursor].isalpha():
        cursor -= 1
    return text[cursor + 1:end]


def _next_alpha_token(text: str, index: int) -> str:
    cursor = index + 1
    while cursor < len(text) and text[cursor] in (" ", "\t", "\r"):
        cursor += 1
    start = cursor
    while cursor < len(text) and text[cursor].isalpha():
        cursor += 1
    return text[start:cursor]


def _linebreak_between_name_like_tokens(text: str, index: int) -> bool:
    previous_token = _previous_alpha_token(text, index)
    next_token = _next_alpha_token(text, index)
    return _is_simple_capitalized_word(previous_token) and _is_simple_capitalized_word(
        next_token
    )


def _analysis_text(text: str, *, bridge_linebreaks: bool = True) -> str:
    """``bridge_linebreaks=False`` applies the NBSP/dash cleanup only,
    without merging any line break - see detect_entities_with_details's
    two-pass design for why a caller needs that raw-but-cleaned variant
    on its own.

    Every substitution below replaces exactly one input character with
    exactly one output character, so a position in the returned string
    always lines up with the same position in ``text`` - no offset
    mapping is needed to translate spaCy's ``start_char``/``end_char``
    (computed against whichever variant was fed to it) back to ``text``.
    """
    analysis_chars: list[str] = []
    for index, char in enumerate(text):
        if char == "\u00a0":
            analysis_chars.append(" ")
        elif char in _DASH_CHARS:
            analysis_chars.append("-")
        elif (
            bridge_linebreaks
            and char == "\n"
            and _linebreak_between_name_like_tokens(text, index)
        ):
            analysis_chars.append(" ")
        else:
            analysis_chars.append(char)
    return "".join(analysis_chars)


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
    if _space_normalized(entity_token) in _SCIENTIFIC_NAME_PHRASES:
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
    if _space_normalized(previous_token) in _SCIENTIFIC_NAME_PHRASES:
        return start
    if any(char not in (" ", "\t") for char in text[previous_end:start]):
        return start
    if _overlaps_any(previous_start, start, placeholder_ranges):
        return start
    return previous_start


def detect_entities_with_details(
    text: str,
    context: NerContext,
) -> tuple[list[NerEntity], dict[str, int], dict[str, int], int]:
    """Detect supported entities and return safe spans plus counters only.

    Two passes, not one - a real bug live-tested on an invoice fixture:
    the line-break bridging below exists only to let a person name split
    across a PDF/document line still be detected as one name, but it
    can't know in advance what an entity will turn out to be, so it also
    bridges any two unrelated capitalized words from separate lines (a
    field label, a city name, a section header) into one merged phrase.
    When that merged phrase turns out to *not* be a person, the whole
    thing gets discarded below - taking a perfectly ordinary, single-line
    company/location name down with it if it happened to sit next to the
    bridge (root cause of a real miss: "Warszawa" from a table row above
    bridged into "Firma Wzorcowa S.A." on the row below, producing one
    non-person entity that was discarded in full).

    The bridged pass runs *first*, and only ever contributes entities
    that themselves cross a bridged line break - the case the raw pass
    can only find by accident (the model happening to span a literal
    newline on its own, unrelated to the bridging). The raw pass then
    runs on the text with line-break bridging *off*, the correct,
    uncorrupted source for any entity that's genuinely whole on a single
    line, which is the overwhelming majority. ``evaluated_spans`` below
    guards specifically against that accidental-overlap case: if the raw
    pass independently reports the exact same span the bridged pass
    already handled, it must not be evaluated (and, if excluded, counted)
    a second time.

    Cost this pays for correctness: whenever any bridge candidate exists
    anywhere in ``text``, the model runs on the *entire* text twice, not
    just the bridged region - there is no cheap way to re-run inference
    on a sub-span alone. Accepted deliberately; NER inference itself has
    never been the measured latency cost in this codebase (pipeline
    *loading* is, and stays cached - see ``_LOADED_NLP_CACHE`` above).

    Bridged-first is load-bearing, not an arbitrary choice: a real bug
    found by code review before this shipped - on "Pan Jan\nKowalski",
    the raw pass alone tags "Jan" as a single-token PERSON candidate
    that a preceding title ("Pan") makes it accept, *before* it ever
    sees "Kowalski" trailing on the next line. Since the raw pass's own
    span-overlap check only ever looks at what's *already* accepted, an
    accepted-first "Jan" would silently block the bridged pass's later,
    correct "Jan Kowalski" from ever being added - leaving "Kowalski"
    exposed in plain text, a worse outcome than the single-pass code
    this replaced (which only ever saw the pre-merged "Jan Kowalski" and
    would never have isolated "Jan" from it at all). Running the bridged
    pass first means its correct, wider span claims the region before
    the raw pass's own narrower same-region fragment is ever evaluated,
    so the raw pass's overlap check is what suppresses the fragment
    instead of the other way around.
    """
    if not isinstance(text, str):
        raise TypeError("text must be a string")
    if context.status != NER_STATUS_AVAILABLE or context.nlp is None:
        return [], {label: 0 for label in NER_LABELS}, {}, 0

    occupied_ranges = _placeholder_ranges(text)
    accepted_ranges: list[tuple[int, int]] = []
    evaluated_spans: set[tuple[int, int]] = set()
    entities: list[NerEntity] = []
    counters = {label: 0 for label in NER_LABELS}
    exclusion_counters = {category: 0 for category in NER_EXCLUSION_CATEGORIES}
    linebreak_person_candidates = 0

    def _process(doc: object, *, require_linebreak_cross: bool) -> None:
        nonlocal linebreak_person_candidates
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
            crosses_bridged_linebreak = "\n" in text[start:end]
            if require_linebreak_cross and not crosses_bridged_linebreak:
                # Redundant with the raw pass by construction (this pass
                # only changed the text at bridged line breaks -
                # anywhere else it's identical to the raw pass's own
                # input) - skipped before any exclusion check runs, not
                # just before being added, so an exclusion never gets
                # counted a second time.
                continue
            if (start, end) in evaluated_spans:
                continue
            evaluated_spans.add((start, end))

            if label == NER_LABEL_PERSON:
                start = _expand_person_start_left(text, start, end, occupied_ranges)
            # Overlap checks run *before* any exclusion-counting check
            # below, specifically so a same-region fragment the OTHER
            # pass already claimed (see this function's own docstring)
            # is silently dropped rather than separately counted as
            # excluded for an unrelated reason (single-token, allowlist,
            # ...) - that count would describe a fragment of an entity
            # that's already being redacted in full, not a real miss.
            if _overlaps_any(start, end, occupied_ranges):
                continue
            if _overlaps_any(start, end, accepted_ranges):
                continue
            exclusion_category = _ner_exclusion_category(text[start:end], label)
            if exclusion_category is not None:
                exclusion_counters[exclusion_category] += 1
                continue
            if label == NER_LABEL_PERSON and _person_single_token_exclusion(
                text,
                start,
                end,
            ):
                exclusion_counters[NER_EXCLUSION_SINGLE_TOKEN_PERSON] += 1
                continue
            if crosses_bridged_linebreak:
                if label == NER_LABEL_PERSON:
                    linebreak_person_candidates += 1
                else:
                    # See this function's own docstring: a non-person
                    # entity that only exists because of the bridging is
                    # far more likely to be an accidental merge than a
                    # genuine multi-line organization/location name.
                    exclusion_counters[NER_EXCLUSION_LINEBREAK_NON_PERSON] += 1
                    continue
            accepted_ranges.append((start, end))
            entities.append(NerEntity(start=start, end=end, label=label))
            counters[label] += 1

    raw_text = _analysis_text(text, bridge_linebreaks=False)
    bridged_text = _analysis_text(text)
    if bridged_text != raw_text:
        _process(context.nlp(bridged_text), require_linebreak_cross=True)

    _process(context.nlp(raw_text), require_linebreak_cross=False)

    return entities, counters, exclusion_counters, linebreak_person_candidates


def detect_entities(text: str, context: NerContext) -> tuple[list[NerEntity], dict[str, int]]:
    """Detect supported entities and return safe spans plus counters only."""
    entities, counters, _, _ = detect_entities_with_details(text, context)
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
    *,
    allowed_labels: frozenset[str] | None = None,
) -> tuple[str, dict[str, int], dict[str, object]]:
    """Apply local NER if available and return safe metadata.

    ``allowed_labels`` (Etap 4 category selection) restricts which
    detected entities actually get redacted in ``text`` - an entity
    whose label isn't in it is left untouched. Detection itself, and
    every counter this returns, stays unfiltered either way: this only
    controls what gets *substituted*, never what gets *reported* as
    found, so "detected but deliberately not redacted" stays visible in
    the report rather than silently disappearing. ``None`` (the
    default) redacts every label, exactly as before this parameter
    existed.
    """
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
        (
            entities,
            counters,
            exclusion_counters,
            linebreak_person_candidates,
        ) = detect_entities_with_details(text, context)
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

    redacted_entities = (
        entities
        if allowed_labels is None
        else [entity for entity in entities if entity.label in allowed_labels]
    )
    anonymized = anonymize_entities(text, redacted_entities)
    # Built from redacted_entities, not the full (unfiltered) counters
    # above - a category the caller excluded via allowed_labels must not
    # show up here as "handled". This is what flows into the main
    # report/checklist's detected-categories count (see
    # _anonymize_text_with_dictionary_counters), and it must match what
    # actually happened to the text: nothing was substituted for an
    # excluded label, so claiming it as anonymized would be a false
    # reassurance that PII was handled when it's still fully in the
    # clear. The full, unfiltered ``counters`` still goes into this
    # function's ner_metadata below, unaffected - the PDF coverage-
    # warning calculation (_attach_pdf_coverage_metadata) reads from
    # there and is separately made aware of active_labels to correctly
    # exclude a deliberate omission from triggering a false warning.
    active_counters: dict[str, int] = {}
    for entity in redacted_entities:
        active_counters[entity.label] = active_counters.get(entity.label, 0) + 1
    return (
        anonymized,
        active_counters,
        build_ner_metadata(
            enabled=context.enabled,
            used=True,
            status=NER_STATUS_AVAILABLE,
            model_name=context.model_name,
            counters=counters,
            exclusion_counters=exclusion_counters,
            linebreak_person_candidates=linebreak_person_candidates,
        ),
    )
