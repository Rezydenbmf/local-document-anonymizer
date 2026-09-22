"""Tests for removing superseded output generations from one folder.

The risky part of this feature is not deleting the right files, it is
never deleting the wrong ones: people routinely point the output at the
folder their source documents live in, so anything outside this app's own
naming scheme has to be invisible to the cleanup.
"""

import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from file_writers import INTERNAL_ARTIFACTS_DIRNAME
from output_cleanup import (
    OutputCleanupPlan,
    apply_output_cleanup_plan,
    build_history_cleanup_plan,
    build_output_cleanup_plan,
    classify_output_file,
    folder_has_any_tracked_output,
    format_cleanup_plan_summary,
    format_file_size,
    format_history_cleanup_summary,
)


def workspace_temp_dir():
    return tempfile.TemporaryDirectory(dir=PROJECT_ROOT / "tests")


class ClassifyOutputFileTests(unittest.TestCase):
    def test_recognizes_each_output_family_and_generation(self) -> None:
        self.assertEqual(classify_output_file("umowa_ANON.txt"), ("umowa|anon_txt", 1))
        self.assertEqual(classify_output_file("umowa_ANON_2.txt"), ("umowa|anon_txt", 2))
        self.assertEqual(
            classify_output_file("umowa_ANON_VISUAL_3.pdf"), ("umowa|visual", 3)
        )
        self.assertEqual(
            classify_output_file("umowa_ANON_REVIEW.pdf"), ("umowa|review", 1)
        )
        self.assertEqual(
            classify_output_file("umowa_ORIGINAL_REDACTED_2.pdf"), ("umowa|original_redacted", 2)
        )
        self.assertEqual(classify_output_file("umowa_RAPORT_4.txt"), ("umowa|report", 4))
        self.assertEqual(
            classify_output_file("umowa_REVIEW_CHECKLIST.txt"), ("umowa|checklist", 1)
        )
        self.assertEqual(
            classify_output_file("umowa_ANON_VISUAL_MANUAL_EDITS.json"),
            ("umowa_ANON_VISUAL|manual_edits", 1),
        )

    def test_batch_artifacts_share_one_group(self) -> None:
        self.assertEqual(classify_output_file("_BATCH_SUMMARY.txt"), ("batch_summary", 1))
        self.assertEqual(
            classify_output_file("_BATCH_REVIEW_CHECKLIST_3.txt"), ("batch_checklist", 3)
        )

    def test_ignores_anything_this_app_did_not_write(self) -> None:
        for name in (
            "umowa.pdf",
            "umowa.docx",
            "notatki.txt",
            "zdjecie.png",
            "umowa_ANON.pdf",
            "ANON.txt",
            "raport_firmowy.txt",
            "_BATCH_NOTES.txt",
        ):
            self.assertIsNone(classify_output_file(name), name)


class BuildOutputCleanupPlanTests(unittest.TestCase):
    def _write(self, folder: Path, name: str, content: str = "x") -> Path:
        path = folder / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def test_keeps_only_the_newest_generation_of_each_document(self) -> None:
        with workspace_temp_dir() as temp_dir:
            folder = Path(temp_dir)
            for name in (
                "umowa_ANON.txt",
                "umowa_ANON_2.txt",
                "umowa_ANON_3.txt",
                "umowa_ANON_VISUAL.pdf",
                "umowa_ANON_VISUAL_2.pdf",
                "umowa_ANON_VISUAL_3.pdf",
                "faktura_ANON.txt",
            ):
                self._write(folder, name)

            plan = build_output_cleanup_plan(folder)
            removable = {path.name for path in plan.removable_paths}

            self.assertEqual(
                removable,
                {
                    "umowa_ANON.txt",
                    "umowa_ANON_2.txt",
                    "umowa_ANON_VISUAL.pdf",
                    "umowa_ANON_VISUAL_2.pdf",
                },
            )
            # newest of each document, and the single-generation faktura
            self.assertEqual(plan.kept_count, 3)

    def test_never_lists_source_documents_or_unrelated_files(self) -> None:
        # The output folder is very often the folder the sources live in.
        with workspace_temp_dir() as temp_dir:
            folder = Path(temp_dir)
            originals = [
                self._write(folder, "umowa.pdf"),
                self._write(folder, "prywatne_notatki.txt"),
                self._write(folder, "zdjecie.png"),
            ]
            self._write(folder, "umowa_ANON.txt")
            self._write(folder, "umowa_ANON_2.txt")

            plan = build_output_cleanup_plan(folder)

            self.assertEqual(
                [path.name for path in plan.removable_paths], ["umowa_ANON.txt"]
            )
            for original in originals:
                self.assertTrue(original.exists())

    def test_covers_the_internal_artifacts_subfolder(self) -> None:
        with workspace_temp_dir() as temp_dir:
            folder = Path(temp_dir)
            internal = folder / INTERNAL_ARTIFACTS_DIRNAME
            self._write(internal, "umowa_RAPORT.txt")
            self._write(internal, "umowa_RAPORT_2.txt")
            self._write(internal, "_BATCH_SUMMARY.txt")
            self._write(internal, "_BATCH_SUMMARY_2.txt")

            plan = build_output_cleanup_plan(folder)

            self.assertEqual(
                {path.name for path in plan.removable_paths},
                {"umowa_RAPORT.txt", "_BATCH_SUMMARY.txt"},
            )

    def test_empty_plan_for_a_folder_with_one_generation(self) -> None:
        with workspace_temp_dir() as temp_dir:
            folder = Path(temp_dir)
            self._write(folder, "umowa_ANON.txt")
            self._write(folder, "umowa_ANON_VISUAL.pdf")

            plan = build_output_cleanup_plan(folder)

            self.assertTrue(plan.is_empty)
            self.assertIn("Brak starszych wersji", format_cleanup_plan_summary(plan))

    def test_missing_folder_yields_an_empty_plan(self) -> None:
        with workspace_temp_dir() as temp_dir:
            plan = build_output_cleanup_plan(Path(temp_dir) / "nie_istnieje")
            self.assertTrue(plan.is_empty)


