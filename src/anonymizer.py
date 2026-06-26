"""Regex-based plain text anonymization engine."""

from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
import re

try:
    from .audit import AUDIT_CATEGORY_ORDER, RISK_LEVELS, audit_text
    from .file_readers import (
        DOCX_EXTENSION,
        IMAGE_EXTENSIONS,
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
        save_anonymized_image_txt_copy,
        save_anonymized_pdf_txt_copy,
        save_anonymized_txt_copy,
    )
    from .ocr import (
        OCR_INPUT_TYPE_IMAGE,
        OCR_INPUT_TYPE_NONE,
        OCR_INPUT_TYPE_PDF,
        OcrUnavailableError,
        build_ocr_not_used_metadata,
        extract_text_with_ocr,
    )
    from .ner import DEFAULT_NER_MODEL, NER_LABELS, NER_STATUSES, anonymize_text_with_ner
    from .ner import build_ner_metadata, prepare_ner_context
    from .llm_review import (
        LLM_REVIEW_STATUSES,
        LLM_RESIDUAL_CATEGORIES,
        LLM_RISK_LEVELS,
        run_llm_review,
    )
    from .report import (
        BATCH_ERROR_EMPTY_TEXT_PDF,
        BATCH_ERROR_FILE_IO,
        BATCH_ERROR_MISSING_DEPENDENCY,
        BATCH_ERROR_OCR_FAILED,
        BATCH_ERROR_OCR_UNAVAILABLE,
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
        IMAGE_EXTENSIONS,
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
        save_anonymized_image_txt_copy,
        save_anonymized_pdf_txt_copy,
        save_anonymized_txt_copy,
    )
    from ocr import (
        OCR_INPUT_TYPE_IMAGE,
        OCR_INPUT_TYPE_NONE,
        OCR_INPUT_TYPE_PDF,
        OcrUnavailableError,
        build_ocr_not_used_metadata,
        extract_text_with_ocr,
    )
    from ner import DEFAULT_NER_MODEL, NER_LABELS, NER_STATUSES, anonymize_text_with_ner
    from ner import build_ner_metadata, prepare_ner_context
    from llm_review import (
        LLM_REVIEW_STATUSES,
        LLM_RESIDUAL_CATEGORIES,
        LLM_RISK_LEVELS,
        run_llm_review,
    )
    from report import (
        BATCH_ERROR_EMPTY_TEXT_PDF,
        BATCH_ERROR_FILE_IO,
        BATCH_ERROR_MISSING_DEPENDENCY,
        BATCH_ERROR_OCR_FAILED,
        BATCH_ERROR_OCR_UNAVAILABLE,
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
REPORT_CATEGORY_ORDER = (*SUPPORTED_LABELS, *NER_LABELS)


@dataclass(frozen=True)
class FileWorkflowResult:
    """Internal single-file workflow result including safe output paths."""

    output_path: Path
    report_path: Path
    counters: dict[str, int]
    audit_result: dict[str, object]
    ocr_result: dict[str, object]
    ner_result: dict[str, object]
    llm_review_result: dict[str, object]


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
    ner_status_counts: dict[str, int] = field(default_factory=dict)
    ner_category_counters: dict[str, int] = field(default_factory=dict)
    llm_review_status_counts: dict[str, int] = field(default_factory=dict)
    llm_review_risk_level_counts: dict[str, int] = field(default_factory=dict)
    llm_review_category_counters: dict[str, int] = field(default_factory=dict)

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
    text: str,
    sensitive_terms: Iterable[SensitiveTerm] | None = None,
    *,
    use_ner: bool = False,
    ner_model_name: str = DEFAULT_NER_MODEL,
) -> tuple[str, dict[str, int]]:
    """Replace high-confidence sensitive values with category placeholders."""
    ner_context = prepare_ner_context(enabled=use_ner, model_name=ner_model_name)
    anonymized, counters, _, _ = _anonymize_text_with_dictionary_counters(
        text,
        sensitive_terms=sensitive_terms,
        ner_context=ner_context,
    )
    return anonymized, counters


