"""Tests for the Stage 5 single-file GUI workflow integration layer."""

import importlib
from pathlib import Path
import sys
import tempfile
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from anonymizer import BatchResult, anonymize_file, anonymize_file_with_audit
from gui import (
    format_anonymize_readiness,
    format_audit_result,
    format_approved_export_status,
    format_batch_audit_result,
    format_batch_status,
    format_dictionary_result,
    format_selected_file_count,
    open_path_with_default_app,
    remove_paths_by_indexes,
)


def workspace_temp_dir():
    return tempfile.TemporaryDirectory(dir=PROJECT_ROOT / "tests")


class GuiWorkflowTests(unittest.TestCase):
    def test_gui_can_be_imported_as_package_module(self) -> None:
        module = importlib.import_module("src.gui")

        self.assertTrue(hasattr(module, "start_gui"))

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
            self.assertEqual(audit_result["risk_level"], "warning")
            self.assertEqual(audit_result["findings"]["CASE_REFERENCE"], 1)
            self.assertNotIn(source_value, repr(audit_result))
            self.assertNotIn(source_value, formatted_audit)
            self.assertIn("Audit status: WARNING", formatted_audit)
            self.assertIn("Risk level: warning", formatted_audit)

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

    def test_gui_formats_selected_file_count(self) -> None:
        self.assertEqual(format_selected_file_count(0), "Selected files: 0")
        self.assertEqual(format_selected_file_count(2), "Selected files: 2")

        with self.assertRaises(ValueError):
            format_selected_file_count(-1)

    def test_gui_formats_anonymization_readiness_hint(self) -> None:
        self.assertEqual(
            format_anonymize_readiness(0, False),
            "Add at least one input file and select an output folder.",
        )
        self.assertEqual(
            format_anonymize_readiness(0, True),
            "Add at least one input file.",
        )
        self.assertEqual(
            format_anonymize_readiness(3, False),
            "Select an output folder.",
        )
        self.assertEqual(
            format_anonymize_readiness(3, True),
            "Ready to anonymize 3 file(s).",
        )

        with self.assertRaises(ValueError):
            format_anonymize_readiness(-1, False)

    def test_gui_removes_paths_by_selected_indexes(self) -> None:
        paths = [
            Path("first.txt"),
            Path("second.txt"),
            Path("third.txt"),
        ]

        remaining_paths = remove_paths_by_indexes(paths, (1, 99, -1))

        self.assertEqual(remaining_paths, [Path("first.txt"), Path("third.txt")])

    def test_gui_batch_status_is_plain_language_and_safe(self) -> None:
        with workspace_temp_dir() as temp_dir:
            output_dir = Path(temp_dir) / "output-folder"
            output_dir.mkdir()
            batch_result = BatchResult(
                summary_path=output_dir / "_BATCH_SUMMARY.txt",
                input_count=2,
                success_count=1,
                error_count=1,
                counters={},
                audit_status_counts={"ok": 1, "warning": 0, "not run": 1},
                risk_level_counts={"ok": 1, "warning": 0, "high_risk": 0},
                audit_category_counters={},
                results=[],
            )

            status = format_batch_status(batch_result)
            audit_status = format_batch_audit_result(batch_result)

            self.assertIn("Processed 1 of 2 selected files", status)
            self.assertIn("Some files could not be processed", status)
            self.assertIn("output-folder", status)
            self.assertIn("_BATCH_SUMMARY.txt", status)
            self.assertNotIn(str(output_dir), status)
            self.assertIn("Risk levels:", audit_status)
            self.assertIn("high_risk: 0", audit_status)

    def test_gui_approved_export_status_is_plain_language_and_safe(self) -> None:
        status = format_approved_export_status(
            exported_output_count=2,
            copied_report_count=1,
            missing_report_count=1,
            index_name="_APPROVED_INDEX.txt",
        )

        self.assertIn("Exported 2 approved _ANON files", status)
        self.assertIn("Copied 1 matching report(s)", status)
        self.assertIn("1 report(s) were missing", status)
        self.assertIn("_APPROVED_INDEX.txt", status)
        self.assertIn("manual user decision", status)
        self.assertIn("not a guarantee", status)

    def test_gui_open_default_app_reports_missing_file(self) -> None:
        with workspace_temp_dir() as temp_dir:
            missing_path = Path(temp_dir) / "missing_ANON.txt"

            with self.assertRaises(FileNotFoundError):
                open_path_with_default_app(missing_path)


if __name__ == "__main__":
    unittest.main()
