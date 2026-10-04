"""Tests for stylometry.py — hand-counted expected values on a tiny known text.

Run: python3 test_stylometry.py
"""
import json
import math
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import stylometry  # noqa: E402

# 19 words, 4 sentences, hand-counted below.
TINY = "The cat sat on the mat. The dog — a big one — barked! Didn't it? It did; honestly, it did."

TINY_WITH_FRONTMATTER = """---
register: newsletter
topic: cats
---

""" + TINY


class TestTokenize(unittest.TestCase):
    def test_word_count(self):
        words = stylometry.tokenize(TINY)
        self.assertEqual(len(words), 19)

    def test_contractions_are_single_tokens(self):
        words = stylometry.tokenize(TINY)
        self.assertIn("didn't", words)


class TestAnalyze(unittest.TestCase):
    def setUp(self):
        self.m = stylometry.analyze_text(TINY)

    def test_sentence_count_and_lengths(self):
        # "The cat sat on the mat."(6) "The dog — a big one — barked!"(6)
        # "Didn't it?"(2) "It did; honestly, it did."(5)
        self.assertEqual(self.m["sentence_count"], 4)
        self.assertAlmostEqual(self.m["sentence_length"]["mean"], 19 / 4)
        self.assertEqual(self.m["sentence_length"]["min"], 2)
        self.assertEqual(self.m["sentence_length"]["max"], 6)

    def test_punctuation_per_100_words(self):
        p = self.m["punctuation"]
        self.assertAlmostEqual(p["em_dash"], 2 / 19 * 100, places=3)
        self.assertAlmostEqual(p["semicolon"], 1 / 19 * 100, places=3)
        self.assertAlmostEqual(p["exclamation"], 1 / 19 * 100, places=3)
        self.assertAlmostEqual(p["question"], 1 / 19 * 100, places=3)
        self.assertAlmostEqual(p["comma"], 1 / 19 * 100, places=3)
        self.assertEqual(p["ellipsis"], 0.0)
        self.assertEqual(p["parenthetical"], 0.0)

    def test_function_word_rates(self):
        fw = self.m["function_words"]
        self.assertAlmostEqual(fw["the"], 3 / 19 * 100, places=3)
        self.assertAlmostEqual(fw["it"], 3 / 19 * 100, places=3)
        self.assertAlmostEqual(fw["on"], 1 / 19 * 100, places=3)
        self.assertNotIn("cat", fw)  # content words excluded

    def test_contraction_rate(self):
        self.assertAlmostEqual(self.m["contraction_rate"], 1 / 19 * 100, places=3)

    def test_ttr(self):
        # unique: the cat sat on mat dog a big one barked didn't it did honestly = 14
        self.assertAlmostEqual(self.m["ttr"], 14 / 19, places=3)
        self.assertIn("mattr_50", self.m)  # falls back to ttr on short texts

    def test_frontmatter_stripped(self):
        m2 = stylometry.analyze_text(stylometry.strip_frontmatter(TINY_WITH_FRONTMATTER))
        self.assertEqual(m2["word_count"], 19)


class TestPunchEndings(unittest.TestCase):
    # Punch ending: paragraph's final sentence ≤ max(6, 0.6 × doc mean
    # sentence length) words. Sentences below: 12, 7 | 14, 2 | 13 words →
    # doc mean 9.6, threshold 6. Only "It didn't." (2 words) qualifies:
    # 1 of 3 paragraphs = 33.333%.
    TEXT = (
        "The committee reviewed the annual budget over several long meetings in March. "
        "They found nothing unusual in the numbers.\n\n"
        "Everyone expected the process to drag on for months without any resolution at all. "
        "It didn't.\n\n"
        "The final report was published quietly the following week without any press coverage."
    )

    def test_punch_ending_pct(self):
        m = stylometry.analyze_text(self.TEXT)
        self.assertAlmostEqual(m["paragraphs"]["punch_ending_pct"], 100 / 3, places=3)


