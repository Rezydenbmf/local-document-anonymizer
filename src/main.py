"""Application entry point for the local document anonymizer."""

import traceback
from datetime import datetime, timezone
from pathlib import Path

from gui import start_gui


def _log_crash(exc: BaseException) -> None:
    """Write an uncaught startup/runtime crash to a local log file.

    A windowed launch (pythonw.exe, or the packaged --noconsole .exe)
    has no console to print a traceback to, so a crash here would
    otherwise be completely silent - the window just never appears,
    with no way to tell why. Never raises itself; a failure to write
    the log must never mask the original crash.
    """
    try:
        log_dir = Path.home() / ".anonimizer"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_path = log_dir / "ostatni_blad.log"
        with log_path.open("a", encoding="utf-8") as handle:
            handle.write(f"\n--- {datetime.now(timezone.utc).isoformat()} ---\n")
            traceback.print_exception(type(exc), exc, exc.__traceback__, file=handle)
    except OSError:
        pass


def main() -> None:
    """Start the default desktop GUI."""
    try:
        start_gui()
    except Exception as error:
        _log_crash(error)
        raise


if __name__ == "__main__":
    main()
