"""Optional local OCR support for image-based inputs."""

from __future__ import annotations

from dataclasses import dataclass
from importlib import import_module
from io import BytesIO
from pathlib import Path
from typing import Any


OCR_STATUS_AVAILABLE = "available"
OCR_STATUS_UNAVAILABLE = "unavailable"
OCR_STATUS_DEPENDENCY_MISSING = "dependency_missing"
OCR_STATUS_ENGINE_NOT_FOUND = "engine_not_found"
OCR_STATUS_UNSUPPORTED_INPUT = "unsupported_input"
OCR_STATUS_NOT_USED = "not_used"
OCR_STATUSES = (
    OCR_STATUS_AVAILABLE,
    OCR_STATUS_UNAVAILABLE,
    OCR_STATUS_DEPENDENCY_MISSING,
    OCR_STATUS_ENGINE_NOT_FOUND,
    OCR_STATUS_UNSUPPORTED_INPUT,
    OCR_STATUS_NOT_USED,
)

OCR_INPUT_TYPE_IMAGE = "image"
OCR_INPUT_TYPE_PDF = "pdf"
OCR_INPUT_TYPE_NONE = "none"
OCR_INPUT_TYPES = (OCR_INPUT_TYPE_IMAGE, OCR_INPUT_TYPE_PDF, OCR_INPUT_TYPE_NONE)

OCR_WARNING_DEPENDENCY_MISSING = "local OCR dependency is missing"
OCR_WARNING_ENGINE_NOT_FOUND = "local OCR engine not found"
OCR_WARNING_UNSUPPORTED_INPUT = "input type is not supported for OCR"
OCR_WARNING_NO_TEXT = "OCR completed but no text was extracted"
OCR_WARNING_FAILED = "OCR failed safely"

IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".tif", ".tiff")


@dataclass(frozen=True)
class OcrExtraction:
    """OCR text plus safe metadata."""

    text: str
    metadata: dict[str, object]


class OcrUnavailableError(RuntimeError):
    """Controlled OCR failure without paths, tracebacks, or source text."""

    def __init__(
        self,
        status: str,
        input_type: str,
        warning: str,
        *,
        items_processed: int = 0,
    ) -> None:
        self.status = status
        self.input_type = input_type
        self.warning = warning
        self.items_processed = items_processed
        super().__init__(warning)

    def metadata(self) -> dict[str, object]:
        return build_ocr_metadata(
            used=False,
            status=self.status,
            input_type=self.input_type,
            items_processed=self.items_processed,
            warning=self.warning,
        )


def build_ocr_metadata(
    *,
    used: bool,
    status: str,
    input_type: str,
    items_processed: int = 0,
    warning: str = "",
) -> dict[str, object]:
    """Build safe OCR metadata for reports and batch summaries."""
    if status not in OCR_STATUSES:
        status = OCR_STATUS_UNAVAILABLE
    if input_type not in OCR_INPUT_TYPES:
        input_type = OCR_INPUT_TYPE_NONE
    if not isinstance(items_processed, int) or items_processed < 0:
        items_processed = 0

    return {
        "used": bool(used),
        "status": status,
        "input_type": input_type,
        "items_processed": items_processed,
        "warning": str(warning or ""),
    }


def build_ocr_not_used_metadata(input_type: str = OCR_INPUT_TYPE_NONE) -> dict[str, object]:
    """Return safe metadata for workflows that did not invoke OCR."""
    return build_ocr_metadata(
        used=False,
        status=OCR_STATUS_NOT_USED,
        input_type=input_type,
        items_processed=0,
    )


def _import_optional(module_name: str) -> Any | None:
    try:
        return import_module(module_name)
    except ModuleNotFoundError:
        return None


def _pytesseract_module():
    return _import_optional("pytesseract")


def _image_module():
    pil_image = _import_optional("PIL.Image")
    if pil_image is not None:
        return pil_image

    pil = _import_optional("PIL")
    return getattr(pil, "Image", None) if pil is not None else None


def _fitz_module():
    return _import_optional("fitz")


