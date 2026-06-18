"""Regex-based plain text anonymization engine."""

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
import re

try:
    from .audit import AUDIT_CATEGORY_ORDER, RISK_LEVELS, audit_text
    from .file_readers import (
        DOCX_EXTENSION,
        PDF_EXTENSION,
        SUPPORTED_EXTENSIONS,
        TXT_EXTENSION,
        read_docx_file,
        read_pdf_file,
        read_txt_file,
    )
    from .file_writers import (
        build_batch_summary_path,
        build_collision_safe_path,
        build_report_path,
        save_anonymized_docx_copy,
        save_anonymized_pdf_txt_copy,
        save_anonymized_txt_copy,
    )
    from .report import (
        BATCH_ERROR_EMPTY_TEXT_PDF,
        BATCH_ERROR_FILE_IO,
        BATCH_ERROR_MISSING_DEPENDENCY,
        BATCH_ERROR_PROCESSING_FAILED,
        BATCH_ERROR_TEXT_DECODING,
        BATCH_ERROR_UNSUPPORTED_FILE_TYPE,
        DICTIONARY_STATUS_INVALID,
        DICTIONARY_STATUS_LOADED,
        DICTIONARY_STATUS_NOT_SELECTED,
        save_batch_summary_file,
        save_report_file,
    )
    from .sensitive_terms import SensitiveTerm, apply_sensitive_terms, load_sensitive_terms
except ImportError:
    from audit import AUDIT_CATEGORY_ORDER, RISK_LEVELS, audit_text
    from file_readers import (
        DOCX_EXTENSION,
        PDF_EXTENSION,
        SUPPORTED_EXTENSIONS,
        TXT_EXTENSION,
        read_docx_file,
        read_pdf_file,
        read_txt_file,
    )
    from file_writers import (
        build_batch_summary_path,
        build_collision_safe_path,
        build_report_path,
        save_anonymized_docx_copy,
        save_anonymized_pdf_txt_copy,
        save_anonymized_txt_copy,
    )
    from report import (
        BATCH_ERROR_EMPTY_TEXT_PDF,
        BATCH_ERROR_FILE_IO,
        BATCH_ERROR_MISSING_DEPENDENCY,
        BATCH_ERROR_PROCESSING_FAILED,
        BATCH_ERROR_TEXT_DECODING,
        BATCH_ERROR_UNSUPPORTED_FILE_TYPE,
        DICTIONARY_STATUS_INVALID,
        DICTIONARY_STATUS_LOADED,
        DICTIONARY_STATUS_NOT_SELECTED,
        save_batch_summary_file,
        save_report_file,
    )
    from sensitive_terms import SensitiveTerm, apply_sensitive_terms, load_sensitive_terms


SUPPORTED_LABELS = ("PESEL", "EMAIL", "TELEFON", "DATA")


@dataclass(frozen=True)
class FileWorkflowResult:
    """Internal single-file workflow result including safe output paths."""

    output_path: Path
    report_path: Path
    counters: dict[str, int]
    audit_result: dict[str, object]


@dataclass(frozen=True)
class BatchResult:
    """Public batch workflow result with paths plus safe summary metadata."""

    summary_path: Path
    input_count: int
    success_count: int
    error_count: int
    counters: dict[str, int]
    audit_status_counts: dict[str, int]
    risk_level_counts: dict[str, int]
    audit_category_counters: dict[str, int]
    results: list[dict[str, object]]

_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "EMAIL",
        re.compile(
            r"(?<![\w.+-])[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
        ),
    ),
    ("PESEL", re.compile(r"(?<!\w)\d{11}(?!\w)")),
    (
        "TELEFON",
        re.compile(
            r"""
            (?<![\w+])
            (?:
                (?:\+48|0048)[ -]?\d{3}[ -]?\d{3}[ -]?\d{3}
                |
                \d{3}[- ]\d{3}[- ]\d{3}
            )
            (?!\w)
            """,
            re.VERBOSE,
        ),
    ),
    (
        "DATA",
        re.compile(
            r"""
            (?<!\w)
            (?:
                \d{4}-(?:0[1-9]|1[0-2])-(?:0[1-9]|[12]\d|3[01])
                |
                (?:0[1-9]|[12]\d|3[01])\.(?:0[1-9]|1[0-2])\.\d{4}
            )
            (?!\w)
            """,
            re.VERBOSE,
        ),
    ),
)


