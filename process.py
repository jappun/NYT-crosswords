from pathlib import Path

import pandas as pd


RAW_PATH = Path("data") / "nyt_crosswords_raw.csv"
CLEAN_PATH = Path("data") / "nyt_crosswords_clean.csv"
FREQUENCIES_PATH = Path("data") / "word_frequencies.csv"
YEARLY_FREQUENCIES_PATH = Path("data") / "word_frequencies_by_year.csv"

SORT_COLUMNS = ["date", "puzzle_type", "clue_number", "direction"]
DEDUPE_COLUMNS = [*SORT_COLUMNS, "answer"]
PUZZLE_TYPES = ["daily", "mini", "midi"]
FREQUENCY_COLUMNS = [
    "answer",
    "total",
    "daily_count",
    "mini_count",
    "midi_count",
    "avg_per_100_daily",
    "avg_per_100_mini",
    "avg_per_100_midi",
]
YEARLY_FREQUENCY_COLUMNS = ["year", *FREQUENCY_COLUMNS]


def clean_raw_data(raw: pd.DataFrame) -> pd.DataFrame:
    clean = raw.copy()
    clean["answer"] = clean["answer"].fillna("").astype(str).str.strip().str.upper()
    clean["clue"] = clean["clue"].fillna("").astype(str).str.strip()

    clean = clean[(clean["answer"] != "") & (clean["clue"] != "")]
    clean = clean.drop_duplicates(subset=DEDUPE_COLUMNS, keep="first")
    clean = clean.sort_values(SORT_COLUMNS).reset_index(drop=True)
    return clean


def aggregate_frequencies(clean: pd.DataFrame) -> pd.DataFrame:
    puzzle_counts = clean.groupby("puzzle_type")["date"].nunique().to_dict()
    grouped = clean.groupby("answer")

    frequencies = pd.DataFrame({"answer": grouped.size().index})
    frequencies["total"] = grouped.size().values

    for puzzle_type in PUZZLE_TYPES:
        counts = (
            clean[clean["puzzle_type"] == puzzle_type]
            .groupby("answer")
            .size()
            .rename(f"{puzzle_type}_count")
        )
        frequencies = frequencies.merge(
            counts,
            on="answer",
            how="left",
        )
        count_column = f"{puzzle_type}_count"
        rate_column = f"avg_per_100_{puzzle_type}"
        frequencies[count_column] = frequencies[count_column].fillna(0).astype(int)
        puzzle_total = puzzle_counts.get(puzzle_type, 0)
        frequencies[rate_column] = (
            frequencies[count_column] / puzzle_total * 100
            if puzzle_total
            else 0.0
        )

    return frequencies[FREQUENCY_COLUMNS].sort_values(
        ["total", "answer"],
        ascending=[False, True],
    )


def aggregate_yearly_frequencies(clean: pd.DataFrame) -> pd.DataFrame:
    yearly = clean.copy()
    yearly["year"] = pd.to_datetime(yearly["date"]).dt.year.astype(int)

    puzzle_counts = (
        yearly.groupby(["year", "puzzle_type"])["date"]
        .nunique()
        .rename("puzzle_count")
    )
    grouped = yearly.groupby(["year", "answer"])
    frequencies = grouped.size().rename("total").reset_index()

    for puzzle_type in PUZZLE_TYPES:
        counts = (
            yearly[yearly["puzzle_type"] == puzzle_type]
            .groupby(["year", "answer"])
            .size()
            .rename(f"{puzzle_type}_count")
            .reset_index()
        )
        frequencies = frequencies.merge(
            counts,
            on=["year", "answer"],
            how="left",
        )
        count_column = f"{puzzle_type}_count"
        rate_column = f"avg_per_100_{puzzle_type}"
        frequencies[count_column] = frequencies[count_column].fillna(0).astype(int)

        denominator = frequencies["year"].map(
            lambda year: puzzle_counts.get((year, puzzle_type), 0)
        )
        frequencies[rate_column] = (
            frequencies[count_column]
            .div(denominator.where(denominator != 0))
            .fillna(0)
            * 100
        )

    return frequencies[YEARLY_FREQUENCY_COLUMNS].sort_values(
        ["year", "total", "answer"],
        ascending=[True, False, True],
    )


def main() -> None:
    raw = pd.read_csv(RAW_PATH, dtype=str, keep_default_na=False)
    clean = clean_raw_data(raw)

    rows_in = len(raw)
    rows_out = len(clean)
    rows_dropped = rows_in - rows_out

    clean.to_csv(CLEAN_PATH, index=False)
    aggregate_frequencies(clean).to_csv(FREQUENCIES_PATH, index=False)
    aggregate_yearly_frequencies(clean).to_csv(YEARLY_FREQUENCIES_PATH, index=False)

    print(f"Total rows in: {rows_in:,}")
    print(f"Rows dropped: {rows_dropped:,}")
    print(f"Rows out: {rows_out:,}")
    print(f"Wrote {CLEAN_PATH}")
    print(f"Wrote {FREQUENCIES_PATH}")
    print(f"Wrote {YEARLY_FREQUENCIES_PATH}")


if __name__ == "__main__":
    main()
