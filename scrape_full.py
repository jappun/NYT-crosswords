import csv
import os
import random
import time
from datetime import date, timedelta
from pathlib import Path

import requests
from dotenv import load_dotenv

from extract import extract_clue_answer_pairs


PUZZLE_RANGES = {
    "daily": date(1993, 11, 21),
    "mini": date(2014, 8, 21),
    "midi": date(2026, 2, 25),
}
END_DATE = date.today()
OUTPUT_PATH = Path("data") / "nyt_crosswords_raw.csv"
LOG_PATH = Path("logs") / "scrape_errors.log"
FIELDNAMES = [
    "date",
    "puzzle_type",
    "puzzle_id",
    "clue_number",
    "direction",
    "answer",
    "clue",
]
ROW_KEY_FIELDS = ["date", "puzzle_type", "clue_number", "direction"]


def date_range(start_date: date, end_date: date):
    current_date = start_date
    while current_date <= end_date:
        yield current_date
        current_date += timedelta(days=1)


def row_key(row: dict) -> tuple[str, str, str, str]:
    return tuple(str(row[field]) for field in ROW_KEY_FIELDS)


def load_existing_row_keys() -> set[tuple[str, str, str, str]]:
    if not OUTPUT_PATH.exists():
        return set()

    with OUTPUT_PATH.open("r", newline="", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)
        return {
            row_key(row)
            for row in reader
            if all(row.get(field) for field in ROW_KEY_FIELDS)
        }


def log_error(message: str) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as log_file:
        log_file.write(f"{message}\n")


def fetch_puzzle(
    session: requests.Session,
    puzzle_type: str,
    puzzle_date: date,
    nyt_s_cookie: str,
) -> requests.Response:
    url = (
        f"https://www.nytimes.com/svc/crosswords/v6/puzzle/"
        f"{puzzle_type}/{puzzle_date.isoformat()}.json"
    )
    return session.get(
        url,
        headers={"Cookie": f"NYT-S={nyt_s_cookie}"},
        timeout=30,
    )


def append_rows(rows: list[dict]) -> None:
    if not rows:
        return

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    write_header = not OUTPUT_PATH.exists() or OUTPUT_PATH.stat().st_size == 0

    with OUTPUT_PATH.open("a", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=FIELDNAMES)
        if write_header:
            writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    load_dotenv()
    nyt_s_cookie = os.getenv("NYT_S_COOKIE")
    if not nyt_s_cookie:
        raise RuntimeError("NYT_S_COOKIE is missing from .env")

    existing_row_keys = load_existing_row_keys()
    total_rows_written = 0
    print(f"Loaded {len(existing_row_keys)} existing row keys")

    with requests.Session() as session:
        for puzzle_type, start_date in PUZZLE_RANGES.items():
            print(f"Starting {puzzle_type}: {start_date} to {END_DATE}")

            for puzzle_date in date_range(start_date, END_DATE):
                date_string = puzzle_date.isoformat()

                try:
                    response = fetch_puzzle(
                        session,
                        puzzle_type,
                        puzzle_date,
                        nyt_s_cookie,
                    )

                    if response.status_code != 200:
                        log_error(
                            f"{date_string} {puzzle_type}: HTTP "
                            f"{response.status_code}"
                        )
                        print(
                            f"Skipped {puzzle_type} {date_string}: "
                            f"HTTP {response.status_code}"
                        )
                        continue

                    rows = extract_clue_answer_pairs(response.json(), puzzle_type)
                    new_rows = [
                        row
                        for row in rows
                        if row_key(row) not in existing_row_keys
                    ]
                    append_rows(new_rows)
                    existing_row_keys.update(row_key(row) for row in new_rows)
                    total_rows_written += len(new_rows)
                    print(
                        f"Fetched {puzzle_type} {date_string}: "
                        f"{len(new_rows)} new rows"
                    )
                except Exception as exc:
                    log_error(f"{date_string} {puzzle_type}: {exc}")
                    print(f"Skipped {puzzle_type} {date_string}: {exc}")
                finally:
                    time.sleep(random.uniform(1.0, 2.0))

    print(f"Wrote {total_rows_written} new rows to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
