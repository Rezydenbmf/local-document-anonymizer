"""Tests for Stage 9 post-anonymization audit."""

from pathlib import Path
import sys
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from audit import audit_text
from sensitive_terms import parse_sensitive_terms


def audit_findings(text: str, sensitive_terms=None) -> dict[str, int]:
    result = audit_text(text, sensitive_terms=sensitive_terms)
    return result["findings"]


class PostAnonymizationAuditTests(unittest.TestCase):
    def test_detects_remaining_email_like_pattern(self) -> None:
        result = audit_text("Remaining contact tester@example.test.")

        self.assertEqual(result["status"], "warning")
        self.assertEqual(result["findings"]["EMAIL"], 1)
        self.assertTrue(result["manual_review_required"])

    def test_detects_remaining_pesel_like_pattern(self) -> None:
        findings = audit_findings("Remaining identifier 00000000000.")

        self.assertEqual(findings["PESEL"], 1)

    def test_detects_remaining_phone_like_pattern(self) -> None:
        findings = audit_findings("Remaining phone +48 123 456 789.")

        self.assertEqual(findings["TELEFON"], 1)

    def test_detects_remaining_date_like_pattern(self) -> None:
        findings = audit_findings("Remaining date 2026-06-01.")

        self.assertEqual(findings["DATA"], 1)

    def test_detects_private_dictionary_term_without_returning_term(self) -> None:
        source_term = "Person One Example"
        terms = parse_sensitive_terms(f"{source_term} = [IMIE NAZWISKO]\n")

        result = audit_text(f"Remaining {source_term}.", sensitive_terms=terms)

        self.assertEqual(result["status"], "warning")
        self.assertEqual(result["findings"]["SENSITIVE_DICTIONARY_TERM"], 1)
        self.assertNotIn(source_term, repr(result))

    def test_detects_private_dictionary_term_with_stage_11_matching(self) -> None:
        source_term = "Person One Example"
        terms = parse_sensitive_terms(
            f"{source_term} | P. One Example = [IMIE NAZWISKO]\n"
        )

        result = audit_text(
            "Remaining person   one    example and p. one example.",
            sensitive_terms=terms,
        )

        self.assertEqual(result["status"], "warning")
        self.assertEqual(result["findings"]["SENSITIVE_DICTIONARY_TERM"], 2)
        self.assertNotIn(source_term, repr(result))

    def test_returns_ok_status_when_no_suspicious_patterns_remain(self) -> None:
        result = audit_text("Clean text with [EMAIL] and [DATA] placeholders.")

        self.assertEqual(result["status"], "ok")
        self.assertTrue(result["manual_review_required"])
        self.assertTrue(all(count == 0 for count in result["findings"].values()))

    def test_detects_simple_case_reference_and_postal_code(self) -> None:
        findings = audit_findings("Reference ABC/123/2026 near code 00-000.")

        self.assertEqual(findings["CASE_REFERENCE"], 1)
        self.assertEqual(findings["POSTAL_CODE"], 1)

    def test_detects_simple_address_like_pattern(self) -> None:
        findings = audit_findings("Possible address ul. Testowa 1.")

        self.assertEqual(findings["ADDRESS"], 1)


if __name__ == "__main__":
    unittest.main()
