"""anonymize_batch runs on a worker thread with a live processing screen
(2026-09-25 user report: with the local-LLM review a file takes a minute
or more, and the old synchronous run froze a static screen that looked
hung)."""

import queue
import sys
import threading
import time
import tkinter as tk
import unittest
from pathlib import Path
from unittest import mock

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

import gui_app
from gui_app import AnonymizerApp
from gui_helpers import format_processing_elapsed


class FormatProcessingElapsedTests(unittest.TestCase):
    def test_seconds_and_minutes(self) -> None:
        self.assertEqual(format_processing_elapsed(0), "Trwa już: 0 s")
        self.assertEqual(format_processing_elapsed(42), "Trwa już: 42 s")
        self.assertEqual(format_processing_elapsed(125), "Trwa już: 2 min 05 s")
        self.assertEqual(format_processing_elapsed(-3), "Trwa już: 0 s")


class BackgroundProcessingTests(unittest.TestCase):
    _root = None

    @classmethod
    def setUpClass(cls) -> None:
        cls._root = tk.Tk()
        cls._root.withdraw()

    @classmethod
    def tearDownClass(cls) -> None:
        cls._root.destroy()

    def _app(self) -> AnonymizerApp:
        app = AnonymizerApp.__new__(AnonymizerApp)
        app.root = self._root
        app.selected_paths = [Path("a.pdf")]
        app.output_dir = Path("out")
        app.page_ranges = {}
        app.page_counts = {}
        app.sensitive_terms_path = None
        app.use_ner = True
        app.llm_model_name = "model"
        app.use_llm_comparison_review = True
        app.use_llm_narrative_review = False
        app.pdf_output_label = gui_app.PDF_OUTPUT_LABEL_VISUAL_REDACTION
        app.active_categories = None
        app.strip_signatures = False
        app.active_screen = "start"
        app.processing_animation = None
        app.processing_animation_label = None
        app.processing_cancel_button = None
        app.progress_elapsed_label = None
        app._processing_active = False
        app._processing_after_id = None
        app._processing_cancel = threading.Event()
        app._processing_started_at = 0.0
        app._processing_events = queue.Queue()
        app.status_label = None

        def fake_show_processing_screen(document_count: int = 1) -> None:
            app.active_screen = "processing"

        app.show_processing_screen = fake_show_processing_screen
        app._on_anonymize_done = mock.Mock()
        return app

    def _pump_until(self, predicate, timeout: float = 5.0) -> None:
        deadline = time.monotonic() + timeout
        while not predicate():
            if time.monotonic() > deadline:
                self.fail("timed out waiting for the worker")
            self._root.update()
            time.sleep(0.01)

    def test_batch_runs_off_the_gui_thread_and_finishes_on_it(self) -> None:
        app = self._app()
        batch_thread = []
        release = threading.Event()

        def fake_batch(paths, out_dir, progress_callback=None, **kwargs):
            batch_thread.append(threading.current_thread())
            release.wait(5)
            return "RESULT"

        with mock.patch.object(gui_app, "anonymize_batch", side_effect=fake_batch), \
                mock.patch.object(gui_app, "dated_output_subdir", return_value=Path("out/d")):
            app.start_anonymize()
            # start_anonymize returned while the batch is still running -
            # the GUI thread is free and navigation is blocked.
            self.assertTrue(app._processing_active)
            self.assertTrue(app._processing_blocks_navigation())
            release.set()
            self._pump_until(lambda: app._on_anonymize_done.called)

        self.assertIsNot(batch_thread[0], threading.main_thread())
        app._on_anonymize_done.assert_called_once_with("RESULT", Path("out/d"))

    def test_second_start_while_running_is_ignored(self) -> None:
        app = self._app()
        app._processing_active = True
        with mock.patch.object(gui_app, "anonymize_batch") as batch:
            app.start_anonymize()
        batch.assert_not_called()

    def test_worker_failure_returns_to_start_screen(self) -> None:
        app = self._app()
        app.show_start_screen = mock.Mock()
        with mock.patch.object(gui_app, "anonymize_batch", side_effect=RuntimeError("x")), \
                mock.patch.object(gui_app, "dated_output_subdir", return_value=Path("out/d")):
            app.start_anonymize()
            self._pump_until(lambda: app.show_start_screen.called)
        self.assertFalse(app._processing_active)

    def test_progress_callback_is_marshalled_to_the_gui_thread(self) -> None:
        app = self._app()
        seen_threads = []
        app._update_processing = lambda i, t: seen_threads.append(
            threading.current_thread()
        )

        def fake_batch(paths, out_dir, progress_callback=None, **kwargs):
            progress_callback(1, 1, Path("a.pdf"))
            return "RESULT"

        with mock.patch.object(gui_app, "anonymize_batch", side_effect=fake_batch), \
                mock.patch.object(gui_app, "dated_output_subdir", return_value=Path("out/d")):
            app.start_anonymize()
            self._pump_until(lambda: app._on_anonymize_done.called)
        self.assertEqual(seen_threads, [threading.main_thread()])

    def test_tick_stops_once_processing_ends(self) -> None:
        app = self._app()
        app.active_screen = "processing"
        app._processing_active = False
        with mock.patch.object(self._root, "after") as after:
            app._tick_processing_screen()
        after.assert_not_called()


if __name__ == "__main__":
    unittest.main()
