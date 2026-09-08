"""Frequency order for learner banks, preserving the already prepared prefix."""

from wordfreq import top_n_list


# These boundaries are fixed migration points, not the growing source maximum.
# Existing cards and prepared sentences must keep their rank identities.
PRESERVED_PREFIX = {"es": 225, "de": 63}
EXCLUDED = {
    "es": frozenset("méxico españa san the argentina madrid juan os etc vos josé chile venezuela asi".split()),
    "de": frozenset("deutschland berlin the de of usa münchen us eu spd europa bayern hab ne is bzw dr and ii".split()),
}
# wordfreq case-folds German ß to ss. Restore standard spelling for new targets.
SPELLINGS = {
    "de": {"weiss": "weiß", "grosse": "große", "grossen": "großen",
           "heisst": "heißt", "ausserdem": "außerdem", "strasse": "straße",
           "schliesslich": "schließlich", "spass": "spaß", "gross": "groß"},
    "es": {},
}


def top_learner_words(language: str, limit: int) -> list[str]:
    """Keep corpus order; skip letters, listed names, acronyms and foreign noise."""
    if limit < 0:
        raise ValueError("limit must be non-negative")
    if not limit:
        return []
    candidate_limit = max(limit, PRESERVED_PREFIX[language])
    while True:
        candidates = top_n_list(language, candidate_limit)
        alphabetic = [word for word in candidates if word.isalpha()]
        words = []
        for raw_rank, word in enumerate(alphabetic, 1):
            if raw_rank > PRESERVED_PREFIX[language]:
                if len(word) == 1 or word in EXCLUDED[language]:
                    continue
                word = SPELLINGS[language].get(word, word)
            if word not in words:
                words.append(word)
        if len(words) >= limit:
            return words[:limit]
        if len(candidates) < candidate_limit:
            raise ValueError(f"wordfreq returned only {len(words)} learner words for {language}")
        candidate_limit *= 2
