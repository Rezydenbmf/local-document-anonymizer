"""Persistence and regeneration for manual "magic pen" PDF redaction edits.

A user can, from the side-by-side comparison view, manually hide a piece of
text that automatic detection missed, or undo (un-redact) a specific
automatically detected rectangle that turned out to be a false positive.

Because true PDF redaction physically removes the underlying text (see
:func:`pdf_redaction.save_word_coordinate_redacted_pdf_copy`), an "undo" can
only be achieved by regenerating the visual PDF from the original source
file with that one rectangle excluded -- never by editing the already
redacted output file. This module stores the small list of such overrides
next to the output file (never any document content) and knows how to apply
them when regenerating.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path

try:
    from .anonymizer import compute_pdf_redaction_spans
    from .file_writers import IMAGE_EXTENSIONS, internal_artifacts_dir
    from .pdf_redaction import (
        MANUAL_REDACTION_LABEL,
        compute_redaction_rects,
        manual_edit_span_key,
        save_word_coordinate_redacted_image_copy,
        save_word_coordinate_redacted_pdf_copy,
    )
    from .sensitive_terms import SensitiveTerm
except ImportError:
    from anonymizer import compute_pdf_redaction_spans
    from file_writers import IMAGE_EXTENSIONS, internal_artifacts_dir
    from pdf_redaction import (
        MANUAL_REDACTION_LABEL,
        compute_redaction_rects,
        manual_edit_span_key,
        save_word_coordinate_redacted_image_copy,
        save_word_coordinate_redacted_pdf_copy,
    )
    from sensitive_terms import SensitiveTerm


MANUAL_EDITS_SUFFIX = "_MANUAL_EDITS"
MANUAL_EDITS_EXTENSION = ".json"
MANUAL_EDITS_SCHEMA = "local-document-anonymizer.manual-redaction-edits.v1"


@dataclass(frozen=True)
class ManualRect:
    """One manually drawn redaction rectangle, in PDF point coordinates."""

    page: int
    x0: float
    y0: float
    x1: float
    y1: float

    def as_tuple(self) -> tuple[float, float, float, float]:
        return (self.x0, self.y0, self.x1, self.y1)


@dataclass(frozen=True)
class ManualEdits:
    """Manual overrides for one PDF's true redaction."""

    removed: frozenset = field(default_factory=frozenset)
    added: tuple[ManualRect, ...] = ()

    @property
    def is_empty(self) -> bool:
        return not self.removed and not self.added


EMPTY_MANUAL_EDITS = ManualEdits()


def manual_edits_path(output_pdf_path: str | Path) -> Path:
    """Return the sidecar JSON path for one visual PDF output's manual edits.

    Lives in the hidden internal-artifacts subfolder next to the output's
    own folder - it is app state (geometry only, never document content),
    not a user-facing deliverable.
    """
    path = Path(output_pdf_path)
    internal_dir = internal_artifacts_dir(path.parent)
    return internal_dir / f"{path.stem}{MANUAL_EDITS_SUFFIX}{MANUAL_EDITS_EXTENSION}"


def load_manual_edits(path: str | Path) -> ManualEdits:
    """Load manual edits from disk, or return an empty set if unavailable."""
    try:
        raw_text = Path(path).read_text(encoding="utf-8")
        data = json.loads(raw_text)
    except (OSError, ValueError):
        return EMPTY_MANUAL_EDITS
    if not isinstance(data, dict):
        return EMPTY_MANUAL_EDITS

    removed_keys = set()
    for entry in data.get("removed", []) or []:
        if not isinstance(entry, list) or len(entry) != 6:
            continue
        page, label, x0, y0, x1, y1 = entry
        try:
            removed_keys.add(
                (int(page), str(label), float(x0), float(y0), float(x1), float(y1))
            )
        except (TypeError, ValueError):
            continue

    added_rects: list[ManualRect] = []
    for entry in data.get("added", []) or []:
        if not isinstance(entry, dict):
            continue
        try:
            added_rects.append(
                ManualRect(
                    page=int(entry["page"]),
                    x0=float(entry["x0"]),
                    y0=float(entry["y0"]),
                    x1=float(entry["x1"]),
                    y1=float(entry["y1"]),
                )
            )
        except (KeyError, TypeError, ValueError):
            continue

    return ManualEdits(removed=frozenset(removed_keys), added=tuple(added_rects))


def save_manual_edits(path: str | Path, edits: ManualEdits) -> Path:
    """Write manual edits to disk as a small JSON sidecar file."""
    destination = Path(path)
    payload = {
        "schema": MANUAL_EDITS_SCHEMA,
        "removed": [list(key) for key in sorted(edits.removed, key=str)],
        "added": [
            {"page": rect.page, "x0": rect.x0, "y0": rect.y0, "x1": rect.x1, "y1": rect.y1}
            for rect in edits.added
        ],
    }
    destination.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return destination