def _is_tesseract_not_found(error: Exception, pytesseract_module: Any) -> bool:
    tesseract_error = getattr(pytesseract_module, "TesseractNotFoundError", None)
    return (
        isinstance(error, FileNotFoundError)
        or (tesseract_error is not None and isinstance(error, tesseract_error))
        or "tesseract" in str(error).lower()
    )


def detect_ocr_support(input_type: str = OCR_INPUT_TYPE_IMAGE) -> dict[str, object]:
    """Detect optional local OCR dependencies without raising on absence."""
    if input_type not in (OCR_INPUT_TYPE_IMAGE, OCR_INPUT_TYPE_PDF):
        return build_ocr_metadata(
            used=False,
            status=OCR_STATUS_UNSUPPORTED_INPUT,
            input_type=OCR_INPUT_TYPE_NONE,
            warning=OCR_WARNING_UNSUPPORTED_INPUT,
        )

    pytesseract_module = _pytesseract_module()
    image_module = _image_module()
    if pytesseract_module is None or image_module is None:
        return build_ocr_metadata(
            used=False,
            status=OCR_STATUS_DEPENDENCY_MISSING,
            input_type=input_type,
            warning=OCR_WARNING_DEPENDENCY_MISSING,
        )

    if input_type == OCR_INPUT_TYPE_PDF and _fitz_module() is None:
        return build_ocr_metadata(
            used=False,
            status=OCR_STATUS_DEPENDENCY_MISSING,
            input_type=input_type,
            warning=OCR_WARNING_DEPENDENCY_MISSING,
        )

    try:
        pytesseract_module.get_tesseract_version()
    except Exception as error:
        status = (
            OCR_STATUS_ENGINE_NOT_FOUND
            if _is_tesseract_not_found(error, pytesseract_module)
            else OCR_STATUS_UNAVAILABLE
        )
        warning = (
            OCR_WARNING_ENGINE_NOT_FOUND
            if status == OCR_STATUS_ENGINE_NOT_FOUND
            else OCR_WARNING_FAILED
        )
        return build_ocr_metadata(
            used=False,
            status=status,
            input_type=input_type,
            warning=warning,
        )

    return build_ocr_metadata(
        used=False,
        status=OCR_STATUS_AVAILABLE,
        input_type=input_type,
    )


def _ensure_image_path(file_path: str | Path) -> Path:
    path = Path(file_path)
    if path.suffix.lower() not in IMAGE_EXTENSIONS:
        raise OcrUnavailableError(
            OCR_STATUS_UNSUPPORTED_INPUT,
            OCR_INPUT_TYPE_IMAGE,
            OCR_WARNING_UNSUPPORTED_INPUT,
        )
    return path


def _ensure_pdf_path(file_path: str | Path) -> Path:
    path = Path(file_path)
    if path.suffix.lower() != ".pdf":
        raise OcrUnavailableError(
            OCR_STATUS_UNSUPPORTED_INPUT,
            OCR_INPUT_TYPE_PDF,
            OCR_WARNING_UNSUPPORTED_INPUT,
        )
    return path


def _raise_if_unavailable(metadata: dict[str, object], input_type: str) -> None:
    if metadata.get("status") == OCR_STATUS_AVAILABLE:
        return
    raise OcrUnavailableError(
        str(metadata.get("status", OCR_STATUS_UNAVAILABLE)),
        input_type,
        str(metadata.get("warning") or OCR_WARNING_FAILED),
        items_processed=int(metadata.get("items_processed", 0)),
    )


