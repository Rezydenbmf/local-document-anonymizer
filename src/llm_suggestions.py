"""Bridges local-LLM comparison/narrative review results (llm_review.py)
to concrete PDF locations, for the comparison window's suggestion-review
UI (PDF only for now - see docs/PROJECT_STATE.md, 2026-09-23, for why
DOCX/TXT has no equivalent visual mechanism yet).

Why word-level matching, not character offsets
------------------------------------------------
The document's ORIGINAL text that llm_review.py splits into numbered
sentences (see anonymizer.py's PDF pipeline) comes from a different
extraction library (pypdf, via file_readers.read_pdf_file_pages) than
the word-coordinate geometry every redaction rect in this app is
resolved against (PyMuPDF, via pdf_redaction.extract_pdf_word_pages).
Two different PDF text extractors can disagree
on whitespace/line-joining for the exact same visible content, so a
character-offset span computed against one library's text is not
guaranteed to land correctly against the other's.

Matching at the WORD level sidesteps this: both extractors tokenize on
whitespace, so a sentence's whitespace-split words should still appear,
in order, in the PyMuPDF word list for the page that sentence is on,
even if inter-word spacing/line-breaks differ. Finding that contiguous
word run and reusing pdf_redaction.merge_rects_by_line (the same
line-grouping logic every auto-detected redaction rect already goes
through - see anonymizer._pdf_detection_spans_for_word_pages, which
computes every auto-detected span against `PdfWordPage.text`) keeps
this consistent with, not parallel to, the existing detection-to-rect
pipeline. A sentence that can't be found this way resolves to no rect
at all rather than a guessed, possibly-wrong one - the suggestion
still surfaces (with its category) for the user to locate and act
on manually.

Known limitations (fail closed, not silently wrong, but worth naming):
a sentence that legitimately repeats verbatim elsewhere in the same
document (a name in both a letterhead and a signature block, a
boilerplate footer) resolves to whichever occurrence is found first,
not necessarily the one the model meant - there is no page-position
hint in the LLM's output to disambiguate, by design (see llm_review.py
- the model is deliberately never told, or allowed to return, more
than a bare sentence number). A sentence broken across a PDF line/page
in a way that tokenizes differently between the two extraction
libraries (e.g. a hyphenated compound word split at the exact point
the line wraps - the same bug class anonymizer.py's auto-detection
already had to special-case for regex/NER spans) fails closed to "not
found" here rather than reusing that same widening logic.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path

try:
    from .file_writers import internal_artifacts_dir
    from .llm_review import normalize_review_text, split_into_review_sentences
    from .pdf_redaction import PdfWord, PdfWordPage, merge_rects_by_line
except ImportError:
    from file_writers import internal_artifacts_dir
    from llm_review import normalize_review_text, split_into_review_sentences
    from pdf_redaction import PdfWord, PdfWordPage, merge_rects_by_line

LLM_SUGGESTIONS_SUFFIX = "_LLM_SUGGESTIONS"
LLM_SUGGESTIONS_EXTENSION = ".json"
LLM_SUGGESTIONS_SCHEMA = "local-document-anonymizer.llm-suggestions.v1"


AI_SUGGESTION_STATUS_PENDING = "pending"
AI_SUGGESTION_STATUS_ACCEPTED = "accepted"
AI_SUGGESTION_STATUS_REJECTED = "rejected"
AI_SUGGESTION_STATUSES = (
    AI_SUGGESTION_STATUS_PENDING,
    AI_SUGGESTION_STATUS_ACCEPTED,
    AI_SUGGESTION_STATUS_REJECTED,
)

AI_SUGGESTION_SOURCE_COMPARISON = "comparison"
AI_SUGGESTION_SOURCE_NARRATIVE = "narrative"


@dataclass(frozen=True)
class AiSuggestion:
    """One reviewable local-LLM suggestion, resolved as far as possible
    to a real PDF location. ``rects`` is only ever populated for a
    comparison "missed_redaction" finding whose sentence could be found
    on a page (see module docstring) - every other case (unnecessary_
    redaction, a narrative combination, or a sentence that could not be
    located) still gets a ``page`` for navigation when resolvable, but
    leaves the exact area for the user to mark manually."""

    id: str
    source: str
    category: str
    justification: str
    sentence_indices: tuple[int, ...]
    finding_type: str | None = None
    confidence: str | None = None
    page: int | None = None
    rects: tuple[dict[str, object], ...] = field(default_factory=tuple)
    status: str = AI_SUGGESTION_STATUS_PENDING


def _sentence_text(sentences: Sequence[str], index: object) -> str | None:
    if not isinstance(index, int) or isinstance(index, bool):
        return None
    if index < 1 or index > len(sentences):
        return None
    return sentences[index - 1]


def _find_word_run(haystack: Sequence[str], needle: Sequence[str]) -> int | None:
    """Return the start index of the first place ``needle`` appears as a
    contiguous run in ``haystack``, or None. Tries an exact match first,
    then a case-insensitive one - never a fuzzier match than that, so a
    "found" result is always a genuine, unambiguous word-for-word run."""
    haystack_len, needle_len = len(haystack), len(needle)
    if needle_len == 0 or needle_len > haystack_len:
        return None
    for start in range(haystack_len - needle_len + 1):
        if haystack[start : start + needle_len] == needle:
            return start
    lowered_haystack = [word.lower() for word in haystack]
    lowered_needle = [word.lower() for word in needle]
    for start in range(haystack_len - needle_len + 1):
        if lowered_haystack[start : start + needle_len] == lowered_needle:
            return start
    return None


def resolve_sentence_rects(
    sentence_text: str,
    category: str,
    word_pages: Sequence[PdfWordPage],
) -> tuple[int, list[dict[str, object]]] | None:
    """Find which page ``sentence_text`` is on and the rect(s) covering
    it, by locating its words as a contiguous run in that page's word
    list. Returns ``(page_number, rects)`` for the first page a full
    match is found on, or None if no page contains the whole sentence
    as one unbroken word run (e.g. it was split across a page break)."""
    target_words = sentence_text.split()
    if not target_words:
        return None
    for page in word_pages:
        page_word_texts = [word.text for word in page.words]
        match_start = _find_word_run(page_word_texts, target_words)
        if match_start is None:
            continue
        matched_words: Sequence[PdfWord] = page.words[
            match_start : match_start + len(target_words)
        ]
        rects = [
            {
                "page": page.page_number,
                "label": category,
                "x0": round(rect.x0, 2),
                "y0": round(rect.y0, 2),
                "x1": round(rect.x1, 2),
                "y1": round(rect.y1, 2),
            }
            for rect in merge_rects_by_line(matched_words)
        ]
        return page.page_number, rects
    return None


def resolve_sentence_page(
    sentence_text: str, word_pages: Sequence[PdfWordPage]
) -> int | None:
    """Like resolve_sentence_rects but only the page number - used for
    narrative suggestions, which never get an auto-proposed rect (see
    AiSuggestion docstring)."""
    resolved = resolve_sentence_rects(sentence_text, "", word_pages)
    return resolved[0] if resolved else None


def build_ai_suggestions(
    original_text: str,
    *,
    comparison_result: dict[str, object] | None,
    narrative_result: dict[str, object] | None,
    word_pages: Sequence[PdfWordPage],
) -> list[AiSuggestion]:
    """Build the reviewable suggestion list for one PDF document from
    its raw llm_review.py results. ``original_text`` must be the exact
    same text that was passed to run_llm_comparison_review/
    run_llm_narrative_review (normalized here the same way those
    functions normalize it, via llm_review.normalize_review_text, so a
    leading BOM can't shift sentence 1 out of alignment), so sentence
    numbering matches."""
    sentences = split_into_review_sentences(normalize_review_text(original_text))
    suggestions: list[AiSuggestion] = []

    comparison_findings = (
        comparison_result.get("findings") if isinstance(comparison_result, dict) else None
    ) or []
    for index, finding in enumerate(comparison_findings):
        if not isinstance(finding, dict):
            continue
        sentence_index = finding.get("sentence_index")
        sentence_text = _sentence_text(sentences, sentence_index)
        category = str(finding.get("category", ""))
        finding_type = finding.get("finding_type")
        page: int | None = None
        rects: list[dict[str, object]] = []
        if sentence_text:
            if finding_type == "missed_redaction":
                resolved = resolve_sentence_rects(sentence_text, category, word_pages)
                if resolved:
                    page, rects = resolved
            else:
                page = resolve_sentence_page(sentence_text, word_pages)
        valid_sentence_index = (
            isinstance(sentence_index, int) and not isinstance(sentence_index, bool)
        )
        suggestions.append(
            AiSuggestion(
                id=f"comparison-{index}",
                source=AI_SUGGESTION_SOURCE_COMPARISON,
                category=category,
                justification=str(finding.get("justification", "")),
                sentence_indices=(sentence_index,) if valid_sentence_index else (),
                finding_type=str(finding_type) if finding_type else None,
                page=page,
                rects=tuple(rects),
            )
        )

    narrative_suggestions = (
        narrative_result.get("suggestions") if isinstance(narrative_result, dict) else None
    ) or []
    for index, suggestion in enumerate(narrative_suggestions):
        if not isinstance(suggestion, dict):
            continue
        raw_indices = suggestion.get("sentence_indices") or []
        indices = tuple(
            value
            for value in raw_indices
            if isinstance(value, int) and not isinstance(value, bool)
        )
        page = None
        for sentence_index in indices:
            sentence_text = _sentence_text(sentences, sentence_index)
            if not sentence_text:
                continue
            page = resolve_sentence_page(sentence_text, word_pages)
            if page is not None:
                break
        suggestions.append(
            AiSuggestion(
                id=f"narrative-{index}",
                source=AI_SUGGESTION_SOURCE_NARRATIVE,
                category=str(suggestion.get("category", "")),
                justification=str(suggestion.get("justification", "")),
                sentence_indices=indices,
                confidence=str(suggestion.get("confidence"))
                if suggestion.get("confidence")
                else None,
                page=page,
            )
        )

    return suggestions


def review_text_fingerprint(text: str) -> str:
    """SHA-256 of the exact (normalized) text a review was run on.

    Stored in the sidecar instead of the text itself, so the comparison
    window can prove that the text it reconstructs on open (see
    anonymizer.candidate_llm_review_texts) is the very text the model
    numbered - a different OCR engine version, or a PDF whose text layer
    the two extraction libraries disagree about, would otherwise shift
    every sentence number silently and put a proposed rect on the wrong
    sentence. A one-way hash of a whole document is not document content.
    """
    normalized = normalize_review_text(text)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def select_review_text(
    candidates: Sequence[str], fingerprint: str | None
) -> str | None:
    """Pick which reconstructed candidate text the model actually saw.

    With a fingerprint: the first candidate whose hash matches, or None if
    none does (fail closed - suggestions then surface without a location
    rather than on a possibly-wrong sentence). Without one (a sidecar
    written before the fingerprint existed): the first non-empty
    candidate, i.e. the same priority order the pipeline itself uses.
    """
    if fingerprint:
        for candidate in candidates:
            if review_text_fingerprint(candidate) == fingerprint:
                return candidate
        return None
    for candidate in candidates:
        if candidate.strip():
            return candidate
    return None


def ai_suggestion_sentence_texts(
    original_text: str, suggestion: AiSuggestion
) -> list[str]:
    """The locally-resolved sentence text(s) a suggestion points at - never
    anything taken from model output (see llm_review.py)."""
    sentences = split_into_review_sentences(normalize_review_text(original_text))
    texts = []
    for index in suggestion.sentence_indices:
        text = _sentence_text(sentences, index)
        if text:
            texts.append(text)
    return texts


def locate_sentence_texts(
    sentence_texts: Sequence[str], word_pages: Sequence[PdfWordPage]
) -> list[dict[str, object]]:
    """Rects covering every resolvable sentence in ``sentence_texts`` -
    used as a location hint (the dashed "look here" outline) for
    suggestions that get no auto-proposed redaction rect of their own."""
    rects: list[dict[str, object]] = []
    for text in sentence_texts:
        resolved = resolve_sentence_rects(text, "", word_pages)
        if resolved:
            rects.extend(resolved[1])
    return rects


# How much of the shorter rect's height two rects must share to count as
# the same line. Word boxes on tightly-leaded lines touch or overlap their
# neighbours by a fraction of a point; any-overlap would let an accepted
# "unnecessary redaction" un-redact PII on the line above or below.
_SAME_LINE_MIN_VERTICAL_OVERLAP = 0.5


def _rects_overlap(first: Mapping[str, object], second: Mapping[str, object]) -> bool:
    if int(first["page"]) != int(second["page"]):
        return False
    if not (
        float(first["x0"]) < float(second["x1"]) and float(second["x0"]) < float(first["x1"])
    ):
        return False
    shared = min(float(first["y1"]), float(second["y1"])) - max(
        float(first["y0"]), float(second["y0"])
    )
    shorter = min(
        float(first["y1"]) - float(first["y0"]), float(second["y1"]) - float(second["y0"])
    )
    return shorter > 0 and shared > shorter * _SAME_LINE_MIN_VERTICAL_OVERLAP


def redactions_overlapping_area(
    redaction_rects: Sequence[Mapping[str, object]],
    area_rects: Sequence[Mapping[str, object]],
) -> list[Mapping[str, object]]:
    """Existing redaction rects that overlap any of ``area_rects`` - how an
    accepted "unnecessary_redaction" finding maps onto concrete redactions
    to un-redact (the model only ever points at a sentence)."""
    return [
        rect
        for rect in redaction_rects
        if any(_rects_overlap(rect, area) for area in area_rects)
    ]


def ai_suggestion_ids(
    comparison_result: dict[str, object] | None,
    narrative_result: dict[str, object] | None,
) -> list[str]:
    """Every suggestion id build_ai_suggestions would produce for these
    results, without needing the document text or word geometry - lets
    the main window's approval gate count unresolved suggestions cheaply.
    Must enumerate exactly the way build_ai_suggestions does."""
    ids: list[str] = []
    for source, key, result in (
        (AI_SUGGESTION_SOURCE_COMPARISON, "findings", comparison_result),
        (AI_SUGGESTION_SOURCE_NARRATIVE, "suggestions", narrative_result),
    ):
        items = (result.get(key) if isinstance(result, dict) else None) or []
        for index, item in enumerate(items):
            if isinstance(item, dict):
                ids.append(f"{source}-{index}")
    return ids


def llm_suggestions_path(output_pdf_path: str | Path) -> Path:
    """Sidecar JSON path for one visual PDF output's raw LLM comparison/
    narrative review results - mirrors manual_redaction.manual_edits_path
    (same hidden internal-artifacts folder, same "app state, not a
    user-facing deliverable" reasoning). Holds only the already-sanitized
    llm_review.py result dicts (status, categories, truncated
    justifications, sentence numbers) - never document content."""
    path = Path(output_pdf_path)
    internal_dir = internal_artifacts_dir(path.parent)
    return internal_dir / f"{path.stem}{LLM_SUGGESTIONS_SUFFIX}{LLM_SUGGESTIONS_EXTENSION}"


def save_llm_suggestions_result(
    path: str | Path,
    *,
    comparison_result: dict[str, object] | None,
    narrative_result: dict[str, object] | None,
    original_text: str | None = None,
) -> Path:
    """Persist the raw comparison/narrative results next to a visual PDF
    output, so the comparison window can build its suggestion list on
    open without re-running the local LLM every time it's opened.
    ``original_text`` - the exact text the model reviewed - is only ever
    stored as its fingerprint (see review_text_fingerprint). A fresh
    save always starts with no user decisions ("resolved" is empty): it
    belongs to a freshly-written output file."""
    destination = Path(path)
    payload = {
        "schema": LLM_SUGGESTIONS_SCHEMA,
        "comparison_result": (
            comparison_result if isinstance(comparison_result, dict) else None
        ),
        "narrative_result": (
            narrative_result if isinstance(narrative_result, dict) else None
        ),
        "original_text_sha256": (
            review_text_fingerprint(original_text) if original_text is not None else None
        ),
        "resolved": {},
    }
    destination.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return destination


def _valid_resolutions(resolved: object) -> dict[str, str]:
    """Keep only well-formed ``{id: accepted|rejected}`` entries - a
    corrupt or hand-edited value must never be trusted verbatim."""
    if not isinstance(resolved, Mapping):
        return {}
    return {
        key: value
        for key, value in resolved.items()
        if isinstance(key, str)
        and value in (AI_SUGGESTION_STATUS_ACCEPTED, AI_SUGGESTION_STATUS_REJECTED)
    }


@dataclass(frozen=True)
class LlmSuggestionsSidecar:
    """Everything the suggestions sidecar holds - see
    save_llm_suggestions_result. ``resolved`` maps a suggestion id to the
    user's saved decision (ids and statuses only, never content)."""

    comparison_result: dict[str, object] | None = None
    narrative_result: dict[str, object] | None = None
    original_text_sha256: str | None = None
    resolved: Mapping[str, str] = field(default_factory=dict)

    def unresolved_ids(self) -> list[str]:
        return [
            suggestion_id
            for suggestion_id in ai_suggestion_ids(
                self.comparison_result, self.narrative_result
            )
            if suggestion_id not in self.resolved
        ]


EMPTY_LLM_SUGGESTIONS_SIDECAR = LlmSuggestionsSidecar()


def load_llm_suggestions_sidecar(path: str | Path) -> LlmSuggestionsSidecar:
    """Load the whole sidecar, or an empty one if it is missing/corrupt -
    build_ai_suggestions already treats a missing result as "no
    suggestions from that source", the same fail-safe default as if the
    feature had never been enabled for this document."""
    try:
        raw_text = Path(path).read_text(encoding="utf-8")
        data = json.loads(raw_text)
    except (OSError, ValueError):
        return EMPTY_LLM_SUGGESTIONS_SIDECAR
    if not isinstance(data, dict):
        return EMPTY_LLM_SUGGESTIONS_SIDECAR
    comparison_result = data.get("comparison_result")
    narrative_result = data.get("narrative_result")
    fingerprint = data.get("original_text_sha256")
    return LlmSuggestionsSidecar(
        comparison_result=(
            comparison_result if isinstance(comparison_result, dict) else None
        ),
        narrative_result=narrative_result if isinstance(narrative_result, dict) else None,
        original_text_sha256=fingerprint if isinstance(fingerprint, str) else None,
        resolved=_valid_resolutions(data.get("resolved")),
    )


def load_llm_suggestions_result(
    path: str | Path,
) -> tuple[dict[str, object] | None, dict[str, object] | None]:
    """Load a previously-saved (comparison_result, narrative_result) pair,
    or (None, None) if the sidecar is missing or corrupt."""
    sidecar = load_llm_suggestions_sidecar(path)
    return sidecar.comparison_result, sidecar.narrative_result


def save_ai_suggestion_resolutions(
    path: str | Path, resolutions: Mapping[str, str]
) -> Path | None:
    """Merge the user's accept/reject decisions into an existing sidecar,
    keeping everything else exactly as it was. Writes nothing (returns
    None) when there is no sidecar to merge into - a decision only means
    something for results that were actually saved."""
    destination = Path(path)
    if not destination.is_file():
        return None
    sidecar = load_llm_suggestions_sidecar(destination)
    merged = dict(sidecar.resolved)
    merged.update(_valid_resolutions(resolutions))
    payload = {
        "schema": LLM_SUGGESTIONS_SCHEMA,
        "comparison_result": sidecar.comparison_result,
        "narrative_result": sidecar.narrative_result,
        "original_text_sha256": sidecar.original_text_sha256,
        "resolved": merged,
    }
    destination.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return destination


def count_unresolved_ai_suggestions(output_pdf_path: str | Path) -> int:
    """How many suggestions for this output still await a decision - the
    main window's approval gate. 0 when there is no sidecar at all."""
    sidecar = load_llm_suggestions_sidecar(llm_suggestions_path(output_pdf_path))
    return len(sidecar.unresolved_ids())


__all__ = [
    "AI_SUGGESTION_SOURCE_COMPARISON",
    "AI_SUGGESTION_SOURCE_NARRATIVE",
    "AI_SUGGESTION_STATUSES",
    "AI_SUGGESTION_STATUS_ACCEPTED",
    "AI_SUGGESTION_STATUS_PENDING",
    "AI_SUGGESTION_STATUS_REJECTED",
    "EMPTY_LLM_SUGGESTIONS_SIDECAR",
    "AiSuggestion",
    "LlmSuggestionsSidecar",
    "ai_suggestion_ids",
    "ai_suggestion_sentence_texts",
    "build_ai_suggestions",
    "count_unresolved_ai_suggestions",
    "llm_suggestions_path",
    "load_llm_suggestions_result",
    "load_llm_suggestions_sidecar",
    "locate_sentence_texts",
    "redactions_overlapping_area",
    "resolve_sentence_page",
    "resolve_sentence_rects",
    "review_text_fingerprint",
    "save_ai_suggestion_resolutions",
    "save_llm_suggestions_result",
    "select_review_text",
]
