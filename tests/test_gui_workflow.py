"""Tests for the Stage 5 single-file GUI workflow integration layer."""

import importlib
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from anonymizer import (
    PDF_OUTPUT_MODE_ORIGINAL_REDACTION,
    PDF_OUTPUT_MODE_REBUILT_REVIEW,
    PDF_OUTPUT_MODE_VISUAL,
    BatchResult,
    anonymize_file,
    anonymize_file_with_audit,
)
from environment_check import EnvironmentCheckItem
from gui import (
    LLM_MODELS_FOUND_HINT,
    LLM_NO_MODELS_HINT,
    PDF_OUTPUT_LABEL_ORIGINAL_SAFE,
    PDF_OUTPUT_LABEL_ORIGINAL_STRICT,
    PDF_OUTPUT_LABEL_REBUILT_REVIEW,
    PDF_OUTPUT_LABEL_VISUAL_REDACTION,
    PDF_OUTPUT_SHORT_LABELS,
    REVIEW_STATUS_APPROVED,
    REVIEW_STATUS_NEEDS_REVIEW,
    REVIEW_STATUS_REJECTED,
    ReviewItem,
    batch_error_label_pl,
    canvas_point_to_pdf_point,
    category_label_pl,
    clamp_zoom_level,
    ctk_widget_scaling_factor,
    default_output_directory,
    environment_status_lookup,
    file_type_badge,
    filter_supported_paths,
    find_rect_at_point,
    format_anonymize_readiness,
    format_approved_export_status,
    format_audit_result,
    format_batch_audit_result,
    format_batch_error_items,
    format_batch_status,
    format_dictionary_result,
    format_drop_result,
    format_llm_model_selector_state,
    format_processing_status,
    format_readiness_pl,
    format_recent_folder_timestamp,
    format_review_summary_line,
    format_selected_file_count,
    format_short_path,
    history_config_path,
    is_degenerate_drag_rect,
    load_recent_folders,
    load_seen_hints,
    mousewheel_scroll_units,
    normalize_drag_rect,
    open_path_with_default_app,
    parse_dropped_file_paths,
    parse_report_summary,
    pdf_output_mode_from_gui_label,
    pdf_page_zoom,
    pdf_redaction_scope_from_gui_label,
    record_recent_folder,
    remove_paths_by_indexes,
    restrict_review_items_to_batch,
    review_status_label_pl,
    risk_style_key,
    save_recent_folders,
    save_seen_hints,
    scroll_sync_units,
    truncate_filename_middle,
    ui_hints_config_path,
    zoom_link_glyph,
    zoom_link_tooltip_text,
    zoom_percent_label,
    zoom_step_from_scroll_event,
)
from llm_review import LLM_STATUS_AVAILABLE, LLM_STATUS_OLLAMA_NOT_FOUND


class FakeWheelEvent:
    def __init__(self, *, delta: int = 0, num: int | None = None) -> None:
        self.delta = delta
        self.num = num


def workspace_temp_dir():
    return tempfile.TemporaryDirectory(dir=PROJECT_ROOT / "tests")


