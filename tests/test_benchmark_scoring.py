"""Benchmark scorer logic on hand-made data (no pipeline run)."""

import json
import re
import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from benchmark import keys, scoring

# Three glyph boxes on one line, 10pt wide.
BOXES = [[0, 0, 10, 12], [10, 0, 20, 12], [20, 0, 30, 12]]


def span(sid="s01", text="Ala", expect="must", page=1, boxes=BOXES):
    return {"id": sid, "text": text, "expect": expect, "page": page, "chars": boxes,
            "policy_tag": "person_private", "category": "PERSON"}


class ScoreSpanTests(unittest.TestCase):
    def test_scan_full_partial_covered(self):
        self.assertEqual(scoring.score_span(span(), []).status, scoring.FULL)
        self.assertEqual(scoring.score_span(span(), [(0, 0, 15, 12)]).status, scoring.PARTIAL)
        self.assertEqual(scoring.score_span(span(), [(0, 0, 30, 12)]).status, scoring.COVERED)

    def test_text_layer_leak_is_what_stays_extractable(self):
        # Fill covers everything but the text is still in the layer: leak + residue.
        chars = [("A", (0, 0, 10, 12)), ("l", (10, 0, 20, 12)), ("a", (20, 0, 30, 12))]
        result = scoring.score_span(span(), [(0, 0, 30, 12)], chars)
        self.assertEqual(result.status, scoring.FULL)
        self.assertEqual(result.residue_chars, 3)
        # Text removed without any fill (the old line-bleed bug) = hidden.
        result = scoring.score_span(span(), [], [])
        self.assertEqual(result.status, scoring.COVERED)

    def test_layer_credit_from_applied_rect_labels(self):
        rects = [{"page": 1, "label": "NER_PERSON", "x0": 0, "y0": 0, "x1": 30, "y1": 12}]
        result = scoring.score_span(span(), [(0, 0, 30, 12)], None, rects)
        self.assertEqual(result.layers, {"ner"})


class PolicyTests(unittest.TestCase):
    def test_policy_flip_changes_expectation_without_regeneration(self):
        policy = keys.load_policy()
        self.assertEqual(keys.resolve_expect("case_reference", policy), "optional")
        policy["enabled_optional_categories"] = ["sygnatury"]
        self.assertEqual(keys.resolve_expect("case_reference", policy), "must")
        policy["tags"]["licence_number"]["expect"] = "must"
        self.assertEqual(keys.resolve_expect("licence_number", policy), "must")

    def test_unknown_tag_fails_loudly(self):
        with self.assertRaises(KeyError):
            keys.resolve_expect("no_such_tag", keys.load_policy())

    def test_user_decisions_of_2026_09_25(self):
        policy = keys.load_policy()
        for tag, expect in (("facility_name", "must"), ("place_name", "must"),
                            ("public_figure", "keep"), ("deceased_private", "must"),
                            ("drug_name", "optional"), ("ean", "optional"),
                            ("licence_number", "optional"), ("statute_reference", "keep"),
                            ("historical_date", "keep"), ("document_date", "optional")):
            self.assertEqual(keys.resolve_expect(tag, policy), expect, tag)


class OverRedactionTests(unittest.TestCase):
    def test_fill_outside_key_spans_is_counted_with_words(self):
        key = {"spans": [span()]}
        fills = {1: [(0, 0, 30, 12), (100, 0, 150, 12)]}
        words = {1: [(100, 0, 140, 12, "Sandomierz")]}
        over = scoring.over_redaction(key, fills, words)
        self.assertEqual(len(over["rects"]), 1)
        self.assertEqual(over["words"], ["Sandomierz"])


class SuggestionTests(unittest.TestCase):
    def test_hit_already_redacted_false_positive_duplicate(self):
        key = {"spans": [span("s01", "Ala"),
                         span("s02", "Ola", boxes=[[0, 50, 10, 62]])]}
        results = [scoring.SpanResult("s01", "must", scoring.FULL, 3, 3),
                   scoring.SpanResult("s02", "must", scoring.COVERED, 0, 1)]
        sentences = ["Tu jest Ala.", "Tu jest Ola.", "Pogoda dobra."]
        suggestions = [
            {"id": "c0", "finding_type": "missed_redaction", "sentence_indices": (1,),
             "page": 1, "rects": ()},
            {"id": "c1", "finding_type": "missed_redaction", "sentence_indices": (2,),
             "page": 1, "rects": ()},
            {"id": "c2", "finding_type": "missed_redaction", "sentence_indices": (3,),
             "page": 1, "rects": ()},
            {"id": "n0", "sentence_indices": (1,), "page": 1, "rects": ()},
            {"id": "c3", "finding_type": "missed_redaction", "sentence_indices": (99,),
             "page": None, "rects": ()},
        ]
        graded = scoring.classify_suggestions(suggestions, sentences, key, results)
        self.assertEqual(graded["hit"], 2)
        self.assertEqual(graded["already_redacted"], 1)
        self.assertEqual(graded["false_positive"], 1)
        self.assertEqual(graded["unresolved"], 1)
        self.assertEqual(graded["duplicates"], 1)
        self.assertEqual(graded["caught_span_ids"], ["s01"])


class BaselineTests(unittest.TestCase):
    def test_compare_flags_new_leaks_and_improvements(self):
        before = {"d": {"partial": ["s02"], "full": ["s05"], "keep_redacted": [],
                        "residue": [], "over_rects": 2}}
        now = {"d": {"partial": [], "full": ["s02", "s07"], "keep_redacted": ["s09"],
                     "residue": [], "over_rects": 1}}
        regressions, improvements = scoring.compare_to_baseline(now, before)
        self.assertIn("d s07: nowy wyciek", regressions)
        self.assertIn("d s02: wyciek częściowy stał się pełny", regressions)
        self.assertIn("d s09: zamazane coś, co ma zostać widoczne", regressions)
        self.assertIn("d s05: już nie wycieka", improvements)

    def test_committed_baseline_holds_no_document_text(self):
        """The repo is public: baseline.json may only hold ids and counts."""
        path = keys.BENCHMARK_DIR / "baseline.json"
        if not path.exists():
            self.skipTest("no baseline yet")
        raw = path.read_text(encoding="utf-8")
        self.assertNotIn('"text"', raw)
        self.assertNotIn('"words"', raw)
        self.assertIsNone(re.search(r"\d{9,}", raw), "long digit run in baseline")
        data = json.loads(raw)
        for summary in data["docs"].values():
            for sid in summary["partial"] + summary["full"] + summary["keep_redacted"]:
                self.assertRegex(sid, r"^s\d{2,}$")


if __name__ == "__main__":
    unittest.main()
