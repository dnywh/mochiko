from learner_frequency import top_learner_words


LANGUAGE = "es"


def top_spanish_words(limit: int) -> list[str]:
    return top_learner_words(LANGUAGE, limit)