def anonymize_text(
    text: str, sensitive_terms: Iterable[SensitiveTerm] | None = None
) -> tuple[str, dict[str, int]]:
    """Replace high-confidence sensitive values with category placeholders."""
    anonymized, counters, _ = _anonymize_text_with_dictionary_counters(
        text, sensitive_terms=sensitive_terms
    )
    return anonymized, counters


def _anonymize_text_with_dictionary_counters(
    text: str, sensitive_terms: Iterable[SensitiveTerm] | None = None
) -> tuple[str, dict[str, int], dict[str, int]]:
    """Return anonymized text, all counters, and dictionary-label counters."""
    if not isinstance(text, str):
        raise TypeError("text must be a string")

    anonymized, counters = apply_sensitive_terms(text, sensitive_terms)
    dictionary_counters = dict(counters)

    for label, pattern in _PATTERNS:
        anonymized, count = pattern.subn(f"[{label}]", anonymized)
        if count:
            counters[label] = counters.get(label, 0) + count

    return anonymized, counters, dictionary_counters


def _reusable_sensitive_terms(
    sensitive_terms: Iterable[SensitiveTerm] | None,
) -> list[SensitiveTerm] | None:
    if sensitive_terms is None:
        return None
    return list(sensitive_terms)


def _dictionary_result(
    *,
    status: str,
    sensitive_terms: Iterable[SensitiveTerm] | None = None,
    label_counters: dict[str, int] | None = None,
) -> dict[str, object]:
    counters_by_label: dict[str, int] = {}
    if sensitive_terms is not None:
        for term in sensitive_terms:
            if not isinstance(term, SensitiveTerm):
                raise TypeError("sensitive_terms must contain SensitiveTerm items")
            counters_by_label.setdefault(term.label, 0)

    if label_counters is not None:
        for label, count in label_counters.items():
            counters_by_label[label] = count

    return {
        "status": status,
        "label_counters": counters_by_label,
    }


def _prepare_workflow_dictionary(
    sensitive_terms: Iterable[SensitiveTerm] | None,
    sensitive_terms_path: str | Path | None,
) -> tuple[list[SensitiveTerm] | None, str]:
    if sensitive_terms is not None and sensitive_terms_path is not None:
        raise ValueError(
            "Provide either sensitive_terms or sensitive_terms_path, not both."
        )

    if sensitive_terms_path is not None:
        try:
            return load_sensitive_terms(sensitive_terms_path), DICTIONARY_STATUS_LOADED
        except (OSError, UnicodeDecodeError, ValueError):
            return None, DICTIONARY_STATUS_INVALID

    if sensitive_terms is None:
        return None, DICTIONARY_STATUS_NOT_SELECTED

    terms = _reusable_sensitive_terms(sensitive_terms)
    return terms, DICTIONARY_STATUS_LOADED


def _attach_dictionary_result(
    audit_result: dict[str, object],
    dictionary_result: dict[str, object],
) -> dict[str, object]:
    audit_with_dictionary = dict(audit_result)
    audit_with_dictionary["dictionary"] = dictionary_result
    return audit_with_dictionary


def _merge_counters(target: dict[str, int], source: dict[str, int]) -> None:
    for label, count in source.items():
        target[label] = target.get(label, 0) + count


def anonymize_txt_file(
    source_path: str | Path,
    sensitive_terms: Iterable[SensitiveTerm] | None = None,
    sensitive_terms_path: str | Path | None = None,
    output_dir: str | Path | None = None,
) -> tuple[Path, dict[str, int]]:
    """Anonymize a TXT file and save output plus a safe report."""
    output_path, counters, _ = anonymize_txt_file_with_audit(
        source_path,
        sensitive_terms=sensitive_terms,
        sensitive_terms_path=sensitive_terms_path,
        output_dir=output_dir,
    )
    return output_path, counters


