"""TXT file writers for Stage 2."""

from pathlib import Path


TXT_EXTENSION = ".txt"
ANON_SUFFIX = "_ANON"


def _ensure_txt_path(file_path: str | Path) -> Path:
    path = Path(file_path)
    if path.suffix.lower() != TXT_EXTENSION:
        suffix = path.suffix or "<none>"
        raise ValueError(
            f"Unsupported file extension for Stage 2: {suffix}. "
            "Only .txt files are supported."
        )
    return path


def build_anonymized_txt_path(source_path: str | Path) -> Path:
    """Return the Stage 2 anonymized output path for a TXT source file."""
    path = _ensure_txt_path(source_path)
    return path.with_name(f"{path.stem}{ANON_SUFFIX}{path.suffix}")


def save_anonymized_txt_copy(
    source_path: str | Path, anonymized_text: str
) -> Path:
    """Write anonymized UTF-8 TXT content without modifying the source file."""
    if not isinstance(anonymized_text, str):
        raise TypeError("anonymized_text must be a string")

    output_path = build_anonymized_txt_path(source_path)
    output_path.write_text(anonymized_text, encoding="utf-8")
    return output_path


def save_anonymized_copy(source_path: str | Path, anonymized_text: str) -> str:
    """Save an anonymized copy and return its path as text."""
    return str(save_anonymized_txt_copy(source_path, anonymized_text))