def extract_text_from_image(file_path: str | Path) -> OcrExtraction:
    """Extract text from a local image with optional Tesseract OCR."""
    path = _ensure_image_path(file_path)
    availability = detect_ocr_support(OCR_INPUT_TYPE_IMAGE)
    _raise_if_unavailable(availability, OCR_INPUT_TYPE_IMAGE)

    pytesseract_module = _pytesseract_module()
    image_module = _image_module()
    if pytesseract_module is None or image_module is None:
        raise OcrUnavailableError(
            OCR_STATUS_DEPENDENCY_MISSING,
            OCR_INPUT_TYPE_IMAGE,
            OCR_WARNING_DEPENDENCY_MISSING,
        )

    try:
        with image_module.open(path) as image:
            text = pytesseract_module.image_to_string(image)
    except Exception as error:
        if _is_tesseract_not_found(error, pytesseract_module):
            raise OcrUnavailableError(
                OCR_STATUS_ENGINE_NOT_FOUND,
                OCR_INPUT_TYPE_IMAGE,
                OCR_WARNING_ENGINE_NOT_FOUND,
            ) from error
        raise OcrUnavailableError(
            OCR_STATUS_UNAVAILABLE,
            OCR_INPUT_TYPE_IMAGE,
            OCR_WARNING_FAILED,
        ) from error

    if not str(text).strip():
        raise OcrUnavailableError(
            OCR_STATUS_UNAVAILABLE,
            OCR_INPUT_TYPE_IMAGE,
            OCR_WARNING_NO_TEXT,
            items_processed=1,
        )

    return OcrExtraction(
        text=str(text),
        metadata=build_ocr_metadata(
            used=True,
            status=OCR_STATUS_AVAILABLE,
            input_type=OCR_INPUT_TYPE_IMAGE,
            items_processed=1,
        ),
    )


def extract_text_from_pdf(file_path: str | Path) -> OcrExtraction:
    """Extract text from a local scanned PDF with optional Tesseract OCR."""
    path = _ensure_pdf_path(file_path)
    availability = detect_ocr_support(OCR_INPUT_TYPE_PDF)
    _raise_if_unavailable(availability, OCR_INPUT_TYPE_PDF)

    pytesseract_module = _pytesseract_module()
    image_module = _image_module()
    fitz_module = _fitz_module()
    if pytesseract_module is None or image_module is None or fitz_module is None:
        raise OcrUnavailableError(
            OCR_STATUS_DEPENDENCY_MISSING,
            OCR_INPUT_TYPE_PDF,
            OCR_WARNING_DEPENDENCY_MISSING,
        )

    text_parts: list[str] = []
    page_count = 0
    document = None
    try:
        document = fitz_module.open(path)
        for page in document:
            page_count += 1
            pixmap = page.get_pixmap()
            image_bytes = pixmap.tobytes("png")
            with image_module.open(BytesIO(image_bytes)) as image:
                page_text = pytesseract_module.image_to_string(image)
            if page_text:
                text_parts.append(str(page_text))
    except Exception as error:
        if pytesseract_module is not None and _is_tesseract_not_found(
            error, pytesseract_module
        ):
            raise OcrUnavailableError(
                OCR_STATUS_ENGINE_NOT_FOUND,
                OCR_INPUT_TYPE_PDF,
                OCR_WARNING_ENGINE_NOT_FOUND,
                items_processed=page_count,
            ) from error
        raise OcrUnavailableError(
            OCR_STATUS_UNAVAILABLE,
            OCR_INPUT_TYPE_PDF,
            OCR_WARNING_FAILED,
            items_processed=page_count,
        ) from error
    finally:
        if document is not None and hasattr(document, "close"):
            document.close()

    text = "\n".join(text_parts)
    if not text.strip():
        raise OcrUnavailableError(
            OCR_STATUS_UNAVAILABLE,
            OCR_INPUT_TYPE_PDF,
            OCR_WARNING_NO_TEXT,
            items_processed=page_count,
        )

    return OcrExtraction(
        text=text,
        metadata=build_ocr_metadata(
            used=True,
            status=OCR_STATUS_AVAILABLE,
            input_type=OCR_INPUT_TYPE_PDF,
            items_processed=page_count,
        ),
    )


def extract_text_with_ocr(file_path: str | Path) -> OcrExtraction:
    """Extract text with OCR for supported image or scanned PDF inputs."""
    path = Path(file_path)
    suffix = path.suffix.lower()
    if suffix in IMAGE_EXTENSIONS:
        return extract_text_from_image(path)
    if suffix == ".pdf":
        return extract_text_from_pdf(path)

    raise OcrUnavailableError(
        OCR_STATUS_UNSUPPORTED_INPUT,
        OCR_INPUT_TYPE_NONE,
        OCR_WARNING_UNSUPPORTED_INPUT,
    )
