"""Frame selection for the processing screen's mascot animation.

Pure logic, no Tk and no file I/O - it only decides *which* PNG filename
(from assets/mascot/) belongs on screen for a given animation state and
elapsed time. All actual state tracking (running/completed/success/error/
cancelled, document counting, the status message) still lives in
docshield_ascii_animation.DocShieldAsciiAnimation; this module only adds
an image on top of it, replacing that module's own text-frame rendering
on the processing screen. gui_helpers.get_mascot_frame_image() turns a
filename returned here into a cached CTkImage.

The 20-frame loop is a hand-drawn cartoon detective searching a document
with a magnifying glass, then marking it with a highlighter, then putting
the marker down and picking the glass back up - seamless, so it can repeat
indefinitely while a batch runs. mascot_success.png (a distinct "thumbs up"
pose) shows once processing finishes successfully.
"""

from __future__ import annotations

# Order matters: this is the animation sequence, not alphabetical filenames.
MASCOT_LOOP_FRAMES: tuple[str, ...] = tuple(
    f"mascot_{index:02d}.png" for index in range(1, 21)
)
MASCOT_SUCCESS_FRAME = "mascot_success.png"
# Neutral pose shown while idle, and held (not looping) on error/cancel/
# between-files pause - a still image reads as "stopped", a looping one
# would look like it's still working.
MASCOT_IDLE_FRAME = MASCOT_LOOP_FRAMES[0]

# Seconds per loop frame - matches the hand-timed preview the user approved.
MASCOT_FRAME_INTERVAL = 0.15

# The states (docshield_ascii_animation.AnimationState) for which the loop
# keeps animating. Every other state holds a single still frame.
_ANIMATING_STATE_VALUES = frozenset({"running"})


def frame_name_for(state_value: str, elapsed_seconds: float) -> str:
    """Return the mascot PNG filename for one screen redraw.

    ``state_value`` is an ``AnimationState`` (or its ``.value``/plain
    string - compared by value so this stays usable without importing
    the GUI-agnostic module's enum, keeping this module dependency-free).
    ``elapsed_seconds`` is time since the *current* document started
    animating (``DocShieldAsciiAnimation.elapsed_seconds()``); ignored
    outside the running state.
    """
    value = getattr(state_value, "value", state_value)
    if value == "success":
        return MASCOT_SUCCESS_FRAME
    if value not in _ANIMATING_STATE_VALUES:
        return MASCOT_IDLE_FRAME
    tick = int(max(0.0, elapsed_seconds) / MASCOT_FRAME_INTERVAL)
    return MASCOT_LOOP_FRAMES[tick % len(MASCOT_LOOP_FRAMES)]
