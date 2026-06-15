"""Tests for Stage 12 safe output workspace and batch processing."""

from pathlib import Path
import sys
import tempfile
import unittest

from docx import Document


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from anonymizer import anonymize_batch, anonymize_file
from file_writers import build_collision_safe_path


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


class BatchProcessingTests(unittest.TestCase):
    def test_collision_safe_path_uses_next_numbered_name(self) -> None:
        with workspace_temp_dir() as temp_dir:
            output_dir = Path(temp_dir)
            candidate = output_dir / "document_ANON.txt"

            self.assertEqual(build_collision_safe_path(candidate), candidate)

            candidate.write_text("existing", encoding="utf-8")
            self.assertEqual(
                build_collision_safe_path(candidate),
                output_dir / "document_ANON_2.txt",
            )

            (output_dir / "document_ANON_2.txt").write_text(
                "existing", encoding="utf-8"
            )
            self.assertEqual(
                build_collision_safe_path(candidate),
                output_dir / "document_ANON_3.txt",
            )

    def test_single_file_output_uses_selected_workspace(self) -> None:
        with workspace_temp_dir() as temp_dir:
            source_dir = Path(temp_dir) / "source"
            output_dir = Path(temp_dir) / "output"
            source_dir.mkdir()
            output_dir.mkdir()
            source_path = source_dir / "document.txt"
            source_path.write_text("Contact safe@example.test.", encoding="utf-8")

            output_path, counters = anonymize_file(source_path, output_dir=output_dir)

            self.assertEqual(output_path, output_dir / "document_ANON.txt")
            self.assertEqual(counters, {"EMAIL": 1})
            self.assertTrue((output_dir / "document_RAPORT.txt").exists())
            self.assertFalse((source_dir / "document_ANON.txt").exists())
            self.assertFalse((source_dir / "document_RAPORT.txt").exists())

    def test_batch_processes_supported_files_and_continues_after_error(self) -> None:
        with workspace_temp_dir() as temp_dir:
            source_dir = Path(temp_dir) / "source"
            output_dir = Path(temp_dir) / "output"
            source_dir.mkdir()
            output_dir.mkdir()

            txt_path = source_dir / "document.TXT"
            docx_path = source_dir / "letter.Docx"
            pdf_path = source_dir / "scan.PDF"
            unsupported_path = source_dir / "notes.rtf"
            txt_path.write_text("Email safe@example.test.", encoding="utf-8")
            write_docx(docx_path, ["Date 2026-06-01."])
            write_text_pdf(pdf_path, "Phone +48 123 456 789.")
            unsupported_path.write_text("Unsupported synthetic file.", encoding="utf-8")

            result = anonymize_batch(
                [txt_path, unsupported_path, docx_path, pdf_path],
                output_dir,
            )

            self.assertEqual(result.input_count, 4)
            self.assertEqual(result.success_count, 3)
            self.assertEqual(result.error_count, 1)
            self.assertEqual(result.counters["EMAIL"], 1)
            self.assertEqual(result.counters["DATA"], 1)
            self.assertEqual(result.counters["TELEFON"], 1)
            self.assertTrue((output_dir / "document_ANON.txt").exists())
            self.assertTrue((output_dir / "letter_ANON.docx").exists())
            self.assertTrue((output_dir / "scan_ANON.txt").exists())
            self.assertFalse((source_dir / "document_ANON.txt").exists())
            self.assertEqual(result.summary_path, output_dir / "_BATCH_SUMMARY.txt")

    def test_batch_summary_is_safe_and_collision_safe(self) -> None:
        with workspace_temp_dir() as temp_dir:
            source_dir = Path(temp_dir) / "source"
            output_dir = Path(temp_dir) / "output"
            source_dir.mkdir()
            output_dir.mkdir()
            (output_dir / "_BATCH_SUMMARY.txt").write_text(
                "existing summary", encoding="utf-8"
            )
            source_term = "Private Alias Example"
            alias = "P. Alias Example"
            dictionary_path = source_dir / "sensitive_terms.txt"
            dictionary_path.write_text(
                f"{source_term} | {alias} = [PRIVATE_LABEL]\n",
                encoding="utf-8",
            )
            source_path = source_dir / "document.txt"
            source_path.write_text(
                f"{alias} contacted safe@example.test on 2026-06-01.",
                encoding="utf-8",
            )
            unsupported_path = source_dir / "notes.rtf"
            unsupported_path.write_text("Unsupported synthetic file.", encoding="utf-8")

            result = anonymize_batch(
                [source_path, unsupported_path],
                output_dir,
                sensitive_terms_path=dictionary_path,
            )
            summary_text = result.summary_path.read_text(encoding="utf-8")

            self.assertEqual(result.summary_path, output_dir / "_BATCH_SUMMARY_2.txt")
            self.assertIn("Input files: 2", summary_text)
            self.assertIn("Successful files: 1", summary_text)
            self.assertIn("Errors: 1", summary_text)
            self.assertIn("input: document.txt", summary_text)
            self.assertIn("output: document_ANON.txt", summary_text)
            self.assertIn("report: document_RAPORT.txt", summary_text)
            self.assertIn("error: unsupported file type", summary_text)
            self.assertNotIn(str(source_dir), summary_text)
            self.assertNotIn(str(output_dir), summary_text)
            self.assertNotIn("safe@example.test", summary_text)
            self.assertNotIn("2026-06-01", summary_text)
            self.assertNotIn(source_term, summary_text)
            self.assertNotIn(alias, summary_text)
            self.assertIn("Original sensitive values stored: no", summary_text)
            self.assertIn("Replacement map created: no", summary_text)
            self.assertIn("Source paths stored: no", summary_text)


if __name__ == "__main__":
    unittest.main()