def anonymize_txt_file_with_audit(
    source_path: str | Path,
    sensitive_terms: Iterable[SensitiveTerm] | None = None,
    sensitive_terms_path: str | Path | None = None,
    output_dir: str | Path | None = None,
) -> tuple[Path, dict[str, int], dict[str, object]]:
    """Anonymize a TXT file and return safe audit metadata."""
    result = _anonymize_txt_file_result(
        source_path,
        sensitive_terms=sensitive_terms,
        sensitive_terms_path=sensitive_terms_path,
        output_dir=output_dir,
    )
    return result.output_path, result.counters, result.audit_result


def _anonymize_txt_file_result(
    source_path: str | Path,
    sensitive_terms: Iterable[SensitiveTerm] | None = None,
    sensitive_terms_path: str | Path | None = None,
    output_dir: str | Path | None = None,
) -> FileWorkflowResult:
    """Anonymize a TXT file and return paths needed by batch processing."""
    terms, dictionary_status = _prepare_workflow_dictionary(
        sensitive_terms, sensitive_terms_path
    )
    text = read_txt_file(source_path)
    anonymized, counters, dictionary_counters = (
        _anonymize_text_with_dictionary_counters(text, sensitive_terms=terms)
    )
    output_path = save_anonymized_txt_copy(
        source_path, anonymized, output_dir=output_dir
    )
    dictionary_result = _dictionary_result(
        status=dictionary_status,
        sensitive_terms=terms,
        label_counters=dictionary_counters,
    )
    audit_result = _attach_dictionary_result(
        audit_text(anonymized, sensitive_terms=terms),
        dictionary_result,
    )
    report_path = _save_anonymization_report(
        source_path,
        output_path,
        counters,
        audit_result,
        dictionary_result,
        output_dir=output_dir,
    )
    return FileWorkflowResult(output_path, report_path, counters, audit_result)


def anonymize_docx_file(
    source_path: str | Path,
    sensitive_terms: Iterable[SensitiveTerm] | None = None,
    sensitive_terms_path: str | Path | None = None,
    output_dir: str | Path | None = None,
) -> tuple[Path, dict[str, int]]:
    """Anonymize a DOCX file and save output plus a safe report."""
    output_path, counters, _ = anonymize_docx_file_with_audit(
        source_path,
        sensitive_terms=sensitive_terms,
        sensitive_terms_path=sensitive_terms_path,
        output_dir=output_dir,
    )
    return output_path, counters


def anonymize_docx_file_with_audit(
    source_path: str | Path,
    sensitive_terms: Iterable[SensitiveTerm] | None = None,
    sensitive_terms_path: str | Path | None = None,
    output_dir: str | Path | None = None,
) -> tuple[Path, dict[str, int], dict[str, object]]:
    """Anonymize a DOCX file and return safe audit metadata."""
    result = _anonymize_docx_file_result(
        source_path,
        sensitive_terms=sensitive_terms,
        sensitive_terms_path=sensitive_terms_path,
        output_dir=output_dir,
    )
    return result.output_path, result.counters, result.audit_result