class ApplyOutputCleanupPlanTests(unittest.TestCase):
    def test_removes_planned_files_only(self) -> None:
        with workspace_temp_dir() as temp_dir:
            folder = Path(temp_dir)
            (folder / "umowa.pdf").write_text("original", encoding="utf-8")
            (folder / "umowa_ANON.txt").write_text("old", encoding="utf-8")
            (folder / "umowa_ANON_2.txt").write_text("new", encoding="utf-8")

            plan = build_output_cleanup_plan(folder)
            removed, failed = apply_output_cleanup_plan(plan)

            self.assertEqual((removed, failed), (1, 0))
            self.assertFalse((folder / "umowa_ANON.txt").exists())
            self.assertTrue((folder / "umowa_ANON_2.txt").exists())
            self.assertTrue((folder / "umowa.pdf").exists())

    def test_counts_failures_without_giving_up_on_the_rest(self) -> None:
        with workspace_temp_dir() as temp_dir:
            folder = Path(temp_dir)
            present = folder / "umowa_ANON.txt"
            present.write_text("old", encoding="utf-8")
            missing = folder / "znikniety_ANON.txt"

            plan = OutputCleanupPlan(
                removable_paths=(missing, present), kept_count=0, total_bytes=0
            )
            removed, failed = apply_output_cleanup_plan(plan)

            self.assertEqual((removed, failed), (1, 1))
            self.assertFalse(present.exists())


