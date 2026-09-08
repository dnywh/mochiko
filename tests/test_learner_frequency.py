import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import daily_frequency as daily
from learner_frequency import EXCLUDED, PRESERVED_PREFIX, SPELLINGS, top_learner_words
from wordfreq import top_n_list


class LearnerFrequencyTests(unittest.TestCase):
    def test_existing_source_rank_identities_and_sentences_are_preserved(self):
        for language in daily.LANGUAGES:
            words = daily.words_for(language)
            bank = {
                (row["rank"], row["variant"]): row
                for row in daily.read_rows(language.bank)
            }
            for row in daily.read_rows(language.source):
                self.assertEqual(words[int(row["rank"])], row["word"])
                self.assertEqual(bank[row["rank"], row["variant"]], row)

    def test_prepared_prefix_keeps_original_corpus_ranks(self):
        for code, boundary in PRESERVED_PREFIX.items():
            original = [w for w in top_n_list(code, 1000) if w.isalpha()]
            actual = top_learner_words(code, 500)
            self.assertEqual(actual[:boundary], original[:boundary])
            for limit in (0, 1, boundary, boundary + 1, 499):
                self.assertEqual(top_learner_words(code, limit), actual[:limit])

    def test_new_words_follow_filtered_corpus_order_without_noise(self):
        for code, boundary in PRESERVED_PREFIX.items():
            original = [w for w in top_n_list(code, 2000) if w.isalpha()]
            actual = top_learner_words(code, 500)
            self.assertEqual(len(set(actual)), 500)
            new_words = actual[boundary:]
            self.assertTrue(all(len(word) > 1 for word in new_words))
            self.assertFalse(set(new_words) & EXCLUDED[code])
            corpus_spellings = {v: k for k, v in SPELLINGS[code].items()}
            indices = [original.index(corpus_spellings.get(word, word)) for word in new_words]
            self.assertEqual(indices, sorted(indices))
        german = top_learner_words("de", 500)
        self.assertNotIn("usa", german)
        self.assertNotIn("the", german)
        self.assertNotIn("a", german)
        self.assertIn("weiß", german)
        self.assertIn("straße", german)
        self.assertNotIn("weiss", german)
        self.assertNotIn("os", top_learner_words("es", 500))

    def test_negative_limit_is_rejected(self):
        for code in PRESERVED_PREFIX:
            with self.assertRaises(ValueError):
                top_learner_words(code, -1)


if __name__ == "__main__":
    unittest.main()
