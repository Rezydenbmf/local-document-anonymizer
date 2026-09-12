"""Optional local OCR support for image-based inputs."""

from __future__ import annotations

import os
import shutil
import sys
import urllib.error
import urllib.request
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
# PyMuPDF's default page.get_pixmap() renders at the PDF's native 72 DPI
# (1 point = 1/72 inch, zoom 1.0) - far below the ~300 DPI Tesseract's
# own documentation recommends for reliable accuracy, and a real
# contributor (alongside the wrong-language default _ocr_language fixes)
# to garbled OCR text on scanned PDFs. A 3x zoom renders at 216 DPI, a
# solid accuracy/speed/memory tradeoff for multi-page documents without
# going all the way to 300+ DPI's much larger per-page images.
OCR_PDF_RENDER_ZOOM = 3.0

# This app's OCR language policy: Polish is the baseline (the target
# documents are Polish business/legal paperwork), English is the
# secondary language always paired with it (for the Latin abbreviations
# - NIP, REGON, IBAN - that show up in otherwise-Polish documents).
PRIMARY_OCR_LANGUAGE = "pol"
SECONDARY_OCR_LANGUAGE = "eng"

# tessdata_fast: Tesseract's own smaller/faster trained-data variant -
# a better fit for an on-demand desktop download than the much larger
# "best"-accuracy models, which trade file size for a level of accuracy
# this app's use case doesn't need.
TESSDATA_DOWNLOAD_URL_TEMPLATE = (
    "https://raw.githubusercontent.com/tesseract-ocr/tessdata_fast"
    "/main/{lang}.traineddata"
)

# A deliberately short list of languages likely to actually show up in
# this app's documents (or be asked for by a Polish-market user), not
# Tesseract's full 100+ language catalog - keeps the Settings dropdown
# usable instead of an overwhelming, mostly-irrelevant wall of options.
COMMON_OCR_LANGUAGES_PL: dict[str, str] = {
    "pol": "polski",
    "eng": "angielski",
    "deu": "niemiecki",
    "ukr": "ukraiński",
    "rus": "rosyjski",
    "fra": "francuski",
    "spa": "hiszpański",
    "ita": "włoski",
    "ces": "czeski",
    "slk": "słowacki",
    "lit": "litewski",
    "nld": "niderlandzki",
}


@dataclass(frozen=True)
class OcrExtraction:
    """OCR text plus safe metadata."""

    text: str
    metadata: dict[str, object]


@dataclass(frozen=True)
class OcrWordPageExtraction:
    """Per-page OCR word boxes (mechanical OCR output only - no text
    reconstruction/offset-tracking here, see
    pdf_redaction.word_pages_from_ocr_boxes for that) plus the same safe
    metadata shape OcrExtraction uses. ``pages`` is a list of
    ``{"page_number": int, "words": [{"text", "rect", "block_no",
    "line_no", "word_no"}, ...]}`` - "rect" is already converted to PDF
    point space (an (x0, y0, x1, y1) tuple), not the OCR render's raw
    pixel space.
    """

    pages: list[dict[str, object]]
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
    return _import_optional("pymupdf")


def _is_tesseract_not_found(error: Exception, pytesseract_module: Any) -> bool:
    tesseract_error = getattr(pytesseract_module, "TesseractNotFoundError", None)
    return (
        isinstance(error, FileNotFoundError)
        or (tesseract_error is not None and isinstance(error, tesseract_error))
        or "tesseract" in str(error).lower()
    )


# The official Windows installer does not reliably add itself to PATH -
# confirmed on a real pilot machine: the binary was present at the default
# location but no PATH entry existed at all (see docs/PROJECT_STATE.md).
# These are the only two locations the installer itself offers, so falling
# back to them covers that case without any manual PATH editing.
_TESSERACT_WINDOWS_CANDIDATES = (
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
)


_BUNDLED_TESSERACT_ZIP_NAME = "tesseract_runtime.zip"


