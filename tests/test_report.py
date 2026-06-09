"""Tests for Stage 6 safe report file output."""

from pathlib import Path
import sys
import tempfile
import unittest

from docx import Document


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from audit import AUDIT_CATEGORY_ORDER, audit_text
from anonymizer import SUPPORTED_LABELS, anonymize_docx_file, anonymize_file
from anonymizer import anonymize_pdf_file, anonymize_txt_file
from file_readers import read_docx_file
from file_writers import build_report_path
from report import build_report_text


def workspace_temp_dir():
    return tempfile.TemporaryDirectory(dir=PROJECT_ROOT / "tests")


def write_docx(path: Path, paragraphs: list[str]) -> None:
    document = Document()
    for text in paragraphs:
        document.add_paragraph(text)
    document.save(path)


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


class ReportTests(unittest.TestCase):
    def test_report_generation_includes_category_counters(self) -> None:
        report_text = build_report_text(
            counters={"EMAIL": 1, "DATA": 2},
            input_extension=".docx",
            output_extension=".docx",
            category_order=SUPPORTED_LABELS,
            audit_result=audit_text("Clean [EMAIL] [DATA]."),
            audit_category_order=AUDIT_CATEGORY_ORDER,
        )

        self.assertIn("Status: completed", report_text)
        self.assertIn("Input type: DOCX", report_text)
        self.assertIn("Output type: DOCX", report_text)
        self.assertIn("* PESEL: 0", report_text)
        self.assertIn("* EMAIL: 1", report_text)
        self.assertIn("* TELEFON: 0", report_text)
        self.assertIn("* DATA: 2", report_text)
        self.assertIn("Post-anonymization audit:", report_text)
        self.assertIn("Status: ok", report_text)
        self.assertIn("* none: 0", report_text)
        self.assertIn("Manual review required: yes", report_text)

    def test_report_does_not_contain_source_values_or_replacement_map(self) -> None:
        source_values = {
            "safe@example.test",
            "00000000000",
            "+48 123 456 789",
            "2026-06-01",
            "C:\\private\\synthetic-name\\document.txt",
            "safe@example.test -> [EMAIL]",
        }

        report_text = build_report_text(
            counters={"EMAIL": 1, "PESEL": 1, "TELEFON": 1, "DATA": 1},
            input_extension="C:\\private\\synthetic-name\\document.txt",
            output_extension=".txt",
            category_order=SUPPORTED_LABELS,
        )

        for source_value in source_values:
            self.assertNotIn(source_value, report_text)
        self.assertIn("Original sensitive values stored: no", report_text)
        self.assertIn("Replacement map created: no", report_text)

    def test_report_audit_section_is_safe_when_warning_is_present(self) -> None:
        source_value = "ABC/123/2026"

        report_text = build_report_text(
            counters={},
            input_extension=".txt",
            output_extension=".txt",
            category_order=SUPPORTED_LABELS,
            audit_result=audit_text(f"Reference {source_value} remains."),
            audit_category_order=AUDIT_CATEGORY_ORDER,
        )

        self.assertIn("Post-anonymization audit:", report_text)
        self.assertIn("Status: warning", report_text)
        self.assertIn("* CASE_REFERENCE: 1", report_text)
        self.assertNotIn(source_value, report_text)

    def test_report_path_is_built_as_raport_txt(self) -> None:
        with workspace_temp_dir() as temp_dir:
            self.assertEqual(
                build_report_path(Path(temp_dir) / "document.txt"),
                Path(temp_dir) / "document_RAPORT.txt",
            )
            self.assertEqual(
                build_report_path(Path(temp_dir) / "document.docx"),
                Path(temp_dir) / "document_RAPORT.txt",
            )
            self.assertEqual(
                build_report_path(Path(temp_dir) / "document.pdf"),
                Path(temp_dir) / "document_RAPORT.txt",
            )

    def test_txt_integration_creates_anon_and_safe_report(self) -> None:
        with workspace_temp_dir() as temp_dir:
            source_path = Path(temp_dir) / "document.txt"
            source_path.write_text(
                "safe@example.test 00000000000 +48 123 456 789 2026-06-01",
                encoding="utf-8",
            )

            output_path, counters = anonymize_txt_file(source_path)
            report_path = Path(temp_dir) / "document_RAPORT.txt"

            self.assertEqual(output_path, Path(temp_dir) / "document_ANON.txt")
            self.assertTrue(output_path.exists())
            self.assertTrue(report_path.exists())
            self.assertEqual(
                counters, {"EMAIL": 1, "PESEL": 1, "TELEFON": 1, "DATA": 1}
            )
            self.assert_report_is_safe(report_path)

    def test_docx_integration_creates_anon_docx_and_safe_report(self) -> None:
        with workspace_temp_dir() as temp_dir:
            source_path = Path(temp_dir) / "document.docx"
            write_docx(source_path, ["Contact safe@example.test on 2026-06-01."])

            output_path, counters = anonymize_docx_file(source_path)
            report_path = Path(temp_dir) / "document_RAPORT.txt"

            self.assertEqual(output_path, Path(temp_dir) / "document_ANON.docx")
            self.assertEqual(read_docx_file(output_path), "Contact [EMAIL] on [DATA].")
            self.assertTrue(report_path.exists())
            self.assertEqual(counters, {"EMAIL": 1, "DATA": 1})
            self.assert_report_is_safe(report_path)

    def test_pdf_integration_creates_anon_txt_and_safe_report(self) -> None:
        with workspace_temp_dir() as temp_dir:
            source_path = Path(temp_dir) / "document.pdf"
            write_text_pdf(source_path, "Contact safe@example.test on 2026-06-01.")

            output_path, counters = anonymize_pdf_file(source_path)
            report_path = Path(temp_dir) / "document_RAPORT.txt"

            self.assertEqual(output_path, Path(temp_dir) / "document_ANON.txt")
            self.assertEqual(
                output_path.read_text(encoding="utf-8").strip(),
                "Contact [EMAIL] on [DATA].",
            )
            self.assertTrue(report_path.exists())
            self.assertEqual(counters, {"EMAIL": 1, "DATA": 1})
            self.assert_report_is_safe(report_path)

    def test_dispatcher_report_does_not_write_source_values(self) -> None:
        with workspace_temp_dir() as temp_dir:
            source_path = Path(temp_dir) / "document.txt"
            source_path.write_text(
                "Contact safe@example.test on 2026-06-01.",
                encoding="utf-8",
            )

            output_path, counters = anonymize_file(source_path)
            report_path = Path(temp_dir) / "document_RAPORT.txt"
            report_text = report_path.read_text(encoding="utf-8")

            self.assertEqual(output_path, Path(temp_dir) / "document_ANON.txt")
            self.assertEqual(counters, {"EMAIL": 1, "DATA": 1})
            self.assertNotIn("safe@example.test", report_text)
            self.assertNotIn("2026-06-01", report_text)
            self.assertNotIn(str(source_path), report_text)

    def assert_report_is_safe(self, report_path: Path) -> None:
        report_text = report_path.read_text(encoding="utf-8")
        for source_value in (
            "safe@example.test",
            "00000000000",
            "+48 123 456 789",
            "2026-06-01",
        ):
            self.assertNotIn(source_value, report_text)

        self.assertIn("Original sensitive values stored: no", report_text)
        self.assertIn("Replacement map created: no", report_text)
        self.assertIn("Post-anonymization audit:", report_text)
        self.assertIn("Possible remaining sensitive patterns:", report_text)


if __name__ == "__main__":
    unittest.main()
