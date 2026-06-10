"""Tests for the Stage 5 single-file GUI workflow integration layer."""

from pathlib import Path
import sys
import tempfile
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from anonymizer import anonymize_file, anonymize_file_with_audit
from gui import format_audit_result, format_dictionary_result


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

    def test_dispatcher_audit_output_does_not_expose_source_values(self) -> None:
        with workspace_temp_dir() as temp_dir:
            source_value = "ABC/123/2026"
            source_path = Path(temp_dir) / "document.txt"
            source_path.write_text(
                f"Reference {source_value} remains for review.",
                encoding="utf-8",
            )

            output_path, counters, audit_result = anonymize_file_with_audit(source_path)
            formatted_audit = format_audit_result(audit_result)

            self.assertEqual(output_path, Path(temp_dir) / "document_ANON.txt")
            self.assertEqual(counters, {})
            self.assertEqual(audit_result["status"], "warning")
            self.assertEqual(audit_result["findings"]["CASE_REFERENCE"], 1)
            self.assertNotIn(source_value, repr(audit_result))
            self.assertNotIn(source_value, formatted_audit)
            self.assertIn("Audit status: WARNING", formatted_audit)

    def test_dispatcher_passes_dictionary_path_and_gui_formats_status(self) -> None:
        with workspace_temp_dir() as temp_dir:
            source_term = "Person One Example"
            dictionary_path = Path(temp_dir) / "sensitive_terms.txt"
            dictionary_path.write_text(
                f"{source_term} = [IMIE NAZWISKO]\n",
                encoding="utf-8",
            )
            source_path = Path(temp_dir) / "document.txt"
            source_path.write_text(source_term, encoding="utf-8")

            output_path, counters, audit_result = anonymize_file_with_audit(
                source_path,
                sensitive_terms_path=dictionary_path,
            )
            formatted_dictionary = format_dictionary_result(
                audit_result["dictionary"]
            )

            self.assertEqual(output_path, Path(temp_dir) / "document_ANON.txt")
            self.assertEqual(output_path.read_text(encoding="utf-8"), "[IMIE NAZWISKO]")
            self.assertEqual(counters, {"IMIE NAZWISKO": 1})
            self.assertEqual(
                formatted_dictionary,
                "Dictionary status: loaded; matches found: yes",
            )
            self.assertNotIn(source_term, formatted_dictionary)

    def test_gui_formats_loaded_dictionary_without_matches(self) -> None:
        formatted_dictionary = format_dictionary_result(
            {
                "status": "loaded",
                "label_counters": {"IMIE NAZWISKO": 0},
            }
        )

        self.assertEqual(
            formatted_dictionary,
            "Dictionary status: loaded; matches found: no",
        )

    def test_gui_formats_invalid_dictionary_status(self) -> None:
        formatted_dictionary = format_dictionary_result(
            {
                "status": "invalid",
                "label_counters": {},
            }
        )

        self.assertEqual(
            formatted_dictionary,
            "Dictionary status: invalid; dictionary replacements skipped",
        )


if __name__ == "__main__":
    unittest.main()