def _extract_bundled_tesseract_zip(bundle_dir: Path) -> Path | None:
    """Unpack the installer's tesseract_runtime.zip into a "tesseract"
    subfolder next to the running exe, the first time it's needed.

    Why a zip and not a plain folder the installer drops loose files
    into: a real install once appeared to lose that subfolder entirely
    after setup. The actual cause turned out to be test-environment
    contamination (a stale Inno Setup "remembered install location" in
    the registry from an earlier test run, plus a permissions issue
    checking a Program Files install as non-admin) rather than anything
    about the files themselves - a from-scratch install with the loose
    layout, verified after clearing that state, worked fine. Kept as a
    zip anyway on general principle: an installer writing one
    unremarkable data file, with extraction happening later from
    DocShield.exe's own already-running process, is a strictly smaller
    surface for *any* third-party security software to react badly to
    than ~60 individually-named unsigned binaries landing at once - a
    real possibility this app has no control over, even without a
    confirmed case of it happening here.

    Idempotent and safe against a half-finished previous attempt: checks
    the real target file's presence before re-extracting, and every
    member path is verified to stay under the destination folder before
    being written (defense in depth - this app controls the zip's
    contents at build time, but a corrupted or tampered file should
    still never write outside its own folder).
    """
    target = bundle_dir / "tesseract" / "tesseract.exe"
    if target.is_file():
        return target
    zip_path = bundle_dir / _BUNDLED_TESSERACT_ZIP_NAME
    if not zip_path.is_file():
        return None
    dest_root = (bundle_dir / "tesseract").resolve()
    try:
        import zipfile

        with zipfile.ZipFile(zip_path) as archive:
            for member in archive.infolist():
                member_path = (dest_root / member.filename).resolve()
                if dest_root != member_path and dest_root not in member_path.parents:
                    continue
                archive.extract(member, dest_root)
    except (OSError, zipfile.BadZipFile):
        return None
    return target if target.is_file() else None


def _bundled_tesseract_path() -> Path | None:
    """The Tesseract copy the installer places next to DocShield.exe,
    if this is a frozen (PyInstaller) build - see build_installer.ps1,
    which stages a trimmed Tesseract runtime as tesseract_runtime.zip
    alongside the packaged executable, unpacked here on first use. None
    when running from source, where no such file exists."""
    if not getattr(sys, "frozen", False):
        return None
    bundle_dir = Path(sys.executable).resolve().parent
    return _extract_bundled_tesseract_zip(bundle_dir)


def _resolve_tesseract_cmd() -> str | None:
    """Find a Tesseract executable even when it isn't on PATH.

    Returns None only when nothing is found anywhere - callers should
    treat that the same as "not installed".
    """
    bundled = _bundled_tesseract_path()
    if bundled is not None:
        return str(bundled)
    found_on_path = shutil.which("tesseract")
    if found_on_path:
        return found_on_path
    if sys.platform != "win32":
        return None
    for candidate in _TESSERACT_WINDOWS_CANDIDATES:
        if Path(candidate).is_file():
            return candidate
    return None


def _configure_tesseract_cmd(pytesseract_module: Any) -> None:
    """Point pytesseract at a discovered Tesseract binary, if needed.

    Cheap and idempotent: only overrides pytesseract's configured command
    when the current one isn't resolvable as-is, so it never clobbers a
    path something else already configured correctly. `getattr(...,
    "pytesseract", pytesseract_module)` tolerates simplified test doubles
    that don't mirror the real package's `pytesseract.pytesseract`
    submodule structure.
    """
    config_target = getattr(pytesseract_module, "pytesseract", pytesseract_module)
    current_cmd = getattr(config_target, "tesseract_cmd", "tesseract")
    if shutil.which(current_cmd):
        return
    resolved = _resolve_tesseract_cmd()
    if resolved:
        try:
            config_target.tesseract_cmd = resolved
        except AttributeError:
            pass


