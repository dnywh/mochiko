import argparse
import csv
from pathlib import Path

from spanish_frequency import top_spanish_words


LANGUAGE = "es"
LANGUAGE_DIR = Path("languages") / LANGUAGE
SOURCE_PATH = LANGUAGE_DIR / "frequency.csv"
OUTPUT_DIR = Path("outputs")
FIELDNAMES = ["rank", "word", "sentence", "tags"]

SENTENCES = {
    "de": "Soy {{de}} Perú.",
    "la": "Veo {{la}} casa.",
    "que": "Sé {{que}} puedes.",
    "el": "Leo {{el}} libro.",
    "en": "Vivo {{en}} Lima.",
    "y": "Ana {{y}} Luis comen.",
    "a": "Voy {{a}} casa.",
    "los": "Veo {{los}} niños.",
    "no": "Yo {{no}} quiero café.",
    "un": "Tengo {{un}} perro.",
    "se": "Ella {{se}} lava las manos.",
    "por": "Camino {{por}} el parque.",
    "es": "Madrid {{es}} grande.",
    "del": "Vengo {{del}} mercado.",
    "las": "Veo {{las}} flores rojas.",
    "con": "Estudio {{con}} Marta.",
    "una": "Quiero {{una}} manzana.",
    "para": "Este regalo es {{para}} ti.",
    "lo": "No {{lo}} entiendo.",
    "su": "Veo {{su}} casa pequeña.",
    "al": "Voy {{al}} parque.",
    "como": "Trabajo {{como}} maestro.",
    "me": "Ella {{me}} llama.",
    "más": "Quiero {{más}} agua.",
    "si": "Voy {{si}} puedo.",
    "pero": "Quiero ir, {{pero}} no puedo.",
    "te": "Yo {{te}} veo.",
    "o": "Quiero té {{o}} café.",
    "mi": "Esta es {{mi}} casa.",
    "le": "Yo {{le}} doy agua.",
    "este": "Uso {{este}} lápiz.",
    "sus": "Veo {{sus}} libros.",
    "esta": "Vivo en {{esta}} ciudad.",
    "todo": "Leo {{todo}} el día.",
    "ya": "Ella {{ya}} llegó.",
    "ha": "Ella {{ha}} comido.",
    "cuando": "Llámame {{cuando}} llegues.",
    "yo": "Lo hago {{yo}}.",
    "ser": "Quiero {{ser}} médico.",
    "son": "Ellos {{son}} amigos.",
}


def validate_sentence(word: str, sentence: str) -> None:
    markers = ["{{" + word + "}}", "{{" + word.capitalize() + "}}"]
    total = sum(sentence.count(marker) for marker in markers)
    if total != 1:
        raise ValueError(f"{word!r} must appear as exactly one cloze in {sentence!r}")
    if sentence.count("{{") != 1 or sentence.count("}}") != 1:
        raise ValueError(f"{word!r} must have exactly one cloze pair in {sentence!r}")


def batch_filename(start_rank: int, end_rank: int) -> str:
    return f"frequency_{start_rank:03d}_{end_rank:03d}.csv"


def preview_path(start_rank: int, end_rank: int) -> Path:
    return OUTPUT_DIR / f"spanish_{batch_filename(start_rank, end_rank)}"


def build_rows(start_rank: int, end_rank: int) -> list[dict[str, str | int]]:
    words = top_spanish_words(end_rank)[start_rank - 1 : end_rank]
    rows = []
    tag = f"rank-{start_rank:03d}-{end_rank:03d}"
    for rank, word in enumerate(words, start=start_rank):
        if word not in SENTENCES:
            raise KeyError(f"No sentence defined for rank {rank}: {word!r}")
        sentence = SENTENCES[word]
        validate_sentence(word, sentence)
        rows.append(
            {
                "rank": rank,
                "word": word,
                "sentence": sentence,
                "tags": f"frequency;generated;{tag}",
            }
        )
    return rows


def write_csv(path: Path, rows: list[dict[str, str | int]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def generate_batch(start_rank: int, end_rank: int) -> list[dict[str, str | int]]:
    rows = build_rows(start_rank, end_rank)
    existing = []
    if SOURCE_PATH.exists():
        with SOURCE_PATH.open(newline="", encoding="utf-8") as f:
            existing = list(csv.DictReader(f))
    by_rank = {int(row["rank"]): row for row in existing}
    by_rank.update({int(row["rank"]): row for row in rows})
    write_csv(SOURCE_PATH, [by_rank[rank] for rank in sorted(by_rank)])
    write_csv(preview_path(start_rank, end_rank), rows)
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start-rank", type=int, default=1)
    parser.add_argument("--end-rank", type=int, default=20)
    args = parser.parse_args()

    rows = generate_batch(args.start_rank, args.end_rank)
    for row in rows:
        print(f"{row['rank']:03d}. {row['word']}: {row['sentence']}")
    print("\nWrote:")
    print(f"- {SOURCE_PATH}")
    print(f"- {preview_path(args.start_rank, args.end_rank)}")


if __name__ == "__main__":
    main()
