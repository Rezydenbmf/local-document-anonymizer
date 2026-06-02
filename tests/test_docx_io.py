"""Tests for Stage 3 DOCX file input and output."""

from pathlib import Path
import sys
import tempfile
import unittest

from docx import Document


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from anonymizer import anonymize_docx_file, anonymize_text
from file_readers import extract_text, read_docx_file
from file_writers import (
    build_anonymized_docx_path,
    save_anonymized_copy,
    save_anonymized_docx_copy,
)


def workspace_temp_dir():
    return tempfile.TemporaryDirectory(dir=PROJECT_ROOT / "tests")


def write_docx(path: Path, paragraphs: list[str]) -> None:
    document = Document()
    for text in paragraphs:
        document.add_paragraph(text)
    document.save(path)


class DocxIoTests(unittest.TestCase):
    def test_reads_docx_file_with_synthetic_data(self) -> None:
        with workspace_temp_dir() as temp_dir:
            source_path = Path(temp_dir) / "document.docx"
            write_docx(
                source_path,
                [
                    "Contact tester@example.test.",
                    "Meeting date 2026-06-01.",
                ],
            )

            expected_text = "Contact tester@example.test.\nMeeting date 2026-06-01."

            self.assertEqual(read_docx_file(source_path), expected_text)
            self.assertEqual(extract_text(source_path), expected_text)

    def test_saves_anonymized_docx_copy_with_anon_suffix(self) -> None:
        with workspace_temp_dir() as temp_dir:
            source_path = Path(temp_dir) / "document.docx"
            write_docx(
                source_path,
                ["Contact tester@example.test on 2026-06-01."],
            )

            output_path, counters = save_anonymized_docx_copy(
                source_path, anonymize_text
            )

            self.assertEqual(output_path, Path(temp_dir) / "document_ANON.docx")
            self.assertEqual(
                read_docx_file(output_path),
                "Contact [EMAIL] on [DATA].",
            )
            self.assertEqual(counters, {"EMAIL": 1, "DATA": 1})

    def test_original_docx_file_is_not_modified(self) -> None:
        with workspace_temp_dir() as temp_dir:
            source_path = Path(temp_dir) / "document.docx"
            original_text = "Original synthetic value: tester@example.test."
            write_docx(source_path, [original_text])

            save_anonymized_docx_copy(source_path, anonymize_text)

            self.assertEqual(read_docx_file(source_path), original_text)

    def test_anonymizes_docx_file_and_writes_anon_copy(self) -> None:
        with workspace_temp_dir() as temp_dir:
            source_path = Path(temp_dir) / "document.docx"
            write_docx(
                source_path,
                [
                    "Contact tester@example.test on 2026-06-01.",
                    "PESEL 00000000000 and phone +48 123 456 789.",
                ],
            )

            output_path, counters = anonymize_docx_file(source_path)

            self.assertEqual(output_path, Path(temp_dir) / "document_ANON.docx")
            self.assertEqual(
                read_docx_file(output_path),
                "Contact [EMAIL] on [DATA].\n"
                "PESEL [PESEL] and phone [TELEFON].",
            )
            self.assertEqual(
                counters, {"EMAIL": 1, "PESEL": 1, "TELEFON": 1, "DATA": 1}
            )

    def test_docx_result_does_not_return_map_or_source_values(self) -> None:
        with workspace_temp_dir() as temp_dir:
            source_path = Path(temp_dir) / "safe_input.docx"
            source_values = {
                "safe@example.test",
                "00000000000",
                "+48 123 456 789",
                "2026-06-01",
            }
            write_docx(
                source_path,
                ["safe@example.test 00000000000 +48 123 456 789 2026-06-01"],
            )

            output_path, counters = anonymize_docx_file(source_path)

            returned_text = repr((output_path, counters))
            output_text = read_docx_file(output_path)
            for source_value in source_values:
                self.assertNotIn(source_value, returned_text)
                self.assertNotIn(source_value, repr(counters))
                self.assertNotIn(source_value, output_text)

            self.assertEqual(
                counters, {"EMAIL": 1, "PESEL": 1, "TELEFON": 1, "DATA": 1}
            )
            self.assertTrue(all(isinstance(count, int) for count in counters.values()))

    def test_rejects_unsupported_extension_for_docx_flow(self) -> None:
        with workspace_temp_dir() as temp_dir:
            rtf_path = Path(temp_dir) / "document.rtf"
            no_extension_path = Path(temp_dir) / "document"

            with self.assertRaisesRegex(ValueError, "Only .txt, .docx, and .pdf"):
                extract_text(rtf_path)
            with self.assertRaisesRegex(ValueError, "Only .docx files are supported"):
                build_anonymized_docx_path(rtf_path)
            with self.assertRaisesRegex(ValueError, "DOCX output requires"):
                save_anonymized_copy(
                    Path(temp_dir) / "document.docx", "Anonymized text."
                )
            with self.assertRaisesRegex(ValueError, "Only .txt, .docx, and .pdf"):
                save_anonymized_copy(no_extension_path, "Anonymized text.")


if __name__ == "__main__":
    unittest.main()
