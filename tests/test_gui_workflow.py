"""Tests for the Stage 5 single-file GUI workflow integration layer."""

from pathlib import Path
import sys
import tempfile
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from anonymizer import anonymize_file


def workspace_temp_dir():
    return tempfile.TemporaryDirectory(dir=PROJECT_ROOT / "tests")


class GuiWorkflowTests(unittest.TestCase):
    def test_anonymizes_supported_txt_file_through_application_workflow(self) -> None:
        with workspace_temp_dir() as temp_dir:
            source_path = Path(temp_dir) / "document.txt"
            source_path.write_text(
                "Contact tester@example.test on 2026-06-01.",
                encoding="utf-8",
            )

            output_path, counters = anonymize_file(source_path)

            self.assertEqual(output_path, Path(temp_dir) / "document_ANON.txt")
            self.assertEqual(
                output_path.read_text(encoding="utf-8"),
                "Contact [EMAIL] on [DATA].",
            )
            self.assertEqual(counters, {"EMAIL": 1, "DATA": 1})
            self.assertEqual(
                source_path.read_text(encoding="utf-8"),
                "Contact tester@example.test on 2026-06-01.",
            )

    def test_rejects_unsupported_file_type_clearly(self) -> None:
        with workspace_temp_dir() as temp_dir:
            source_path = Path(temp_dir) / "document.rtf"
            source_path.write_text("Contact tester@example.test.", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "Only .txt, .docx, .pdf"):
                anonymize_file(source_path)


if __name__ == "__main__":
    unittest.main()
