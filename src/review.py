"""Manual review workflow metadata for generated anonymized outputs."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path, PurePosixPath, PureWindowsPath
import re

from file_writers import build_collision_safe_path


REVIEW_STATUS_APPROVED = "approved"
REVIEW_STATUS_NEEDS_REVIEW = "needs_review"
REVIEW_STATUS_REJECTED = "rejected"
REVIEW_STATUSES = (
    REVIEW_STATUS_APPROVED,
    REVIEW_STATUS_NEEDS_REVIEW,
    REVIEW_STATUS_REJECTED,
)
DEFAULT_REVIEW_STATUS = REVIEW_STATUS_NEEDS_REVIEW
REVIEW_STATUS_FILENAME = "_REVIEW_STATUS.json"
REVIEW_SUMMARY_FILENAME = "_REVIEW_SUMMARY.txt"
REVIEW_SCHEMA = "local-document-anonymizer.review-status.v1"

_ANON_STEM_PATTERN = re.compile(r"^(?P<base>.+)_ANON(?P<number>_\d+)?$")
_REPORT_STEM_PATTERN = re.compile(r"^(?P<base>.+)_RAPORT(?P<number>_\d+)?$")
_BATCH_SUMMARY_PATTERN = re.compile(r"^_BATCH_SUMMARY(?:_\d+)?\.txt$")
_SUPPORTED_REVIEW_OUTPUT_EXTENSIONS = (".txt", ".docx")


@dataclass(frozen=True)
class ReviewItem:
    """Safe review item for one generated anonymized output."""

    output_name: str
    report_name: str | None = None
    status: str = DEFAULT_REVIEW_STATUS


@dataclass(frozen=True)
class ReviewWorkspace:
    """Detected safe review metadata for one output workspace."""

    items: list[ReviewItem]
    batch_summary_names: list[str]


@dataclass(frozen=True)
class ReviewSaveResult:
    """Paths and counts written by the manual review save workflow."""

    status_path: Path
    summary_path: Path
    item_count: int
    status_counts: dict[str, int]
    manual_review_completed: bool


def _now_timestamp() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _safe_filename(value: object) -> str:
    text = str(value).strip()
    if not text:
        return "unknown"

    windows_name = PureWindowsPath(text).name
    return PurePosixPath(windows_name).name or "unknown"


def _validate_review_status(status: str) -> None:
    if status not in REVIEW_STATUSES:
        allowed = ", ".join(REVIEW_STATUSES)
        raise ValueError(f"review status must be one of: {allowed}")


def _coerce_review_item(item: ReviewItem) -> ReviewItem:
    output_name = _safe_filename(item.output_name)
    report_name = (
        _safe_filename(item.report_name) if item.report_name is not None else None
    )
    _validate_review_status(item.status)
    return ReviewItem(
        output_name=output_name,
        report_name=report_name,
        status=item.status,
    )


def _sorted_review_items(items: Iterable[ReviewItem]) -> list[ReviewItem]:
    coerced = [_coerce_review_item(item) for item in items]
    return sorted(coerced, key=lambda item: item.output_name.lower())


def _status_counts(items: Iterable[ReviewItem]) -> dict[str, int]:
    counts = {status: 0 for status in REVIEW_STATUSES}
    for item in items:
        _validate_review_status(item.status)
        counts[item.status] += 1
    return counts


def _manual_review_completed(status_counts: Mapping[str, int], item_count: int) -> bool:
    if item_count == 0:
        return False
    return status_counts.get(REVIEW_STATUS_NEEDS_REVIEW, 0) == 0


def _is_anonymized_output(path: Path) -> bool:
    if not path.is_file():
        return False
    if path.suffix.lower() not in _SUPPORTED_REVIEW_OUTPUT_EXTENSIONS:
        return False
    return _ANON_STEM_PATTERN.match(path.stem) is not None


def _report_names_by_stem(output_dir: Path) -> set[str]:
    report_names: set[str] = set()
    for path in output_dir.iterdir():
        if path.is_file() and path.suffix.lower() == ".txt":
            if _REPORT_STEM_PATTERN.match(path.stem):
                report_names.add(path.name)
    return report_names


def _matching_report_name(output_path: Path, report_names: set[str]) -> str | None:
    match = _ANON_STEM_PATTERN.match(output_path.stem)
    if match is None:
        return None

    base = match.group("base")
    number = match.group("number") or ""
    numbered_candidate = f"{base}_RAPORT{number}.txt"
    base_candidate = f"{base}_RAPORT.txt"

    for candidate in (numbered_candidate, base_candidate):
        if candidate in report_names:
            return candidate

    possible_matches = sorted(
        name
        for name in report_names
        if re.match(rf"^{re.escape(base)}_RAPORT(?:_\d+)?\.txt$", name)
    )
    if len(possible_matches) == 1:
        return possible_matches[0]
    return None


def _detect_batch_summary_names(output_dir: Path) -> list[str]:
    return sorted(
        path.name
        for path in output_dir.iterdir()
        if path.is_file() and _BATCH_SUMMARY_PATTERN.match(path.name)
    )


def build_review_status_path(output_dir: str | Path) -> Path:
    """Return the fixed review manifest path for an output workspace."""
    return Path(output_dir) / REVIEW_STATUS_FILENAME


def build_review_summary_path(output_dir: str | Path) -> Path:
    """Return the default manual review summary path."""
    return Path(output_dir) / REVIEW_SUMMARY_FILENAME


def detect_review_workspace(output_dir: str | Path) -> ReviewWorkspace:
    """Detect generated anonymized outputs and safe companion files."""
    folder = Path(output_dir)
    report_names = _report_names_by_stem(folder)
    items = [
        ReviewItem(
            output_name=path.name,
            report_name=_matching_report_name(path, report_names),
        )
        for path in folder.iterdir()
        if _is_anonymized_output(path)
    ]

    return ReviewWorkspace(
        items=_sorted_review_items(items),
        batch_summary_names=_detect_batch_summary_names(folder),
    )


def apply_review_statuses(
    items: Iterable[ReviewItem],
    statuses_by_output_name: Mapping[str, str],
) -> list[ReviewItem]:
    """Apply manually selected statuses to detected review items."""
    status_by_safe_name = {
        _safe_filename(output_name): status
        for output_name, status in statuses_by_output_name.items()
    }
    updated_items: list[ReviewItem] = []

    for item in _sorted_review_items(items):
        status = status_by_safe_name.get(item.output_name, item.status)
        _validate_review_status(status)
        updated_items.append(
            ReviewItem(
                output_name=item.output_name,
                report_name=item.report_name,
                status=status,
            )
        )

    return updated_items


def load_review_statuses(output_dir: str | Path) -> dict[str, str]:
    """Load existing safe review statuses, ignoring invalid stale entries."""
    status_path = build_review_status_path(output_dir)
    if not status_path.exists():
        return {}

    try:
        payload = json.loads(status_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError):
        return {}

    raw_items = payload.get("items", [])
    if not isinstance(raw_items, list):
        return {}

    statuses: dict[str, str] = {}
    for raw_item in raw_items:
        if not isinstance(raw_item, Mapping):
            continue
        output_name = _safe_filename(raw_item.get("output_name", ""))
        status = raw_item.get("status")
        if output_name == "unknown" or status not in REVIEW_STATUSES:
            continue
        statuses[output_name] = str(status)

    return statuses


def load_review_workspace(output_dir: str | Path) -> ReviewWorkspace:
    """Detect review items and apply previously saved manual statuses."""
    workspace = detect_review_workspace(output_dir)
    statuses = load_review_statuses(output_dir)
    return ReviewWorkspace(
        items=apply_review_statuses(workspace.items, statuses),
        batch_summary_names=workspace.batch_summary_names,
    )


def build_review_status_payload(
    *,
    items: Iterable[ReviewItem],
    batch_summary_names: Iterable[str] | None = None,
    saved_at: str | None = None,
) -> dict[str, object]:
    """Build deterministic safe JSON metadata for manual review decisions."""
    review_items = _sorted_review_items(items)
    counts = _status_counts(review_items)
    item_count = len(review_items)
    summaries = sorted(
        _safe_filename(name) for name in (batch_summary_names or []) if str(name)
    )

    return {
        "schema": REVIEW_SCHEMA,
        "saved_at": saved_at or _now_timestamp(),
        "review_item_count": item_count,
        "status_counts": counts,
        "manual_review_completed": _manual_review_completed(counts, item_count),
        "batch_summary_names": summaries,
        "items": [
            {
                "output_name": item.output_name,
                "report_name": item.report_name,
                "report_present": item.report_name is not None,
                "status": item.status,
            }
            for item in review_items
        ],
        "document_contents_stored": False,
        "original_sensitive_values_stored": False,
        "source_paths_stored": False,
        "dictionary_aliases_stored": False,
        "dictionary_private_terms_stored": False,
        "replacement_map_created": False,
        "automatic_approval_used": False,
    }


def build_review_summary_text(
    *,
    items: Iterable[ReviewItem],
    batch_summary_names: Iterable[str] | None = None,
    saved_at: str | None = None,
) -> str:
    """Build a safe human-readable review summary without document contents."""
    review_items = _sorted_review_items(items)
    counts = _status_counts(review_items)
    item_count = len(review_items)
    manual_completed = _manual_review_completed(counts, item_count)
    summaries = sorted(
        _safe_filename(name) for name in (batch_summary_names or []) if str(name)
    )

    lines = [
        "Manual review summary",
        "",
        f"Saved at: {saved_at or _now_timestamp()}",
        f"Detected review files: {item_count}",
        f"Approved files: {counts[REVIEW_STATUS_APPROVED]}",
        f"Needs review files: {counts[REVIEW_STATUS_NEEDS_REVIEW]}",
        f"Rejected files: {counts[REVIEW_STATUS_REJECTED]}",
        f"Manual review completed: {'yes' if manual_completed else 'no'}",
        "",
        "Review decisions are manual user decisions.",
        "Approved means the user manually approved the file.",
        "Application guarantee of complete anonymization: no",
        "Automatic approval used: no",
        "",
        "Batch summaries:",
    ]

    if summaries:
        for name in summaries:
            lines.append(f"* {name}")
    else:
        lines.append("* none")

    lines.extend(["", "Files:"])
    if review_items:
        for item in review_items:
            report_name = item.report_name or "missing"
            lines.append(f"* output: {item.output_name}")
            lines.append(f"  report: {report_name}")
            lines.append(f"  status: {item.status}")
    else:
        lines.append("* none")

    lines.extend(
        [
            "",
            "Document contents stored: no",
            "Original sensitive values stored: no",
            "Source paths stored: no",
            "Dictionary aliases stored: no",
            "Dictionary private terms stored: no",
            "Replacement map created: no",
            "Tracebacks stored: no",
        ]
    )
    return "\n".join(lines) + "\n"


def save_review_status_file(
    output_dir: str | Path,
    *,
    items: Iterable[ReviewItem],
    batch_summary_names: Iterable[str] | None = None,
    saved_at: str | None = None,
) -> Path:
    """Save the fixed review status manifest for an output workspace."""
    path = build_review_status_path(output_dir)
    payload = build_review_status_payload(
        items=items,
        batch_summary_names=batch_summary_names,
        saved_at=saved_at,
    )
    path.write_text(
        json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return path


def save_review_summary_file(
    output_dir: str | Path,
    *,
    items: Iterable[ReviewItem],
    batch_summary_names: Iterable[str] | None = None,
    saved_at: str | None = None,
) -> Path:
    """Save a collision-safe review summary report for an output workspace."""
    path = build_collision_safe_path(build_review_summary_path(output_dir))
    path.write_text(
        build_review_summary_text(
            items=items,
            batch_summary_names=batch_summary_names,
            saved_at=saved_at,
        ),
        encoding="utf-8",
    )
    return path


def save_review_files(
    output_dir: str | Path,
    *,
    items: Iterable[ReviewItem],
    batch_summary_names: Iterable[str] | None = None,
    saved_at: str | None = None,
) -> ReviewSaveResult:
    """Save both safe review metadata files for manual review decisions."""
    timestamp = saved_at or _now_timestamp()
    review_items = _sorted_review_items(items)
    status_path = save_review_status_file(
        output_dir,
        items=review_items,
        batch_summary_names=batch_summary_names,
        saved_at=timestamp,
    )
    summary_path = save_review_summary_file(
        output_dir,
        items=review_items,
        batch_summary_names=batch_summary_names,
        saved_at=timestamp,
    )
    counts = _status_counts(review_items)
    return ReviewSaveResult(
        status_path=status_path,
        summary_path=summary_path,
        item_count=len(review_items),
        status_counts=counts,
        manual_review_completed=_manual_review_completed(counts, len(review_items)),
    )