def _resolve_word_pages_and_spans(
    source_path: str | Path,
    *,
    word_pages: Sequence | None,
    spans: object,
    sensitive_terms: list[SensitiveTerm] | None,
    sensitive_terms_path: str | Path | None,
    use_ner: bool,
    ner_model_name: str,
    active_categories: Sequence[str] | None,
    active_labels: frozenset[str] | None = None,
    active_pages: frozenset[int] | None = None,
) -> tuple[Sequence, object]:
    """Return ``(word_pages, spans)`` as-given when both were supplied by
    the caller, otherwise recompute detection from scratch. Shared by
    :func:`regenerate_pdf_with_manual_overrides` and
    :func:`compute_visible_redaction_rects` so their "both or neither"
    precomputed-pair contract can't drift apart between the two.
    """
    if word_pages is not None and spans is not None:
        return word_pages, spans
    kwargs = {
        "sensitive_terms": sensitive_terms,
        "sensitive_terms_path": sensitive_terms_path,
        "use_ner": use_ner,
        "active_categories": active_categories,
        "active_labels": active_labels,
        "active_pages": active_pages,
    }
    if ner_model_name:
        kwargs["ner_model_name"] = ner_model_name
    return compute_pdf_redaction_spans(source_path, **kwargs)


def regenerate_pdf_with_manual_overrides(
    source_path: str | Path,
    *,
    output_path: str | Path,
    edits: ManualEdits,
    sensitive_terms: list[SensitiveTerm] | None = None,
    sensitive_terms_path: str | Path | None = None,
    use_ner: bool = False,
    ner_model_name: str = "",
    word_pages: Sequence | None = None,
    spans: object = None,
    active_categories: Sequence[str] | None = None,
    active_labels: frozenset[str] | None = None,
    active_pages: frozenset[int] | None = None,
) -> dict[str, object]:
    """Rebuild the true-redacted visual PDF in place, applying manual overrides.

    Reruns detection on the original source file (never on the already
    redacted output), then excludes ``edits.removed`` rectangles and adds
    ``edits.added`` rectangles before burning in the true redaction, exactly
    like the normal batch workflow does.

    A caller that already has ``word_pages``/``spans`` from an earlier
    detection pass on this exact source file in the same session (for
    example the comparison window's cache) can pass both to skip
    redetection entirely -- including a scanned document's OCR, the
    single most expensive step in this pipeline. Passing only one of the
    two is treated as not passing either, since a partial pair can't be
    used safely. When redetection does happen, ``active_labels`` should
    be the resolved label set loaded from the document's own sidecar
    (see category_selection_path/load_category_selection) - frozen to
    what was active when the document was first produced, not
    re-resolved against category_selection.py's *current* mapping (see
    compute_pdf_redaction_spans). Omitting both this and
    ``active_categories`` here would silently redact every category
    again, overriding whatever the user originally chose to leave
    unredacted. ``active_pages`` (Etap 5) is the same freeze-at-save-time
    story for the page-range restriction - see
    anonymizer.load_active_pages_selection.
    """
    word_pages, spans = _resolve_word_pages_and_spans(
        source_path,
        word_pages=word_pages,
        spans=spans,
        sensitive_terms=sensitive_terms,
        sensitive_terms_path=sensitive_terms_path,
        use_ner=use_ner,
        ner_model_name=ner_model_name,
        active_categories=active_categories,
        active_labels=active_labels,
        active_pages=active_pages,
    )

    extra_rects = [(rect.page, rect.as_tuple()) for rect in edits.added]
    if Path(source_path).suffix.lower() in IMAGE_EXTENSIONS:
        # A standalone scan/photo: its visual output is a PDF wrapping the
        # redacted image, so regeneration has to go through the image
        # writer rather than opening the source as if it were a PDF.
        return save_word_coordinate_redacted_image_copy(
            source_path,
            word_pages=word_pages,
            spans=spans,
            output_path=output_path,
            removed_span_keys=edits.removed,
            extra_redaction_rects=extra_rects,
        )
    return save_word_coordinate_redacted_pdf_copy(
        source_path,
        word_pages=word_pages,
        spans=spans,
        output_path=output_path,
        removed_span_keys=edits.removed,
        extra_redaction_rects=extra_rects,
        active_pages=active_pages,
    )


