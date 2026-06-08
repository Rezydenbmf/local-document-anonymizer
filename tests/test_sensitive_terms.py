"""Tests for Stage 8 private sensitive terms dictionary support."""

from pathlib import Path
import sys
import tempfile
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from anonymizer import anonymize_text, anonymize_txt_file
from sensitive_terms import (
    apply_sensitive_terms,
    load_sensitive_terms,
    parse_sensitive_terms,
)


def workspace_temp_dir():
    return tempfile.TemporaryDirectory(dir=PROJECT_ROOT / "tests")


class SensitiveTermsTests(unittest.TestCase):
    def test_loads_valid_dictionary_file(self) -> None:
        with workspace_temp_dir() as temp_dir:
            dictionary_path = Path(temp_dir) / "sensitive_terms.txt"
            dictionary_path.write_text(
                "Person One Example = [IMIE NAZWISKO]\n"
                "Example Institution = [NAZWA PODMIOTU]\n",
                encoding="utf-8",
            )

            terms = load_sensitive_terms(dictionary_path)

            self.assertEqual(len(terms), 2)
            self.assertEqual(terms[0].term, "Person One Example")
            self.assertEqual(terms[0].label, "IMIE NAZWISKO")
            self.assertEqual(terms[1].term, "Example Institution")
            self.assertEqual(terms[1].label, "NAZWA PODMIOTU")

    def test_ignores_comments_and_empty_lines(self) -> None:
        terms = parse_sensitive_terms(
            "# Synthetic private dictionary example\n"
            "\n"
            "Person One Example = [IMIE NAZWISKO]\n"
            "   # Another comment\n"
            "\n"
            "Example Department = [KOMORKA ORGANIZACYJNA]\n"
        )

        self.assertEqual([term.label for term in terms], [
            "IMIE NAZWISKO",
            "KOMORKA ORGANIZACYJNA",
        ])

    def test_applies_dictionary_replacement_and_counts_by_label(self) -> None:
        terms = parse_sensitive_terms(
            "Person One Example = [IMIE NAZWISKO]\n"
            "Example Institution = [NAZWA PODMIOTU]\n"
        )

        anonymized, counters = apply_sensitive_terms(
            "Person One Example visited Example Institution. "
            "Person One Example returned later.",
            terms,
        )

        self.assertEqual(
            anonymized,
            "[IMIE NAZWISKO] visited [NAZWA PODMIOTU]. "
            "[IMIE NAZWISKO] returned later.",
        )
        self.assertEqual(counters, {"IMIE NAZWISKO": 2, "NAZWA PODMIOTU": 1})

    def test_counters_and_repr_do_not_expose_original_terms(self) -> None:
        source_term = "Person One Example"
        terms = parse_sensitive_terms(f"{source_term} = [IMIE NAZWISKO]\n")

        _, counters = apply_sensitive_terms(source_term, terms)

        self.assertNotIn(source_term, repr(counters))
        self.assertNotIn(source_term, repr(terms))
        self.assertEqual(counters, {"IMIE NAZWISKO": 1})

    def test_replaces_longer_terms_before_shorter_terms(self) -> None:
        terms = parse_sensitive_terms(
            "Person One Example = [IMIE NAZWISKO]\n"
            "Person = [IMIE]\n"
        )

        anonymized, counters = apply_sensitive_terms(
            "Person One Example met Person.",
            terms,
        )

        self.assertEqual(anonymized, "[IMIE NAZWISKO] met [IMIE].")
        self.assertEqual(counters, {"IMIE NAZWISKO": 1, "IMIE": 1})

    def test_malformed_dictionary_line_validation_is_safe(self) -> None:
        source_term = "Person One Example"

        with self.assertRaises(ValueError) as context:
            parse_sensitive_terms(f"{source_term} [IMIE NAZWISKO]\n")

        self.assertIn("line 1", str(context.exception))
        self.assertNotIn(source_term, str(context.exception))

    def test_without_dictionary_preserves_existing_regex_behavior(self) -> None:
        text = "Person One Example contacted tester@example.test."

        anonymized, counters = anonymize_text(text)

        self.assertEqual(anonymized, "Person One Example contacted [EMAIL].")
        self.assertEqual(counters, {"EMAIL": 1})

    def test_dictionary_integrates_with_regex_anonymization(self) -> None:
        terms = parse_sensitive_terms("Person One Example = [IMIE NAZWISKO]\n")

        anonymized, counters = anonymize_text(
            "Person One Example contacted tester@example.test on 2026-06-01.",
            sensitive_terms=terms,
        )

        self.assertEqual(
            anonymized,
            "[IMIE NAZWISKO] contacted [EMAIL] on [DATA].",
        )
        self.assertEqual(counters, {"IMIE NAZWISKO": 1, "EMAIL": 1, "DATA": 1})

    def test_report_from_dictionary_flow_does_not_include_original_terms(self) -> None:
        with workspace_temp_dir() as temp_dir:
            source_term = "Person One Example"
            terms = parse_sensitive_terms(f"{source_term} = [IMIE NAZWISKO]\n")
            source_path = Path(temp_dir) / "document.txt"
            source_path.write_text(
                f"{source_term} contacted tester@example.test.",
                encoding="utf-8",
            )

            output_path, counters = anonymize_txt_file(
                source_path, sensitive_terms=terms
            )
            report_path = Path(temp_dir) / "document_RAPORT.txt"
            report_text = report_path.read_text(encoding="utf-8")

            self.assertEqual(
                output_path.read_text(encoding="utf-8"),
                "[IMIE NAZWISKO] contacted [EMAIL].",
            )
            self.assertEqual(counters, {"IMIE NAZWISKO": 1, "EMAIL": 1})
            self.assertNotIn(source_term, output_path.read_text(encoding="utf-8"))
            self.assertNotIn(source_term, repr(counters))
            self.assertNotIn(source_term, report_text)
            self.assertIn("* IMIE NAZWISKO: 1", report_text)
            self.assertIn("* EMAIL: 1", report_text)


if __name__ == "__main__":
    unittest.main()
