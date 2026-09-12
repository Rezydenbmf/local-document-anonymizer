"""Finding and removing superseded output files in one output folder.

Every anonymization run writes a full set of companion files and nothing
ever removes them, so a folder that gets re-used - the normal way people
work - accumulates one numbered generation per run. An audit of what the
app leaves on disk raised this directly: more generations mean a larger
surface to look after, and a stale generation can be worse than clutter
(a file produced by an older, buggier version can be less redacted than
the current one, while looking just as finished).

Selecting what to delete is kept here as pure, testable functions with no
GUI and no deletion of its own, deliberately:

* Only files this app itself writes are ever considered - matched against
  its own naming scheme, anchored to a source stem. A user pointing the
  output at the folder their source documents live in is normal, and
  their originals (and anything else of theirs) must be untouchable.
* The newest generation of every document is always kept.
* Nothing is removed without the caller confirming a concrete plan first.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

try:
    from .file_writers import INTERNAL_ARTIFACTS_DIRNAME
except ImportError:
    from file_writers import INTERNAL_ARTIFACTS_DIRNAME


# Batch-level artifacts first: one per run, with no document stem of
# their own, and their names would otherwise also match the document
# patterns below with a stem of "_BATCH".
_BATCH_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("batch_summary", re.compile(r"^_BATCH_SUMMARY(?P<number>_\d+)?\.txt$")),
    (
        "batch_checklist",
        re.compile(r"^_BATCH_REVIEW_CHECKLIST(?P<number>_\d+)?\.txt$"),
    ),
)
# Output families, each anchored to a document stem and ending in an
# optional generation number. Anything that does not match one of these -
# a source document, a user's own note, an unrelated PDF - is invisible to
# this module by construction.
_OUTPUT_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("anon_txt", re.compile(r"^(?P<stem>.+)_ANON(?P<number>_\d+)?\.txt$")),
    ("anon_docx", re.compile(r"^(?P<stem>.+)_ANON(?P<number>_\d+)?\.docx$")),
    ("visual", re.compile(r"^(?P<stem>.+)_ANON_VISUAL(?P<number>_\d+)?\.pdf$")),
    ("review", re.compile(r"^(?P<stem>.+)_ANON_REVIEW(?P<number>_\d+)?\.pdf$")),
    (
        "original_redacted",
        re.compile(r"^(?P<stem>.+)_ORIGINAL_REDACTED(?P<number>_\d+)?\.pdf$"),
    ),
    ("report", re.compile(r"^(?P<stem>.+)_RAPORT(?P<number>_\d+)?\.txt$")),
    (
        "checklist",
        re.compile(r"^(?P<stem>.+)_REVIEW_CHECKLIST(?P<number>_\d+)?\.txt$"),
    ),
    (
        "manual_edits",
        re.compile(r"^(?P<stem>.+)_MANUAL_EDITS(?P<number>_\d+)?\.json$"),
    ),
)


def _generation_number(raw_number: str | None) -> int:
    """Generation for a collision suffix: "" is the first, "_2" the
    second, and so on."""
    if not raw_number:
        return 1
    return int(raw_number.lstrip("_"))


def classify_output_file(file_name: str) -> tuple[str, int] | None:
    """Return ``(group, generation)`` for a file this app wrote, else None.

    ``group`` combines the document stem with the output family, so the
    newest generation is kept *per family*. Grouping by stem alone looked
    simpler but was wrong: reports and checklists are still numbered
    independently of the main outputs, so a folder can legitimately hold
    ``umowa_ANON_3.txt`` next to ``umowa_RAPORT_2.txt`` - and a
    stem-wide "keep only generation 3" would delete that report, leaving
    the newest run with none at all.
    """
    for family, pattern in _BATCH_PATTERNS:
        match = pattern.match(file_name)
        if match is not None:
            return family, _generation_number(match.group("number"))
    for family, pattern in _OUTPUT_PATTERNS:
        match = pattern.match(file_name)
        if match is not None:
            stem = match.group("stem")
            return f"{stem}|{family}", _generation_number(match.group("number"))
    return None


@dataclass(frozen=True)
class OutputCleanupPlan:
    """What a cleanup would remove, for confirmation before anything is."""

    removable_paths: tuple[Path, ...]
    kept_count: int
    total_bytes: int

    @property
    def removable_count(self) -> int:
        return len(self.removable_paths)

    @property
    def is_empty(self) -> bool:
        return not self.removable_paths


def _iter_output_files(output_dir: Path):
    for path in sorted(output_dir.iterdir()):
        if path.is_file():
            yield path
    internal_dir = output_dir / INTERNAL_ARTIFACTS_DIRNAME
    if internal_dir.is_dir():
        for path in sorted(internal_dir.iterdir()):
            if path.is_file():
                yield path


def build_output_cleanup_plan(output_dir: str | Path) -> OutputCleanupPlan:
    """Plan removal of every superseded generation in ``output_dir``.

    Keeps the newest generation of each document (and of the batch-level
    artifacts) and lists the rest. Never touches anything outside this
    app's own naming scheme, so source documents sitting in the same
    folder are not even candidates.
    """
    folder = Path(output_dir)
    if not folder.is_dir():
        return OutputCleanupPlan(removable_paths=(), kept_count=0, total_bytes=0)

    by_group: dict[str, list[tuple[int, Path]]] = {}
    for path in _iter_output_files(folder):
        classified = classify_output_file(path.name)
        if classified is None:
            continue
        group, generation = classified
        by_group.setdefault(group, []).append((generation, path))

    removable: list[Path] = []
    kept = 0
    for entries in by_group.values():
        newest = max(generation for generation, _path in entries)
        for generation, path in entries:
            if generation == newest:
                kept += 1
            else:
                removable.append(path)

    total_bytes = 0
    for path in removable:
        try:
            total_bytes += path.stat().st_size
        except OSError:
            continue
    return OutputCleanupPlan(
        removable_paths=tuple(removable), kept_count=kept, total_bytes=total_bytes
    )


def apply_output_cleanup_plan(plan: OutputCleanupPlan) -> tuple[int, int]:
    """Delete the planned files; return ``(removed, failed)``.

    Deletes only what the plan lists - a plan the caller has already had
    confirmed - and never gives up the whole operation because one file
    happened to be locked or already gone.
    """
    removed = 0
    failed = 0
    for path in plan.removable_paths:
        try:
            path.unlink()
        except OSError:
            failed += 1
        else:
            removed += 1
    return removed, failed


def format_cleanup_plan_summary(plan: OutputCleanupPlan) -> str:
    """One human-readable line describing a plan, for the confirmation."""
    if plan.is_empty:
        return "Brak starszych wersji do usunięcia - w folderze jest tylko najnowszy wynik."
    megabytes = plan.total_bytes / (1024 * 1024)
    size_text = (
        f"{megabytes:.1f} MB" if megabytes >= 0.1 else f"{max(plan.total_bytes // 1024, 1)} KB"
    )
    return (
        f"Do usunięcia: {plan.removable_count} starszych plików ({size_text}). "
        f"Najnowsza wersja każdego dokumentu zostaje ({plan.kept_count} plików)."
    )