def compute_visible_redaction_rects(
    source_path: str | Path,
    *,
    edits: ManualEdits,
    sensitive_terms: list[SensitiveTerm] | None = None,
    sensitive_terms_path: str | Path | None = None,
    use_ner: bool = False,
    ner_model_name: str = "",
    word_pages: Sequence | None = None,
    spans: object = None,
    active_categories: Sequence[str] | None = None,
    active_labels: frozenset[str] | None = None,
    active_pages: frozenset[int] | None = None,
) -> list[dict[str, object]]:
    """Return every rectangle currently visible on a true-redacted PDF.

    Combines auto-detected rectangles (minus ``edits.removed``) with
    ``edits.added``, without opening or writing the true-redacted output
    file. Used to hit-test clicks in the comparison view's magic pen.

    Accepts an already-computed ``word_pages``/``spans`` pair (both or
    neither) the same way :func:`regenerate_pdf_with_manual_overrides`
    does, to skip redetection when a caller already has one from this
    session on this exact source file. See that function's docstring for
    why ``active_labels``/``active_categories``/``active_pages`` matter
    when redetection does happen.
    """
    word_pages, spans = _resolve_word_pages_and_spans(
        source_path,
        word_pages=word_pages,
        spans=spans,
        sensitive_terms=sensitive_terms,
        sensitive_terms_path=sensitive_terms_path,
        use_ner=use_ner,
        ner_model_name=ner_model_name,
        active_labels=active_labels,
        active_categories=active_categories,
        active_pages=active_pages,
    )
    auto_rects, _counters, _unmapped = compute_redaction_rects(
        word_pages, spans, removed_span_keys=edits.removed
    )
    added_rects = [
        {
            "page": rect.page,
            "label": MANUAL_REDACTION_LABEL,
            "x0": rect.x0,
            "y0": rect.y0,
            "x1": rect.x1,
            "y1": rect.y1,
        }
        for rect in edits.added
    ]
    return auto_rects + added_rects


MAGIC_PEN_REPORT_BEGIN = "--- Magic pen (manual PDF edits) ---"
MAGIC_PEN_REPORT_END = "--- end magic pen ---"


def apply_manual_redaction_count_to_report_text(
    report_text: str, manual_count: int
) -> str:
    """Add/update/remove a distinct magic-pen note in a _RAPORT.txt.

    A magic pen save regenerates the true-redacted PDF directly and never
    reruns the full text-based anonymization pipeline that originally wrote
    the report's category counts. Rather than rewriting those counts (which
    would make the report claim it re-ran detection it never actually ran),
    this appends a clearly separate, delimited note stating how many
    manually hidden fragments the *current* PDF contains -- so a reviewer
    sees both the original automatic detection and the manual override,
    without either being silently overwritten. Calling this again (for
    example after another magic pen save) replaces the note in place.
    """
    lines = report_text.splitlines()
    try:
        begin = lines.index(MAGIC_PEN_REPORT_BEGIN)
        end = lines.index(MAGIC_PEN_REPORT_END, begin)
        del lines[begin : end + 1]
        if (
            begin > 0
            and lines[begin - 1] == ""
            and begin < len(lines)
            and lines[begin] == ""
        ):
            del lines[begin - 1]
    except ValueError:
        pass

    if manual_count > 0:
        if lines and lines[-1] != "":
            lines.append("")
        lines.extend(
            [
                MAGIC_PEN_REPORT_BEGIN,
                f"* Manually hidden fragments currently in the PDF: {manual_count}",
                "* Note: the visual PDF may differ from the automatic categories above.",
                MAGIC_PEN_REPORT_END,
            ]
        )

    return "\n".join(lines) + "\n"


def rect_info_key(rect_info: Mapping[str, object]) -> tuple:
    """Return the geometry key for a rect dict as produced by rect helpers here."""
    as_rect = ManualRect(
        page=int(rect_info["page"]),
        x0=float(rect_info["x0"]),
        y0=float(rect_info["y0"]),
        x1=float(rect_info["x1"]),
        y1=float(rect_info["y1"]),
    )
    return manual_edit_span_key(as_rect.page, str(rect_info["label"]), as_rect)


def apply_pending_overrides(
    edits: ManualEdits,
    visible_rects: Sequence[Mapping[str, object]],
    pending_remove_keys: Sequence[tuple] | set[tuple],
    pending_add_rects: Sequence[ManualRect],
) -> ManualEdits:
    """Fold this-session staged magic-pen changes into a new :class:`ManualEdits`.

    ``visible_rects`` is what :func:`compute_visible_redaction_rects` returns
    for the *current* ``edits`` (so it already reflects prior overrides).
    Rects identified by a key in ``pending_remove_keys`` are excluded from
    the result: an auto-detected rectangle is folded into ``removed``, while
    a previously manually added rectangle is simply dropped from ``added``.
    ``pending_add_rects`` are appended as new manual additions.
    """
    removed = set(edits.removed)
    pending_remove = set(pending_remove_keys)
    kept_added = [
        rect
        for rect in edits.added
        if manual_edit_span_key(rect.page, MANUAL_REDACTION_LABEL, rect)
        not in pending_remove
    ]
    for rect_info in visible_rects:
        if str(rect_info["label"]) == MANUAL_REDACTION_LABEL:
            continue
        key = rect_info_key(rect_info)
        if key in pending_remove:
            removed.add(key)
    new_added = tuple(kept_added) + tuple(pending_add_rects)
    return ManualEdits(removed=frozenset(removed), added=new_added)


__all__ = [
    "EMPTY_MANUAL_EDITS",
    "MANUAL_REDACTION_LABEL",
    "ManualEdits",
    "ManualRect",
    "apply_manual_redaction_count_to_report_text",
    "apply_pending_overrides",
    "compute_visible_redaction_rects",
    "load_manual_edits",
    "manual_edit_span_key",
    "manual_edits_path",
    "rect_info_key",
    "regenerate_pdf_with_manual_overrides",
    "save_manual_edits",
]
