from generate_spanish_frequency_batches import generate_batch, output_paths


def main() -> None:
    start_rank = 1
    end_rank = 20
    rows = generate_batch(start_rank, end_rank)
    for row in rows:
        print(f"{row['rank']:03d}. {row['word']}: {row['sentence']}")
    print("\nWrote:")
    for path in output_paths(start_rank, end_rank):
        print(f"- {path}")


if __name__ == "__main__":
    main()