class TestCompare(unittest.TestCase):
    def _write(self, d, name, text):
        p = os.path.join(d, name)
        with open(p, "w") as f:
            f.write(text)
        return p

    def test_compare_flags_deviant_marker(self):
        # Author never uses semicolons or exclamations; target uses both heavily.
        with tempfile.TemporaryDirectory() as d:
            a1 = self._write(d, "a1.md", "I like it here. The room is warm, and the light is good. "
                                         "We stay for an hour — maybe two. It works.")
            a2 = self._write(d, "a2.md", "The morning starts slow. I read for a while — an old habit. "
                                         "Coffee helps, and the quiet helps more. It adds up.")
            a3 = self._write(d, "a3.md", "You notice the small things. A door that sticks — the third stair. "
                                         "It becomes a kind of map, and you keep it.")
            t = self._write(d, "t.md", "This is great! The results are amazing; furthermore, the data is clear; "
                                       "indeed, we must celebrate! Wonderful!")
            report = stylometry.compare([a1, a2, a3], t)
            flagged_keys = [f["metric"] for f in report["flagged"]]
            self.assertIn("punctuation.semicolon", flagged_keys)
            self.assertIn("punctuation.exclamation", flagged_keys)
            # z sign: target above author mean
            for f in report["flagged"]:
                if f["metric"] == "punctuation.semicolon":
                    self.assertTrue(f["z"] is None or f["z"] > 0)

    def test_spaced_hyphen_dash_counted_separately(self):
        # Some authors dash with " - " instead of an em-dash (e.g. classic
        # blog style); it must be counted as its own marker, not missed,
        # and not conflated with hyphenated compounds like "well-known".
        m = stylometry.analyze_text("I take this seriously - we all do. A well-known fact — obviously.")
        # 13 words: i take this seriously we all do a well-known fact obviously → recount below
        self.assertAlmostEqual(m["punctuation"]["dash_spaced"],
                               1 / m["word_count"] * 100, places=3)
        self.assertAlmostEqual(m["punctuation"]["em_dash"],
                               1 / m["word_count"] * 100, places=3)

    def test_robust_z_floors_tiny_sd(self):
        # n=3 samples can produce near-zero sd; an on-pattern target that is
        # merely diluted by a longer text must not explode into a huge z.
        # Real case: "here's" rate mean 0.442, sd 0.016, target 0.376 (one
        # use, longer piece) — naive z = -4.13; robust z must stay < 1.5.
        z = stylometry.robust_z(0.442, 0.016, 0.376)
        self.assertLess(abs(z), 1.5)
        # Genuine drift with a healthy sd must remain flagged.
        z2 = stylometry.robust_z(3.246, 0.326, 2.25)
        self.assertGreater(abs(z2), 1.5)
        # ttr-scale sanity: mean 0.642, sd 0.006, target 0.60 → not flagged
        self.assertLess(abs(stylometry.robust_z(0.642, 0.006, 0.60)), 1.5)

    def test_rare_function_words_not_flaggable(self):
        # A function word occurring once in one text ("hence" at 0.1/100w)
        # is sampling noise, not signal — real same-author pairs produced
        # 30+ such false flags. Function words below 0.5/100w on both sides
        # stay in metrics but must not be flagged.
        self.assertFalse(stylometry.is_flaggable("function_words.hence", 0.1, 0.0))
        self.assertFalse(stylometry.is_flaggable("function_words.hence", 0.0, 0.3))
        self.assertTrue(stylometry.is_flaggable("function_words.the", 4.2, 2.0))
        # non-function-word metrics are always flaggable
        self.assertTrue(stylometry.is_flaggable("punctuation.semicolon", 0.0, 0.1))

    def test_cli_analyze_outputs_json(self):
        with tempfile.TemporaryDirectory() as d:
            p = self._write(d, "s.md", TINY)
            out = subprocess.run(
                [sys.executable, os.path.join(HERE, "stylometry.py"), "analyze", p],
                capture_output=True, text=True, check=True)
            data = json.loads(out.stdout)
            self.assertEqual(data["files"][0]["metrics"]["word_count"], 19)


if __name__ == "__main__":
    unittest.main()