def _anonymize_text_with_dictionary_counters(
    text: str,
    sensitive_terms: Iterable[SensitiveTerm] | None = None,
    ner_context=None,
) -> tuple[str, dict[str, int], dict[str, int], dict[str, object]]:
    """Return anonymized text, counters, dictionary counters, and NER metadata."""
    if not isinstance(text, str):
        raise TypeError("text must be a string")

    anonymized, counters = apply_sensitive_terms(text, sensitive_terms)
    dictionary_counters = dict(counters)

    for label, pattern in _PATTERNS:
        anonymized, count = pattern.subn(f"[{label}]", anonymized)
        if count:
            counters[label] = counters.get(label, 0) + count

    if ner_context is None:
        ner_result = build_ner_metadata(
            enabled=False,
            used=False,
            status="disabled",
            model_name=DEFAULT_NER_MODEL,
        )
    else:
        anonymized, ner_counters, ner_result = anonymize_text_with_ner(
            anonymized, ner_context
        )
        _merge_counters(counters, ner_counters)

    return anonymized, counters, dictionary_counters, ner_result


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


def _attach_ner_result(
    audit_result: dict[str, object],
    ner_result: dict[str, object],
) -> dict[str, object]:
    audit_with_ner = dict(audit_result)
    audit_with_ner["ner"] = ner_result
    return audit_with_ner


def _run_optional_llm_review(
    anonymized_text: str,
    *,
    use_llm_review: bool,
    llm_model_name: str,
) -> dict[str, object]:
    return run_llm_review(
        anonymized_text,
        enabled=use_llm_review,
        model_name=llm_model_name,
    )


def _merge_counters(target: dict[str, int], source: dict[str, int]) -> None:
    for label, count in source.items():
        target[label] = target.get(label, 0) + count


def anonymize_txt_file(
    source_path: str | Path,
    sensitive_terms: Iterable[SensitiveTerm] | None = None,
    sensitive_terms_path: str | Path | None = None,
    output_dir: str | Path | None = None,
    *,
    use_ner: bool = False,
    ner_model_name: str = DEFAULT_NER_MODEL,
    use_llm_review: bool = False,
    llm_model_name: str = "",
) -> tuple[Path, dict[str, int]]:
    """Anonymize a TXT file and save output plus a safe report."""
    output_path, counters, _ = anonymize_txt_file_with_audit(
        source_path,
        sensitive_terms=sensitive_terms,
        sensitive_terms_path=sensitive_terms_path,
        output_dir=output_dir,
        use_ner=use_ner,
        ner_model_name=ner_model_name,
        use_llm_review=use_llm_review,
        llm_model_name=llm_model_name,
    )
    return output_path, counters


def anonymize_txt_file_with_audit(
    source_path: str | Path,
    sensitive_terms: Iterable[SensitiveTerm] | None = None,
    sensitive_terms_path: str | Path | None = None,
    output_dir: str | Path | None = None,
    *,
    use_ner: bool = False,
    ner_model_name: str = DEFAULT_NER_MODEL,
    use_llm_review: bool = False,
    llm_model_name: str = "",
) -> tuple[Path, dict[str, int], dict[str, object]]:
    """Anonymize a TXT file and return safe audit metadata."""
    result = _anonymize_txt_file_result(
        source_path,
        sensitive_terms=sensitive_terms,
        sensitive_terms_path=sensitive_terms_path,
        output_dir=output_dir,
        use_ner=use_ner,
        ner_model_name=ner_model_name,
        use_llm_review=use_llm_review,
        llm_model_name=llm_model_name,
    )
    return result.output_path, result.counters, result.audit_result