def _anonymize_docx_file_result(
    source_path: str | Path,
    sensitive_terms: Iterable[SensitiveTerm] | None = None,
    sensitive_terms_path: str | Path | None = None,
    output_dir: str | Path | None = None,
) -> FileWorkflowResult:
    """Anonymize a DOCX file and return paths needed by batch processing."""
    terms, dictionary_status = _prepare_workflow_dictionary(
        sensitive_terms, sensitive_terms_path
    )
    dictionary_counters: dict[str, int] = {}

    def anonymize_docx_text(text: str) -> tuple[str, dict[str, int]]:
        anonymized, counters, paragraph_dictionary_counters = (
            _anonymize_text_with_dictionary_counters(text, sensitive_terms=terms)
        )
        _merge_counters(dictionary_counters, paragraph_dictionary_counters)
        return anonymized, counters

    def anonymize_docx_run(text: str) -> tuple[str, dict[str, int]]:
        anonymized, counters, _ = _anonymize_text_with_dictionary_counters(
            text, sensitive_terms=terms
        )
        return anonymized, counters

    output_path, counters = save_anonymized_docx_copy(
        source_path,
        anonymize_docx_text,
        anonymize_run=anonymize_docx_run,
        output_dir=output_dir,
    )
    anonymized_text = read_docx_file(output_path)
    dictionary_result = _dictionary_result(
        status=dictionary_status,
        sensitive_terms=terms,
        label_counters=dictionary_counters,
    )
    audit_result = _attach_dictionary_result(
        audit_text(anonymized_text, sensitive_terms=terms),
        dictionary_result,
    )
    report_path = _save_anonymization_report(
        source_path,
        output_path,
        counters,
        audit_result,
        dictionary_result,
        output_dir=output_dir,
    )
    return FileWorkflowResult(output_path, report_path, counters, audit_result)


def anonymize_pdf_file(
    source_path: str | Path,
    sensitive_terms: Iterable[SensitiveTerm] | None = None,
    sensitive_terms_path: str | Path | None = None,
    output_dir: str | Path | None = None,
) -> tuple[Path, dict[str, int]]:
    """Anonymize text from a PDF and save TXT output plus a safe report."""
    output_path, counters, _ = anonymize_pdf_file_with_audit(
        source_path,
        sensitive_terms=sensitive_terms,
        sensitive_terms_path=sensitive_terms_path,
        output_dir=output_dir,
    )
    return output_path, counters


def anonymize_pdf_file_with_audit(
    source_path: str | Path,
    sensitive_terms: Iterable[SensitiveTerm] | None = None,
    sensitive_terms_path: str | Path | None = None,
    output_dir: str | Path | None = None,
) -> tuple[Path, dict[str, int], dict[str, object]]:
    """Anonymize text from a PDF and return safe audit metadata."""
    result = _anonymize_pdf_file_result(
        source_path,
        sensitive_terms=sensitive_terms,
        sensitive_terms_path=sensitive_terms_path,
        output_dir=output_dir,
    )
    return result.output_path, result.counters, result.audit_result


def _anonymize_pdf_file_result(
    source_path: str | Path,
    sensitive_terms: Iterable[SensitiveTerm] | None = None,
    sensitive_terms_path: str | Path | None = None,
    output_dir: str | Path | None = None,
) -> FileWorkflowResult:
    """Anonymize a PDF file and return paths needed by batch processing."""
    terms, dictionary_status = _prepare_workflow_dictionary(
        sensitive_terms, sensitive_terms_path
    )
    text = read_pdf_file(source_path)
    anonymized, counters, dictionary_counters = (
        _anonymize_text_with_dictionary_counters(text, sensitive_terms=terms)
    )
    output_path = save_anonymized_pdf_txt_copy(
        source_path, anonymized, output_dir=output_dir
    )
    dictionary_result = _dictionary_result(
        status=dictionary_status,
        sensitive_terms=terms,
        label_counters=dictionary_counters,
    )
    audit_result = _attach_dictionary_result(
        audit_text(anonymized, sensitive_terms=terms),
        dictionary_result,
    )
    report_path = _save_anonymization_report(
        source_path,
        output_path,
        counters,
        audit_result,
        dictionary_result,
        output_dir=output_dir,
    )
    return FileWorkflowResult(output_path, report_path, counters, audit_result)