class GuiWorkflowTests(unittest.TestCase):
    def test_gui_can_be_imported_as_package_module(self) -> None:
        module = importlib.import_module("src.gui")

        self.assertTrue(hasattr(module, "start_gui"))

    def test_mousewheel_scroll_units_handles_wheel_and_touchpad_deltas(self) -> None:
        self.assertEqual(mousewheel_scroll_units(FakeWheelEvent(delta=120)), -3)
        self.assertEqual(mousewheel_scroll_units(FakeWheelEvent(delta=-120)), 3)
        self.assertEqual(mousewheel_scroll_units(FakeWheelEvent(delta=1)), -3)
        self.assertEqual(mousewheel_scroll_units(FakeWheelEvent(delta=0)), 0)
        self.assertEqual(mousewheel_scroll_units(FakeWheelEvent(num=4)), -3)
        self.assertEqual(mousewheel_scroll_units(FakeWheelEvent(num=5)), 3)

    def test_pdf_output_label_defaults_to_visual_and_supports_auxiliary_modes(self) -> None:
        self.assertEqual(
            pdf_output_mode_from_gui_label(PDF_OUTPUT_LABEL_VISUAL_REDACTION),
            PDF_OUTPUT_MODE_VISUAL,
        )
        self.assertEqual(
            pdf_redaction_scope_from_gui_label(PDF_OUTPUT_LABEL_VISUAL_REDACTION),
            "safe",
        )
        self.assertEqual(
            pdf_output_mode_from_gui_label(PDF_OUTPUT_LABEL_REBUILT_REVIEW),
            PDF_OUTPUT_MODE_REBUILT_REVIEW,
        )
        self.assertEqual(
            pdf_redaction_scope_from_gui_label(PDF_OUTPUT_LABEL_REBUILT_REVIEW),
            "safe",
        )
        self.assertEqual(
            pdf_output_mode_from_gui_label(PDF_OUTPUT_LABEL_ORIGINAL_SAFE),
            PDF_OUTPUT_MODE_ORIGINAL_REDACTION,
        )
        self.assertEqual(
            pdf_redaction_scope_from_gui_label(PDF_OUTPUT_LABEL_ORIGINAL_SAFE),
            "safe",
        )
        self.assertEqual(
            pdf_output_mode_from_gui_label(PDF_OUTPUT_LABEL_ORIGINAL_STRICT),
            PDF_OUTPUT_MODE_ORIGINAL_REDACTION,
        )
        self.assertEqual(
            pdf_redaction_scope_from_gui_label(PDF_OUTPUT_LABEL_ORIGINAL_STRICT),
            "strict",
        )
        self.assertEqual(pdf_output_mode_from_gui_label("unknown"), PDF_OUTPUT_MODE_VISUAL)
        self.assertEqual(pdf_redaction_scope_from_gui_label("unknown"), "safe")

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

    def test_gui_formats_processing_status(self) -> None:
        self.assertEqual(
            format_processing_status(2, 3, Path("document.docx")),
            "Processing 2/3: document.docx\nPlease wait...",
        )

        with self.assertRaises(ValueError):
            format_processing_status(0, 3, Path("document.docx"))

    def test_gui_llm_model_selector_uses_installed_models(self) -> None:
        values, selected_model, hint = format_llm_model_selector_state(
            LLM_STATUS_AVAILABLE,
            ["gemma3:4b", "bielik:latest", "gemma3:4b"],
        )

        self.assertEqual(values, ["gemma3:4b", "bielik:latest"])
        self.assertEqual(selected_model, "gemma3:4b")
        self.assertEqual(hint, LLM_MODELS_FOUND_HINT)

    def test_gui_llm_model_selector_handles_missing_ollama(self) -> None:
        values, selected_model, hint = format_llm_model_selector_state(
            LLM_STATUS_OLLAMA_NOT_FOUND,
            [],
        )

        self.assertEqual(values, [])
        self.assertEqual(selected_model, "")
        self.assertEqual(hint, LLM_NO_MODELS_HINT)

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

    def test_gui_parses_dropped_file_paths_with_and_without_spaces(self) -> None:
        data = "{C:/My Docs/a file.pdf} C:/b.pdf {C:/c d/e.txt}"

        paths = parse_dropped_file_paths(data)

        self.assertEqual(
            paths,
            [
                Path("C:/My Docs/a file.pdf"),
                Path("C:/b.pdf"),
                Path("C:/c d/e.txt"),
            ],
        )

    def test_gui_parses_empty_drop_data_as_no_paths(self) -> None:
        self.assertEqual(parse_dropped_file_paths(""), [])

    def test_gui_filters_supported_and_unsupported_dropped_paths(self) -> None:
        paths = [
            Path("a.pdf"),
            Path("b.docx"),
            Path("c.exe"),
            Path("d.txt"),
        ]

        supported, unsupported = filter_supported_paths(paths)

        self.assertEqual(supported, [Path("a.pdf"), Path("b.docx"), Path("d.txt")])
        self.assertEqual(unsupported, [Path("c.exe")])

    def test_gui_formats_drop_result_variants(self) -> None:
        self.assertEqual(format_drop_result(1, 0), "Dodano 1 plik.")
        self.assertEqual(format_drop_result(2, 0), "Dodano 2 pliki.")
        self.assertEqual(format_drop_result(5, 0), "Dodano 5 plików.")
        self.assertIn("Pominięto", format_drop_result(2, 1))
        self.assertIn("Nie dodano plików", format_drop_result(0, 1))
        self.assertEqual(format_drop_result(0, 0), "Wybrane pliki były już na liście.")

    def test_gui_formats_polish_readiness_hint(self) -> None:
        self.assertEqual(
            format_readiness_pl(0, False),
            "Dodaj co najmniej jeden plik i wybierz folder wynikowy.",
        )
        self.assertEqual(
            format_readiness_pl(0, True), "Dodaj co najmniej jeden plik."
        )
        self.assertEqual(format_readiness_pl(3, False), "Wybierz folder wynikowy.")
        self.assertEqual(
            format_readiness_pl(1, True), "Gotowe do anonimizacji: 1 plik."
        )
        self.assertEqual(
            format_readiness_pl(3, True), "Gotowe do anonimizacji: 3 pliki."
        )
        self.assertEqual(
            format_readiness_pl(5, True), "Gotowe do anonimizacji: 5 plików."
        )

        with self.assertRaises(ValueError):
            format_readiness_pl(-1, False)

    def test_gui_formats_short_path_keeps_full_short_paths(self) -> None:
        self.assertEqual(format_short_path(Path("C:/Wyniki")), "C:\\Wyniki")

    def test_gui_formats_short_path_truncates_long_paths_to_readable_tail(
        self,
    ) -> None:
        long_path = Path(
            "C:/Users/example/AppData/Local/Temp/some-very-long-session-id"
            "/scratchpad/gui_shots/output"
        )

        result = format_short_path(long_path, max_length=48)

        self.assertLessEqual(len(result), 48)
        self.assertTrue(result.startswith("..."))
        self.assertTrue(result.endswith("output"))

    def test_gui_file_type_badge_recognizes_known_extensions(self) -> None:
        self.assertEqual(file_type_badge(Path("a.pdf")), "PDF")
        self.assertEqual(file_type_badge(Path("a.DOCX")), "DOCX")
        self.assertEqual(file_type_badge(Path("a.jpeg")), "JPG")
        self.assertEqual(file_type_badge(Path("a.xyz")), "XYZ")
        self.assertEqual(file_type_badge(Path("noext")), "FILE")

    def test_gui_risk_style_key_falls_back_to_unknown(self) -> None:
        self.assertEqual(risk_style_key("ok"), "ok")
        self.assertEqual(risk_style_key("warning"), "warning")
        self.assertEqual(risk_style_key("high_risk"), "high_risk")
        self.assertEqual(risk_style_key(None), "unknown")
        self.assertEqual(risk_style_key("something_else"), "unknown")

    def test_gui_formats_review_summary_line(self) -> None:
        self.assertEqual(format_review_summary_line(2, 4), "Zatwierdzono: 2/4")

    def test_gui_pdf_output_short_labels_cover_every_mode(self) -> None:
        for label in (
            PDF_OUTPUT_LABEL_VISUAL_REDACTION,
            PDF_OUTPUT_LABEL_REBUILT_REVIEW,
            PDF_OUTPUT_LABEL_ORIGINAL_SAFE,
            PDF_OUTPUT_LABEL_ORIGINAL_STRICT,
        ):
            self.assertIn(label, PDF_OUTPUT_SHORT_LABELS)
            self.assertTrue(PDF_OUTPUT_SHORT_LABELS[label])

    def test_gui_default_output_directory_is_under_documents(self) -> None:
        result = default_output_directory()

        self.assertEqual(result.parent.name, "Documents")
        self.assertEqual(result.name, "DocShield - wyniki")

    def test_gui_review_status_label_pl_covers_every_status(self) -> None:
        self.assertEqual(review_status_label_pl(REVIEW_STATUS_APPROVED), "zatwierdzony")
        self.assertEqual(review_status_label_pl(REVIEW_STATUS_REJECTED), "odrzucony")
        self.assertEqual(
            review_status_label_pl(REVIEW_STATUS_NEEDS_REVIEW), "wymaga przeglądu"
        )

    def test_gui_category_label_pl_falls_back_to_raw_label(self) -> None:
        self.assertEqual(category_label_pl("PESEL"), "PESEL")
        self.assertEqual(category_label_pl("EMAIL"), "E-mail")
        self.assertEqual(category_label_pl("UNKNOWN_FUTURE_LABEL"), "UNKNOWN_FUTURE_LABEL")

    def test_gui_parses_report_summary_categories_and_risk(self) -> None:
        report_text = (
            "Anonymization report\n\n"
            "Status: completed\n\n"
            "Detected categories:\n"
            "* PESEL: 0\n"
            "* EMAIL: 1\n"
            "* NIP: 2\n\n"
            "Dictionary:\n"
            "Dictionary used: no\n\n"
            "Post-anonymization audit:\n"
            "Status: warning\n"
            "Risk level: warning\n\n"
            "Manual review required: yes\n"
        )

        summary = parse_report_summary(report_text)

        self.assertEqual(summary["categories"], [("EMAIL", 1), ("NIP", 2)])
        self.assertEqual(summary["risk_level"], "warning")
        self.assertTrue(summary["manual_review_required"])

    def test_gui_parses_report_summary_with_no_detected_categories(self) -> None:
        report_text = (
            "Detected categories:\n"
            "* PESEL: 0\n"
            "* EMAIL: 0\n\n"
            "Risk level: ok\n"
            "Manual review required: yes\n"
        )

        summary = parse_report_summary(report_text)

        self.assertEqual(summary["categories"], [])
        self.assertEqual(summary["risk_level"], "ok")

    def test_restrict_review_items_to_batch_drops_leftover_old_files(self) -> None:
        review_items = [
            ReviewItem(output_name="new_ANON.txt"),
            ReviewItem(output_name="old_leftover_ANON.txt"),
        ]
        batch_results = [
            {"status": "success", "output_name": "new_ANON.txt"},
        ]

        result = restrict_review_items_to_batch(review_items, batch_results)

        self.assertEqual([item.output_name for item in result], ["new_ANON.txt"])

    def test_restrict_review_items_to_batch_ignores_failed_results(self) -> None:
        review_items = [
            ReviewItem(output_name="ok_ANON.txt"),
            ReviewItem(output_name="unrelated_old_ANON.txt"),
        ]
        batch_results = [
            {"status": "success", "output_name": "ok_ANON.txt"},
            {"status": "error", "output_name": "unrelated_old_ANON.txt"},
        ]

        result = restrict_review_items_to_batch(review_items, batch_results)

        self.assertEqual([item.output_name for item in result], ["ok_ANON.txt"])

    def test_restrict_review_items_to_batch_with_empty_batch_keeps_nothing(self) -> None:
        review_items = [ReviewItem(output_name="a_ANON.txt")]

        result = restrict_review_items_to_batch(review_items, [])

        self.assertEqual(result, [])

    def test_gui_history_config_path_is_under_home_dot_folder(self) -> None:
        result = history_config_path()

        self.assertEqual(result.parent.name, ".anonimizer")
        self.assertEqual(result.name, "recent_folders.json")

    def test_gui_load_recent_folders_missing_file_returns_empty(self) -> None:
        with workspace_temp_dir() as temp_dir:
            missing_path = Path(temp_dir) / "does_not_exist.json"

            self.assertEqual(load_recent_folders(missing_path), [])

    def test_gui_load_recent_folders_ignores_corrupt_file(self) -> None:
        with workspace_temp_dir() as temp_dir:
            bad_path = Path(temp_dir) / "recent_folders.json"
            bad_path.write_text("not valid json {{{", encoding="utf-8")

            self.assertEqual(load_recent_folders(bad_path), [])

    def test_gui_save_and_load_recent_folders_round_trips(self) -> None:
        with workspace_temp_dir() as temp_dir:
            config_path = Path(temp_dir) / "nested" / "recent_folders.json"
            entries = [{"path": "C:/Wyniki", "last_used": "2026-09-08T10:00:00+00:00"}]

            save_recent_folders(config_path, entries)
            loaded = load_recent_folders(config_path)

            self.assertEqual(loaded, entries)

    def test_gui_record_recent_folder_adds_new_entry_to_front(self) -> None:
        entries = [{"path": "C:/Old", "last_used": "2026-09-01T10:00:00+00:00"}]

        updated = record_recent_folder(
            entries, Path("C:/New"), "2026-09-08T10:00:00+00:00"
        )

        self.assertEqual(updated[0]["path"], "C:\\New")
        self.assertEqual(updated[1]["path"], "C:/Old")

    def test_gui_record_recent_folder_moves_existing_entry_to_front(self) -> None:
        entries = [
            {"path": "C:\\A", "last_used": "2026-09-01T10:00:00+00:00"},
            {"path": "C:\\B", "last_used": "2026-09-02T10:00:00+00:00"},
        ]

        updated = record_recent_folder(
            entries, Path("C:\\B"), "2026-09-08T10:00:00+00:00"
        )

        self.assertEqual(len(updated), 2)
        self.assertEqual(updated[0]["path"], "C:\\B")
        self.assertEqual(updated[0]["last_used"], "2026-09-08T10:00:00+00:00")

    def test_gui_record_recent_folder_caps_list_length(self) -> None:
        entries = [
            {"path": f"C:\\folder{i}", "last_used": "2026-09-01T10:00:00+00:00"}
            for i in range(20)
        ]

        updated = record_recent_folder(
            entries, Path("C:\\newest"), "2026-09-08T10:00:00+00:00"
        )

        self.assertEqual(len(updated), 15)
        self.assertEqual(updated[0]["path"], "C:\\newest")

    def test_truncate_filename_middle_leaves_short_names_alone(self) -> None:
        self.assertEqual(truncate_filename_middle("short.pdf"), "short.pdf")

    def test_truncate_filename_middle_elides_the_middle_not_the_end(self) -> None:
        result = truncate_filename_middle(
            "2_faktura_vat_FIKCYJNA_ANON_4.txt", max_length=26
        )

        self.assertLessEqual(len(result), 26)
        self.assertIn("…", result)
        # Keeps the start (most distinguishing between similar files)
        # and the tail (extension/markers), not just a plain end-cut.
        self.assertTrue(result.startswith("2_faktura_vat"))
        self.assertTrue(result.endswith(".txt"))

    def test_truncate_filename_middle_guards_against_tiny_budgets(self) -> None:
        # max_length too small to sensibly truncate - return as-is rather
        # than producing a nonsensical near-empty result.
        self.assertEqual(
            truncate_filename_middle("a_very_long_filename.pdf", max_length=3),
            "a_very_long_filename.pdf",
        )

    def test_gui_formats_recent_folder_timestamp(self) -> None:
        result = format_recent_folder_timestamp("2026-09-08T14:32:00+00:00")

        self.assertEqual(result, "08.09.2026, 14:32")

    def test_gui_formats_invalid_recent_folder_timestamp(self) -> None:
        self.assertEqual(format_recent_folder_timestamp("not-a-date"), "nieznana data")

    def test_pdf_page_zoom_scales_page_width_to_target(self) -> None:
        self.assertEqual(pdf_page_zoom(200, 400), 2.0)

    def test_pdf_page_zoom_guards_against_zero_width(self) -> None:
        self.assertEqual(pdf_page_zoom(0, 460), 460.0)

    def test_canvas_point_to_pdf_point_divides_by_zoom(self) -> None:
        self.assertEqual(canvas_point_to_pdf_point(100, 50, 2.0), (50.0, 25.0))

    def test_canvas_point_to_pdf_point_guards_against_zero_zoom(self) -> None:
        self.assertEqual(canvas_point_to_pdf_point(10, 10, 0), (10.0, 10.0))

    def test_ctk_widget_scaling_factor_returns_tracker_value(self) -> None:
        with patch("gui.ctk.ScalingTracker.get_widget_scaling", return_value=1.25):
            self.assertEqual(ctk_widget_scaling_factor(object()), 1.25)

    def test_ctk_widget_scaling_factor_falls_back_to_one_on_error(self) -> None:
        # Cosmetic-only lookup: any failure (e.g. a widget the tracker
        # never registered) must never crash the preview.
        with patch(
            "gui.ctk.ScalingTracker.get_widget_scaling", side_effect=KeyError("boom")
        ):
            self.assertEqual(ctk_widget_scaling_factor(object()), 1.0)

    def test_normalize_drag_rect_handles_any_drag_direction(self) -> None:
        self.assertEqual(normalize_drag_rect(50, 60, 10, 20), (10, 20, 50, 60))
        self.assertEqual(normalize_drag_rect(10, 20, 50, 60), (10, 20, 50, 60))

    def test_is_degenerate_drag_rect_flags_tiny_selections(self) -> None:
        self.assertTrue(is_degenerate_drag_rect(0, 0, 2, 2))
        self.assertFalse(is_degenerate_drag_rect(0, 0, 10, 10))

    def test_find_rect_at_point_matches_containing_rect_on_same_page(self) -> None:
        rects = [
            {"page": 1, "label": "EMAIL", "x0": 0, "y0": 0, "x1": 50, "y1": 20},
            {"page": 2, "label": "PESEL", "x0": 0, "y0": 0, "x1": 50, "y1": 20},
        ]

        self.assertEqual(find_rect_at_point(rects, 1, 25, 10), rects[0])
        self.assertIsNone(find_rect_at_point(rects, 1, 25, 100))
        self.assertIsNone(find_rect_at_point(rects, 3, 25, 10))

    def test_find_rect_at_point_prefers_most_recently_added_overlap(self) -> None:
        rects = [
            {"page": 1, "label": "EMAIL", "x0": 0, "y0": 0, "x1": 50, "y1": 20},
            {"page": 1, "label": "RECZNE", "x0": 10, "y0": 5, "x1": 40, "y1": 15},
        ]

        self.assertEqual(find_rect_at_point(rects, 1, 20, 10), rects[1])

    def test_clamp_zoom_level_keeps_values_within_range(self) -> None:
        self.assertEqual(clamp_zoom_level(1.0), 1.0)
        self.assertEqual(clamp_zoom_level(0.1), 0.5)
        self.assertEqual(clamp_zoom_level(9.0), 3.0)

    def test_clamp_zoom_level_rounds_to_two_decimals(self) -> None:
        self.assertEqual(clamp_zoom_level(1.234567), 1.23)

    def test_zoom_percent_label_formats_whole_percent(self) -> None:
        self.assertEqual(zoom_percent_label(1.0), "100%")
        self.assertEqual(zoom_percent_label(1.2), "120%")
        self.assertEqual(zoom_percent_label(0.5), "50%")

    def test_zoom_step_from_scroll_event_handles_windows_delta(self) -> None:
        self.assertEqual(zoom_step_from_scroll_event(FakeWheelEvent(delta=120)), 1)
        self.assertEqual(zoom_step_from_scroll_event(FakeWheelEvent(delta=-120)), -1)
        self.assertEqual(zoom_step_from_scroll_event(FakeWheelEvent(delta=0)), 0)

    def test_zoom_step_from_scroll_event_handles_x11_button_numbers(self) -> None:
        self.assertEqual(zoom_step_from_scroll_event(FakeWheelEvent(num=4)), 1)
        self.assertEqual(zoom_step_from_scroll_event(FakeWheelEvent(num=5)), -1)

    def test_scroll_sync_units_matches_ctk_scrollable_frame_windows_formula(self) -> None:
        # -int(delta / 6), exactly CTkScrollableFrame's own internal
        # formula on Windows - unit parity is the whole point, otherwise
        # a linked pane would gradually drift out of sync with the one
        # the cursor is actually over.
        self.assertEqual(scroll_sync_units(FakeWheelEvent(delta=120)), -20)
        self.assertEqual(scroll_sync_units(FakeWheelEvent(delta=-120)), 20)
        self.assertEqual(scroll_sync_units(FakeWheelEvent(delta=0)), 0)

    def test_scroll_sync_units_handles_x11_button_numbers(self) -> None:
        self.assertEqual(scroll_sync_units(FakeWheelEvent(num=4)), -1)
        self.assertEqual(scroll_sync_units(FakeWheelEvent(num=5)), 1)

    def test_scroll_sync_units_handles_macos_delta(self) -> None:
        with patch("gui.sys.platform", "darwin"):
            self.assertEqual(scroll_sync_units(FakeWheelEvent(delta=3)), -3)
            self.assertEqual(scroll_sync_units(FakeWheelEvent(delta=-3)), 3)

    def test_zoom_link_glyph_shows_closed_padlock_when_linked(self) -> None:
        self.assertEqual(zoom_link_glyph(True), "🔒")
        self.assertEqual(zoom_link_glyph(False), "🔓")

    def test_zoom_link_tooltip_text_describes_current_state_and_next_action(self) -> None:
        linked_text = zoom_link_tooltip_text(True)
        unlinked_text = zoom_link_tooltip_text(False)
        self.assertIn("połączone", linked_text)
        self.assertIn("osobno", linked_text)
        self.assertIn("niezależne", unlinked_text)
        self.assertIn("połączyć", unlinked_text)

    def test_ui_hints_config_path_is_under_home_dot_folder(self) -> None:
        path = ui_hints_config_path()
        self.assertEqual(path.parent.name, ".anonimizer")
        self.assertEqual(path.name, "ui_hints_seen.json")

    def test_load_seen_hints_missing_file_returns_empty_set(self) -> None:
        with workspace_temp_dir() as temp_dir:
            missing = Path(temp_dir) / "does_not_exist.json"
            self.assertEqual(load_seen_hints(missing), set())

    def test_load_seen_hints_ignores_corrupt_file(self) -> None:
        with workspace_temp_dir() as temp_dir:
            path = Path(temp_dir) / "corrupt.json"
            path.write_text("{not valid json", encoding="utf-8")
            self.assertEqual(load_seen_hints(path), set())

    def test_save_and_load_seen_hints_round_trips(self) -> None:
        with workspace_temp_dir() as temp_dir:
            path = Path(temp_dir) / "hints" / "seen.json"
            save_seen_hints(path, {"zoom_link_toggle", "another_hint"})

            self.assertEqual(load_seen_hints(path), {"zoom_link_toggle", "another_hint"})


    def test_batch_error_label_pl_translates_known_codes(self) -> None:
        self.assertIn(
            "OCR", batch_error_label_pl("OCR unavailable for image-based input")
        )
        self.assertIn("Tesseract", batch_error_label_pl("OCR unavailable for image-based input"))

    def test_batch_error_label_pl_falls_back_to_raw_code(self) -> None:
        self.assertEqual(batch_error_label_pl("something new"), "something new")

    def test_format_batch_error_items_lists_only_failed_files(self) -> None:
        batch_result = BatchResult(
            summary_path=Path("output") / "_wewnetrzne" / "_BATCH_SUMMARY.txt",
            input_count=2,
            success_count=1,
            error_count=1,
            counters={},
            audit_status_counts={},
            risk_level_counts={},
            audit_category_counters={},
            results=[
                {"input_name": "ok.txt", "status": "success"},
                {
                    "input_name": "scan.pdf",
                    "status": "error",
                    "error": "OCR unavailable for image-based input",
                },
            ],
        )

        items = format_batch_error_items(batch_result)

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0][0], "scan.pdf")
        self.assertIn("OCR", items[0][1])

    def test_format_batch_error_items_empty_when_all_succeeded(self) -> None:
        batch_result = BatchResult(
            summary_path=Path("output") / "_wewnetrzne" / "_BATCH_SUMMARY.txt",
            input_count=1,
            success_count=1,
            error_count=0,
            counters={},
            audit_status_counts={},
            risk_level_counts={},
            audit_category_counters={},
            results=[{"input_name": "ok.txt", "status": "success"}],
        )

        self.assertEqual(format_batch_error_items(batch_result), [])

    def test_environment_status_lookup_maps_item_to_ok(self) -> None:
        items = [
            EnvironmentCheckItem("ner", True, "NER", "Dostępne."),
            EnvironmentCheckItem("ocr", False, "OCR", "Brak."),
        ]

        self.assertEqual(
            environment_status_lookup(items), {"ner": True, "ocr": False}
        )

    def test_environment_status_lookup_none_is_empty_not_unavailable(self) -> None:
        # None means "not checked yet", distinct from a known-missing item -
        # an empty dict lets callers tell the two apart via .get(key) is None.
        self.assertEqual(environment_status_lookup(None), {})


if __name__ == "__main__":
    unittest.main()
