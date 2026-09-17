"""Tests for the Stage 1 plain text anonymizer."""

from pathlib import Path
import sys
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from anonymizer import SUPPORTED_LABELS, anonymize_text


class AnonymizerEngineTests(unittest.TestCase):
    def test_replaces_pesel(self) -> None:
        text = "Synthetic PESEL: 00000000000."

        anonymized, report = anonymize_text(text)

        self.assertEqual(anonymized, "Synthetic PESEL: [PESEL].")
        self.assertEqual(report, {"PESEL": 1})

    def test_replaces_nip_number(self) -> None:
        text = "NIP: 123-456-32-18."

        anonymized, report = anonymize_text(text)

        self.assertEqual(anonymized, "[NIP].")
        self.assertEqual(report, {"NIP": 1})

    def test_replaces_regon_number_short_and_long_form(self) -> None:
        text = "REGON: 123456785. REGON: 12345678512347."

        anonymized, report = anonymize_text(text)

        self.assertEqual(anonymized, "[REGON]. [REGON].")
        self.assertEqual(report, {"REGON": 2})

    def test_does_not_replace_short_nip_like_number_without_keyword_context(
        self,
    ) -> None:
        text = "Sprawa numer 12345 dotyczy zamowienia."

        anonymized, report = anonymize_text(text)

        self.assertEqual(anonymized, text)
        self.assertEqual(report, {})

    def test_pairs_table_separated_nip_and_regon_labels_with_their_values(
        self,
    ) -> None:
        """Direct regression test for the exact scenario reported live on
        a real invoice: NIP/REGON_PATTERN require the label and its
        digits on the same line, but a common invoice-table layout
        groups every field label in one block and every value in
        another a few lines later - leaving both completely undetected
        before this fallback existed.
        """
        text = "NIP\nREGON\n526-000-12-46\n012345678"

        anonymized, report = anonymize_text(text)

        self.assertEqual(anonymized, "NIP\nREGON\n[NIP]\n[REGON]")
        self.assertEqual(report, {"NIP": 1, "REGON": 1})

    def test_table_separated_pairing_matches_multiple_labels_in_reading_order(
        self,
    ) -> None:
        text = "NIP\nNIP\n1111111111\n2222222222"

        anonymized, report = anonymize_text(text)

        self.assertEqual(anonymized, "NIP\nNIP\n[NIP]\n[NIP]")
        self.assertEqual(report, {"NIP": 2})

    def test_table_separated_pairing_does_not_reach_across_unrelated_pages(
        self,
    ) -> None:
        """A label many lines away from any digits must not silently
        grab an unrelated number much later in the document - bounded
        to the same table/block, not the rest of a long document."""
        filler = "linia wypelniajaca\n" * 12
        text = f"NIP\n{filler}526-000-12-46"

        anonymized, report = anonymize_text(text)

        self.assertEqual(anonymized, text)
        self.assertEqual(report, {})

    def test_table_separated_pairing_leaves_the_field_label_itself_untouched(
        self,
    ) -> None:
        text = "NIP\n526-000-12-46"

        anonymized, _report = anonymize_text(text)

        self.assertIn("NIP", anonymized)
        self.assertNotIn("526-000-12-46", anonymized)

    def test_table_separated_pairing_does_not_claim_a_pesel_shaped_number(
        self,
    ) -> None:
        """PESEL is 11 digits, NIP is exactly 10 - the two patterns
        already run in an order where PESEL claims its match first, so
        this fallback must never additionally treat an 11-digit PESEL
        as a disconnected NIP value."""
        text = "NIP\n00000000000"

        anonymized, report = anonymize_text(text)

        self.assertEqual(anonymized, "NIP\n[PESEL]")
        self.assertEqual(report, {"PESEL": 1})

    def test_replaces_dowod_osobisty_number(self) -> None:
        text = "Numer dowodu: ABC123456."

        anonymized, report = anonymize_text(text)

        self.assertEqual(anonymized, "Numer dowodu: [DOWOD_OSOBISTY].")
        self.assertEqual(report, {"DOWOD_OSOBISTY": 1})

    def test_does_not_replace_lowercase_or_wrong_length_dowod_like_code(self) -> None:
        text = "Kod produktu abc123456 lub AB123456 lub ABCD123456."

        anonymized, report = anonymize_text(text)

        self.assertEqual(anonymized, text)
        self.assertEqual(report, {})

    def test_replaces_iban_with_and_without_spaces(self) -> None:
        text = (
            "Konto: PL61 1090 1014 0000 0712 1981 2874. "
            "IBAN PL61109010140000071219812874."
        )

        anonymized, report = anonymize_text(text)

        self.assertEqual(anonymized, "Konto: [IBAN]. IBAN [IBAN].")
        self.assertEqual(report, {"IBAN": 2})

    def test_does_not_replace_malformed_iban_grouping(self) -> None:
        text = "PL6 1109 0101 4000 0071 2198 1287 4"

        anonymized, report = anonymize_text(text)

        self.assertEqual(anonymized, text)
        self.assertEqual(report, {})

    def test_replaces_email(self) -> None:
        text = "Contact: tester@example.test."

        anonymized, report = anonymize_text(text)

        self.assertEqual(anonymized, "Contact: [EMAIL].")
        self.assertEqual(report, {"EMAIL": 1})

    def test_replaces_telefon(self) -> None:
        text = "Phone: +48 123 456 789."

        anonymized, report = anonymize_text(text)

        self.assertEqual(anonymized, "Phone: [TELEFON].")
        self.assertEqual(report, {"TELEFON": 1})

    def test_replaces_grouped_phone_only_with_contact_context(self) -> None:
        text = "Kontakt tel. 123 456 789."

        anonymized, report = anonymize_text(text)

        self.assertEqual(anonymized, "Kontakt tel. [TELEFON].")
        self.assertEqual(report, {"TELEFON": 1})

    def test_does_not_replace_weak_table_like_phone_number(self) -> None:
        text = "Tabela: populacja 123 456 789 oraz warto\u015b\u0107 43 595."

        anonymized, report = anonymize_text(text)

        self.assertEqual(anonymized, text)
        self.assertEqual(report, {})

    def test_replaces_data(self) -> None:
        text = "Date: 2026-06-01."

        anonymized, report = anonymize_text(text)

        self.assertEqual(anonymized, "Date: [DATA].")
        self.assertEqual(report, {"DATA": 1})

    def test_replaces_data_in_dash_slash_and_written_month_formats(self) -> None:
        text = (
            "Zawarta dnia 04-09-2026. Termin do 04/09/2026. "
            "Data urodzenia: 4 września 2026, drugi zapis: 04 września 2026."
        )

        anonymized, report = anonymize_text(text)

        self.assertEqual(
            anonymized,
            "Zawarta dnia [DATA]. Termin do [DATA]. "
            "Data urodzenia: [DATA], drugi zapis: [DATA].",
        )
        self.assertEqual(report, {"DATA": 4})

    def test_replaces_written_month_date_without_polish_diacritics(self) -> None:
        text = (
            "Spotkanie 15 wrzesnia 2026 roku. Kolejne 3 pazdziernika 2026 roku."
        )

        anonymized, report = anonymize_text(text)

        self.assertEqual(
            anonymized,
            "Spotkanie [DATA] roku. Kolejne [DATA] roku.",
        )
        self.assertEqual(report, {"DATA": 2})

    def test_does_not_replace_invalid_dash_or_written_month_date(self) -> None:
        text = "Kod referencyjny 45-67-8901. Notatka: 13 miasto 2026."

        anonymized, report = anonymize_text(text)

        self.assertEqual(anonymized, text)
        self.assertEqual(report, {})

    def test_replaces_postal_code(self) -> None:
        text = "Adres: ul. Testowa 12, 00-950 Warszawa."

        anonymized, report = anonymize_text(text)

        self.assertEqual(anonymized, "Adres: [ULICA], [POSTAL_CODE] [MIEJSCOWOSC].")
        self.assertEqual(report, {"ULICA": 1, "POSTAL_CODE": 1, "MIEJSCOWOSC": 1})

    def test_replaces_street_name_with_and_without_period_prefix(self) -> None:
        text = "UL. Testowa 5. Ul Testowa 5. al. Niepodległości 10a. Plac Zamkowy 1."

        anonymized, report = anonymize_text(text)

        self.assertEqual(
            anonymized,
            "[ULICA]. [ULICA]. [ULICA]. [ULICA].",
        )
        self.assertEqual(report, {"ULICA": 4})

    def test_replaces_street_name_without_building_number(self) -> None:
        text = "Zamieszkały przy ulicy Kwiatowej."

        anonymized, report = anonymize_text(text)

        self.assertEqual(anonymized, "Zamieszkały przy [ULICA].")
        self.assertEqual(report, {"ULICA": 1})

    def test_street_name_match_does_not_cross_a_line_break(self) -> None:
        """Same class of bug as the MIEJSCOWOSC regression above, for the
        street-name pattern's own multi-word/building-number joins."""
        text = "ul. Kwiatowa\nNumer PESEL: 00000000000."

        anonymized, report = anonymize_text(text)

        self.assertEqual(anonymized, "[ULICA]\nNumer PESEL: [PESEL].")
        self.assertEqual(report, {"ULICA": 1, "PESEL": 1})

    def test_does_not_replace_bare_street_abbreviation_without_name(self) -> None:
        text = "Kolega ulubiony ul lubi kawę. Prosze o pl. wplat na koncie."

        anonymized, report = anonymize_text(text)

        self.assertEqual(anonymized, text)
        self.assertEqual(report, {})

    def test_replaces_compound_city_name_after_postal_code(self) -> None:
        text = "62-800 Ostrów Wielkopolski. 43-300 Bielsko-Biała."

        anonymized, report = anonymize_text(text)

        self.assertEqual(
            anonymized,
            "[POSTAL_CODE] [MIEJSCOWOSC]. [POSTAL_CODE] [MIEJSCOWOSC].",
        )
        self.assertEqual(report, {"POSTAL_CODE": 2, "MIEJSCOWOSC": 2})

    def test_city_name_match_does_not_cross_a_line_break(self) -> None:
        """Regression test for a real bug found live on a table-layout PDF:
        word_pages_for_redaction_geometry joins each extracted line/table
        row with a single "\\n", and this pattern's trailing optional word
        used to match across that boundary - "02-500 Testowo" followed by
        an unrelated next line/row starting with a capitalized word ("
        Numer PESEL") swept "Numer" into the same MIEJSCOWOSC match.
        """
        text = "62-800 Ostrów\nNumer PESEL: 00000000000."

        anonymized, report = anonymize_text(text)

        self.assertEqual(
            anonymized, "[POSTAL_CODE] [MIEJSCOWOSC]\nNumer PESEL: [PESEL]."
        )
        self.assertEqual(report, {"POSTAL_CODE": 1, "MIEJSCOWOSC": 1, "PESEL": 1})

    def test_does_not_replace_city_name_without_preceding_postal_code(self) -> None:
        text = "Miasto Warszawa jest stolica Polski."

        anonymized, report = anonymize_text(text)

        self.assertEqual(anonymized, text)
        self.assertEqual(report, {})

    def test_replaces_postal_code_without_following_city_name(self) -> None:
        text = "Kod pocztowy: 00-950."

        anonymized, report = anonymize_text(text)

        self.assertEqual(anonymized, "Kod pocztowy: [POSTAL_CODE].")
        self.assertEqual(report, {"POSTAL_CODE": 1})

    def test_replaces_conservative_person_name_typo_pattern(self) -> None:
        text = "Reviewer Jan-Kowalski Kowalski signed."

        anonymized, report = anonymize_text(text)

        self.assertEqual(anonymized, "Reviewer [PERSON_NAME_TYPO] signed.")
        self.assertEqual(report, {"PERSON_NAME_TYPO": 1})

    def test_replaces_malformed_hyphenated_person_name_pattern(self) -> None:
        text = "Reviewer Jan-Kowalski Nowak signed."

        anonymized, report = anonymize_text(text)

        self.assertEqual(anonymized, "Reviewer [PERSON_NAME_TYPO] signed.")
        self.assertEqual(report, {"PERSON_NAME_TYPO": 1})

    def test_replaces_person_name_typo_with_unicode_dash_variants(self) -> None:
        examples = (
            "Reviewer Jan\u2011Kowalski Nowak signed.",
            "Reviewer Jan\u2013Kowalski Nowak signed.",
            "Reviewer Jan \u2014 Kowalski Nowak signed.",
            "Reviewer Jan\u00adKowalski Nowak signed.",
            "Reviewer Jan-\u00a0Kowalski\u00a0Nowak signed.",
            "Reviewer \u0141ukasz-\u017bak Nowak signed.",
            "podpisano: Jan-Kowalski Nowak,",
        )

        for text in examples[:-1]:
            with self.subTest(text=text):
                anonymized, report = anonymize_text(text)

                self.assertEqual(anonymized, "Reviewer [PERSON_NAME_TYPO] signed.")
                self.assertEqual(report, {"PERSON_NAME_TYPO": 1})

        anonymized, report = anonymize_text(examples[-1])
        self.assertEqual(anonymized, "podpisano: [PERSON_NAME_TYPO],")
        self.assertEqual(report, {"PERSON_NAME_TYPO": 1})

    def test_hyphenated_surname_does_not_absorb_the_next_lines_first_word(
        self,
    ) -> None:
        """Direct regression test for the exact bug reported live on a
        table-layout PDF: a table row ending in a hyphenated surname
        ("Zoltan Nagy-Kowalski") sat directly above the next row's field
        label ("Adres zamieszkania"), joined by a single "\\n" in the
        extracted text. PERSON_NAME_TYPO_PATTERN's trailing word - meant
        to complete a genuine 3-token typo shape like "Jan-Kowalski
        Nowak" - used to also happily match across that "\\n", so "Adres"
        (a field label, not a name) got swept into the same redaction and
        silently vanished from the output. A plain 2-token hyphenated
        surname on its own line is not a typo shape this pattern should
        match at all - see anonymize_text_with_ner/NER_PERSON for actual
        full-name detection, which is a separate, AI-driven path.
        """
        text = "Imie i nazwisko: Zoltan Nagy-Kowalski\nAdres zamieszkania: brak."

        anonymized, report = anonymize_text(text)

        self.assertEqual(anonymized, text)
        self.assertEqual(report, {})

    def test_does_not_replace_normal_hyphenated_non_person_phrase(self) -> None:
        examples = (
            "Status Raport-Roczny Finansowy remains unchanged.",
            "bia\u0142o-czerwony sztandar",
            "sanitarno-epidemiologiczna stacja",
            "\u017co\u0142\u0105dkowo-jelitowych i bronchoskop\u00f3w",
        )

        for text in examples:
            with self.subTest(text=text):
                anonymized, report = anonymize_text(text)

                self.assertEqual(anonymized, text)
                self.assertEqual(report, {})

    def test_replaces_multiple_categories_in_one_text(self) -> None:
        text = (
            "Email tester@example.test on 2026-06-01. "
            "PESEL: 00000000000. Tel: 123-456-789."
        )

        anonymized, report = anonymize_text(text)

        self.assertEqual(
            anonymized,
            "Email [EMAIL] on [DATA]. PESEL: [PESEL]. Tel: [TELEFON].",
        )
        self.assertEqual(
            report,
            {"EMAIL": 1, "PESEL": 1, "TELEFON": 1, "DATA": 1},
        )

    def test_counts_multiple_occurrences_of_same_category(self) -> None:
        text = "Emails: first@example.test and second@example.test."

        anonymized, report = anonymize_text(text)

        self.assertEqual(anonymized, "Emails: [EMAIL] and [EMAIL].")
        self.assertEqual(report, {"EMAIL": 2})

    def test_no_match_returns_unchanged_text_and_empty_report(self) -> None:
        text = "Plain synthetic note without supported identifiers."

        anonymized, report = anonymize_text(text)

        self.assertEqual(anonymized, text)
        self.assertEqual(report, {})

    def test_does_not_replace_values_embedded_in_tokens(self) -> None:
        text = "token00000000000x ref2026-06-01x abc123-456-789z"

        anonymized, report = anonymize_text(text)

        self.assertEqual(anonymized, text)
        self.assertEqual(report, {})

    def test_report_does_not_contain_source_values(self) -> None:
        source_values = {
            "safe@example.test",
            "00000000000",
            "+48 123 456 789",
            "2026-06-01",
        }
        text = "safe@example.test 00000000000 +48 123 456 789 2026-06-01"

        _, report = anonymize_text(text)

        report_as_text = repr(report)
        for source_value in source_values:
            self.assertNotIn(source_value, report_as_text)
        self.assertEqual(report, {"EMAIL": 1, "PESEL": 1, "TELEFON": 1, "DATA": 1})

    def test_supported_labels_are_limited_to_current_regex_categories(self) -> None:
        self.assertEqual(
            SUPPORTED_LABELS,
            (
                "PESEL",
                "EMAIL",
                "TELEFON",
                "DATA",
                "PERSON_NAME_TYPO",
                "ULICA",
                "MIEJSCOWOSC",
                "POSTAL_CODE",
                "NIP",
                "REGON",
                "DOWOD_OSOBISTY",
                "IBAN",
            ),
        )


if __name__ == "__main__":
    unittest.main()
