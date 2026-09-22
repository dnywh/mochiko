import csv
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from subprocess import CompletedProcess
from unittest.mock import patch
from zoneinfo import ZoneInfo


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import daily_frequency as daily


class DailyFrequencyTests(unittest.TestCase):
    def test_committed_banks_contain_complete_valid_trios(self):
        for language in daily.LANGUAGES:
            rows = daily.read_rows(language.bank)
            ranks = sorted({int(row["rank"]) for row in rows})
            self.assertEqual(ranks, list(range(1, daily.CAP_RANK + 1)))
            self.assertEqual(len(rows), daily.CAP_RANK * 3)
            self.assertEqual(len(daily.bank_slice(language, ranks)), daily.CAP_RANK * 3)

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

    def test_recent_activity_reads_nested_mochi_review_dates(self):
        now = datetime(2026, 9, 21, 15, tzinfo=ZoneInfo("Australia/Melbourne"))
        cards = [
            {
                "reviews": [
                    {
                        "date": {"date": "2026-09-20T00:00:00.000Z"},
                        "due": {"date": "2026-09-21T00:00:00.000Z"},
                        "remembered?": True,
                    }
                ]
            }
        ]
        recent, count, latest = daily.recent_activity(cards, 24, now)
        self.assertTrue(recent)
        self.assertEqual(count, 1)
        self.assertEqual(latest, "2026-09-20")

    def test_local_midnight_utc_counts_as_melbourne_study_day(self):
        # Sunday 00:00 in Melbourne is Saturday 14:00 UTC.
        now = datetime(2026, 9, 21, 15, tzinfo=ZoneInfo("Australia/Melbourne"))
        cards = [{"reviews": [{"date": {"date": "2026-09-19T14:00:00.000Z"}}]}]
        recent, count, latest = daily.recent_activity(cards, 24, now)
        self.assertTrue(recent)
        self.assertEqual(count, 1)
        self.assertEqual(latest, "2026-09-20")

    def test_morning_run_needs_yesterdays_melbourne_day(self):
        now = datetime(2026, 9, 22, 7, tzinfo=ZoneInfo("Australia/Melbourne"))
        stale = [{"id": "a", "reviews": [{"date": {"date": "2026-09-20T00:00:00.000Z"}}]}]
        recent, _, latest = daily.recent_activity(stale, 24, now)
        self.assertFalse(recent)
        self.assertEqual(latest, "2026-09-20")
        snapshot = daily.activity_snapshot(stale, 24, now)
        self.assertEqual(snapshot["threshold_day"], "2026-09-21")
        fresh = [{"id": "b", "reviews": [{"date": {"date": "2026-09-21T12:00:00.000Z"}}]}]
        recent, _, latest = daily.recent_activity(fresh, 24, now)
        self.assertTrue(recent)
        self.assertEqual(latest, "2026-09-21")

    def test_recent_activity_reports_old_review_day_without_passing(self):
        now = datetime(2026, 9, 21, 15, tzinfo=ZoneInfo("Australia/Melbourne"))
        cards = [{"reviews": [{"date": {"date": "2026-09-19T00:00:00.000Z"}}]}]
        recent, count, latest = daily.recent_activity(cards, 24, now)
        self.assertFalse(recent)
        self.assertEqual(count, 1)
        self.assertEqual(latest, "2026-09-19")

    def test_local_publish_commits_without_push(self):
        calls = []

        def fake_git(*args, **kwargs):
            calls.append(args)
            if args[:3] == ("diff", "--cached", "--name-only"):
                output = "languages/es/frequency.csv\n"
            elif args == ("rev-parse", "--short", "HEAD"):
                output = "abc1234\n"
            else:
                output = ""
            return CompletedProcess(["git", *args], 0, output, "")

        with patch.object(daily, "git", side_effect=fake_git):
            commit, push = daily.publish("2026-09-10", push=False)

        self.assertEqual((commit, push), ("abc1234", "skipped"))
        self.assertNotIn(("push", "origin", "main"), calls)


if __name__ == "__main__":
    unittest.main()
