"""Tests for Stage 6 safe report file output."""

from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from docx import Document


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from audit import AUDIT_CATEGORY_ORDER, audit_text
from checklist import build_review_checklist_text
from anonymizer import SUPPORTED_LABELS, anonymize_docx_file, anonymize_file
from anonymizer import anonymize_pdf_file, anonymize_txt_file
from file_readers import read_docx_file
from file_writers import (
    apply_collision_suffix,
    build_report_path,
    build_shared_collision_suffix,
)
from report import build_batch_summary_text, build_report_text
from review import preferred_review_output_path


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
        self.assertIn("Risk level: ok", report_text)
        self.assertIn("* none: 0", report_text)
        self.assertIn("Manual review required: yes", report_text)
        self.assertIn("Dictionary:", report_text)
        self.assertIn("Dictionary status: not selected", report_text)

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

    def test_report_dictionary_section_is_safe_and_counts_labels_only(self) -> None:
        source_term = "Person One Example"

        report_text = build_report_text(
            counters={"IMIE NAZWISKO": 1},
            input_extension=".txt",
            output_extension=".txt",
            category_order=SUPPORTED_LABELS,
            dictionary_result={
                "status": "loaded",
                "label_counters": {"IMIE NAZWISKO": 1},
            },
        )

        self.assertIn("Dictionary used: yes", report_text)
        self.assertIn("Dictionary status: loaded", report_text)
        self.assertIn("Dictionary matches found: yes", report_text)
        self.assertIn("* IMIE NAZWISKO: 1", report_text)
        self.assertNotIn(source_term, report_text)

    def test_report_dictionary_section_handles_invalid_dictionary(self) -> None:
        report_text = build_report_text(
            counters={"EMAIL": 1},
            input_extension=".txt",
            output_extension=".txt",
            category_order=SUPPORTED_LABELS,
            dictionary_result={
                "status": "invalid",
                "label_counters": {},
            },
        )

        self.assertIn("Dictionary used: no", report_text)
        self.assertIn("Dictionary status: invalid", report_text)
        self.assertIn("Dictionary matches found: no", report_text)
        self.assertIn("* none: 0", report_text)

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
        self.assertIn("Risk level: warning", report_text)
        self.assertIn("* CASE_REFERENCE: 1", report_text)
        self.assertNotIn(source_value, report_text)

    def test_report_audit_section_includes_high_risk_level_safely(self) -> None:
        source_value = "tester@example.test"

        report_text = build_report_text(
            counters={},
            input_extension=".txt",
            output_extension=".txt",
            category_order=SUPPORTED_LABELS,
            audit_result=audit_text(f"Remaining {source_value}."),
            audit_category_order=AUDIT_CATEGORY_ORDER,
        )

        self.assertIn("Risk level: high_risk", report_text)
        self.assertIn("* EMAIL: 1", report_text)
        self.assertNotIn(source_value, report_text)

    def test_report_path_is_built_as_raport_txt(self) -> None:
        with workspace_temp_dir() as temp_dir:
            internal_dir = Path(temp_dir) / "_wewnetrzne"
            self.assertEqual(
                build_report_path(Path(temp_dir) / "document.txt"),
                internal_dir / "document_RAPORT.txt",
            )
            self.assertEqual(
                build_report_path(Path(temp_dir) / "document.docx"),
                internal_dir / "document_RAPORT.txt",
            )
            self.assertEqual(
                build_report_path(Path(temp_dir) / "document.pdf"),
                internal_dir / "document_RAPORT.txt",
            )

    def test_txt_integration_creates_anon_and_safe_report(self) -> None:
        with workspace_temp_dir() as temp_dir:
            source_path = Path(temp_dir) / "document.txt"
            source_path.write_text(
                "safe@example.test 00000000000 +48 123 456 789 2026-06-01",
                encoding="utf-8",
            )

            output_path, counters = anonymize_txt_file(source_path)
            report_path = Path(temp_dir) / "_wewnetrzne" / "document_RAPORT.txt"

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
            report_path = Path(temp_dir) / "_wewnetrzne" / "document_RAPORT.txt"

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
            report_path = Path(temp_dir) / "_wewnetrzne" / "document_RAPORT.txt"
            visual_pdf_path = Path(temp_dir) / "document_ANON_VISUAL.pdf"
            review_pdf_path = Path(temp_dir) / "document_ANON_REVIEW.pdf"
            checklist_path = Path(temp_dir) / "_wewnetrzne" / "document_REVIEW_CHECKLIST.txt"

            self.assertEqual(output_path, Path(temp_dir) / "document_ANON.txt")
            self.assertEqual(
                output_path.read_text(encoding="utf-8").strip(),
                "Contact [EMAIL] on [DATA].",
            )
            self.assertTrue(visual_pdf_path.exists())
            self.assertTrue(review_pdf_path.exists())
            self.assertTrue(checklist_path.exists())
            self.assertTrue(report_path.exists())
            self.assertEqual(counters, {"EMAIL": 1, "DATA": 1})
            self.assert_report_is_safe(report_path)
            report_text = report_path.read_text(encoding="utf-8")
            self.assertIn("PDF redaction:", report_text)
            self.assertIn("PDF text extraction used: text_layer", report_text)
            self.assertIn("Visual PDF created: yes", report_text)
            self.assertIn("Visual PDF output: document_ANON_VISUAL.pdf", report_text)
            self.assertIn("Redaction mapping: word_coordinates", report_text)
            self.assertIn("Review PDF created: yes", report_text)
            self.assertIn("Review PDF type: rebuilt_from_anonymized_text", report_text)
            self.assertIn("Layout-preserving original redaction used: yes", report_text)
            self.assertIn("PDF redaction output created: yes", report_text)
            self.assertIn("PDF redaction status: completed", report_text)
            self.assertIn("PDF true redaction used: yes", report_text)
            self.assertIn("PDF redaction color legend:", report_text)
            self.assertIn("* EMAIL: 1", report_text)
            self.assertIn("Review checklist created: yes", report_text)
            self.assertIn("Review checklist output: document_REVIEW_CHECKLIST.txt", report_text)
            self.assertIn("Review PDF note: rebuilt from anonymized text", report_text)
            self.assertIn("Review PDF table-heavy note:", report_text)

    def test_review_checklist_reports_positions_not_document_excerpts(self) -> None:
        # A security audit of what the app leaves on disk found the review
        # checklist quoting the anonymized text around every finding.
        # Detected values are masked in such an excerpt, but anything
        # detection *missed* - exactly the text a reviewer has to worry
        # about - was written out verbatim, one copy per run, inside a
        # tool whose whole point is keeping that text off disk.
        undetected_value = "Jan Kowalski"
        anonymized_text = (
            "UMOWA\n"
            f"Pracownik: {undetected_value}\n"
            "PESEL: [PESEL]\n"
            "E-mail: [EMAIL]\n"
        )

        checklist_text = build_review_checklist_text(
            source_name="umowa.pdf",
            input_extension=".pdf",
            output_names=["umowa_ANON.txt"],
            report_name="umowa_RAPORT.txt",
            counters={"PESEL": 1, "EMAIL": 1},
            audit_result={"status": "ok", "risk_level": "ok", "findings": {}},
            ocr_result={"used": False, "status": "not_used"},
            ner_result={"used": False, "status": "disabled"},
            llm_review_result={"used": False, "status": "disabled"},
            anonymized_text=anonymized_text,
            # How the PDF path calls it: one section per source page, so a
            # line number inside the section genuinely locates a finding.
            sections=[anonymized_text],
            section_label="Source page",
        )

        self.assertNotIn(undetected_value, checklist_text)
        self.assertNotIn("Kowalski", checklist_text)
        # Still useful for review: where to look in the original.
        self.assertIn("[PESEL]: linia 3", checklist_text)
        self.assertIn("[EMAIL]: linia 4", checklist_text)

    def test_review_checklist_omits_redundant_position_for_line_sections(self) -> None:
        # A per-line section header already names the line, so repeating
        # "linia 1" under every finding would be noise.
        checklist_text = build_review_checklist_text(
            source_name="notatka.txt",
            input_extension=".txt",
            output_names=["notatka_ANON.txt"],
            report_name="notatka_RAPORT.txt",
            counters={"PESEL": 1},
            audit_result={"status": "ok", "risk_level": "ok", "findings": {}},
            ocr_result={"used": False, "status": "not_used"},
            ner_result={"used": False, "status": "disabled"},
            llm_review_result={"used": False, "status": "disabled"},
            anonymized_text="Pracownik: ktos\nPESEL: [PESEL]\n",
        )

        self.assertIn("[PESEL] x1", checklist_text)
        self.assertNotIn("linia 1", checklist_text)

    def test_shared_collision_suffix_skips_numbers_taken_by_any_companion(self) -> None:
        with workspace_temp_dir() as temp_dir:
            folder = Path(temp_dir)
            txt = folder / "scan_ANON.txt"
            visual = folder / "scan_ANON_VISUAL.pdf"

            self.assertEqual(build_shared_collision_suffix([txt, visual]), "")

            # Only the visual PDF exists (a run from before visual output
            # existed, or one where that step failed) - the *shared*
            # suffix must still move past it, so the TXT does not end up
            # numbered independently of its own visual PDF.
            visual.write_bytes(b"%PDF-1.4\n")
            self.assertEqual(build_shared_collision_suffix([txt, visual]), "_2")

            (folder / "scan_ANON_2.txt").write_text("x", encoding="utf-8")
            self.assertEqual(build_shared_collision_suffix([txt, visual]), "_3")

    def test_apply_collision_suffix_inserts_before_the_extension(self) -> None:
        path = Path("C:/out/scan_ANON_VISUAL.pdf")
        self.assertEqual(apply_collision_suffix(path, ""), path)
        self.assertEqual(
            apply_collision_suffix(path, "_2").name, "scan_ANON_VISUAL_2.pdf"
        )

    def test_repeated_runs_keep_txt_and_visual_pdf_numbers_in_step(self) -> None:
        # The regression behind a user report repeated across four
        # sessions: a scan that showed colored visual redaction once and
        # then only ever showed the rebuilt bracket-placeholder text
        # again. Root cause was numbering, not OCR - each output picked
        # its own collision number, so one run that produced no visual
        # PDF offset them permanently, and preferred_review_output_path
        # (which looks up the visual PDF by the TXT's number) missed from
        # then on and silently fell back to the review PDF.
        with workspace_temp_dir() as temp_dir:
            folder = Path(temp_dir)
            source_path = folder / "scan.pdf"
            write_text_pdf(source_path, "Contact safe@example.test on 2026-06-01.")

            first_txt, _ = anonymize_pdf_file(source_path, output_dir=folder)
            self.assertEqual(
                preferred_review_output_path(folder, first_txt.name).name,
                "scan_ANON_VISUAL.pdf",
            )

            # Simulate the folder state that caused the bug: a visual PDF
            # missing for one earlier run (deleted, or never produced).
            (folder / "scan_ANON_VISUAL.pdf").unlink()

            second_txt, _ = anonymize_pdf_file(source_path, output_dir=folder)
            resolved = preferred_review_output_path(folder, second_txt.name)

            self.assertEqual(second_txt.name, "scan_ANON_2.txt")
            self.assertEqual(resolved.name, "scan_ANON_VISUAL_2.pdf")
            self.assertTrue(resolved.is_file())

    def test_pdf_visual_redaction_failure_falls_back_without_crashing(self) -> None:
        # A real user report, repeated across several sessions: a scan
        # came back with placeholder-bracket text instead of colored
        # visual redaction, with no crash and no error shown - meaning
        # whatever failed inside save_word_coordinate_redacted_pdf_copy
        # was swallowed with zero diagnostic trail. Forces that failure
        # directly (any exception, not just RuntimeError - see the
        # broadened except in anonymizer.py) and confirms two things:
        # the file still gets a fully working plain-text-anonymized
        # fallback rather than a crash, and the failure is now
        # diagnosable from the report instead of invisible.
        with workspace_temp_dir() as temp_dir:
            source_path = Path(temp_dir) / "document.pdf"
            write_text_pdf(source_path, "Contact safe@example.test on 2026-06-01.")

            with patch(
                "anonymizer.save_word_coordinate_redacted_pdf_copy",
                side_effect=ValueError("boom"),
            ):
                output_path, counters = anonymize_pdf_file(source_path)

            report_path = Path(temp_dir) / "_wewnetrzne" / "document_RAPORT.txt"
            visual_pdf_path = Path(temp_dir) / "document_ANON_VISUAL.pdf"
            review_pdf_path = Path(temp_dir) / "document_ANON_REVIEW.pdf"

            # The anonymization itself is unaffected - only the colored
            # visual presentation was lost.
            self.assertEqual(
                output_path.read_text(encoding="utf-8").strip(),
                "Contact [EMAIL] on [DATA].",
            )
            self.assertEqual(counters, {"EMAIL": 1, "DATA": 1})
            self.assertFalse(visual_pdf_path.exists())
            self.assertTrue(review_pdf_path.exists())

            report_text = report_path.read_text(encoding="utf-8")
            self.assertIn("Visual PDF created: no", report_text)
            self.assertIn("Visual redaction fallback reason: ValueError", report_text)

    def test_pdf_report_marks_partial_redaction_with_safe_warning(self) -> None:
        report_text = build_report_text(
            counters={"EMAIL": 1, "NER_ORG": 1},
            input_extension=".pdf",
            output_extension=".txt",
            category_order=SUPPORTED_LABELS,
            pdf_redaction_result={
                "used": True,
                "status": "completed_with_warnings",
                "output_name": "document_ANON.pdf",
                "visual_pdf_created": True,
                "visual_pdf_name": "document_ANON_VISUAL.pdf",
                "visual_pdf_type": "original_layout_word_coordinate_redaction",
                "visual_redaction_mode": "word_coordinates",
                "review_pdf_created": False,
                "review_pdf_name": "",
                "review_pdf_type": "none",
                "text_extraction": "text_layer",
                "original_layout_redaction_used": True,
                "original_layout_redaction_experimental": True,
                "redaction_count": 1,
                "counters": {"EMAIL": 1},
                "true_redaction": True,
                "detected_categories": {"EMAIL": 1, "NER_ORG": 1},
                "txt_anonymized_categories": {"EMAIL": 1, "NER_ORG": 1},
                "pdf_redacted_categories": {"EMAIL": 1},
                "detected_not_pdf_redacted_categories": {"NER_ORG": 1},
                "unmapped_categories": {"NER_ORG": 1},
                "warning": (
                    "PDF redaction may be partial; some detected categories "
                    "were not PDF-redacted"
                ),
            },
        )

        self.assertIn("PDF redaction status: completed_with_warnings", report_text)
        self.assertIn("Visual PDF output: document_ANON_VISUAL.pdf", report_text)
        self.assertIn("Unmapped PDF detections:", report_text)
        self.assertIn("Detected but not PDF-redacted categories:", report_text)
        self.assertIn("* NER_ORG: 1", report_text)
        self.assertIn("PDF redaction warning: PDF redaction may be partial", report_text)
        self.assertNotIn("Example Test Clinic", report_text)

    def test_pdf_report_omits_visual_redaction_fallback_reason_by_default(self) -> None:
        report_text = build_report_text(
            counters={"EMAIL": 1},
            input_extension=".pdf",
            output_extension=".txt",
            category_order=SUPPORTED_LABELS,
            pdf_redaction_result={
                "used": False,
                "status": "skipped",
                "output_name": "document_ANON.txt",
                "text_extraction": "ocr_word_coordinates",
                "redaction_count": 0,
                "counters": {},
                "true_redaction": False,
            },
        )

        self.assertNotIn("Visual redaction fallback reason", report_text)

    def test_pdf_report_surfaces_visual_redaction_fallback_reason_for_scans(
        self,
    ) -> None:
        # A scan whose word-level OCR gave up (see OcrUnavailableError)
        # falls back to the old placeholder-text style instead of true
        # colored visual redaction - this field is what makes *why* that
        # happened diagnosable afterwards, rather than only guessed at.
        report_text = build_report_text(
            counters={"EMAIL": 1},
            input_extension=".pdf",
            output_extension=".txt",
            category_order=SUPPORTED_LABELS,
            pdf_redaction_result={
                "used": False,
                "status": "skipped",
                "output_name": "document_ANON.txt",
                "text_extraction": "ocr_fallback",
                "redaction_count": 0,
                "counters": {},
                "true_redaction": False,
                "visual_redaction_fallback_reason": "unavailable",
            },
        )

        self.assertIn("Visual redaction fallback reason: unavailable", report_text)

    def test_pdf_report_sanitizes_unrecognized_visual_redaction_fallback_reason(
        self,
    ) -> None:
        report_text = build_report_text(
            counters={"EMAIL": 1},
            input_extension=".pdf",
            output_extension=".txt",
            category_order=SUPPORTED_LABELS,
            pdf_redaction_result={
                "used": False,
                "status": "skipped",
                "output_name": "document_ANON.txt",
                "text_extraction": "ocr_fallback",
                "redaction_count": 0,
                "counters": {},
                "true_redaction": False,
                "visual_redaction_fallback_reason": "<script>not a real status</script>",
            },
        )

        self.assertIn("Visual redaction fallback reason: unknown", report_text)
        self.assertNotIn("<script>", report_text)

    def test_pdf_report_surfaces_visual_redaction_fallback_reason_as_exception_name(
        self,
    ) -> None:
        # The word-coordinate visual redaction step itself can raise for
        # reasons other than "OCR gave up" (see anonymizer.py) - the
        # exception's class name is recorded and must pass through
        # unsanitized (it can never contain document content or paths,
        # only ever a plain Python identifier like "ValueError").
        report_text = build_report_text(
            counters={"EMAIL": 1},
            input_extension=".pdf",
            output_extension=".txt",
            category_order=SUPPORTED_LABELS,
            pdf_redaction_result={
                "used": False,
                "status": "skipped",
                "output_name": "document_ANON.txt",
                "text_extraction": "text_layer",
                "redaction_count": 0,
                "counters": {},
                "true_redaction": False,
                "visual_redaction_fallback_reason": "ValueError",
            },
        )

        self.assertIn("Visual redaction fallback reason: ValueError", report_text)

    def test_batch_summary_marks_partial_pdf_redaction_with_safe_warning(self) -> None:
        summary_text = build_batch_summary_text(
            input_count=1,
            success_count=1,
            error_count=0,
            counters={"EMAIL": 1, "NER_ORG": 1},
            audit_status_counts={"ok": 1, "warning": 0, "not run": 0},
            results=[
                {
                    "input_name": "document.pdf",
                    "status": "success",
                    "output_name": "document_ANON.txt",
                    "report_name": "document_RAPORT.txt",
                    "checklist_name": "document_REVIEW_CHECKLIST.txt",
                    "audit_status": "ok",
                    "risk_level": "ok",
                    "pdf_redaction_output_created": True,
                    "pdf_redaction_output_name": "document_ANON.pdf",
                    "pdf_redaction_status": "completed_with_warnings",
                    "pdf_redaction_warning": (
                        "PDF redaction may be partial; some detected categories "
                        "were not PDF-redacted"
                    ),
                }
            ],
            pdf_redaction_status_counts={"completed_with_warnings": 1},
            batch_review_checklist_name="_BATCH_REVIEW_CHECKLIST.txt",
            category_order=SUPPORTED_LABELS,
            audit_category_order=AUDIT_CATEGORY_ORDER,
        )

        self.assertIn("Batch review checklist: _BATCH_REVIEW_CHECKLIST.txt", summary_text)
        self.assertIn("checklist: document_REVIEW_CHECKLIST.txt", summary_text)
        self.assertIn("* completed_with_warnings: 1", summary_text)
        self.assertIn("PDF redaction status: completed_with_warnings", summary_text)
        self.assertIn("PDF redaction warning: PDF redaction may be partial", summary_text)
        self.assertNotIn("Example Test Clinic", summary_text)

    def test_dispatcher_report_does_not_write_source_values(self) -> None:
        with workspace_temp_dir() as temp_dir:
            source_path = Path(temp_dir) / "document.txt"
            source_path.write_text(
                "Contact safe@example.test on 2026-06-01.",
                encoding="utf-8",
            )

            output_path, counters = anonymize_file(source_path)
            report_path = Path(temp_dir) / "_wewnetrzne" / "document_RAPORT.txt"
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
        self.assertIn("Risk level:", report_text)
        self.assertEqual(report_text.count("Manual review required:"), 1)


if __name__ == "__main__":
    unittest.main()
