"""Safe anonymization report generation."""

from collections.abc import Iterable, Mapping
from pathlib import Path


def _safe_file_type(value: str) -> str:
    text = str(value).strip()
    if not text:
        return "UNKNOWN"

    suffix = text if text.startswith(".") else Path(text).suffix
    label = (suffix or text).lstrip(".").upper()
    return label or "UNKNOWN"


def _ordered_categories(
    counters: Mapping[str, int], category_order: Iterable[str] | None
) -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()

    if category_order is not None:
        for label in category_order:
            if label not in seen:
                ordered.append(label)
                seen.add(label)

    for label in sorted(counters):
        if label not in seen:
            ordered.append(label)
            seen.add(label)

    return ordered


def build_report_text(
    *,
    counters: Mapping[str, int],
    input_extension: str,
    output_extension: str,
    status: str = "completed",
    category_order: Iterable[str] | None = None,
) -> str:
    """Build a safe text report without source values or replacement maps."""
    if not isinstance(status, str):
        raise TypeError("status must be a string")

    lines = [
        "Anonymization report",
        "",
        f"Status: {status}",
        f"Input type: {_safe_file_type(input_extension)}",
        f"Output type: {_safe_file_type(output_extension)}",
        "",
        "Detected categories:",
    ]

    categories = _ordered_categories(counters, category_order)
    if categories:
        for label in categories:
            count = counters.get(label, 0)
            if not isinstance(count, int):
                raise TypeError("counter values must be integers")
            if count < 0:
                raise ValueError("counter values must not be negative")
            lines.append(f"* {label}: {count}")
    else:
        lines.append("* none: 0")

    lines.extend(
        [
            "",
            "Manual review required: yes",
            "Original sensitive values stored: no",
            "Replacement map created: no",
        ]
    )
    return "\n".join(lines) + "\n"


def save_report_file(
    report_path: str | Path,
    *,
    counters: Mapping[str, int],
    input_extension: str,
    output_extension: str,
    status: str = "completed",
    category_order: Iterable[str] | None = None,
) -> Path:
    """Save a safe anonymization report and return the report path."""
    path = Path(report_path)
    report_text = build_report_text(
        counters=counters,
        input_extension=input_extension,
        output_extension=output_extension,
        status=status,
        category_order=category_order,
    )
    path.write_text(report_text, encoding="utf-8")
    return path