def _ocr_language(pytesseract_module: Any) -> str:
    """Pick the best installed Tesseract language for this app's target
    documents (Polish business/legal paperwork).

    Without an explicit `lang`, pytesseract defaults to Tesseract's own
    default - "eng" - which reads Polish text as if it were English:
    diacritics (ą, ę, ć, ł, ń, ó, ś, ź, ż) and Polish letter combinations
    get silently misrecognized into plausible-looking but wrong
    characters, producing exactly the kind of garbled-but-not-obviously-
    broken output that's hard to notice until someone reads the result.
    Prefers "pol+eng" (Polish primary, English still recognized for the
    English/Latin abbreviations and acronyms that show up in Polish
    business documents - NIP, REGON, IBAN, etc.); falls back to "eng"
    alone only when the "pol" trained-data file isn't installed, so OCR
    still produces *something* rather than failing outright - never
    raises, since a wrong language degrades quality but a crash here
    would be worse.
    """
    available = list_installed_languages(pytesseract_module)
    if PRIMARY_OCR_LANGUAGE in available:
        if SECONDARY_OCR_LANGUAGE in available:
            return f"{PRIMARY_OCR_LANGUAGE}+{SECONDARY_OCR_LANGUAGE}"
        return PRIMARY_OCR_LANGUAGE
    return SECONDARY_OCR_LANGUAGE


def list_installed_languages(pytesseract_module: Any | None = None) -> list[str]:
    """Return the Tesseract language codes actually installed, sorted -
    "osd"/"equ" (orientation-detection/equation auxiliary data, not real
    languages) filtered out since they'd be confusing in a "supported
    languages" list shown to the user. Empty list on any failure
    (Tesseract missing, call unsupported, ...) rather than raising."""
    if pytesseract_module is None:
        pytesseract_module = _pytesseract_module()
    if pytesseract_module is None:
        return []
    try:
        _configure_tesseract_cmd(pytesseract_module)
        available = set(pytesseract_module.get_languages(config=""))
    except Exception:  # noqa: BLE001 - listing languages must never crash
        return []
    return order_languages_primary_first(sorted(available - {"osd", "equ"}))


def order_languages_primary_first(language_codes: list[str]) -> list[str]:
    """Sort a language-code list with PRIMARY_OCR_LANGUAGE (Polish) first,
    then SECONDARY_OCR_LANGUAGE (English), then everything else
    alphabetically - so any "installed/supported languages" display
    consistently reflects this app's Polish-first policy instead of a
    plain alphabetical order that would bury Polish behind "angielski"."""
    rest = sorted(
        code
        for code in language_codes
        if code not in (PRIMARY_OCR_LANGUAGE, SECONDARY_OCR_LANGUAGE)
    )
    ordered = [
        code
        for code in (PRIMARY_OCR_LANGUAGE, SECONDARY_OCR_LANGUAGE)
        if code in language_codes
    ]
    return ordered + rest


def _resolve_tessdata_dir(pytesseract_module: Any) -> Path | None:
    """Find the tessdata directory Tesseract itself reads language files
    from, so a downloaded pack lands somewhere Tesseract will actually
    look - honors TESSDATA_PREFIX if set (the standard Tesseract
    override), otherwise falls back to the conventional `tessdata`
    folder next to the resolved tesseract executable (matches how the
    official Windows installer lays it out). Returns None, never raises,
    when neither can be determined - the caller reports that as a clear
    failure rather than guessing a path that might be wrong.
    """
    prefix = os.environ.get("TESSDATA_PREFIX")
    if prefix:
        candidate = Path(prefix)
        if candidate.is_dir():
            return candidate
    config_target = getattr(pytesseract_module, "pytesseract", pytesseract_module)
    cmd = getattr(config_target, "tesseract_cmd", "tesseract")
    resolved = shutil.which(cmd) or (cmd if Path(cmd).is_file() else None)
    if not resolved:
        return None
    candidate = Path(resolved).resolve().parent / "tessdata"
    return candidate if candidate.is_dir() else None


