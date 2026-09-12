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
    apply_output_cleanup_plan,
    build_output_cleanup_plan,
    classify_output_file,
    format_cleanup_plan_summary,
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

            from output_cleanup import OutputCleanupPlan

            plan = OutputCleanupPlan(
                removable_paths=(missing, present), kept_count=0, total_bytes=0
            )
            removed, failed = apply_output_cleanup_plan(plan)

            self.assertEqual((removed, failed), (1, 1))
            self.assertFalse(present.exists())


if __name__ == "__main__":
    unittest.main()
