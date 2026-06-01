"""Placeholder anonymization module.

Real detection and replacement logic will be added in a later stage.
"""

from dataclasses import dataclass


SUPPORTED_LABELS = (
    "IMIE NAZWISKO",
    "PESEL",
    "DATA",
    "MIEJSCOWOSC",
    "ULICA",
    "NUMER",
    "TELEFON",
    "EMAIL",
    "NAZWA PODMIOTU",
    "ADRES",
    "INNE DANE",
)


@dataclass(frozen=True)
class AnonymizationResult:
    """Result returned by the placeholder anonymizer."""

    text: str
    detected_labels: tuple[str, ...] = ()


def anonymize_text(text: str) -> AnonymizationResult:
    """Return input text unchanged until real anonymization is implemented."""
    if not isinstance(text, str):
        raise TypeError("text must be a string")

    return AnonymizationResult(text=text)
