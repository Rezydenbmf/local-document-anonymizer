"""Tests for Stage 13 manual review workflow metadata."""

from pathlib import Path
import json
import sys
import tempfile
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from anonymizer import anonymize_batch
from review import (
    REVIEW_STATUS_APPROVED,
    REVIEW_STATUS_NEEDS_REVIEW,
    REVIEW_STATUS_REJECTED,
    apply_review_statuses,
    detect_review_workspace,
    save_review_files,
)


def workspace_temp_dir():
    return tempfile.TemporaryDirectory(dir=PROJECT_ROOT / "tests")


class ReviewWorkflowTests(unittest.TestCase):
    def test_detects_anon_files_and_pairs_matching_reports(self) -> None:
        with workspace_temp_dir() as temp_dir:
            output_dir = Path(temp_dir)
            (output_dir / "document_ANON.txt").write_text(
                "Synthetic anonymized output.", encoding="utf-8"
            )
            (output_dir / "document_RAPORT.txt").write_text(
                "Synthetic report.", encoding="utf-8"
            )
            (output_dir / "letter_ANON.docx").write_bytes(b"synthetic docx")
            (output_dir / "scan_ANON_2.txt").write_text(
                "Synthetic PDF text output.", encoding="utf-8"
            )
            (output_dir / "scan_RAPORT_2.txt").write_text(
                "Synthetic report.", encoding="utf-8"
            )
            (output_dir / "_BATCH_SUMMARY.txt").write_text(
                "Synthetic batch summary.", encoding="utf-8"
            )
            (output_dir / "_REVIEW_SUMMARY.txt").write_text(
                "Old review summary.", encoding="utf-8"
            )

            workspace = detect_review_workspace(output_dir)

            items = {item.output_name: item for item in workspace.items}
            self.assertEqual(
                sorted(items),
                ["document_ANON.txt", "letter_ANON.docx", "scan_ANON_2.txt"],
            )
            self.assertEqual(
                items["document_ANON.txt"].report_name,
                "document_RAPORT.txt",
            )
            self.assertIsNone(items["letter_ANON.docx"].report_name)
            self.assertEqual(items["scan_ANON_2.txt"].report_name, "scan_RAPORT_2.txt")
            self.assertEqual(workspace.batch_summary_names, ["_BATCH_SUMMARY.txt"])

    def test_supports_manual_review_statuses_and_saves_status_json(self) -> None:
        with workspace_temp_dir() as temp_dir:
            output_dir = Path(temp_dir)
            for name in ("a_ANON.txt", "b_ANON.txt", "c_ANON.txt"):
                (output_dir / name).write_text("Synthetic output.", encoding="utf-8")

            workspace = detect_review_workspace(output_dir)
            items = apply_review_statuses(
                workspace.items,
                {
                    "a_ANON.txt": REVIEW_STATUS_APPROVED,
                    "b_ANON.txt": REVIEW_STATUS_NEEDS_REVIEW,
                    "c_ANON.txt": REVIEW_STATUS_REJECTED,
                },
            )

            save_result = save_review_files(
                output_dir,
                items=items,
                saved_at="2026-06-16T10:00:00Z",
            )
            payload = json.loads(save_result.status_path.read_text(encoding="utf-8"))

            self.assertEqual(save_result.status_path.name, "_REVIEW_STATUS.json")
            self.assertEqual(save_result.summary_path.name, "_REVIEW_SUMMARY.txt")
            self.assertEqual(payload["review_item_count"], 3)
            self.assertEqual(payload["status_counts"][REVIEW_STATUS_APPROVED], 1)
            self.assertEqual(payload["status_counts"][REVIEW_STATUS_NEEDS_REVIEW], 1)
            self.assertEqual(payload["status_counts"][REVIEW_STATUS_REJECTED], 1)
            self.assertFalse(payload["manual_review_completed"])
            self.assertFalse(payload["automatic_approval_used"])

    def test_review_summary_is_safe_and_does_not_include_document_content(self) -> None:
        with workspace_temp_dir() as temp_dir:
            output_dir = Path(temp_dir)
            source_personal_data = "safe@example.test"
            source_document_content = "Synthetic source content 00000000000"
            private_dictionary_term = "Private Alias Example"
            (output_dir / "document_ANON.txt").write_text(
                (
                    f"{source_document_content}\n"
                    f"{source_personal_data}\n"
                    f"{private_dictionary_term}\n"
                ),
                encoding="utf-8",
            )
            (output_dir / "document_RAPORT.txt").write_text(
                "Synthetic safe report.", encoding="utf-8"
            )
            (output_dir / "_BATCH_SUMMARY.txt").write_text(
                "Synthetic batch summary.", encoding="utf-8"
            )

            workspace = detect_review_workspace(output_dir)
            items = apply_review_statuses(
                workspace.items,
                {"document_ANON.txt": REVIEW_STATUS_APPROVED},
            )
            save_result = save_review_files(
                output_dir,
                items=items,
                batch_summary_names=workspace.batch_summary_names,
                saved_at="2026-06-16T10:00:00Z",
            )
            status_text = save_result.status_path.read_text(encoding="utf-8")
            summary_text = save_result.summary_path.read_text(encoding="utf-8")

            self.assertIn("Manual review completed: yes", summary_text)
            self.assertIn("Review decisions are manual user decisions.", summary_text)
            self.assertIn("Approved means the user manually approved the file.", summary_text)
            self.assertIn("output: document_ANON.txt", summary_text)
            self.assertIn("report: document_RAPORT.txt", summary_text)
            self.assertIn("_BATCH_SUMMARY.txt", summary_text)
            for unsafe_text in (
                source_personal_data,
                source_document_content,
                private_dictionary_term,
                str(output_dir),
            ):
                self.assertNotIn(unsafe_text, status_text)
                self.assertNotIn(unsafe_text, summary_text)
            self.assertIn("Document contents stored: no", summary_text)
            self.assertIn("Original sensitive values stored: no", summary_text)
            self.assertIn("Source paths stored: no", summary_text)
            self.assertIn("Replacement map created: no", summary_text)

    def test_review_summary_uses_collision_safe_name(self) -> None:
        with workspace_temp_dir() as temp_dir:
            output_dir = Path(temp_dir)
            (output_dir / "document_ANON.txt").write_text(
                "Synthetic output.", encoding="utf-8"
            )
            (output_dir / "_REVIEW_SUMMARY.txt").write_text(
                "Existing summary.", encoding="utf-8"
            )
            workspace = detect_review_workspace(output_dir)

            save_result = save_review_files(
                output_dir,
                items=workspace.items,
                saved_at="2026-06-16T10:00:00Z",
            )

            self.assertEqual(save_result.summary_path.name, "_REVIEW_SUMMARY_2.txt")
            self.assertTrue((output_dir / "_REVIEW_SUMMARY.txt").exists())

    def test_stage_12_batch_outputs_reports_and_audit_are_reviewable(self) -> None:
        with workspace_temp_dir() as temp_dir:
            source_dir = Path(temp_dir) / "source"
            output_dir = Path(temp_dir) / "output"
            source_dir.mkdir()
            output_dir.mkdir()
            source_path = source_dir / "document.txt"
            source_path.write_text(
                "Reference ABC/123/2026 and contact safe@example.test.",
                encoding="utf-8",
            )

            batch_result = anonymize_batch([source_path], output_dir)
            workspace = detect_review_workspace(output_dir)
            report_text = (output_dir / "document_RAPORT.txt").read_text(
                encoding="utf-8"
            )

            self.assertEqual(batch_result.success_count, 1)
            self.assertEqual(batch_result.audit_status_counts["warning"], 1)
            self.assertEqual(len(workspace.items), 1)
            self.assertEqual(workspace.items[0].output_name, "document_ANON.txt")
            self.assertEqual(workspace.items[0].report_name, "document_RAPORT.txt")
            self.assertEqual(workspace.batch_summary_names, ["_BATCH_SUMMARY.txt"])
            self.assertIn("Post-anonymization audit:", report_text)
            self.assertIn("Status: warning", report_text)
            self.assertNotIn("safe@example.test", report_text)
            self.assertNotIn(str(source_dir), report_text)


if __name__ == "__main__":
    unittest.main()
