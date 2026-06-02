"""TXT file readers for Stage 2."""

from pathlib import Path


TXT_EXTENSION = ".txt"


def _ensure_txt_path(file_path: str | Path) -> Path:
    path = Path(file_path)
    if path.suffix.lower() != TXT_EXTENSION:
        suffix = path.suffix or "<none>"
        raise ValueError(
            f"Unsupported file extension for Stage 2: {suffix}. "
            "Only .txt files are supported."
        )
    return path


def read_txt_file(file_path: str | Path) -> str:
    """Read a UTF-8 TXT file and return its text content."""
    path = _ensure_txt_path(file_path)
    return path.read_text(encoding="utf-8")


def extract_text(file_path: str | Path) -> str:
    """Extract text from a supported Stage 2 input file."""
    return read_txt_file(file_path)
