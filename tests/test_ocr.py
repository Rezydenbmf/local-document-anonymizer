"""Tests for optional local OCR foundation."""

from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from anonymizer import anonymize_batch, anonymize_file, anonymize_image_file
from ocr import (
    OCR_INPUT_TYPE_IMAGE,
    OCR_INPUT_TYPE_NONE,
    OCR_INPUT_TYPE_PDF,
    OCR_STATUS_AVAILABLE,
    OCR_STATUS_DEPENDENCY_MISSING,
    OCR_STATUS_ENGINE_NOT_FOUND,
    OCR_STATUS_UNSUPPORTED_INPUT,
    OCR_WARNING_ENGINE_NOT_FOUND,
    OCR_WARNING_UNSUPPORTED_INPUT,
    OcrExtraction,
    OcrUnavailableError,
    build_ocr_metadata,
    detect_ocr_support,
)


def workspace_temp_dir():
    return tempfile.TemporaryDirectory(dir=PROJECT_ROOT / "tests")


def _escape_pdf_text(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _write_pdf(path: Path, objects: list[bytes]) -> None:
    content = bytearray(b"%PDF-1.4\n")
    offsets = [0]

    for index, obj in enumerate(objects, start=1):
        offsets.append(len(content))
        content.extend(f"{index} 0 obj\n".encode("ascii"))
        content.extend(obj)
        content.extend(b"\nendobj\n")

    xref_start = len(content)
    content.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    content.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        content.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    content.extend(
        (
            f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
            f"startxref\n{xref_start}\n%%EOF\n"
        ).encode("ascii")
    )

    path.write_bytes(content)


def write_text_pdf(path: Path, text: str) -> None:
    escaped_text = _escape_pdf_text(text)
    stream = f"BT /F1 12 Tf 72 720 Td ({escaped_text}) Tj ET\n".encode("ascii")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        (
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>"
        ),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length "
        + str(len(stream)).encode("ascii")
        + b" >>\nstream\n"
        + stream
        + b"endstream",
    ]
    _write_pdf(path, objects)


def write_blank_pdf(path: Path) -> None:
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        (
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            b"/Resources << >> >>"
        ),
    ]
    _write_pdf(path, objects)


