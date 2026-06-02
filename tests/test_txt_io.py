"""Tests for Stage 2 TXT file input and output."""

from pathlib import Path
import sys
import tempfile
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from anonymizer import anonymize_txt_file
from file_readers import extract_text, read_txt_file
from file_writers import (
    build_anonymized_txt_path,
    save_anonymized_copy,
    save_anonymized_txt_copy,
)


def workspace_temp_dir():
    return tempfile.TemporaryDirectory(dir=PROJECT_ROOT / "tests")


class TxtIoTests(unittest.TestCase):
    def test_reads_txt_file_as_utf8_text(self) -> None:
        with workspace_temp_dir() as temp_dir:
            source_path = Path(temp_dir) / "document.txt"
            source_text = "Synthetic TXT content for Stage 2."
            source_path.write_text(source_text, encoding="utf-8")

            self.assertEqual(read_txt_file(source_path), source_text)
            self.assertEqual(extract_text(source_path), source_text)

    def test_saves_anonymized_txt_copy_with_anon_suffix(self) -> None:
        with workspace_temp_dir() as temp_dir:
            source_path = Path(temp_dir) / "document.txt"
            source_path.write_text("Original synthetic text.", encoding="utf-8")

            output_path = save_anonymized_txt_copy(
                source_path, "Anonymized [EMAIL] text."
            )

            self.assertEqual(output_path, Path(temp_dir) / "document_ANON.txt")
            self.assertEqual(
                output_path.read_text(encoding="utf-8"),
                "Anonymized [EMAIL] text.",
            )

    def test_original_txt_file_is_not_modified(self) -> None:
        with workspace_temp_dir() as temp_dir:
            source_path = Path(temp_dir) / "document.txt"
            original_text = "Original synthetic value: tester@example.test."
            source_path.write_text(original_text, encoding="utf-8")

            save_anonymized_txt_copy(source_path, "Original synthetic value: [EMAIL].")

            self.assertEqual(source_path.read_text(encoding="utf-8"), original_text)

    def test_rejects_unsupported_extensions(self) -> None:
        with workspace_temp_dir() as temp_dir:
            docx_path = Path(temp_dir) / "document.docx"
            pdf_path = Path(temp_dir) / "document.pdf"
            no_extension_path = Path(temp_dir) / "document"

            with self.assertRaisesRegex(ValueError, "Only .txt files are supported"):
                read_txt_file(docx_path)
            with self.assertRaisesRegex(ValueError, "Only .txt files are supported"):
                build_anonymized_txt_path(pdf_path)
            with self.assertRaisesRegex(ValueError, "Only .txt, .docx, and .pdf"):
                save_anonymized_copy(no_extension_path, "Anonymized text.")

    def test_anonymizes_txt_file_and_writes_anon_copy(self) -> None:
        with workspace_temp_dir() as temp_dir:
            source_path = Path(temp_dir) / "document.txt"
            source_path.write_text(
                "Contact tester@example.test on 2026-06-01. "
                "PESEL 00000000000.",
                encoding="utf-8",
            )

            output_path, counters = anonymize_txt_file(source_path)

            self.assertEqual(output_path, Path(temp_dir) / "document_ANON.txt")
            self.assertEqual(
                output_path.read_text(encoding="utf-8"),
                "Contact [EMAIL] on [DATA]. PESEL [PESEL].",
            )
            self.assertEqual(counters, {"EMAIL": 1, "PESEL": 1, "DATA": 1})

    def test_txt_file_result_does_not_return_map_or_source_values(self) -> None:
        with workspace_temp_dir() as temp_dir:
            source_path = Path(temp_dir) / "safe_input.txt"
            source_values = {
                "safe@example.test",
                "00000000000",
                "+48 123 456 789",
                "2026-06-01",
            }
            source_path.write_text(
                "safe@example.test 00000000000 +48 123 456 789 2026-06-01",
                encoding="utf-8",
            )

            output_path, counters = anonymize_txt_file(source_path)

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