class BuildHistoryCleanupPlanTests(unittest.TestCase):
    """The "Wyczyść historię" sweep: one button across every folder in the
    user's history, working files always removable, final results only
    removable on explicit opt-in. Direct feedback drove both halves of
    that split - "po co nam te stare pliki, user chce mieć zanonimizowany
    i oryginał... wszystkie te txt/checklisty nie potrzebuje" for the
    default, and "opcjonalnie można je też usunąć" for the opt-in.

    One filesystem walk returns both plans (working_plan, final_plan) -
    deliberately not two separate calls the caller diffs against each
    other. A code review caught that the two-call version opened a race
    window (the folder could change between calls) and forced total_bytes
    for the final-only set to be computed by subtracting two independent
    scans - which could go visibly wrong (even negative) if that race
    was hit, right before an irreversible deletion. These tests check
    the single-walk version's output directly.
    """

    def _write(self, folder: Path, name: str, content: str = "x") -> Path:
        path = folder / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def test_working_files_and_final_results_split_into_separate_plans(self) -> None:
        with workspace_temp_dir() as temp_dir:
            folder = Path(temp_dir)
            self._write(folder, "umowa_ANON.txt")
            self._write(folder, "umowa_ANON_VISUAL.pdf")
            self._write(folder / "_wewnetrzne", "umowa_RAPORT.txt")
            self._write(folder / "_wewnetrzne", "umowa_REVIEW_CHECKLIST.txt")
            self._write(folder, "_BATCH_SUMMARY.txt")

            working_plan, final_plan = build_history_cleanup_plan([folder])

            self.assertEqual(
                {path.name for path in working_plan.removable_paths},
                {"umowa_RAPORT.txt", "umowa_REVIEW_CHECKLIST.txt", "_BATCH_SUMMARY.txt"},
            )
            self.assertEqual(
                {path.name for path in final_plan.removable_paths},
                {"umowa_ANON.txt", "umowa_ANON_VISUAL.pdf"},
            )
            # working_plan's kept_count reflects the final files it leaves
            # untouched; final_plan has nothing else left to report kept.
            self.assertEqual(working_plan.kept_count, 2)
            self.assertEqual(final_plan.kept_count, 0)

    def test_final_plan_total_bytes_is_summed_directly_not_by_subtraction(self) -> None:
        """The exact bug a code review caught in the two-call version:
        each plan's total_bytes must come from summing its own paths,
        never derived by subtracting one plan's total from another's."""
        with workspace_temp_dir() as temp_dir:
            folder = Path(temp_dir)
            self._write(folder, "umowa_ANON.txt", content="12345")  # 5 bytes
            self._write(folder / "_wewnetrzne", "umowa_RAPORT.txt", content="1234567890")  # 10 bytes

            working_plan, final_plan = build_history_cleanup_plan([folder])

            self.assertEqual(working_plan.total_bytes, 10)
            self.assertEqual(final_plan.total_bytes, 5)

    def test_manual_edits_sidecar_counts_as_a_final_result_not_junk(self) -> None:
        """Deliberately not "obviously a working file" even though it
        looks internal: deleting it would silently break the ability to
        reopen and continue editing a document's magic-pen selections
        later - a real workflow the 30-day reminder default exists to
        respect in the first place."""
        with workspace_temp_dir() as temp_dir:
            folder = Path(temp_dir)
            self._write(folder, "umowa_ANON_VISUAL.pdf")
            self._write(folder / "_wewnetrzne", "umowa_ANON_VISUAL_MANUAL_EDITS.json")

            working_plan, final_plan = build_history_cleanup_plan([folder])

            self.assertTrue(working_plan.is_empty)
            self.assertEqual(
                {path.name for path in final_plan.removable_paths},
                {"umowa_ANON_VISUAL.pdf", "umowa_ANON_VISUAL_MANUAL_EDITS.json"},
            )

    def test_sweeps_multiple_folders_in_one_pair_of_plans(self) -> None:
        with workspace_temp_dir() as outer:
            folder_a = Path(outer) / "a"
            folder_b = Path(outer) / "b"
            self._write(folder_a, "faktura_RAPORT.txt")
            self._write(folder_b, "umowa_RAPORT.txt")

            working_plan, _final_plan = build_history_cleanup_plan([folder_a, folder_b])

            self.assertEqual(
                {path.name for path in working_plan.removable_paths},
                {"faktura_RAPORT.txt", "umowa_RAPORT.txt"},
            )

    def test_a_missing_folder_in_the_list_is_skipped_not_fatal(self) -> None:
        with workspace_temp_dir() as outer:
            real_folder = Path(outer) / "real"
            missing_folder = Path(outer) / "does_not_exist"
            self._write(real_folder, "umowa_RAPORT.txt")

            working_plan, _final_plan = build_history_cleanup_plan(
                [real_folder, missing_folder]
            )

            self.assertEqual(
                {path.name for path in working_plan.removable_paths}, {"umowa_RAPORT.txt"}
            )

    def test_never_lists_source_documents_or_unrelated_files(self) -> None:
        with workspace_temp_dir() as temp_dir:
            folder = Path(temp_dir)
            original = self._write(folder, "umowa.pdf")
            self._write(folder, "umowa_RAPORT.txt")

            working_plan, final_plan = build_history_cleanup_plan([folder])

            self.assertEqual(
                [path.name for path in working_plan.removable_paths], ["umowa_RAPORT.txt"]
            )
            self.assertTrue(final_plan.is_empty)
            self.assertTrue(original.exists())

    def test_recurses_into_dated_output_subfolders(self) -> None:
        """A run made after the dated-output-folder redesign (2026-09-22)
        writes everything one level down, in its own "DD.MM.RRRR" folder
        - PDFs directly in it, TXT/DOCX in its own "txt" child, reports/
        checklists in its own "_wewnetrzne" child (see
        file_writers.dated_output_subdir). "Wyczyść historię" must still
        find and offer to remove all of it, not just whatever happens to
        sit in the flat root."""
        with workspace_temp_dir() as temp_dir:
            folder = Path(temp_dir)
            dated = folder / "22.09.2026"
            self._write(dated, "umowa_ANON_VISUAL.pdf")
            self._write(dated / "txt", "umowa_ANON.txt")
            self._write(dated / "_wewnetrzne", "umowa_RAPORT.txt")

            working_plan, final_plan = build_history_cleanup_plan([folder])

            self.assertEqual(
                {path.name for path in working_plan.removable_paths},
                {"umowa_RAPORT.txt"},
            )
            self.assertEqual(
                {path.name for path in final_plan.removable_paths},
                {"umowa_ANON_VISUAL.pdf", "umowa_ANON.txt"},
            )

    def test_old_flat_folder_without_any_dated_subfolder_is_unaffected(self) -> None:
        """Regression guard: a folder from before the redesign, with no
        "DD.MM.RRRR" subfolder at all, must behave exactly as it always
        has - the new recursion finds nothing extra to add."""
        with workspace_temp_dir() as temp_dir:
            folder = Path(temp_dir)
            self._write(folder, "umowa_ANON.txt")
            self._write(folder, "umowa_ANON_VISUAL.pdf")
            self._write(folder / "_wewnetrzne", "umowa_RAPORT.txt")

            working_plan, final_plan = build_history_cleanup_plan([folder])

            self.assertEqual(
                {path.name for path in working_plan.removable_paths},
                {"umowa_RAPORT.txt"},
            )
            self.assertEqual(
                {path.name for path in final_plan.removable_paths},
                {"umowa_ANON.txt", "umowa_ANON_VISUAL.pdf"},
            )

    def test_a_folder_that_merely_looks_dated_but_is_not_named_that_way_is_ignored(
        self,
    ) -> None:
        """Only an exact "DD.MM.RRRR" folder name is recursed into -
        anything else (a source document's own subfolder, a folder named
        "2026-09-22" in a different format, ...) is left alone, matching
        the deliberately narrow, non-general-recursive design."""
        with workspace_temp_dir() as temp_dir:
            folder = Path(temp_dir)
            self._write(folder / "2026-09-22", "umowa_ANON.txt")
            self._write(folder / "podfolder_klienta", "notatki_RAPORT.txt")

            working_plan, final_plan = build_history_cleanup_plan([folder])

            self.assertTrue(working_plan.is_empty)
            self.assertTrue(final_plan.is_empty)