def _save_anonymization_report(
    source_path: str | Path,
    output_path: str | Path,
    counters: dict[str, int],
    audit_result: dict[str, object],
    dictionary_result: dict[str, object],
    output_dir: str | Path | None = None,
) -> Path:
    source = Path(source_path)
    output = Path(output_path)
    report_path = build_collision_safe_path(
        build_report_path(source, output_dir=output_dir)
    )
    return save_report_file(
        report_path,
        counters=counters,
        input_extension=source.suffix,
        output_extension=output.suffix,
        category_order=SUPPORTED_LABELS,
        audit_result=audit_result,
        audit_category_order=AUDIT_CATEGORY_ORDER,
        dictionary_result=dictionary_result,
    )


def anonymize_file(
    source_path: str | Path,
    sensitive_terms: Iterable[SensitiveTerm] | None = None,
    sensitive_terms_path: str | Path | None = None,
    output_dir: str | Path | None = None,
) -> tuple[Path, dict[str, int]]:
    """Anonymize one supported application file using existing workflows."""
    output_path, counters, _ = anonymize_file_with_audit(
        source_path,
        sensitive_terms=sensitive_terms,
        sensitive_terms_path=sensitive_terms_path,
        output_dir=output_dir,
    )
    return output_path, counters


def anonymize_file_with_audit(
    source_path: str | Path,
    sensitive_terms: Iterable[SensitiveTerm] | None = None,
    sensitive_terms_path: str | Path | None = None,
    output_dir: str | Path | None = None,
) -> tuple[Path, dict[str, int], dict[str, object]]:
    """Anonymize one supported file and return safe audit metadata."""
    result = _anonymize_file_result(
        source_path,
        sensitive_terms=sensitive_terms,
        sensitive_terms_path=sensitive_terms_path,
        output_dir=output_dir,
    )
    return result.output_path, result.counters, result.audit_result


def _anonymize_file_result(
    source_path: str | Path,
    sensitive_terms: Iterable[SensitiveTerm] | None = None,
    sensitive_terms_path: str | Path | None = None,
    output_dir: str | Path | None = None,
) -> FileWorkflowResult:
    """Anonymize one supported file and return paths needed by batch processing."""
    path = Path(source_path)

    if path.suffix.lower() == TXT_EXTENSION:
        return _anonymize_txt_file_result(
            path,
            sensitive_terms=sensitive_terms,
            sensitive_terms_path=sensitive_terms_path,
            output_dir=output_dir,
        )
    if path.suffix.lower() == DOCX_EXTENSION:
        return _anonymize_docx_file_result(
            path,
            sensitive_terms=sensitive_terms,
            sensitive_terms_path=sensitive_terms_path,
            output_dir=output_dir,
        )
    if path.suffix.lower() == PDF_EXTENSION:
        return _anonymize_pdf_file_result(
            path,
            sensitive_terms=sensitive_terms,
            sensitive_terms_path=sensitive_terms_path,
            output_dir=output_dir,
        )

    suffix = path.suffix.lower() or "<none>"
    supported = ", ".join(SUPPORTED_EXTENSIONS)
    raise ValueError(
        f"Unsupported file extension for anonymize_file: {suffix}. "
        f"Only {supported} files are supported."
    )


def _safe_batch_error_description(error: Exception) -> str:
    if isinstance(error, UnicodeDecodeError):
        return BATCH_ERROR_TEXT_DECODING
    if isinstance(error, ValueError) and "no extractable text" in str(error):
        return BATCH_ERROR_EMPTY_TEXT_PDF
    if isinstance(error, OSError):
        return BATCH_ERROR_FILE_IO
    if isinstance(error, RuntimeError):
        return BATCH_ERROR_MISSING_DEPENDENCY
    return BATCH_ERROR_PROCESSING_FAILED


def _merge_audit_status_count(
    audit_status_counts: dict[str, int],
    audit_result: dict[str, object],
) -> None:
    status = audit_result.get("status")
    if status not in ("ok", "warning"):
        status = "not run"
    audit_status_counts[str(status)] = audit_status_counts.get(str(status), 0) + 1


