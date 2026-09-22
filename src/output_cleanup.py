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
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

try:
    from .file_writers import (
        INTERNAL_ARTIFACTS_DIRNAME,
        TXT_SUBFOLDER_DIRNAME,
        dated_output_dirname_to_date,
    )
except ImportError:
    from file_writers import (
        INTERNAL_ARTIFACTS_DIRNAME,
        TXT_SUBFOLDER_DIRNAME,
        dated_output_dirname_to_date,
    )


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


# The families a user actually wants to keep, per direct feedback: "po co
# nam te stare pliki - user chce mieć zanonimizowany [wynik] i oryginał, to
# dwa które potrzebuje; wszystkie te txt/checklisty nie potrzebuje". Every
# PDF output mode (visual/review/original_redacted) writes a different
# family for what is, depending on the user's chosen mode, *the* deliverable
# - so all of them count as a "final result", never just one. manual_edits
# is included too even though it looks internal: it is what lets a document
# be reopened and re-edited later (a real workflow - approval round-trips
# reported to take anywhere from same-day to two weeks), so silently
# dropping it would quietly break editability rather than just tidy up.
_FINAL_RESULT_FAMILIES = frozenset(
    {"anon_txt", "anon_docx", "visual", "review", "original_redacted", "manual_edits"}
)


def _family_of(group: str) -> str:
    """The output family for a classify_output_file() group - group is
    either the bare family name (batch-level artifacts) or
    "stem|family" (everything anchored to a document), so splitting off
    the last "|"-separated piece gets the family either way."""
    return group.rsplit("|", 1)[-1]


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


def _iter_files_in(folder: Path):
    for path in sorted(folder.iterdir()):
        if path.is_file():
            yield path


def _iter_one_output_folder(folder: Path):
    """Every tracked-output-candidate file directly in ``folder``, plus
    its own "_wewnetrzne" and "txt" children (see internal_artifacts_dir/
    file_writers.TXT_SUBFOLDER_DIRNAME) - the same three-location shape
    whether ``folder`` is an output workspace's root or one of its own
    "DD.MM.RRRR" dated subfolders (see _iter_output_files), so a folder
    handed to cleanup that already *is* a dated folder (e.g. the user
    picked it directly via "Wybierz inny folder") is scanned exactly as
    completely as one found by recursing into a root's dated child."""
    yield from _iter_files_in(folder)
    for subfolder_name in (INTERNAL_ARTIFACTS_DIRNAME, TXT_SUBFOLDER_DIRNAME):
        subfolder = folder / subfolder_name
        if subfolder.is_dir():
            yield from _iter_files_in(subfolder)


def _iter_output_files(output_dir: Path):
    yield from _iter_one_output_folder(output_dir)

    # A pre-dated-output-folder run left everything flat right here, no
    # dated subfolders at all - the loop below then simply finds none
    # and this function behaves exactly as it always has. A run made
    # after the redesign put everything one level down instead, in its
    # own "DD.MM.RRRR" folder - walked the same way as the root itself,
    # deliberately one explicit, bounded level, never a general
    # recursive walk, so this can never wander into a source document's
    # own unrelated subfolder.
    for entry in sorted(output_dir.iterdir()):
        if not entry.is_dir() or dated_output_dirname_to_date(entry.name) is None:
            continue
        yield from _iter_one_output_folder(entry)


def folder_has_any_tracked_output(output_dir: str | Path) -> bool:
    """True if ``output_dir`` still contains at least one file this app's
    own naming scheme recognizes (working or final) - used after a
    history cleanup to decide whether a folder is now empty of
    everything the app tracks and can be forgotten from the history
    list, without needing to touch anything else in that folder."""
    folder = Path(output_dir)
    if not folder.is_dir():
        return False
    for path in _iter_output_files(folder):
        if classify_output_file(path.name) is not None:
            return True
    return False