class FormatHistoryCleanupSummaryTests(unittest.TestCase):
    def test_empty_plan(self) -> None:
        plan = OutputCleanupPlan(removable_paths=(), kept_count=3, total_bytes=0)
        summary = format_history_cleanup_summary(plan, include_final_outputs=False)
        self.assertIn("Brak plików", summary)

    def test_working_only_summary_mentions_final_results_stay(self) -> None:
        plan = OutputCleanupPlan(
            removable_paths=(Path("a_RAPORT.txt"),), kept_count=2, total_bytes=2048
        )
        summary = format_history_cleanup_summary(plan, include_final_outputs=False)
        self.assertIn("plików roboczych", summary)
        self.assertIn("Finalne wyniki", summary)

    def test_include_final_outputs_summary_says_so(self) -> None:
        plan = OutputCleanupPlan(
            removable_paths=(Path("a_ANON.txt"),), kept_count=0, total_bytes=1024
        )
        summary = format_history_cleanup_summary(plan, include_final_outputs=True)
        self.assertIn("finalnymi wynikami", summary)


class FolderHasAnyTrackedOutputTests(unittest.TestCase):
    """Used by gui_app.py's "Wyczyść historię" to decide whether a
    folder can be forgotten from the history list after a cleanup - a
    folder still holding anything this app's own naming scheme
    recognizes must never be forgotten, even if some other cleanup step
    already ran."""

    def test_true_when_a_tracked_output_file_is_present(self) -> None:
        with workspace_temp_dir() as temp_dir:
            folder = Path(temp_dir)
            (folder / "umowa_ANON.txt").write_text("x", encoding="utf-8")
            self.assertTrue(folder_has_any_tracked_output(folder))

    def test_false_for_an_empty_folder(self) -> None:
        with workspace_temp_dir() as temp_dir:
            self.assertFalse(folder_has_any_tracked_output(temp_dir))

    def test_false_when_only_unrecognized_files_are_present(self) -> None:
        with workspace_temp_dir() as temp_dir:
            folder = Path(temp_dir)
            (folder / "zrodlo.pdf").write_text("x", encoding="utf-8")
            self.assertFalse(folder_has_any_tracked_output(folder))

    def test_true_for_a_tracked_file_inside_the_internal_subfolder(self) -> None:
        with workspace_temp_dir() as temp_dir:
            folder = Path(temp_dir)
            internal = folder / INTERNAL_ARTIFACTS_DIRNAME
            internal.mkdir()
            (internal / "umowa_RAPORT.txt").write_text("x", encoding="utf-8")
            self.assertTrue(folder_has_any_tracked_output(folder))

    def test_false_for_a_missing_folder(self) -> None:
        with workspace_temp_dir() as temp_dir:
            self.assertFalse(
                folder_has_any_tracked_output(Path(temp_dir) / "does_not_exist")
            )


class FormatFileSizeTests(unittest.TestCase):
    def test_small_sizes_in_kb_never_rounds_to_zero(self) -> None:
        self.assertEqual(format_file_size(1), "1 KB")
        self.assertEqual(format_file_size(2048), "2 KB")

    def test_larger_sizes_in_mb(self) -> None:
        self.assertEqual(format_file_size(5 * 1024 * 1024), "5.0 MB")


if __name__ == "__main__":
    unittest.main()