def _merge_risk_level_count(
    risk_level_counts: dict[str, int],
    audit_result: dict[str, object],
) -> None:
    risk_level = audit_result.get("risk_level")
    if risk_level in RISK_LEVELS:
        risk_level_counts[str(risk_level)] = risk_level_counts.get(str(risk_level), 0) + 1


def _merge_audit_findings(
    audit_category_counters: dict[str, int],
    audit_result: dict[str, object],
) -> None:
    findings = audit_result.get("findings")
    if not isinstance(findings, dict):
        return

    for label in AUDIT_CATEGORY_ORDER:
        count = findings.get(label, 0)
        if isinstance(count, int):
            audit_category_counters[label] = (
                audit_category_counters.get(label, 0) + count
            )


def anonymize_batch(
    source_paths: Iterable[str | Path],
    output_dir: str | Path,
    sensitive_terms: Iterable[SensitiveTerm] | None = None,
    sensitive_terms_path: str | Path | None = None,
) -> BatchResult:
    """Anonymize supported files sequentially into one output workspace."""
    if sensitive_terms is not None and sensitive_terms_path is not None:
        raise ValueError(
            "Provide either sensitive_terms or sensitive_terms_path, not both."
        )

    paths = [Path(path) for path in source_paths]
    reusable_terms = _reusable_sensitive_terms(sensitive_terms)
    aggregate_counters: dict[str, int] = {}
    audit_status_counts = {"ok": 0, "warning": 0, "not run": 0}
    risk_level_counts = {risk_level: 0 for risk_level in RISK_LEVELS}
    audit_category_counters = {category: 0 for category in AUDIT_CATEGORY_ORDER}
    results: list[dict[str, object]] = []
    success_count = 0
    error_count = 0

    for path in paths:
        if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            error_count += 1
            audit_status_counts["not run"] += 1
            results.append(
                {
                    "input_name": path.name,
                    "status": "error",
                    "error": BATCH_ERROR_UNSUPPORTED_FILE_TYPE,
                }
            )
            continue

        try:
            result = _anonymize_file_result(
                path,
                sensitive_terms=reusable_terms,
                sensitive_terms_path=sensitive_terms_path,
                output_dir=output_dir,
            )
        except Exception as error:
            error_count += 1
            audit_status_counts["not run"] += 1
            results.append(
                {
                    "input_name": path.name,
                    "status": "error",
                    "error": _safe_batch_error_description(error),
                }
            )
            continue

        success_count += 1
        _merge_counters(aggregate_counters, result.counters)
        _merge_audit_status_count(audit_status_counts, result.audit_result)
        _merge_risk_level_count(risk_level_counts, result.audit_result)
        _merge_audit_findings(audit_category_counters, result.audit_result)
        dictionary_result = result.audit_result.get("dictionary", {})
        dictionary_status = (
            dictionary_result.get("status")
            if isinstance(dictionary_result, dict)
            else "unknown"
        )
        results.append(
            {
                "input_name": path.name,
                "status": "success",
                "output_name": result.output_path.name,
                "report_name": result.report_path.name,
                "audit_status": result.audit_result.get("status", "unknown"),
                "risk_level": result.audit_result.get("risk_level", "unknown"),
                "dictionary_status": dictionary_status,
            }
        )

    summary_path = build_collision_safe_path(build_batch_summary_path(output_dir))
    save_batch_summary_file(
        summary_path,
        input_count=len(paths),
        success_count=success_count,
        error_count=error_count,
        counters=aggregate_counters,
        audit_status_counts=audit_status_counts,
        risk_level_counts=risk_level_counts,
        audit_category_counters=audit_category_counters,
        results=results,
        category_order=SUPPORTED_LABELS,
        audit_category_order=AUDIT_CATEGORY_ORDER,
        manual_review_required=True,
    )

    return BatchResult(
        summary_path=summary_path,
        input_count=len(paths),
        success_count=success_count,
        error_count=error_count,
        counters=aggregate_counters,
        audit_status_counts=audit_status_counts,
        risk_level_counts=risk_level_counts,
        audit_category_counters=audit_category_counters,
        results=results,
    )
