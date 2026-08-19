from wordfreq import top_n_list


LANGUAGE = "es"


def top_spanish_words(limit: int) -> list[str]:
    """Return wordfreq tokens in order, excluding digits and other non-words."""
    if limit < 0:
        raise ValueError("limit must be non-negative")
    if limit == 0:
        return []

    candidate_limit = limit
    while True:
        candidates = top_n_list(LANGUAGE, candidate_limit)
        words = [word for word in candidates if word.isalpha()]
        if len(words) >= limit:
            return words[:limit]
        if len(candidates) < candidate_limit:
            raise ValueError(f"wordfreq returned only {len(words)} Spanish word tokens")
        candidate_limit *= 2
