"""The processing screen's ASCII animation (docshield_ascii_animation,
2026-09-25): the GUI-agnostic module itself, and how AnonymizerApp drives
it from anonymize_batch's worker-thread events - one file, several files,
a failure, "Anuluj", and closing the window mid-run."""

import queue
import sys
import tempfile
import threading
import time
import tkinter as tk
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

import gui_app
from docshield_ascii_animation import AnimationState, DocShieldAsciiAnimation
from gui_app import AnonymizerApp

# A file name that looks like real PII - it must never reach the animation.
PII_FILE_NAME = "Nowak_Anna_PESEL_90020212345.pdf"


class AsciiAnimationModuleTests(unittest.TestCase):
    def test_every_frame_has_the_same_fixed_width(self) -> None:
        animation = DocShieldAsciiAnimation(3)
        animation.start_document("doc-1")
        for step in range(40):
            lines = animation.render_frame(now=time.monotonic() + step * 0.1).split("\n")
            self.assertEqual({len(line) for line in lines}, {DocShieldAsciiAnimation.FRAME_WIDTH})

    def test_frame_counts_documents_and_shows_no_percentage(self) -> None:
        animation = DocShieldAsciiAnimation(3)
        animation.start_document("doc-1")
        animation.mark_current_completed()
        animation.advance_to_next("doc-2")
        frame = animation.render_frame()
        self.assertIn("Dokument 2 z 3", frame)
        self.assertNotIn("%", frame)

    def test_source_id_is_never_rendered(self) -> None:
        animation = DocShieldAsciiAnimation(1)
        animation.start_document(PII_FILE_NAME)
        self.assertNotIn("Nowak", animation.render_frame())
        self.assertEqual(animation.snapshot().source_id, PII_FILE_NAME)

    def test_completed_document_masks_all_demo_data(self) -> None:
        animation = DocShieldAsciiAnimation(1)
        animation.start_document()
        animation.mark_current_completed()
        frame = animation.render_frame()
        for fragment in ("JAN KOWALSKI", "82010112345", "501 234 567", "LESNA 14"):
            self.assertNotIn(fragment, frame)

    def test_request_cancel_changes_only_the_status_line(self) -> None:
        animation = DocShieldAsciiAnimation(2)
        animation.start_document()
        animation.request_cancel()
        self.assertEqual(animation.snapshot().state, AnimationState.RUNNING)
        self.assertIn(DocShieldAsciiAnimation.MESSAGE_CANCEL_PENDING, animation.render_frame())
        animation.cancel()
        self.assertTrue(animation.snapshot().is_terminal)
        self.assertIn(DocShieldAsciiAnimation.MESSAGE_CANCELLED, animation.render_frame())

    def test_advance_requires_a_completed_document(self) -> None:
        animation = DocShieldAsciiAnimation(2)
        animation.start_document()
        with self.assertRaises(RuntimeError):
            animation.advance_to_next()

    def test_elapsed_seconds_resets_on_start_and_advance(self) -> None:
        """mascot_animation.frame_name_for relies on this for its own
        looping clock, instead of parsing render_frame()'s text."""
        animation = DocShieldAsciiAnimation(2)
        animation.start_document("doc-1")
        self.assertAlmostEqual(
            animation.elapsed_seconds(now=time.monotonic() + 5.0), 5.0, places=2
        )
        animation.mark_current_completed()
        animation.advance_to_next("doc-2")
        self.assertAlmostEqual(
            animation.elapsed_seconds(now=time.monotonic() + 1.0), 1.0, places=2
        )

    def test_current_message_matches_render_frame_status_line(self) -> None:
        animation = DocShieldAsciiAnimation(1)
        self.assertEqual(animation.current_message(), DocShieldAsciiAnimation.MESSAGE_IDLE)
        animation.start_document()
        self.assertEqual(animation.current_message(), DocShieldAsciiAnimation.MESSAGE_RUNNING)
        animation.request_cancel()
        self.assertEqual(
            animation.current_message(), DocShieldAsciiAnimation.MESSAGE_CANCEL_PENDING
        )


