# Module: Local OCR Foundation

## Purpose

This module documents Stage 19: optional local OCR foundation.

The goal is a safe, dependency-detected OCR layer, not a production OCR
product. OCR is used only to extract text locally before the existing
anonymization pipeline runs.

## Related files

- `src/ocr.py`
- `src/anonymizer.py`
- `src/file_writers.py`
- `src/report.py`
- `src/gui.py`
- `tests/test_ocr.py`

## Runtime dependencies

Core TXT/DOCX/PDF support still uses the existing local dependencies. OCR adds
optional Python packages listed in `requirements.txt`:

```text
pytesseract
Pillow
PyMuPDF
```

Tesseract itself is a separate local system dependency. The repository does
not bundle Tesseract binaries, OCR language data, external installers, real
documents, or generated OCR outputs.

## Public API

```python
detect_ocr_support(input_type="image") -> dict[str, object]
extract_text_from_image(file_path) -> OcrExtraction
extract_text_from_pdf(file_path) -> OcrExtraction
extract_text_with_ocr(file_path) -> OcrExtraction
anonymize_image_file(source_path, sensitive_terms=None, sensitive_terms_path=None, output_dir=None)
anonymize_image_file_with_audit(source_path, sensitive_terms=None, sensitive_terms_path=None, output_dir=None)
```

OCR status values are controlled metadata:

- `available`
- `unavailable`
- `dependency_missing`
- `engine_not_found`
- `unsupported_input`
- `not_used`

## Behavior

Supported image inputs:

- `.png`
- `.jpg`
- `.jpeg`
- `.tif`
- `.tiff`

Image files are not edited. OCR text is anonymized and saved as TXT:

```text
scan.png -> scan_ANON.txt
scan.png -> scan_RAPORT.txt
```

PDF behavior:

1. Try the existing text-based PDF extraction path first.
2. If extractable text exists, do not run OCR.
3. If no extractable text exists, attempt local OCR when dependencies are
   available.
4. If OCR is unavailable, return a controlled safe error.
5. PDF output remains TXT only.

## Report and batch metadata

Per-file reports can include:

- OCR used: yes/no
- OCR status
- OCR input type
- OCR pages/images processed
- safe OCR warning when applicable

Batch summaries can include:

- files processed with OCR
- OCR unavailable or failed
- per-file OCR status when relevant

Reports and summaries must not include raw OCR text, source snippets,
sensitive values, private dictionary aliases, full paths, tracebacks, or
replacement maps.

## Safety assumptions

- OCR is local and optional.
- OCR does not use cloud services, API calls, OpenAI API, online processing,
  AI services, local LLMs, databases, or network calls.
- OCR can be inaccurate and can miss or distort sensitive text.
- Manual review is still required for every generated output.
- OCR metadata is safe metadata only.
- Original images and PDFs are not modified.
- No edited image output or scanned-PDF visual redaction is created.

## How to test

Run:

```bash
python -m unittest discover -s tests
```

`tests/test_ocr.py` uses mocked OCR extraction and synthetic placeholder files
so tests do not require Tesseract to be installed. It covers availability
detection, missing dependency behavior, missing engine behavior, image OCR
workflow, text-based PDF regression, scanned PDF fallback, report safety, and
batch summary safety.

## Known limitations

- OCR quality depends on local Tesseract installation, language data, input
  quality, and image/PDF rendering quality.
- No OCR language selector is exposed in the GUI.
- No preview, highlighting, split-screen review, or OCR correction interface
  exists.
- No handwritten-text support is claimed.
- No edited image or scanned-PDF visual redaction is produced.
- Manual review remains required.
