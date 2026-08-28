import csv
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import daily_frequency as daily


class DailyFrequencyTests(unittest.TestCase):
    def test_committed_banks_contain_complete_valid_trios(self):
        for language in daily.LANGUAGES:
            rows = daily.read_rows(language.bank)
            ranks = sorted({int(row["rank"]) for row in rows})
            self.assertEqual(len(ranks), 30)
            self.assertEqual(len(rows), 90)
            self.assertEqual(len(daily.bank_slice(language, ranks)), 90)

    def test_source_writer_supports_legacy_and_three_variant_rows(self):
        rows = [
            {"rank": "1", "word": "uno", "sentence": "{{Uno}}.", "tags": "old"},
            {"rank": "2", "variant": "2", "word": "dos", "sentence": "{{Dos}}.", "tags": "new"},
        ]
        normalised = [{**row, "variant": row.get("variant") or "1"} for row in rows]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "frequency.csv"
            daily.write_rows(path, normalised)
            with path.open(newline="", encoding="utf-8") as handle:
                written = list(csv.DictReader(handle))
        self.assertEqual([row["variant"] for row in written], ["1", "2"])

    def test_partial_trio_counts_as_one_started_word(self):
        language = daily.LANGUAGES[0]
        now = datetime(2026, 8, 28, 9, tzinfo=ZoneInfo("Australia/Melbourne"))
        cards = [
            {
                "deck-id": language.deck_id,
                "created-at": {"date": "2026-08-28T08:00:00+10:00"},
                "manual-tags": ["frequency-rank-196", "variant-1"],
            }
        ]
        self.assertEqual(daily.started_today(cards, language, now), {196})
        self.assertEqual(daily.approved_ranks(196, {196}, 1), [196])

    def test_partial_german_batch_recovers_all_started_ranks(self):
        self.assertEqual(daily.approved_ranks(34, {34, 35, 36}, 3), [34, 35, 36])
        self.assertEqual(daily.approved_ranks(34, {34}, 3), [34, 35, 36])

    def test_sentence_requires_one_target_cloze(self):
        daily.validate_sentence("aber", "Ich bin müde, {{aber}} glücklich.")
        with self.assertRaises(ValueError):
            daily.validate_sentence("aber", "{{aber}} und {{aber}}")
        with self.assertRaises(ValueError):
            daily.validate_sentence("sein", "Das muss {{sein}} Schlüssel sein.")


if __name__ == "__main__":
    unittest.main()