class OcrFoundationTests(unittest.TestCase):
    def test_ocr_detection_reports_unsupported_input(self) -> None:
        status = detect_ocr_support(OCR_INPUT_TYPE_NONE)

        self.assertEqual(status["status"], OCR_STATUS_UNSUPPORTED_INPUT)
        self.assertEqual(status["warning"], OCR_WARNING_UNSUPPORTED_INPUT)

    def test_ocr_detection_handles_missing_python_dependency(self) -> None:
        with patch("ocr._pytesseract_module", return_value=None):
            status = detect_ocr_support(OCR_INPUT_TYPE_IMAGE)

        self.assertEqual(status["status"], OCR_STATUS_DEPENDENCY_MISSING)
        self.assertEqual(status["input_type"], OCR_INPUT_TYPE_IMAGE)

    def test_ocr_detection_handles_missing_tesseract_engine(self) -> None:
        class FakePytesseract:
            @staticmethod
            def get_tesseract_version():
                raise FileNotFoundError("tesseract")

        with patch("ocr._pytesseract_module", return_value=FakePytesseract):
            with patch("ocr._image_module", return_value=object()):
                status = detect_ocr_support(OCR_INPUT_TYPE_IMAGE)

        self.assertEqual(status["status"], OCR_STATUS_ENGINE_NOT_FOUND)
        self.assertEqual(status["warning"], OCR_WARNING_ENGINE_NOT_FOUND)

    def test_image_ocr_path_uses_existing_anonymization_pipeline_safely(self) -> None:
        raw_ocr_text = "Contact safe@example.test on 2026-06-01."
        extraction = OcrExtraction(
            text=raw_ocr_text,
            metadata=build_ocr_metadata(
                used=True,
                status=OCR_STATUS_AVAILABLE,
                input_type=OCR_INPUT_TYPE_IMAGE,
                items_processed=1,
            ),
        )

        with workspace_temp_dir() as temp_dir:
            source_path = Path(temp_dir) / "scan.png"
            source_path.write_bytes(b"synthetic image placeholder")

            with patch("anonymizer.extract_text_with_ocr", return_value=extraction):
                output_path, counters = anonymize_image_file(source_path)

            report_text = (Path(temp_dir) / "scan_RAPORT.txt").read_text(
                encoding="utf-8"
            )

            self.assertEqual(output_path, Path(temp_dir) / "scan_ANON.txt")
            self.assertEqual(
                output_path.read_text(encoding="utf-8").strip(),
                "Contact [EMAIL] on [DATA].",
            )
            self.assertEqual(counters, {"EMAIL": 1, "DATA": 1})
            self.assertIn("OCR used: yes", report_text)
            self.assertIn("OCR status: available", report_text)
            self.assertIn("OCR input type: image", report_text)
            self.assertIn("OCR pages/images processed: 1", report_text)
            self.assertNotIn(raw_ocr_text, report_text)
            self.assertNotIn("safe@example.test", report_text)
            self.assertEqual(source_path.read_bytes(), b"synthetic image placeholder")

    def test_image_ocr_missing_engine_is_controlled_in_batch_summary(self) -> None:
        error = OcrUnavailableError(
            OCR_STATUS_ENGINE_NOT_FOUND,
            OCR_INPUT_TYPE_IMAGE,
            OCR_WARNING_ENGINE_NOT_FOUND,
        )

        with workspace_temp_dir() as temp_dir:
            source_dir = Path(temp_dir) / "source"
            output_dir = Path(temp_dir) / "output"
            source_dir.mkdir()
            output_dir.mkdir()
            source_path = source_dir / "scan.jpg"
            source_path.write_bytes(b"synthetic image placeholder")

            with patch("anonymizer.extract_text_with_ocr", side_effect=error):
                result = anonymize_batch([source_path], output_dir)

            summary_text = result.summary_path.read_text(encoding="utf-8")

            self.assertEqual(result.success_count, 0)
            self.assertEqual(result.error_count, 1)
            self.assertIn("error: OCR unavailable for image-based input", summary_text)
            self.assertIn("* OCR unavailable or failed: 1", summary_text)
            self.assertIn("OCR status: engine_not_found", summary_text)
            self.assertNotIn(str(source_dir), summary_text)
            self.assertFalse((output_dir / "scan_ANON.txt").exists())

    def test_text_based_pdf_path_does_not_force_ocr(self) -> None:
        with workspace_temp_dir() as temp_dir:
            source_path = Path(temp_dir) / "document.pdf"
            write_text_pdf(source_path, "Contact safe@example.test.")

            with patch("anonymizer.extract_text_with_ocr") as mocked_ocr:
                output_path, counters = anonymize_file(source_path)

            report_text = (Path(temp_dir) / "document_RAPORT.txt").read_text(
                encoding="utf-8"
            )

            mocked_ocr.assert_not_called()
            self.assertEqual(output_path, Path(temp_dir) / "document_ANON.txt")
            self.assertEqual(counters, {"EMAIL": 1})
            self.assertIn("OCR used: no", report_text)
            self.assertIn("OCR status: not_used", report_text)

    def test_scanned_pdf_falls_back_to_ocr_when_text_layer_is_empty(self) -> None:
        raw_ocr_text = "Scanned contact safe@example.test."
        extraction = OcrExtraction(
            text=raw_ocr_text,
            metadata=build_ocr_metadata(
                used=True,
                status=OCR_STATUS_AVAILABLE,
                input_type=OCR_INPUT_TYPE_PDF,
                items_processed=1,
            ),
        )

        with workspace_temp_dir() as temp_dir:
            source_path = Path(temp_dir) / "scan.pdf"
            write_blank_pdf(source_path)

            with patch("anonymizer.extract_text_with_ocr", return_value=extraction):
                output_path, counters = anonymize_file(source_path)

            report_text = (Path(temp_dir) / "scan_RAPORT.txt").read_text(
                encoding="utf-8"
            )

            self.assertEqual(output_path, Path(temp_dir) / "scan_ANON.txt")
            self.assertEqual(
                output_path.read_text(encoding="utf-8").strip(),
                "Scanned contact [EMAIL].",
            )
            self.assertEqual(counters, {"EMAIL": 1})
            self.assertIn("OCR used: yes", report_text)
            self.assertIn("OCR input type: pdf", report_text)
            self.assertNotIn(raw_ocr_text, report_text)

    def test_scanned_pdf_ocr_unavailable_is_controlled(self) -> None:
        error = OcrUnavailableError(
            OCR_STATUS_DEPENDENCY_MISSING,
            OCR_INPUT_TYPE_PDF,
            "local OCR dependency is missing",
        )

        with workspace_temp_dir() as temp_dir:
            source_dir = Path(temp_dir) / "source"
            output_dir = Path(temp_dir) / "output"
            source_dir.mkdir()
            output_dir.mkdir()
            source_path = source_dir / "scan.pdf"
            write_blank_pdf(source_path)

            with patch("anonymizer.extract_text_with_ocr", side_effect=error):
                result = anonymize_batch([source_path], output_dir)

            summary_text = result.summary_path.read_text(encoding="utf-8")

            self.assertEqual(result.success_count, 0)
            self.assertEqual(result.error_count, 1)
            self.assertIn("error: OCR unavailable for image-based input", summary_text)
            self.assertIn("OCR status: dependency_missing", summary_text)
            self.assertNotIn(str(source_dir), summary_text)


if __name__ == "__main__":
    unittest.main()
