"""Stage 18 end-to-end MVP workflow validation tests."""

from pathlib import Path
import sys
import tempfile
import unittest

from docx import Document


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from anonymizer import anonymize_batch
from review import (
    REVIEW_STATUS_APPROVED,
    REVIEW_STATUS_NEEDS_REVIEW,
    REVIEW_STATUS_REJECTED,
    apply_review_statuses,
    detect_review_workspace,
    export_approved_workspace,
    save_review_files,
)


UNSAFE_PATTERNS = (
    "safe@example.test",
    "dictionary@example.test",
    "Private Alias Example",
    "P. Alias Example",
    "Example Person",
    "E. Person",
    "12345678901",
    "+48 123 456 789",
    "2026-06-01",
)


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


def assert_safe_metadata(testcase: unittest.TestCase, text: str, *extra: str) -> None:
    for unsafe_text in (*UNSAFE_PATTERNS, *extra):
        testcase.assertNotIn(unsafe_text, text)
    testcase.assertIn("Original sensitive values stored: no", text)
    testcase.assertIn("Replacement map created: no", text)


class Stage18EndToEndWorkflowTests(unittest.TestCase):
    def test_simple_low_risk_txt_can_be_approved_and_exported(self) -> None:
        with workspace_temp_dir() as temp_dir:
            root = Path(temp_dir)
            source_dir = root / "source"
            output_dir = root / "output"
            source_dir.mkdir()
            output_dir.mkdir()
            source_path = source_dir / "simple.txt"
            source_path.write_text(
                "Synthetic notice for safe@example.test.", encoding="utf-8"
            )

            batch_result = anonymize_batch([source_path], output_dir)
            workspace = detect_review_workspace(output_dir)
            reviewed_items = apply_review_statuses(
                workspace.items,
                {"simple_ANON.txt": REVIEW_STATUS_APPROVED},
            )
            save_review_files(
                output_dir,
                items=reviewed_items,
                batch_summary_names=workspace.batch_summary_names,
                saved_at="2026-06-19T08:00:00Z",
            )
            export_result = export_approved_workspace(
                output_dir,
                exported_at="2026-06-19T08:05:00Z",
            )

            report_text = (output_dir / "simple_RAPORT.txt").read_text(
                encoding="utf-8"
            )
            summary_text = batch_result.summary_path.read_text(encoding="utf-8")
            index_text = export_result.index_path.read_text(encoding="utf-8")

            self.assertEqual(batch_result.success_count, 1)
            self.assertEqual(batch_result.risk_level_counts["ok"], 1)
            self.assertEqual(workspace.items[0].risk_level, "ok")
            self.assertEqual(export_result.exported_output_count, 1)
            self.assertEqual(export_result.copied_report_count, 1)
            self.assertTrue((output_dir / "approved" / "simple_ANON.txt").exists())
            self.assertTrue((output_dir / "approved" / "simple_RAPORT.txt").exists())
            assert_safe_metadata(self, report_text)
            assert_safe_metadata(self, summary_text)
            self.assertNotIn("safe@example.test", index_text)
            self.assertIn("Approval is a manual user decision.", index_text)
            self.assertIn("Automatic approval used: no", index_text)

    def test_mixed_risk_batch_prioritizes_review_and_exports_only_approved(self) -> None:
        with workspace_temp_dir() as temp_dir:
            root = Path(temp_dir)
            source_dir = root / "source"
            output_dir = root / "output"
            source_dir.mkdir()
            output_dir.mkdir()
            low_path = source_dir / "low.txt"
            warning_path = source_dir / "warning.txt"
            high_path = source_dir / "high.txt"
            low_path.write_text("Synthetic note without warning data.", encoding="utf-8")
            warning_path.write_text(
                "Synthetic case reference ABC/123/2026 remains.", encoding="utf-8"
            )
            high_path.write_text(
                "Synthetic address ul. Testowa 12 remains.", encoding="utf-8"
            )

            batch_result = anonymize_batch(
                [low_path, warning_path, high_path],
                output_dir,
            )
            workspace = detect_review_workspace(output_dir)
            reviewed_items = apply_review_statuses(
                workspace.items,
                {
                    "low_ANON.txt": REVIEW_STATUS_APPROVED,
                    "warning_ANON.txt": REVIEW_STATUS_NEEDS_REVIEW,
                    "high_ANON.txt": REVIEW_STATUS_REJECTED,
                },
            )
            save_review_files(
                output_dir,
                items=reviewed_items,
                batch_summary_names=workspace.batch_summary_names,
                saved_at="2026-06-19T08:10:00Z",
            )
            export_result = export_approved_workspace(
                output_dir,
                exported_at="2026-06-19T08:15:00Z",
            )
            summary_text = batch_result.summary_path.read_text(encoding="utf-8")
            index_text = export_result.index_path.read_text(encoding="utf-8")

            self.assertEqual(batch_result.success_count, 3)
            self.assertEqual(batch_result.risk_level_counts["ok"], 1)
            self.assertEqual(batch_result.risk_level_counts["warning"], 1)
            self.assertEqual(batch_result.risk_level_counts["high_risk"], 1)
            self.assertEqual(
                [item.output_name for item in workspace.items],
                ["high_ANON.txt", "warning_ANON.txt", "low_ANON.txt"],
            )
            self.assertIn("* CASE_REFERENCE: 1", summary_text)
            self.assertIn("* ADDRESS_LIKE: 1", summary_text)
            self.assertEqual(export_result.copied_output_names, ["low_ANON.txt"])
            self.assertTrue((output_dir / "approved" / "low_ANON.txt").exists())
            self.assertFalse((output_dir / "approved" / "warning_ANON.txt").exists())
            self.assertFalse((output_dir / "approved" / "high_ANON.txt").exists())
            self.assertIn("Needs review files copied: no", index_text)
            self.assertIn("Rejected files copied: no", index_text)

    def test_dictionary_workflow_keeps_reports_and_index_safe(self) -> None:
        with workspace_temp_dir() as temp_dir:
            root = Path(temp_dir)
            source_dir = root / "source"
            output_dir = root / "output"
            source_dir.mkdir()
            output_dir.mkdir()
            dictionary_path = source_dir / "sensitive_terms.txt"
            dictionary_path.write_text(
                "Example Person | E. Person = [PERSON_LABEL]\n"
                "Private Alias Example | P. Alias Example = [PRIVATE_LABEL]\n",
                encoding="utf-8",
            )
            source_path = source_dir / "dictionary.txt"
            source_path.write_text(
                "E. Person contacted dictionary@example.test. "
                "P. Alias Example was copied.",
                encoding="utf-8",
            )

            batch_result = anonymize_batch(
                [source_path],
                output_dir,
                sensitive_terms_path=dictionary_path,
            )
            workspace = detect_review_workspace(output_dir)
            reviewed_items = apply_review_statuses(
                workspace.items,
                {"dictionary_ANON.txt": REVIEW_STATUS_APPROVED},
            )
            save_review_files(
                output_dir,
                items=reviewed_items,
                batch_summary_names=workspace.batch_summary_names,
                saved_at="2026-06-19T08:20:00Z",
            )
            export_result = export_approved_workspace(
                output_dir,
                exported_at="2026-06-19T08:25:00Z",
            )

            output_text = (output_dir / "dictionary_ANON.txt").read_text(
                encoding="utf-8"
            )
            report_text = (output_dir / "dictionary_RAPORT.txt").read_text(
                encoding="utf-8"
            )
            summary_text = batch_result.summary_path.read_text(encoding="utf-8")
            index_text = export_result.index_path.read_text(encoding="utf-8")

            self.assertIn("[PERSON_LABEL]", output_text)
            self.assertIn("[PRIVATE_LABEL]", output_text)
            self.assertIn("[EMAIL]", output_text)
            self.assertIn("Dictionary status: loaded", report_text)
            self.assertIn("Dictionary matches found: yes", report_text)
            self.assertIn("* PERSON_LABEL: 1", report_text)
            self.assertIn("* PRIVATE_LABEL: 1", report_text)
            assert_safe_metadata(self, report_text)
            assert_safe_metadata(self, summary_text)
            self.assertNotIn("Example Person", index_text)
            self.assertNotIn("Private Alias Example", index_text)
            self.assertIn("Dictionary private terms stored: no", index_text)

    def test_docx_and_text_pdf_workflows_participate_in_full_batch(self) -> None:
        with workspace_temp_dir() as temp_dir:
            root = Path(temp_dir)
            source_dir = root / "source"
            output_dir = root / "output"
            source_dir.mkdir()
            output_dir.mkdir()
            docx_path = source_dir / "document.docx"
            pdf_path = source_dir / "notice.pdf"
            write_docx(docx_path, ["Synthetic date 2026-06-01."])
            write_text_pdf(pdf_path, "Synthetic phone +48 123 456 789.")

            batch_result = anonymize_batch([docx_path, pdf_path], output_dir)
            workspace = detect_review_workspace(output_dir)
            reviewed_items = apply_review_statuses(
                workspace.items,
                {
                    "document_ANON.docx": REVIEW_STATUS_APPROVED,
                    "notice_ANON.txt": REVIEW_STATUS_APPROVED,
                },
            )
            save_review_files(
                output_dir,
                items=reviewed_items,
                batch_summary_names=workspace.batch_summary_names,
                saved_at="2026-06-19T08:30:00Z",
            )
            export_result = export_approved_workspace(
                output_dir,
                exported_at="2026-06-19T08:35:00Z",
            )
            summary_text = batch_result.summary_path.read_text(encoding="utf-8")

            self.assertEqual(batch_result.success_count, 2)
            self.assertTrue((output_dir / "document_ANON.docx").exists())
            self.assertTrue((output_dir / "document_RAPORT.txt").exists())
            self.assertTrue((output_dir / "notice_ANON.txt").exists())
            self.assertTrue((output_dir / "notice_RAPORT.txt").exists())
            self.assertEqual(export_result.exported_output_count, 2)
            self.assertEqual(export_result.copied_report_count, 2)
            self.assertTrue((output_dir / "approved" / "document_ANON.docx").exists())
            self.assertTrue((output_dir / "approved" / "notice_ANON.txt").exists())
            assert_safe_metadata(self, summary_text)

    def test_generated_outputs_and_local_workspaces_remain_gitignored(self) -> None:
        gitignore_text = (PROJECT_ROOT / ".gitignore").read_text(encoding="utf-8")

        for pattern in (
            "_manual_test/",
            "_local_diary/",
            "private/",
            "real_data/",
            "data/",
            "*.log",
            ".env",
            "*_ANON.*",
            "*_RAPORT.*",
            "*_BATCH_SUMMARY*.txt",
            "_REVIEW_STATUS*.json",
            "_REVIEW_SUMMARY*.txt",
            "_APPROVED_INDEX*.txt",
        ):
            self.assertIn(pattern, gitignore_text)


if __name__ == "__main__":
    unittest.main()