def build_output_cleanup_plan(output_dir: str | Path) -> OutputCleanupPlan:
    """Plan removal of every superseded generation in ``output_dir``.

    Keeps the newest generation of each document (and of the batch-level
    artifacts) and lists the rest. Never touches anything outside this
    app's own naming scheme, so source documents sitting in the same
    folder are not even candidates.

    Not wired to any button today (see BuildHistoryCleanupPlanTests'
    own docstring) - kept for its tests/possible reuse. Since
    _iter_output_files started recursing into "DD.MM.RRRR" dated
    subfolders, calling this on a root that has more than one such
    subfolder would compare generation numbers *across different days*
    (e.g. day 1's only run and day 2's only run both look like
    "generation 1" of the same document name) - if this is ever wired
    up again, it needs to group per dated folder, not just per document
    name, or it can delete a still-current file from an earlier day
    while keeping a same-numbered but actually older one from a later
    day.
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


def _plan_from_paths(paths: list[Path], *, kept_count: int) -> OutputCleanupPlan:
    total_bytes = 0
    for path in paths:
        try:
            total_bytes += path.stat().st_size
        except OSError:
            continue
    return OutputCleanupPlan(
        removable_paths=tuple(paths), kept_count=kept_count, total_bytes=total_bytes
    )


def build_history_cleanup_plan(
    output_dirs: Sequence[str | Path],
) -> tuple[OutputCleanupPlan, OutputCleanupPlan]:
    """Plan a single "Wyczyść historię" sweep across every folder in the
    user's output history at once - one button for the whole history
    instead of one per folder, per direct feedback that a button repeated
    per folder was pointless when it always does the same thing.

    Unlike build_output_cleanup_plan (kept for its own tests/possible
    reuse, but no longer wired to any button), this is not generation-
    aware - it does not matter whether a file is the newest run or the
    oldest. What matters is *what kind* of file it is: working/internal
    files (reports, checklists, batch summaries) are always removable;
    the final-result families (see _FINAL_RESULT_FAMILIES) are only
    removable on the caller's separate, explicit opt-in - the two-tier
    "always clear junk, only optionally clear real results" the user
    asked for.

    Returns ``(working_plan, final_plan)`` from a *single* filesystem
    walk - deliberately not two separate calls the caller diffs against
    each other (an earlier version worked that way). Two independent
    scans open a race window where a file changes or disappears between
    them, and forced the caller to derive final_plan's byte total by
    subtracting two already-summed totals - which can go visibly wrong
    (even negative) if that race is hit, right before an irreversible
    deletion. One walk, two buckets, each plan's own total summed
    directly from its own paths, makes that class of bug structurally
    impossible rather than merely unlikely.

    Deduplicates by resolved path across every folder in ``output_dirs``
    - the user's history can legitimately contain both an output root
    and one of its own "DD.MM.RRRR" dated subfolders at once (picking a
    dated folder directly via "Wybierz inny folder" adds it to history
    too, alongside the root a batch run itself already added), and
    ``_iter_output_files`` recurses into dated children - so without
    this, a file under the overlap would be listed and summed twice,
    and the second of its two deletions would fail with "file not
    found" right after the first one already succeeded, misreporting a
    real success as a failure.
    """
    working_paths: list[Path] = []
    final_paths: list[Path] = []
    seen_paths: set[Path] = set()
    for output_dir in output_dirs:
        folder = Path(output_dir)
        if not folder.is_dir():
            continue
        for path in _iter_output_files(folder):
            resolved_path = path.resolve()
            if resolved_path in seen_paths:
                continue
            seen_paths.add(resolved_path)
            classified = classify_output_file(path.name)
            if classified is None:
                continue
            group, _generation = classified
            if _family_of(group) in _FINAL_RESULT_FAMILIES:
                final_paths.append(path)
            else:
                working_paths.append(path)

    working_plan = _plan_from_paths(working_paths, kept_count=len(final_paths))
    final_plan = _plan_from_paths(final_paths, kept_count=0)
    return working_plan, final_plan


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
    size_text = format_file_size(plan.total_bytes)
    return (
        f"Do usunięcia: {plan.removable_count} starszych plików ({size_text}). "
        f"Najnowsza wersja każdego dokumentu zostaje ({plan.kept_count} plików)."
    )


def format_file_size(total_bytes: int) -> str:
    """Human-readable byte count for a confirmation dialog - MB above
    ~100KB, KB below (never "0 KB", even for a handful of tiny files)."""
    megabytes = total_bytes / (1024 * 1024)
    return f"{megabytes:.1f} MB" if megabytes >= 0.1 else f"{max(total_bytes // 1024, 1)} KB"


def format_history_cleanup_summary(
    plan: OutputCleanupPlan, *, include_final_outputs: bool
) -> str:
    """One human-readable line for the "Wyczyść historię" confirmation -
    deliberately separate from format_cleanup_plan_summary, since that one
    talks about "the newest generation" (build_output_cleanup_plan's
    concept), which does not apply here: build_history_cleanup_plan keeps
    or removes by file *kind*, not by version number."""
    if plan.is_empty:
        return "Brak plików do usunięcia w historii."
    size_text = format_file_size(plan.total_bytes)
    if include_final_outputs:
        return (
            f"Do usunięcia: {plan.removable_count} plików ({size_text}), "
            "łącznie z finalnymi wynikami anonimizacji."
        )
    return (
        f"Do usunięcia: {plan.removable_count} plików roboczych ({size_text}). "
        f"Finalne wyniki anonimizacji zostają ({plan.kept_count} plików)."
    )