def download_language_pack(
    lang_code: str, timeout_seconds: float = 30.0
) -> tuple[bool, str]:
    """Download one Tesseract trained-data file into the local tessdata
    folder - a plain data file Tesseract already reads from, not an
    installer, so (unlike Tesseract/Ollama themselves) this is safely
    automatable as long as that folder is writable by the current user.

    Reaches the internet on this one explicit, user-triggered action
    only (same as the existing pip-package-update/spaCy-model-download
    flows) - never during normal document processing. Writes to a
    `.part` file first and renames it into place only once the download
    fully succeeds, so a failure partway through never leaves a
    corrupt/partial `.traineddata` file that Tesseract would then fail
    to load. Never raises - every failure mode (no Tesseract, unknown
    tessdata location, no write permission, network error) becomes a
    `(False, polish_message)` result the caller can show directly.
    """
    pytesseract_module = _pytesseract_module()
    if pytesseract_module is None:
        return False, "Biblioteka pytesseract nie jest zainstalowana."
    _configure_tesseract_cmd(pytesseract_module)
    tessdata_dir = _resolve_tessdata_dir(pytesseract_module)
    if tessdata_dir is None:
        return False, (
            "Nie udało się znaleźć folderu tessdata - upewnij się, że "
            "Tesseract jest zainstalowany."
        )

    url = TESSDATA_DOWNLOAD_URL_TEMPLATE.format(lang=lang_code)
    target_path = tessdata_dir / f"{lang_code}.traineddata"
    part_path = tessdata_dir / f"{lang_code}.traineddata.part"
    try:
        with urllib.request.urlopen(url, timeout=timeout_seconds) as response:
            part_path.write_bytes(response.read())
        os.replace(part_path, target_path)
    except (urllib.error.URLError, TimeoutError, OSError) as error:
        try:
            part_path.unlink(missing_ok=True)
        except OSError:
            pass
        if isinstance(error, PermissionError):
            return False, (
                f"Brak uprawnień do zapisu w folderze {tessdata_dir} - "
                "uruchom aplikację jako administrator albo dodaj plik "
                "ręcznie."
            )
        return False, (
            "Nie udało się pobrać pakietu językowego (sprawdź połączenie "
            "z internetem)."
        )
    return True, ""


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

    _configure_tesseract_cmd(pytesseract_module)
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
            text = pytesseract_module.image_to_string(
                image, lang=_ocr_language(pytesseract_module)
            )
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

    lang = _ocr_language(pytesseract_module)
    render_matrix = fitz_module.Matrix(OCR_PDF_RENDER_ZOOM, OCR_PDF_RENDER_ZOOM)
    text_parts: list[str] = []
    page_count = 0
    document = None
    try:
        document = fitz_module.open(path)
        for page in document:
            page_count += 1
            pixmap = page.get_pixmap(matrix=render_matrix)
            image_bytes = pixmap.tobytes("png")
            with image_module.open(BytesIO(image_bytes)) as image:
                page_text = pytesseract_module.image_to_string(image, lang=lang)
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


# Tesseract's own confidence score (0-100; -1 for non-text structural
# lines) for one recognized word. Below this, a word is dropped rather
# than risk drawing - or failing to draw - a redaction box in the wrong
# place on a poor-quality scan; the plain-text OCR path (image_to_string
# above) has no equivalent guard since a wrong character there is just a
# wrong character, not a rectangle burned into the wrong part of the page.
MIN_OCR_WORD_CONFIDENCE = 40


def _ocr_word_boxes(
    pytesseract_module: Any, image: Any, lang: str, zoom: float = 1.0
) -> list[dict[str, object]]:
    """Run Tesseract's word-level OCR (image_to_data) and return each
    confidently-recognized word's text plus its bounding box, converted
    from the OCR render's pixel space to point space by dividing by
    ``zoom`` (pass 1.0 - a no-op - when the caller is already working in
    a space where 1 pixel == 1 point, e.g. a synthetic page built at the
    source image's own pixel dimensions).
    """
    data = pytesseract_module.image_to_data(
        image, lang=lang, output_type=pytesseract_module.Output.DICT
    )
    words: list[dict[str, object]] = []
    for i in range(len(data.get("text", []))):
        text = str(data["text"][i]).strip()
        if not text:
            continue
        try:
            confidence = float(data["conf"][i])
        except (TypeError, ValueError):
            confidence = -1.0
        if confidence < MIN_OCR_WORD_CONFIDENCE:
            continue
        left = float(data["left"][i]) / zoom
        top = float(data["top"][i]) / zoom
        width = float(data["width"][i]) / zoom
        height = float(data["height"][i]) / zoom
        words.append(
            {
                "text": text,
                "rect": (left, top, left + width, top + height),
                "block_no": int(data["block_num"][i]),
                "line_no": int(data["line_num"][i]),
                "word_no": int(data["word_num"][i]),
            }
        )
    return words


