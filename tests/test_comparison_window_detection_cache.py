"""Tests for ComparisonWindow's per-session detection cache (Etap 2 perf
fix - see docs/PROJECT_STATE.md). Exercises the plain-Python caching
methods directly against a bare instance (via __new__, bypassing Tk
widget construction entirely), since none of this logic touches the GUI.
"""

import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from gui_comparison_window import ComparisonWindow


def workspace_temp_dir():
    return tempfile.TemporaryDirectory(dir=PROJECT_ROOT / "tests")


def write_fitz_text_pdf(path: Path, lines: list[str]) -> None:
    import pymupdf as fitz

    document = fitz.open()
    page = document.new_page()
    y = 72
    for line in lines:
        page.insert_text((72, y), line, fontsize=12)
        y += 18
    document.save(path)
    document.close()


class FakeApp:
    def __init__(self, sensitive_terms_path=None, use_ner=False):
        self.sensitive_terms_path = sensitive_terms_path
        self.use_ner = use_ner


def make_bare_window(source_path: Path, app: FakeApp) -> ComparisonWindow:
    window = ComparisonWindow.__new__(ComparisonWindow)
    window.app = app
    window.source_path = source_path
    window._detection_cache = None
    window._detection_cache_key = None
    return window


class CachedDetectionTests(unittest.TestCase):
    def test_second_call_with_unchanged_settings_reuses_cached_result(self) -> None:
        with workspace_temp_dir() as temp_dir:
            source_path = Path(temp_dir) / "source.pdf"
            write_fitz_text_pdf(source_path, ["Contact tester@example.test today."])
            window = make_bare_window(source_path, FakeApp())

            first = window._cached_detection()
            second = window._cached_detection()

            self.assertIs(first, second)

    def test_use_ner_change_invalidates_cache(self) -> None:
        with workspace_temp_dir() as temp_dir:
            source_path = Path(temp_dir) / "source.pdf"
            write_fitz_text_pdf(source_path, ["Contact tester@example.test today."])
            app = FakeApp()
            window = make_bare_window(source_path, app)

            first = window._cached_detection()
            app.use_ner = True
            second = window._cached_detection()

            self.assertIsNot(first, second)

    def test_editing_dictionary_file_in_place_invalidates_cache(self) -> None:
        """Regression guard: an earlier version of this cache keyed only on
        the dictionary's *path*, so editing the file's contents in place
        (same path) while the window stayed open silently kept serving
        detection results from before the edit - a real behavior change
        from the pre-cache code, which always re-read the file from disk.
        """
        with workspace_temp_dir() as temp_dir:
            source_path = Path(temp_dir) / "source.pdf"
            write_fitz_text_pdf(source_path, ["Contact tester@example.test today."])
            dictionary_path = Path(temp_dir) / "dictionary.txt"
            dictionary_path.write_text("EMAIL: nobody@example.test\n", encoding="utf-8")

            app = FakeApp(sensitive_terms_path=dictionary_path)
            window = make_bare_window(source_path, app)

            first = window._cached_detection()
            # Same path, new content - a plausible mtime collision on a
            # fast filesystem is why the fingerprint also checks size.
            dictionary_path.write_text(
                "EMAIL: nobody@example.test\nADDED: something-new\n", encoding="utf-8"
            )
            second = window._cached_detection()

            self.assertIsNot(first, second)

    def test_missing_dictionary_path_does_not_crash(self) -> None:
        with workspace_temp_dir() as temp_dir:
            source_path = Path(temp_dir) / "source.pdf"
            write_fitz_text_pdf(source_path, ["Contact tester@example.test today."])
            app = FakeApp(sensitive_terms_path=Path(temp_dir) / "does_not_exist.txt")
            window = make_bare_window(source_path, app)

            word_pages, _spans = window._cached_detection()

            self.assertIsInstance(word_pages, list)


if __name__ == "__main__":
    unittest.main()