class ProcessingScreenAnimationTests(unittest.TestCase):
    _root = None

    @classmethod
    def setUpClass(cls) -> None:
        cls._root = tk.Tk()
        cls._root.withdraw()

    @classmethod
    def tearDownClass(cls) -> None:
        cls._root.destroy()

    def _app(self, paths: list[Path]) -> AnonymizerApp:
        app = AnonymizerApp.__new__(AnonymizerApp)
        app.root = self._root
        app.selected_paths = paths
        app.output_dir = Path("out")
        app.page_ranges = {}
        app.page_counts = {}
        app.sensitive_terms_path = None
        app.use_ner = False
        app.llm_model_name = ""
        app.use_llm_comparison_review = False
        app.use_llm_narrative_review = False
        app.pdf_output_label = gui_app.PDF_OUTPUT_LABEL_VISUAL_REDACTION
        app.active_categories = None
        app.strip_signatures = False
        app.active_screen = "start"
        app.processing_animation = None
        app.processing_document_label = None
        app.processing_mascot_label = None
        app.processing_status_label = None
        app.processing_cancel_button = None
        app.progress_elapsed_label = None
        app._processing_active = False
        app._processing_started_at = 0.0
        app._processing_after_id = None
        app._processing_events = queue.Queue()
        app._processing_cancel = threading.Event()
        app.status_label = mock.Mock()
        app.rendered_frames = []
        app.document_counts = []
        app._last_document_text = ""
        app._last_status_text = ""

        def _record_combined() -> None:
            # The mascot animation replaced one text widget (the ASCII box,
            # which carried "Dokument N z M" and the status message in one
            # string) with three: an image plus two small text labels. Tests
            # below were written against that single combined string, so the
            # fixture recombines the two text labels' latest values the same
            # way, rather than rewriting every assertion for a UI-layout
            # detail that isn't what they're actually checking.
            app.rendered_frames.append(
                f"{app._last_document_text} {app._last_status_text}".strip()
            )

        document_label = mock.Mock()

        def _document_configure(**kw) -> None:
            if "text" in kw:
                app._last_document_text = kw["text"]
            _record_combined()

        document_label.configure.side_effect = _document_configure

        status_label = mock.Mock()

        def _status_configure(**kw) -> None:
            if "text" in kw:
                app._last_status_text = kw["text"]
            _record_combined()

        status_label.configure.side_effect = _status_configure
        mascot_label = mock.Mock()

        def fake_show_processing_screen(document_count: int = 1) -> None:
            app.active_screen = "processing"
            app.document_counts.append(document_count)
            app.processing_animation = DocShieldAsciiAnimation(document_count)
            app.processing_document_label = document_label
            app.processing_mascot_label = mascot_label
            app.processing_status_label = status_label

        app.show_processing_screen = fake_show_processing_screen
        app.show_start_screen = mock.Mock()
        app._on_anonymize_done = mock.Mock(
            side_effect=lambda *a: setattr(app, "_processing_active", False)
        )
        return app

    def _pump_until(self, predicate, timeout: float = 10.0) -> None:
        deadline = time.monotonic() + timeout
        while not predicate():
            if time.monotonic() > deadline:
                self.fail("timed out waiting for the processing screen")
            self._root.update()
            time.sleep(0.01)

    def _run(self, app: AnonymizerApp, fake_batch) -> None:
        with mock.patch.object(gui_app, "anonymize_batch", side_effect=fake_batch), \
                mock.patch.object(gui_app, "dated_output_subdir", return_value=Path("out/d")):
            app.start_anonymize()
            self._pump_until(lambda: not app._processing_active)

    def _state(self, app: AnonymizerApp) -> AnimationState:
        return app.processing_animation.snapshot().state

    def test_single_document_success(self) -> None:
        app = self._app([Path(PII_FILE_NAME)])

        def fake_batch(paths, out_dir, progress_callback=None, **kwargs):
            progress_callback(1, 1, paths[0])
            time.sleep(0.3)
            return SimpleNamespace(success_count=1, error_count=0)

        self._run(app, fake_batch)
        self.assertEqual(self._state(app), AnimationState.SUCCESS)
        app._on_anonymize_done.assert_called_once()
        self.assertIsNone(app._processing_after_id)
        self.assertIn("Dokument 1 z 1", app.rendered_frames[-1])
        self.assertIn("Wszystkie dokumenty zakończone", app.rendered_frames[-1])

    def test_several_documents_are_counted_in_order(self) -> None:
        paths = [Path(f"doc{i}.pdf") for i in range(1, 4)]
        app = self._app(paths)
        states_seen = []

        def fake_batch(paths, out_dir, progress_callback=None, **kwargs):
            for index, path in enumerate(paths, start=1):
                progress_callback(index, len(paths), path)
                time.sleep(0.3)
            return SimpleNamespace(success_count=3, error_count=0)

        original_update = app._update_processing

        def recording_update(index, total):
            original_update(index, total)
            snap = app.processing_animation.snapshot()
            states_seen.append((snap.document_number, snap.source_id, snap.state))

        app._update_processing = recording_update
        self._run(app, fake_batch)

        self.assertEqual(app.document_counts, [3])
        self.assertEqual(
            states_seen,
            [
                (1, "doc-1", AnimationState.RUNNING),
                (2, "doc-2", AnimationState.RUNNING),
                (3, "doc-3", AnimationState.RUNNING),
            ],
        )
        rendered = "\n".join(app.rendered_frames)
        for number in (1, 2, 3):
            self.assertIn(f"Dokument {number} z 3", rendered)
        self.assertEqual(self._state(app), AnimationState.SUCCESS)

    def test_batch_failure_stops_with_error_frame(self) -> None:
        app = self._app([Path("a.pdf"), Path("b.pdf")])

        def fake_batch(paths, out_dir, progress_callback=None, **kwargs):
            progress_callback(1, 2, paths[0])
            time.sleep(0.2)
            raise RuntimeError("secret detail from " + PII_FILE_NAME)

        self._run(app, fake_batch)
        self.assertEqual(self._state(app), AnimationState.ERROR)
        app.show_start_screen.assert_called_once()
        app._on_anonymize_done.assert_not_called()
        self.assertIn("błąd", app.rendered_frames[-1])
        self.assertNotIn("secret", app.rendered_frames[-1])

    def test_all_files_failing_ends_as_error_frame_but_still_opens_review(self) -> None:
        app = self._app([Path("a.pdf")])

        def fake_batch(paths, out_dir, progress_callback=None, **kwargs):
            progress_callback(1, 1, paths[0])
            return SimpleNamespace(success_count=0, error_count=1)

        self._run(app, fake_batch)
        self.assertEqual(self._state(app), AnimationState.ERROR)
        app._on_anonymize_done.assert_called_once()

    def test_cancel_stops_before_the_next_file(self) -> None:
        app = self._app([Path("a.pdf"), Path("b.pdf"), Path("c.pdf")])
        second_file_started = threading.Event()
        first_file_running = threading.Event()
        release_first_file = threading.Event()

        def fake_batch(paths, out_dir, progress_callback=None, **kwargs):
            progress_callback(1, 3, paths[0])
            first_file_running.set()
            release_first_file.wait(5)
            progress_callback(2, 3, paths[1])  # raises: cancel was requested
            second_file_started.set()
            return SimpleNamespace(success_count=3, error_count=0)

        with mock.patch.object(gui_app, "anonymize_batch", side_effect=fake_batch), \
                mock.patch.object(gui_app, "dated_output_subdir", return_value=Path("out/d")):
            app.start_anonymize()
            self._pump_until(first_file_running.is_set)
            self._pump_until(
                lambda: self._state(app) == AnimationState.RUNNING
            )
            app._request_processing_cancel()
            self.assertIn(
                DocShieldAsciiAnimation.MESSAGE_CANCEL_PENDING, app.rendered_frames[-1]
            )
            release_first_file.set()
            self._pump_until(lambda: not app._processing_active)

        self.assertFalse(second_file_started.is_set())
        self.assertEqual(self._state(app), AnimationState.CANCELLED)
        app._on_anonymize_done.assert_not_called()
        app.show_start_screen.assert_called_once()
        status_text = app.status_label.configure.call_args.kwargs["text"]
        self.assertIn("Anulowano po 1 z 3", status_text)

    def test_cancel_propagates_through_the_real_anonymize_batch(self) -> None:
        """The cancel exception is raised from progress_callback, which
        anonymize_batch calls outside its per-file error handling - if
        that ever changes, cancelling would silently become a per-file
        error instead of stopping the batch."""
        from anonymizer import anonymize_batch

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            sources = []
            for name in ("a.txt", "b.txt"):
                source = tmp_path / name
                source.write_text("Test bez danych.", encoding="utf-8")
                sources.append(source)
            out_dir = tmp_path / "out"
            calls = []

            def cancelling_callback(index, total, path):
                calls.append(index)
                if index == 2:
                    raise gui_app._BatchCancelled(index - 1)

            with self.assertRaises(gui_app._BatchCancelled):
                anonymize_batch(
                    sources, out_dir, use_ner=False, progress_callback=cancelling_callback
                )
            self.assertEqual(calls, [1, 2])

    def test_closing_the_window_mid_run_asks_then_stops_the_timer(self) -> None:
        app = self._app([Path("a.pdf"), Path("b.pdf")])
        release = threading.Event()

        def fake_batch(paths, out_dir, progress_callback=None, **kwargs):
            progress_callback(1, 2, paths[0])
            release.wait(5)
            return SimpleNamespace(success_count=2, error_count=0)

        with mock.patch.object(gui_app, "anonymize_batch", side_effect=fake_batch), \
                mock.patch.object(gui_app, "dated_output_subdir", return_value=Path("out/d")):
            app.start_anonymize()
            self._pump_until(lambda: self._state(app) == AnimationState.RUNNING)

            # "No" keeps everything running.
            with mock.patch.object(gui_app.messagebox, "askyesno", return_value=False), \
                    mock.patch.object(self._root, "destroy") as destroy:
                app._on_close_request()
            destroy.assert_not_called()
            self.assertTrue(app._processing_active)
            self.assertIsNotNone(app._processing_after_id)

            # "Yes" cancels the pending tick before destroying the window.
            with mock.patch.object(gui_app.messagebox, "askyesno", return_value=True), \
                    mock.patch.object(self._root, "destroy") as destroy, \
                    mock.patch.object(self._root, "after_cancel", wraps=self._root.after_cancel) as after_cancel:
                app._on_close_request()
            release.set()

        destroy.assert_called_once()
        after_cancel.assert_called_once()
        self.assertFalse(app._processing_active)
        self.assertIsNone(app._processing_after_id)
        self.assertTrue(app._processing_cancel.is_set())
        self.assertEqual(self._state(app), AnimationState.CANCELLED)

    def test_closing_the_window_when_idle_does_not_ask(self) -> None:
        app = self._app([])
        with mock.patch.object(gui_app.messagebox, "askyesno") as ask, \
                mock.patch.object(self._root, "destroy") as destroy:
            app._on_close_request()
        ask.assert_not_called()
        destroy.assert_called_once()

    def test_no_path_or_file_name_reaches_the_screen(self) -> None:
        app = self._app([Path("C:/tajne_akta") / PII_FILE_NAME])
        queued = []
        original_put = queue.Queue.put

        def fake_batch(paths, out_dir, progress_callback=None, **kwargs):
            progress_callback(1, 1, paths[0])
            return SimpleNamespace(success_count=1, error_count=0)

        def recording_put(q, item, *args, **kwargs):
            queued.append(item)
            return original_put(q, item, *args, **kwargs)

        with mock.patch.object(queue.Queue, "put", recording_put):
            self._run(app, fake_batch)

        progress_events = [event for event in queued if event[0] == "progress"]
        self.assertEqual(progress_events, [("progress", 1, 1)])
        for frame in app.rendered_frames:
            self.assertNotIn("Nowak", frame)
            self.assertNotIn("tajne_akta", frame)


if __name__ == "__main__":
    unittest.main()