def extract_pdf_word_boxes(file_path: str | Path) -> OcrWordPageExtraction:
    """OCR each page of a scanned PDF and return word-level text plus
    bounding boxes in PDF point space - the positional counterpart to
    extract_text_from_pdf's plain text, letting a caller (see
    pdf_redaction.word_pages_from_ocr_boxes) draw true colored redaction
    boxes over a scanned page exactly the way it already does for a
    PDF's real text layer, instead of only ever falling back to a
    rebuilt plain-text document. Raises OcrUnavailableError the same way
    extract_text_from_pdf does on any failure - never returns partial or
    wrong positional data silently.
    """
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

    lang = _ocr_language(pytesseract_module)
    render_matrix = fitz_module.Matrix(OCR_PDF_RENDER_ZOOM, OCR_PDF_RENDER_ZOOM)
    pages: list[dict[str, object]] = []
    document = None
    try:
        document = fitz_module.open(path)
        for page_index, page in enumerate(document, start=1):
            pixmap = page.get_pixmap(matrix=render_matrix)
            image_bytes = pixmap.tobytes("png")
            with image_module.open(BytesIO(image_bytes)) as image:
                words = _ocr_word_boxes(
                    pytesseract_module, image, lang, OCR_PDF_RENDER_ZOOM
                )
            pages.append({"page_number": page_index, "words": words})
    except Exception as error:
        if pytesseract_module is not None and _is_tesseract_not_found(
            error, pytesseract_module
        ):
            raise OcrUnavailableError(
                OCR_STATUS_ENGINE_NOT_FOUND,
                OCR_INPUT_TYPE_PDF,
                OCR_WARNING_ENGINE_NOT_FOUND,
                items_processed=len(pages),
            ) from error
        raise OcrUnavailableError(
            OCR_STATUS_UNAVAILABLE,
            OCR_INPUT_TYPE_PDF,
            OCR_WARNING_FAILED,
            items_processed=len(pages),
        ) from error
    finally:
        if document is not None and hasattr(document, "close"):
            document.close()

    if not any(page["words"] for page in pages):
        raise OcrUnavailableError(
            OCR_STATUS_UNAVAILABLE,
            OCR_INPUT_TYPE_PDF,
            OCR_WARNING_NO_TEXT,
            items_processed=len(pages),
        )

    return OcrWordPageExtraction(
        pages=pages,
        metadata=build_ocr_metadata(
            used=True,
            status=OCR_STATUS_AVAILABLE,
            input_type=OCR_INPUT_TYPE_PDF,
            items_processed=len(pages),
        ),
    )


def extract_image_word_boxes(file_path: str | Path) -> OcrWordPageExtraction:
    """OCR a single image and return word-level text plus bounding boxes,
    in the same shape extract_pdf_word_boxes returns - one page, with
    rects already in the image's own pixel space treated as point space
    (zoom=1.0), matching how a synthetic one-page PDF built at the
    image's exact pixel dimensions would be measured. See
    pdf_redaction.save_word_coordinate_redacted_image_copy for how this
    becomes a true colored-redaction output for a standalone scan/photo,
    not just PDF pages.
    """
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

    lang = _ocr_language(pytesseract_module)
    try:
        with image_module.open(path) as image:
            words = _ocr_word_boxes(pytesseract_module, image, lang, zoom=1.0)
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

    if not words:
        raise OcrUnavailableError(
            OCR_STATUS_UNAVAILABLE,
            OCR_INPUT_TYPE_IMAGE,
            OCR_WARNING_NO_TEXT,
            items_processed=1,
        )

    return OcrWordPageExtraction(
        pages=[{"page_number": 1, "words": words}],
        metadata=build_ocr_metadata(
            used=True,
            status=OCR_STATUS_AVAILABLE,
            input_type=OCR_INPUT_TYPE_IMAGE,
            items_processed=1,
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