def _anonymize_txt_file_result(
    source_path: str | Path,
    sensitive_terms: Iterable[SensitiveTerm] | None = None,
    sensitive_terms_path: str | Path | None = None,
    output_dir: str | Path | None = None,
    *,
    use_ner: bool = False,
    ner_model_name: str = DEFAULT_NER_MODEL,
    use_llm_review: bool = False,
    llm_model_name: str = "",
) -> FileWorkflowResult:
    """Anonymize a TXT file and return paths needed by batch processing."""
    terms, dictionary_status = _prepare_workflow_dictionary(
        sensitive_terms, sensitive_terms_path
    )
    ner_context = prepare_ner_context(enabled=use_ner, model_name=ner_model_name)
    text = read_txt_file(source_path)
    anonymized, counters, dictionary_counters, ner_result = (
        _anonymize_text_with_dictionary_counters(
            text,
            sensitive_terms=terms,
            ner_context=ner_context,
        )
    )
    output_path = save_anonymized_txt_copy(
        source_path, anonymized, output_dir=output_dir
    )
    llm_review_result = _run_optional_llm_review(
        anonymized,
        use_llm_review=use_llm_review,
        llm_model_name=llm_model_name,
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
    audit_result = _attach_ner_result(audit_result, ner_result)
    ocr_result = build_ocr_not_used_metadata(OCR_INPUT_TYPE_NONE)
    report_path = _save_anonymization_report(
        source_path,
        output_path,
        counters,
        audit_result,
        dictionary_result,
        ocr_result,
        ner_result,
        llm_review_result,
        output_dir=output_dir,
    )
    return FileWorkflowResult(
        output_path,
        report_path,
        counters,
        audit_result,
        ocr_result,
        ner_result,
        llm_review_result,
    )


def anonymize_docx_file(
    source_path: str | Path,
    sensitive_terms: Iterable[SensitiveTerm] | None = None,
    sensitive_terms_path: str | Path | None = None,
    output_dir: str | Path | None = None,
    *,
    use_ner: bool = False,
    ner_model_name: str = DEFAULT_NER_MODEL,
    use_llm_review: bool = False,
    llm_model_name: str = "",
) -> tuple[Path, dict[str, int]]:
    """Anonymize a DOCX file and save output plus a safe report."""
    output_path, counters, _ = anonymize_docx_file_with_audit(
        source_path,
        sensitive_terms=sensitive_terms,
        sensitive_terms_path=sensitive_terms_path,
        output_dir=output_dir,
        use_ner=use_ner,
        ner_model_name=ner_model_name,
        use_llm_review=use_llm_review,
        llm_model_name=llm_model_name,
    )
    return output_path, counters


def anonymize_docx_file_with_audit(
    source_path: str | Path,
    sensitive_terms: Iterable[SensitiveTerm] | None = None,
    sensitive_terms_path: str | Path | None = None,
    output_dir: str | Path | None = None,
    *,
    use_ner: bool = False,
    ner_model_name: str = DEFAULT_NER_MODEL,
    use_llm_review: bool = False,
    llm_model_name: str = "",
) -> tuple[Path, dict[str, int], dict[str, object]]:
    """Anonymize a DOCX file and return safe audit metadata."""
    result = _anonymize_docx_file_result(
        source_path,
        sensitive_terms=sensitive_terms,
        sensitive_terms_path=sensitive_terms_path,
        output_dir=output_dir,
        use_ner=use_ner,
        ner_model_name=ner_model_name,
        use_llm_review=use_llm_review,
        llm_model_name=llm_model_name,
    )
    return result.output_path, result.counters, result.audit_result


def _anonymize_docx_file_result(
    source_path: str | Path,
    sensitive_terms: Iterable[SensitiveTerm] | None = None,
    sensitive_terms_path: str | Path | None = None,
    output_dir: str | Path | None = None,
    *,
    use_ner: bool = False,
    ner_model_name: str = DEFAULT_NER_MODEL,
    use_llm_review: bool = False,
    llm_model_name: str = "",
) -> FileWorkflowResult:
    """Anonymize a DOCX file and return paths needed by batch processing."""
    terms, dictionary_status = _prepare_workflow_dictionary(
        sensitive_terms, sensitive_terms_path
    )
    ner_context = prepare_ner_context(enabled=use_ner, model_name=ner_model_name)
    dictionary_counters: dict[str, int] = {}
    ner_counters: dict[str, int] = {}
    ner_status = build_ner_metadata(
        enabled=ner_context.enabled,
        used=False,
        status=ner_context.status,
        model_name=ner_context.model_name,
        warning=ner_context.warning,
    )

    def anonymize_docx_text(text: str) -> tuple[str, dict[str, int]]:
        nonlocal ner_status
        paragraph_result = _anonymize_text_with_dictionary_counters(
            text,
            sensitive_terms=terms,
            ner_context=ner_context,
        )
        anonymized, counters, paragraph_dictionary_counters, paragraph_ner_result = (
            paragraph_result
        )
        _merge_counters(dictionary_counters, paragraph_dictionary_counters)
        paragraph_ner_counters = paragraph_ner_result.get("counters", {})
        if isinstance(paragraph_ner_counters, dict):
            _merge_counters(
                ner_counters,
                {
                    label: count
                    for label, count in paragraph_ner_counters.items()
                    if isinstance(count, int)
                },
            )
        ner_status = paragraph_ner_result
        return anonymized, counters

    def anonymize_docx_run(text: str) -> tuple[str, dict[str, int]]:
        anonymized, counters, _, _ = _anonymize_text_with_dictionary_counters(
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
    llm_review_result = _run_optional_llm_review(
        anonymized_text,
        use_llm_review=use_llm_review,
        llm_model_name=llm_model_name,
    )
    dictionary_result = _dictionary_result(
        status=dictionary_status,
        sensitive_terms=terms,
        label_counters=dictionary_counters,
    )
    ner_result = dict(ner_status)
    if ner_counters:
        ner_result["used"] = True
        ner_result["counters"] = {
            label: ner_counters.get(label, 0)
            for label in NER_LABELS
        }
    audit_result = _attach_dictionary_result(
        audit_text(anonymized_text, sensitive_terms=terms),
        dictionary_result,
    )
    audit_result = _attach_ner_result(audit_result, ner_result)
    ocr_result = build_ocr_not_used_metadata(OCR_INPUT_TYPE_NONE)
    report_path = _save_anonymization_report(
        source_path,
        output_path,
        counters,
        audit_result,
        dictionary_result,
        ocr_result,
        ner_result,
        llm_review_result,
        output_dir=output_dir,
    )
    return FileWorkflowResult(
        output_path,
        report_path,
        counters,
        audit_result,
        ocr_result,
        ner_result,
        llm_review_result,
    )


def anonymize_pdf_file(
    source_path: str | Path,
    sensitive_terms: Iterable[SensitiveTerm] | None = None,
    sensitive_terms_path: str | Path | None = None,
    output_dir: str | Path | None = None,
    *,
    use_ner: bool = False,
    ner_model_name: str = DEFAULT_NER_MODEL,
    use_llm_review: bool = False,
    llm_model_name: str = "",
) -> tuple[Path, dict[str, int]]:
    """Anonymize text from a PDF and save TXT output plus a safe report."""
    output_path, counters, _ = anonymize_pdf_file_with_audit(
        source_path,
        sensitive_terms=sensitive_terms,
        sensitive_terms_path=sensitive_terms_path,
        output_dir=output_dir,
        use_ner=use_ner,
        ner_model_name=ner_model_name,
        use_llm_review=use_llm_review,
        llm_model_name=llm_model_name,
    )
    return output_path, counters


def anonymize_pdf_file_with_audit(
    source_path: str | Path,
    sensitive_terms: Iterable[SensitiveTerm] | None = None,
    sensitive_terms_path: str | Path | None = None,
    output_dir: str | Path | None = None,
    *,
    use_ner: bool = False,
    ner_model_name: str = DEFAULT_NER_MODEL,
    use_llm_review: bool = False,
    llm_model_name: str = "",
) -> tuple[Path, dict[str, int], dict[str, object]]:
    """Anonymize text from a PDF and return safe audit metadata."""
    result = _anonymize_pdf_file_result(
        source_path,
        sensitive_terms=sensitive_terms,
        sensitive_terms_path=sensitive_terms_path,
        output_dir=output_dir,
        use_ner=use_ner,
        ner_model_name=ner_model_name,
        use_llm_review=use_llm_review,
        llm_model_name=llm_model_name,
    )
    return result.output_path, result.counters, result.audit_result


def _anonymize_pdf_file_result(
    source_path: str | Path,
    sensitive_terms: Iterable[SensitiveTerm] | None = None,
    sensitive_terms_path: str | Path | None = None,
    output_dir: str | Path | None = None,
    *,
    use_ner: bool = False,
    ner_model_name: str = DEFAULT_NER_MODEL,
    use_llm_review: bool = False,
    llm_model_name: str = "",
) -> FileWorkflowResult:
    """Anonymize a PDF file and return paths needed by batch processing."""
    terms, dictionary_status = _prepare_workflow_dictionary(
        sensitive_terms, sensitive_terms_path
    )
    ner_context = prepare_ner_context(enabled=use_ner, model_name=ner_model_name)
    try:
        text = read_pdf_file(source_path)
        ocr_result = build_ocr_not_used_metadata(OCR_INPUT_TYPE_PDF)
    except ValueError as error:
        if "no extractable text" not in str(error):
            raise
        extraction = extract_text_with_ocr(source_path)
        text = extraction.text
        ocr_result = extraction.metadata
    anonymized, counters, dictionary_counters, ner_result = (
        _anonymize_text_with_dictionary_counters(
            text,
            sensitive_terms=terms,
            ner_context=ner_context,
        )
    )
    output_path = save_anonymized_pdf_txt_copy(
        source_path, anonymized, output_dir=output_dir
    )
    llm_review_result = _run_optional_llm_review(
        anonymized,
        use_llm_review=use_llm_review,
        llm_model_name=llm_model_name,
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
    audit_result = _attach_ner_result(audit_result, ner_result)
    report_path = _save_anonymization_report(
        source_path,
        output_path,
        counters,
        audit_result,
        dictionary_result,
        ocr_result,
        ner_result,
        llm_review_result,
        output_dir=output_dir,
    )
    return FileWorkflowResult(
        output_path,
        report_path,
        counters,
        audit_result,
        ocr_result,
        ner_result,
        llm_review_result,
    )


def anonymize_image_file(
    source_path: str | Path,
    sensitive_terms: Iterable[SensitiveTerm] | None = None,
    sensitive_terms_path: str | Path | None = None,
    output_dir: str | Path | None = None,
    *,
    use_ner: bool = False,
    ner_model_name: str = DEFAULT_NER_MODEL,
    use_llm_review: bool = False,
    llm_model_name: str = "",
) -> tuple[Path, dict[str, int]]:
    """Anonymize OCR text from an image and save TXT output plus a safe report."""
    output_path, counters, _ = anonymize_image_file_with_audit(
        source_path,
        sensitive_terms=sensitive_terms,
        sensitive_terms_path=sensitive_terms_path,
        output_dir=output_dir,
        use_ner=use_ner,
        ner_model_name=ner_model_name,
        use_llm_review=use_llm_review,
        llm_model_name=llm_model_name,
    )
    return output_path, counters


def anonymize_image_file_with_audit(
    source_path: str | Path,
    sensitive_terms: Iterable[SensitiveTerm] | None = None,
    sensitive_terms_path: str | Path | None = None,
    output_dir: str | Path | None = None,
    *,
    use_ner: bool = False,
    ner_model_name: str = DEFAULT_NER_MODEL,
    use_llm_review: bool = False,
    llm_model_name: str = "",
) -> tuple[Path, dict[str, int], dict[str, object]]:
    """Anonymize OCR text from an image and return safe audit metadata."""
    result = _anonymize_image_file_result(
        source_path,
        sensitive_terms=sensitive_terms,
        sensitive_terms_path=sensitive_terms_path,
        output_dir=output_dir,
        use_ner=use_ner,
        ner_model_name=ner_model_name,
        use_llm_review=use_llm_review,
        llm_model_name=llm_model_name,
    )
    return result.output_path, result.counters, result.audit_result


def _anonymize_image_file_result(
    source_path: str | Path,
    sensitive_terms: Iterable[SensitiveTerm] | None = None,
    sensitive_terms_path: str | Path | None = None,
    output_dir: str | Path | None = None,
    *,
    use_ner: bool = False,
    ner_model_name: str = DEFAULT_NER_MODEL,
    use_llm_review: bool = False,
    llm_model_name: str = "",
) -> FileWorkflowResult:
    """Anonymize OCR text from an image and return paths for batch processing."""
    terms, dictionary_status = _prepare_workflow_dictionary(
        sensitive_terms, sensitive_terms_path
    )
    ner_context = prepare_ner_context(enabled=use_ner, model_name=ner_model_name)
    extraction = extract_text_with_ocr(source_path)
    anonymized, counters, dictionary_counters, ner_result = (
        _anonymize_text_with_dictionary_counters(
            extraction.text,
            sensitive_terms=terms,
            ner_context=ner_context,
        )
    )
    output_path = save_anonymized_image_txt_copy(
        source_path, anonymized, output_dir=output_dir
    )
    llm_review_result = _run_optional_llm_review(
        anonymized,
        use_llm_review=use_llm_review,
        llm_model_name=llm_model_name,
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
    audit_result = _attach_ner_result(audit_result, ner_result)
    report_path = _save_anonymization_report(
        source_path,
        output_path,
        counters,
        audit_result,
        dictionary_result,
        extraction.metadata,
        ner_result,
        llm_review_result,
        output_dir=output_dir,
    )
    return FileWorkflowResult(
        output_path,
        report_path,
        counters,
        audit_result,
        extraction.metadata,
        ner_result,
        llm_review_result,
    )


def _save_anonymization_report(
    source_path: str | Path,
    output_path: str | Path,
    counters: dict[str, int],
    audit_result: dict[str, object],
    dictionary_result: dict[str, object],
    ocr_result: dict[str, object],
    ner_result: dict[str, object],
    llm_review_result: dict[str, object],
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
        category_order=REPORT_CATEGORY_ORDER,
        audit_result=audit_result,
        audit_category_order=AUDIT_CATEGORY_ORDER,
        dictionary_result=dictionary_result,
        ocr_result=ocr_result,
        ner_result=ner_result,
        llm_review_result=llm_review_result,
    )


def anonymize_file(
    source_path: str | Path,
    sensitive_terms: Iterable[SensitiveTerm] | None = None,
    sensitive_terms_path: str | Path | None = None,
    output_dir: str | Path | None = None,
    *,
    use_ner: bool = False,
    ner_model_name: str = DEFAULT_NER_MODEL,
    use_llm_review: bool = False,
    llm_model_name: str = "",
) -> tuple[Path, dict[str, int]]:
    """Anonymize one supported application file using existing workflows."""
    output_path, counters, _ = anonymize_file_with_audit(
        source_path,
        sensitive_terms=sensitive_terms,
        sensitive_terms_path=sensitive_terms_path,
        output_dir=output_dir,
        use_ner=use_ner,
        ner_model_name=ner_model_name,
        use_llm_review=use_llm_review,
        llm_model_name=llm_model_name,
    )
    return output_path, counters


def anonymize_file_with_audit(
    source_path: str | Path,
    sensitive_terms: Iterable[SensitiveTerm] | None = None,
    sensitive_terms_path: str | Path | None = None,
    output_dir: str | Path | None = None,
    *,
    use_ner: bool = False,
    ner_model_name: str = DEFAULT_NER_MODEL,
    use_llm_review: bool = False,
    llm_model_name: str = "",
) -> tuple[Path, dict[str, int], dict[str, object]]:
    """Anonymize one supported file and return safe audit metadata."""
    result = _anonymize_file_result(
        source_path,
        sensitive_terms=sensitive_terms,
        sensitive_terms_path=sensitive_terms_path,
        output_dir=output_dir,
        use_ner=use_ner,
        ner_model_name=ner_model_name,
        use_llm_review=use_llm_review,
        llm_model_name=llm_model_name,
    )
    return result.output_path, result.counters, result.audit_result


def _anonymize_file_result(
    source_path: str | Path,
    sensitive_terms: Iterable[SensitiveTerm] | None = None,
    sensitive_terms_path: str | Path | None = None,
    output_dir: str | Path | None = None,
    *,
    use_ner: bool = False,
    ner_model_name: str = DEFAULT_NER_MODEL,
    use_llm_review: bool = False,
    llm_model_name: str = "",
) -> FileWorkflowResult:
    """Anonymize one supported file and return paths needed by batch processing."""
    path = Path(source_path)

    if path.suffix.lower() == TXT_EXTENSION:
        return _anonymize_txt_file_result(
            path,
            sensitive_terms=sensitive_terms,
            sensitive_terms_path=sensitive_terms_path,
            output_dir=output_dir,
            use_ner=use_ner,
            ner_model_name=ner_model_name,
            use_llm_review=use_llm_review,
            llm_model_name=llm_model_name,
        )
    if path.suffix.lower() == DOCX_EXTENSION:
        return _anonymize_docx_file_result(
            path,
            sensitive_terms=sensitive_terms,
            sensitive_terms_path=sensitive_terms_path,
            output_dir=output_dir,
            use_ner=use_ner,
            ner_model_name=ner_model_name,
            use_llm_review=use_llm_review,
            llm_model_name=llm_model_name,
        )
    if path.suffix.lower() == PDF_EXTENSION:
        return _anonymize_pdf_file_result(
            path,
            sensitive_terms=sensitive_terms,
            sensitive_terms_path=sensitive_terms_path,
            output_dir=output_dir,
            use_ner=use_ner,
            ner_model_name=ner_model_name,
            use_llm_review=use_llm_review,
            llm_model_name=llm_model_name,
        )
    if path.suffix.lower() in IMAGE_EXTENSIONS:
        return _anonymize_image_file_result(
            path,
            sensitive_terms=sensitive_terms,
            sensitive_terms_path=sensitive_terms_path,
            output_dir=output_dir,
            use_ner=use_ner,
            ner_model_name=ner_model_name,
            use_llm_review=use_llm_review,
            llm_model_name=llm_model_name,
        )

    suffix = path.suffix.lower() or "<none>"
    supported = ", ".join(SUPPORTED_EXTENSIONS)
    raise ValueError(
        f"Unsupported file extension for anonymize_file: {suffix}. "
        f"Only {supported} files are supported."
    )


def _safe_batch_error_description(error: Exception) -> str:
    if isinstance(error, OcrUnavailableError):
        if error.status in ("dependency_missing", "engine_not_found"):
            return BATCH_ERROR_OCR_UNAVAILABLE
        return BATCH_ERROR_OCR_FAILED
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
    *,
    use_ner: bool = False,
    ner_model_name: str = DEFAULT_NER_MODEL,
    use_llm_review: bool = False,
    llm_model_name: str = "",
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
    ner_status_counts = {status: 0 for status in NER_STATUSES}
    ner_category_counters = {label: 0 for label in NER_LABELS}
    llm_review_status_counts = {status: 0 for status in LLM_REVIEW_STATUSES}
    llm_review_risk_level_counts = {risk: 0 for risk in LLM_RISK_LEVELS}
    llm_review_category_counters = {category: 0 for category in LLM_RESIDUAL_CATEGORIES}
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
                use_ner=use_ner,
                ner_model_name=ner_model_name,
                use_llm_review=use_llm_review,
                llm_model_name=llm_model_name,
            )
        except Exception as error:
            error_count += 1
            audit_status_counts["not run"] += 1
            error_result = {
                "input_name": path.name,
                "status": "error",
                "error": _safe_batch_error_description(error),
            }
            if isinstance(error, OcrUnavailableError):
                error_result["ocr_used"] = False
                error_result["ocr_status"] = error.status
            results.append(
                error_result
            )
            continue

        success_count += 1
        _merge_counters(aggregate_counters, result.counters)
        _merge_audit_status_count(audit_status_counts, result.audit_result)
        _merge_risk_level_count(risk_level_counts, result.audit_result)
        _merge_audit_findings(audit_category_counters, result.audit_result)
        ner_status = str(result.ner_result.get("status", "unavailable"))
        if ner_status not in ner_status_counts:
            ner_status = "unavailable"
        ner_status_counts[ner_status] = ner_status_counts.get(ner_status, 0) + 1
        ner_result_counters = result.ner_result.get("counters", {})
        if isinstance(ner_result_counters, dict):
            for label in NER_LABELS:
                count = ner_result_counters.get(label, 0)
                if isinstance(count, int):
                    ner_category_counters[label] = (
                        ner_category_counters.get(label, 0) + count
                    )
        llm_status = str(result.llm_review_result.get("status", "disabled"))
        if llm_status not in llm_review_status_counts:
            llm_status = "unavailable"
        llm_review_status_counts[llm_status] = (
            llm_review_status_counts.get(llm_status, 0) + 1
        )
        llm_risk_level = str(result.llm_review_result.get("risk_level", "unknown"))
        if llm_risk_level not in llm_review_risk_level_counts:
            llm_risk_level = "unknown"
        llm_review_risk_level_counts[llm_risk_level] = (
            llm_review_risk_level_counts.get(llm_risk_level, 0) + 1
        )
        llm_categories = result.llm_review_result.get("possible_residual_categories", [])
        if isinstance(llm_categories, list):
            for category in llm_categories:
                if category in llm_review_category_counters:
                    llm_review_category_counters[category] = (
                        llm_review_category_counters.get(category, 0) + 1
                    )
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
                "ocr_used": result.ocr_result.get("used", False),
                "ocr_status": result.ocr_result.get("status", "not_used"),
                "ner_used": result.ner_result.get("used", False),
                "ner_status": result.ner_result.get("status", "unavailable"),
                "llm_review_used": result.llm_review_result.get("used", False),
                "llm_review_status": result.llm_review_result.get(
                    "status", "disabled"
                ),
                "llm_risk_level": result.llm_review_result.get(
                    "risk_level", "unknown"
                ),
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
        ner_status_counts=ner_status_counts,
        ner_category_counters=ner_category_counters,
        llm_review_status_counts=llm_review_status_counts,
        llm_review_risk_level_counts=llm_review_risk_level_counts,
        llm_review_category_counters=llm_review_category_counters,
        results=results,
        category_order=REPORT_CATEGORY_ORDER,
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
        ner_status_counts=ner_status_counts,
        ner_category_counters=ner_category_counters,
        llm_review_status_counts=llm_review_status_counts,
        llm_review_risk_level_counts=llm_review_risk_level_counts,
        llm_review_category_counters=llm_review_category_counters,
    )
