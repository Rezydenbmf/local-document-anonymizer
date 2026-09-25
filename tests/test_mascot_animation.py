"""mascot_animation.frame_name_for: pure frame selection for the
processing screen's sprite animation (see gui_app._render_processing_frame,
which calls this directly - no Tk needed here)."""

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from mascot_animation import (
    MASCOT_FRAME_INTERVAL,
    MASCOT_IDLE_FRAME,
    MASCOT_LOOP_FRAMES,
    MASCOT_SUCCESS_FRAME,
    frame_name_for,
)


class MascotFrameSelectionTests(unittest.TestCase):
    def test_loop_has_twenty_ordered_frames_starting_at_one(self) -> None:
        self.assertEqual(len(MASCOT_LOOP_FRAMES), 20)
        self.assertEqual(MASCOT_LOOP_FRAMES[0], "mascot_01.png")
        self.assertEqual(MASCOT_LOOP_FRAMES[-1], "mascot_20.png")
        self.assertEqual(MASCOT_IDLE_FRAME, MASCOT_LOOP_FRAMES[0])

    def test_running_advances_one_frame_per_interval(self) -> None:
        self.assertEqual(frame_name_for("running", 0.0), MASCOT_LOOP_FRAMES[0])
        self.assertEqual(
            frame_name_for("running", MASCOT_FRAME_INTERVAL), MASCOT_LOOP_FRAMES[1]
        )
        self.assertEqual(
            frame_name_for("running", 2 * MASCOT_FRAME_INTERVAL), MASCOT_LOOP_FRAMES[2]
        )

    def test_running_loops_seamlessly_past_the_last_frame(self) -> None:
        wrap_elapsed = len(MASCOT_LOOP_FRAMES) * MASCOT_FRAME_INTERVAL
        self.assertEqual(frame_name_for("running", wrap_elapsed), MASCOT_LOOP_FRAMES[0])
        self.assertEqual(
            frame_name_for("running", wrap_elapsed + MASCOT_FRAME_INTERVAL),
            MASCOT_LOOP_FRAMES[1],
        )

    def test_negative_elapsed_is_clamped_not_a_crash(self) -> None:
        self.assertEqual(frame_name_for("running", -5.0), MASCOT_LOOP_FRAMES[0])

    def test_success_state_shows_the_distinct_success_frame(self) -> None:
        self.assertEqual(frame_name_for("success", 3.0), MASCOT_SUCCESS_FRAME)
        # Elapsed time must not matter once the state is success.
        self.assertEqual(frame_name_for("success", 999.0), MASCOT_SUCCESS_FRAME)

    def test_non_animating_states_hold_the_idle_frame(self) -> None:
        for state in ("idle", "document_completed", "error", "cancelled"):
            self.assertEqual(frame_name_for(state, 5.0), MASCOT_IDLE_FRAME)

    def test_accepts_an_enum_like_object_via_its_value_attribute(self) -> None:
        class FakeState:
            value = "running"

        self.assertEqual(frame_name_for(FakeState(), 0.0), MASCOT_LOOP_FRAMES[0])


class MascotAssetIntegrityTests(unittest.TestCase):
    """Every filename this module can return must exist in assets/mascot/ -
    packaging (DocShield.spec) ships that whole folder, but a rename on
    either side would otherwise only surface as a blank image at runtime."""

    def test_every_referenced_frame_file_exists(self) -> None:
        mascot_dir = PROJECT_ROOT / "assets" / "mascot"
        on_disk = {p.name for p in mascot_dir.glob("*.png")}
        referenced = set(MASCOT_LOOP_FRAMES) | {MASCOT_SUCCESS_FRAME}
        self.assertTrue(referenced.issubset(on_disk), referenced - on_disk)

    def test_no_stray_frame_files_go_unused(self) -> None:
        mascot_dir = PROJECT_ROOT / "assets" / "mascot"
        on_disk = {p.name for p in mascot_dir.glob("*.png")}
        referenced = set(MASCOT_LOOP_FRAMES) | {MASCOT_SUCCESS_FRAME}
        self.assertEqual(on_disk - referenced, set())


if __name__ == "__main__":
    unittest.main()
