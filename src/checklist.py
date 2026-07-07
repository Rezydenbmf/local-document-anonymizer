"""Privacy-safe manual review checklist generation."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path, PurePosixPath, PureWindowsPath
import re

try:
    from .file_writers import (
        build_batch_review_checklist_path,
        build_collision_safe_path,
        build_review_checklist_path,
    )
except ImportError:
    from file_writers import (
        build_batch_review_checklist_path,
        build_collision_safe_path,
        build_review_checklist_path,
    )


PLACEHOLDER_PATTERN = re.compile(r"\[[^\[\]\r\n]{1,80}\]")
CONTACT_LABELS = ("[EMAIL]", "[TELEFON]")
PERSON_LABELS = ("[NER_PERSON]", "[PERSON_NAME_TYPO]")
ORG_LOCATION_LABELS = ("[NER_ORG]", "[NER_LOCATION]")
AUDIT_REVIEW_LABELS = (
    "POSTAL_CODE",
    "ADDRESS_LIKE",
    "STREET_LIKE",
    "ID_LIKE_NUMBER",
    "LONG_NUMBER_SEQUENCE",
)
MAX_CONTEXT_EXAMPLES_PER_SECTION = 4
CONTEXT_RADIUS = 60


def _safe_filename(value: object) -> str:
    text = str(value).strip()
    if not text:
        return "unknown"
    windows_name = PureWindowsPath(text).name
    return PurePosixPath(windows_name).name or "unknown"


def _safe_bool(value: object) -> str:
    return "yes" if bool(value) else "no"


def _positive_counts(counters: object) -> dict[str, int]:
    if not isinstance(counters, Mapping):
        return {}
    result: dict[str, int] = {}
    for label, count in counters.items():
        if isinstance(count, int) and count > 0:
            result[str(label)] = count
    return result


def _append_counter_lines(lines: list[str], title: str, counters: Mapping[str, int]) -> None:
    lines.append(title)
    if counters:
        for label in sorted(counters):
            lines.append(f"* {label}: {counters[label]}")
    else:
        lines.append("* none: 0")


def _context_for_match(text: str, start: int, end: int) -> str:
    left = max(0, start - CONTEXT_RADIUS)
    right = min(len(text), end + CONTEXT_RADIUS)
    context = " ".join(text[left:right].split())
    if left > 0:
        context = "..." + context
    if right < len(text):
        context = context + "..."
    return context


def _placeholder_counts(text: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for match in PLACEHOLDER_PATTERN.finditer(text):
        label = match.group(0)
        counts[label] = counts.get(label, 0) + 1
    return counts


def _context_examples(text: str) -> list[tuple[str, str]]:
    examples: list[tuple[str, str]] = []
    for match in PLACEHOLDER_PATTERN.finditer(text):
        examples.append((match.group(0), _context_for_match(text, match.start(), match.end())))
        if len(examples) >= MAX_CONTEXT_EXAMPLES_PER_SECTION:
            break
    return examples


def _section_entries(
    anonymized_text: str,
    *,
    section_label: str,
    sections: Sequence[str] | None,
) -> list[tuple[str, str]]:
    if sections:
        return [(f"{section_label} {index}", text) for index, text in enumerate(sections, start=1)]

    lines = anonymized_text.splitlines() or [anonymized_text]
    return [(f"Line {index}", line) for index, line in enumerate(lines, start=1) if line.strip()]


def _review_tasks(
    counters: Mapping[str, int],
    audit_warnings: Mapping[str, int],
    *,
    input_extension: str,
    pdf_redaction_result: Mapping[str, object] | None,
) -> list[str]:
    labels = {f"[{label}]" for label, count in counters.items() if count > 0}
    tasks: list[str] = []
    if any(label in labels for label in CONTACT_LABELS):
        tasks.append("Check contact data labels: [EMAIL], [TELEFON]")
    if any(label in labels for label in PERSON_LABELS):
        tasks.append("Check person labels: [NER_PERSON], [PERSON_NAME_TYPO]")
    if any(label in labels for label in ORG_LOCATION_LABELS):
        tasks.append("Check organization/location labels if enabled: [NER_ORG], [NER_LOCATION]")

    warning_labels = [
        label
        for label in AUDIT_REVIEW_LABELS
        if audit_warnings.get(label, 0) > 0
    ]
    if warning_labels:
        tasks.append(f"Check audit warnings: {', '.join(warning_labels)}")

    if input_extension.lower() == ".pdf":
        tasks.append(
            "For PDF/table-heavy documents: verify extracted text order manually "
            "against the original if the document has tables, multi-column layout, "
            "charts, or scanned/embedded images."
        )
        if pdf_redaction_result and pdf_redaction_result.get("original_layout_redaction_used"):
            tasks.append("Original-layout redaction was used: treat it as experimental.")
        if pdf_redaction_result and pdf_redaction_result.get("weak_phone_like_skipped"):
            tasks.append(
                "Weak phone-like numeric table values were left visible unless "
                "strong phone/contact context was present."
            )
        if pdf_redaction_result:
            tasks.append(
                "Single-token person-like terms are skipped unless strong person "
                "context exists; verify names manually."
            )

    if not tasks:
        tasks.append("Review the anonymized output and report before use.")
    return tasks


def build_review_checklist_text(
    *,
    source_name: str,
    input_extension: str,
    output_names: Iterable[str],
    report_name: str,
    counters: Mapping[str, int],
    audit_result: Mapping[str, object],
    ocr_result: Mapping[str, object],
    ner_result: Mapping[str, object],
    llm_review_result: Mapping[str, object],
    anonymized_text: str,
    sections: Sequence[str] | None = None,
    section_label: str = "Line",
    pdf_redaction_result: Mapping[str, object] | None = None,
) -> str:
    """Build a safe checklist from anonymized text and safe metadata only."""
    safe_source_name = _safe_filename(source_name)
    safe_outputs = [_safe_filename(name) for name in output_names if str(name).strip()]
    safe_report_name = _safe_filename(report_name)
    detected_counts = _positive_counts(counters)
    audit_warnings = _positive_counts(audit_result.get("findings"))
    risk_level = str(audit_result.get("risk_level", "unknown"))
    audit_status = str(audit_result.get("status", "unknown"))
    pdf_review_type = "not applicable"
    if pdf_redaction_result:
        pdf_review_type = str(pdf_redaction_result.get("review_pdf_type", "none"))

    lines = [
        "Manual review checklist",
        "",
        "Header:",
        f"Source file: {safe_source_name}",
        f"Input type: {input_extension.lstrip('.').upper() or 'UNKNOWN'}",
        "Output files created:",
    ]
    if safe_outputs:
        for output_name in safe_outputs:
            lines.append(f"* {output_name}")
    else:
        lines.append("* none")
    lines.extend(
        [
            f"Report file: {safe_report_name}",
            "Manual review required: yes",
            f"Audit status: {audit_status}",
            f"Risk level: {risk_level}",
            f"OCR used/status: {_safe_bool(ocr_result.get('used', False))}/{ocr_result.get('status', 'unknown')}",
            f"NER used/status: {_safe_bool(ner_result.get('used', False))}/{ner_result.get('status', 'unknown')}",
            f"LLM review used/status: {_safe_bool(llm_review_result.get('used', False))}/{llm_review_result.get('status', 'unknown')}",
            f"PDF review artifact type: {pdf_review_type}",
            "",
            "Summary:",
        ]
    )
    _append_counter_lines(lines, "Detected categories and counts:", detected_counts)
    _append_counter_lines(lines, "Post-anonymization audit warnings:", audit_warnings)

    if pdf_redaction_result:
        text_extraction = str(pdf_redaction_result.get("text_extraction", "unknown"))
        review_type = str(pdf_redaction_result.get("review_pdf_type", "none"))
        visual_name = str(pdf_redaction_result.get("visual_pdf_name", "")).strip()
        visual_type = str(pdf_redaction_result.get("visual_pdf_type", "none")).strip()
        visual_created = bool(pdf_redaction_result.get("visual_pdf_created", False))
        visual_mapping = str(pdf_redaction_result.get("visual_redaction_mode", "")).strip()
        weak_phone_like_skipped = pdf_redaction_result.get("weak_phone_like_skipped", 0)
        lines.extend(
            [
                f"PDF text extraction mode: {text_extraction}",
                f"Main visual PDF created: {'yes' if visual_created else 'no'}",
                f"Main visual PDF type: {visual_type}",
                f"Main visual PDF output: {_safe_filename(visual_name) if visual_name else 'not created'}",
                f"Main visual PDF mapping: {visual_mapping or 'none'}",
                f"PDF review PDF type: {review_type}",
                "PDF review PDF layout: not_layout_preserving",
                "PDF review PDF suitability: auxiliary simple text review only",
                f"Weak phone-like numeric values skipped: {weak_phone_like_skipped}",
            ]
        )
        unmapped = _positive_counts(pdf_redaction_result.get("unmapped_categories"))
        _append_counter_lines(lines, "Unmapped PDF detections:", unmapped)
        if pdf_redaction_result.get("original_layout_redaction_experimental"):
            lines.append("Original-layout redaction: experimental")

    lines.extend(["", "Review tasks:"])
    for task in _review_tasks(
        detected_counts,
        audit_warnings,
        input_extension=input_extension,
        pdf_redaction_result=pdf_redaction_result,
    ):
        lines.append(f"- [ ] {task}")

    lines.extend(["", "Findings from anonymized output:"])
    entries = _section_entries(
        anonymized_text,
        section_label=section_label,
        sections=sections,
    )
    found_any = False
    for entry_label, entry_text in entries:
        counts = _placeholder_counts(entry_text)
        if not counts:
            continue
        found_any = True
        count_text = ", ".join(f"{label} x{count}" for label, count in sorted(counts.items()))
        lines.append(f"{entry_label}: {count_text}")
        for label, context in _context_examples(entry_text):
            lines.append(f"  - {label}: {context}")
    if not found_any:
        lines.append("* No replacement labels found in anonymized output.")

    lines.extend(
        [
            "",
            "Safety notes:",
            "- Checklist uses anonymized output only.",
            "- Original sensitive values stored: no",
            "- Source paths stored: no",
            "- Replacement map created: no",
        ]
    )
    return "\n".join(lines) + "\n"


def save_review_checklist_file(
    source_path: str | Path,
    *,
    output_dir: str | Path | None,
    text: str,
) -> Path:
    """Save a per-file review checklist with collision-safe naming."""
    path = build_collision_safe_path(
        build_review_checklist_path(source_path, output_dir=output_dir)
    )
    path.write_text(text, encoding="utf-8")
    return path


def build_batch_review_checklist_text(
    *,
    input_count: int,
    success_count: int,
    error_count: int,
    counters: Mapping[str, int],
    results: Iterable[Mapping[str, object]],
) -> str:
    """Build a safe batch-level review checklist from per-file metadata."""
    materialized_results = list(results)
    priorities = sorted(
        (
            result
            for result in materialized_results
            if result.get("status") == "success"
        ),
        key=lambda result: {"high_risk": 0, "warning": 1, "ok": 2}.get(
            str(result.get("risk_level", "unknown")),
            3,
        ),
    )
    lines = [
        "Batch review checklist",
        "",
        f"Total files processed: {input_count}",
        f"Successful files: {success_count}",
        f"Errors: {error_count}",
        f"Files requiring manual review: {success_count}",
        "",
        "Top review priorities:",
    ]
    if priorities:
        for result in priorities:
            lines.append(
                f"* {result.get('risk_level', 'unknown')}: "
                f"{_safe_filename(result.get('input_name', 'unknown'))}"
            )
            lines.append(f"  checklist: {_safe_filename(result.get('checklist_name', 'missing'))}")
            lines.append(f"  report: {_safe_filename(result.get('report_name', 'missing'))}")
            lines.append(f"  output: {_safe_filename(result.get('output_name', 'missing'))}")
    else:
        lines.append("* none")

    lines.extend(["", "Batch category summary:"])
    _append_counter_lines(lines, "Detected categories across batch:", _positive_counts(counters))

    lines.extend(["", "Files:"])
    for result in materialized_results:
        lines.append(f"* input: {_safe_filename(result.get('input_name', 'unknown'))}")
        lines.append(f"  status: {result.get('status', 'unknown')}")
        if result.get("status") == "success":
            lines.append(f"  risk level: {result.get('risk_level', 'unknown')}")
            lines.append(f"  checklist: {_safe_filename(result.get('checklist_name', 'missing'))}")
            lines.append(f"  report: {_safe_filename(result.get('report_name', 'missing'))}")
            lines.append(f"  output: {_safe_filename(result.get('output_name', 'missing'))}")
        else:
            lines.append(f"  error: {result.get('error', 'file processing failed')}")

    lines.extend(
        [
            "",
            "Safety notes:",
            "- Checklist stores safe filenames and category counts only.",
            "- Source paths stored: no",
            "- Original sensitive values stored: no",
            "- Replacement map created: no",
        ]
    )
    return "\n".join(lines) + "\n"


def save_batch_review_checklist_file(
    output_dir: str | Path,
    *,
    text: str,
) -> Path:
    """Save a batch review checklist with collision-safe naming."""
    path = build_collision_safe_path(build_batch_review_checklist_path(output_dir))
    path.write_text(text, encoding="utf-8")
    return path
