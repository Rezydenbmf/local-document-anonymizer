"""Tests for Stage 4 text-based PDF input and TXT output."""

from pathlib import Path
import sys
import tempfile
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from anonymizer import anonymize_pdf_file
from file_readers import extract_text, read_pdf_file
from file_writers import (
    build_anonymized_pdf_txt_path,
    save_anonymized_copy,
    save_anonymized_pdf_txt_copy,
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


class PdfIoTests(unittest.TestCase):
    def test_reads_simple_text_based_pdf_with_synthetic_data(self) -> None:
        with workspace_temp_dir() as temp_dir:
            source_path = Path(temp_dir) / "document.pdf"
            source_text = "Contact tester@example.test on 2026-06-01."
            write_text_pdf(source_path, source_text)

            self.assertEqual(read_pdf_file(source_path).strip(), source_text)
            self.assertEqual(extract_text(source_path).strip(), source_text)

    def test_pdf_without_extractable_text_fails_clearly(self) -> None:
        with workspace_temp_dir() as temp_dir:
            source_path = Path(temp_dir) / "blank.pdf"
            write_blank_pdf(source_path)

            with self.assertRaisesRegex(ValueError, "no extractable text"):
                read_pdf_file(source_path)

    def test_pdf_output_filename_is_anon_txt(self) -> None:
        with workspace_temp_dir() as temp_dir:
            source_path = Path(temp_dir) / "document.pdf"
            write_text_pdf(source_path, "Synthetic PDF content.")

            self.assertEqual(
                build_anonymized_pdf_txt_path(source_path),
                Path(temp_dir) / "document_ANON.txt",
            )
            self.assertEqual(
                save_anonymized_copy(source_path, "Anonymized PDF text."),
                str(Path(temp_dir) / "document_ANON.txt"),
            )
            self.assertFalse((Path(temp_dir) / "document_ANON.pdf").exists())

    def test_saves_pdf_anonymized_text_as_txt_copy(self) -> None:
        with workspace_temp_dir() as temp_dir:
            source_path = Path(temp_dir) / "document.pdf"
            write_text_pdf(source_path, "Contact tester@example.test.")

            output_path = save_anonymized_pdf_txt_copy(
                source_path, "Contact [EMAIL]."
            )

            self.assertEqual(output_path, Path(temp_dir) / "document_ANON.txt")
            self.assertEqual(
                output_path.read_text(encoding="utf-8"),
                "Contact [EMAIL].",
            )

    def test_original_pdf_file_is_not_modified(self) -> None:
        with workspace_temp_dir() as temp_dir:
            source_path = Path(temp_dir) / "document.pdf"
            write_text_pdf(source_path, "Original synthetic value: tester@example.test.")
            original_bytes = source_path.read_bytes()

            save_anonymized_pdf_txt_copy(source_path, "Original synthetic value: [EMAIL].")

            self.assertEqual(source_path.read_bytes(), original_bytes)

    def test_anonymizes_pdf_file_and_writes_txt_copy(self) -> None:
        with workspace_temp_dir() as temp_dir:
            source_path = Path(temp_dir) / "document.pdf"
            write_text_pdf(
                source_path,
                "safe@example.test 00000000000 +48 123 456 789 2026-06-01",
            )

            output_path, counters = anonymize_pdf_file(source_path)

            self.assertEqual(output_path, Path(temp_dir) / "document_ANON.txt")
            self.assertEqual(
                output_path.read_text(encoding="utf-8").strip(),
                "[EMAIL] [PESEL] [TELEFON] [DATA]",
            )
            self.assertEqual(
                counters, {"EMAIL": 1, "PESEL": 1, "TELEFON": 1, "DATA": 1}
            )
            self.assertFalse((Path(temp_dir) / "document_ANON.pdf").exists())

    def test_pdf_dictionary_path_flow_replaces_terms(self) -> None:
        with workspace_temp_dir() as temp_dir:
            source_term = "Person One Example"
            dictionary_path = Path(temp_dir) / "sensitive_terms.txt"
            dictionary_path.write_text(
                f"{source_term} = [IMIE NAZWISKO]\n",
                encoding="utf-8",
            )
            source_path = Path(temp_dir) / "document.pdf"
            write_text_pdf(
                source_path,
                f"{source_term} contacted tester@example.test.",
            )

            output_path, counters = anonymize_pdf_file(
                source_path,
                sensitive_terms_path=dictionary_path,
            )
            report_text = (Path(temp_dir) / "document_RAPORT.txt").read_text(
                encoding="utf-8"
            )

            self.assertEqual(output_path, Path(temp_dir) / "document_ANON.txt")
            self.assertEqual(
                output_path.read_text(encoding="utf-8").strip(),
                "[IMIE NAZWISKO] contacted [EMAIL].",
            )
            self.assertEqual(counters, {"IMIE NAZWISKO": 1, "EMAIL": 1})
            self.assertIn("Dictionary status: loaded", report_text)
            self.assertNotIn(source_term, report_text)

    def test_pdf_result_does_not_return_map_or_source_values(self) -> None:
        with workspace_temp_dir() as temp_dir:
            source_path = Path(temp_dir) / "safe_input.pdf"
            source_values = {
                "safe@example.test",
                "00000000000",
                "+48 123 456 789",
                "2026-06-01",
            }
            write_text_pdf(
                source_path,
                "safe@example.test 00000000000 +48 123 456 789 2026-06-01",
            )

            output_path, counters = anonymize_pdf_file(source_path)

            returned_text = repr((output_path, counters))
            output_text = output_path.read_text(encoding="utf-8")
            for source_value in source_values:
                self.assertNotIn(source_value, returned_text)
                self.assertNotIn(source_value, repr(counters))
                self.assertNotIn(source_value, output_text)

            self.assertEqual(
                counters, {"EMAIL": 1, "PESEL": 1, "TELEFON": 1, "DATA": 1}
            )
            self.assertTrue(all(isinstance(count, int) for count in counters.values()))


if __name__ == "__main__":
    unittest.main()
