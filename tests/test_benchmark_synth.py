"""Benchmark corpus generator: checksums, determinism, key schema."""

import json
import random
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from benchmark import generate, keys, synth
from benchmark.layout import S, ScanDoc, TextDoc


class ChecksumTests(unittest.TestCase):
    def test_generated_identifiers_are_checksum_valid(self):
        rng = random.Random(1)
        for _ in range(200):
            self.assertTrue(synth.nip_is_valid(synth.nip(rng)))
            self.assertTrue(synth.regon_is_valid(synth.regon9(rng)))
            self.assertTrue(synth.iban_is_valid(synth.iban_pl(rng)))
            self.assertTrue(synth.pesel_is_valid(synth.random_pesel(rng, female=True)))

    def test_known_values(self):
        # Published examples: NIP 526-000-12-46, IBAN PL61 1090 1014 0000 0712 1981 2874.
        self.assertTrue(synth.nip_is_valid("526-000-12-46"))
        self.assertTrue(synth.iban_is_valid("PL61 1090 1014 0000 0712 1981 2874"))
        self.assertFalse(synth.iban_is_valid("PL62 1090 1014 0000 0712 1981 2874"))

    def test_pesel_uses_1800s_month_encoding(self):
        value = synth.pesel_1800s(1855, 3, 12, 417, female=True)
        self.assertEqual(value[2:4], "83")
        self.assertTrue(synth.pesel_is_valid(value))

    def test_same_seed_same_values(self):
        self.assertEqual(synth.iban_pl(random.Random(7)), synth.iban_pl(random.Random(7)))


class LayoutTests(unittest.TestCase):
    def test_text_doc_locates_every_span_character(self):
        doc = TextDoc()
        doc.para("Pan ", S("Jan Kowal", "PERSON", "person_private", "ner"),
                 " i znowu ", S("Kowal", "PERSON", "person_private", "ner"), ".")
        doc.para("Nazwisko przełamane: ", S("Kowal-\nski", "PERSON", "person_private", "ner"))
        with tempfile.TemporaryDirectory() as tmp:
            placed = doc.save(Path(tmp) / "t.pdf")
        self.assertEqual([len(p.chars) for p in placed], [8, 5, 9])
        # The second "Kowal" is a different occurrence than the one in "Jan Kowal".
        self.assertGreater(placed[1].chars[0][0], placed[0].chars[-1][2])
        # The hyphenated name spans two lines.
        self.assertGreater(placed[2].chars[-1][1], placed[2].chars[0][3] - 1)

    def test_scan_boxes_follow_rotation(self):
        doc = ScanDoc("bad", seed=1)
        doc.add("body", "Na lewo ", S("Lewy", "PERSON", "person_private"),
                " i daleko na prawo tekst tekst tekst ", S("Prawy", "PERSON", "person_private"))
        with tempfile.TemporaryDirectory() as tmp:
            placed = doc.save(Path(tmp) / "s.pdf")
        left, right = placed
        # 0.9 deg counter-clockwise: text further right sits higher.
        self.assertLess(right.chars[0][1], left.chars[0][1])


class KeyTests(unittest.TestCase):
    def test_generated_key_is_valid_and_reference_pdf_exists(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            generate.generate(out, only={"06_pelnomocnictwo"})
            key = keys.load_key(out / ("06_pelnomocnictwo" + generate.KEY_SUFFIX))
            self.assertTrue((out / ("06_pelnomocnictwo" + generate.REFERENCE_SUFFIX)).exists())
        keys.validate_key(key, keys.load_policy())
        self.assertEqual(key["generator"], keys.generator_fingerprint())
        tags = {s["policy_tag"] for s in key["spans"]}
        self.assertIn("deceased_private", tags)

    def test_generation_is_deterministic(self):
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            generate.generate(Path(a), only={"02_faktura_vat_tabela"})
            generate.generate(Path(b), only={"02_faktura_vat_tabela"})
            name = "02_faktura_vat_tabela" + generate.KEY_SUFFIX
            self.assertEqual(json.loads((Path(a) / name).read_text(encoding="utf-8")),
                             json.loads((Path(b) / name).read_text(encoding="utf-8")))


if __name__ == "__main__":
    unittest.main()
