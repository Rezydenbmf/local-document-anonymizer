"""Placeholder report builder.

Reports must never include original sensitive source values.
"""


def build_report(detected_labels: tuple[str, ...]) -> dict[str, object]:
    """Build a minimal placeholder report without source values."""
    return {
        "status": "placeholder",
        "detected_label_count": len(detected_labels),
        "contains_source_values": False,
    }
