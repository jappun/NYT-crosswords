import csv
import random
import time
from datetime import date, timedelta
from pathlib import Path

import requests
from dotenv import load_dotenv
import os

from extract import extract_clue_answer_pairs


PUZZLE_TYPE = "midi"
START_DATE = date(2026, 6, 1)
END_DATE = date(2026, 6, 28)
OUTPUT_PATH = Path("data") / "validation.csv"
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


def date_range(start_date: date, end_date: date):
    current_date = start_date
    while current_date <= end_date:
        yield current_date
        current_date += timedelta(days=1)


def log_error(message: str) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as log_file:
        log_file.write(f"{message}\n")


def fetch_puzzle(session: requests.Session, puzzle_date: date, nyt_s_cookie: str):
    date_string = puzzle_date.isoformat()
    url = (
        f"https://www.nytimes.com/svc/crosswords/v6/puzzle/"
        f"{PUZZLE_TYPE}/{date_string}.json"
    )
    response = session.get(
        url,
        headers={"Cookie": f"NYT-S={nyt_s_cookie}"},
        timeout=30,
    )
    return url, response


def write_rows(rows: list[dict]) -> None:
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    load_dotenv()
    nyt_s_cookie = os.getenv("NYT_S_COOKIE")
    if not nyt_s_cookie:
        raise RuntimeError("NYT_S_COOKIE is missing from .env")

    rows = []
    with requests.Session() as session:
        for puzzle_date in date_range(START_DATE, END_DATE):
            date_string = puzzle_date.isoformat()

            try:
                _, response = fetch_puzzle(session, puzzle_date, nyt_s_cookie)
                if response.status_code != 200:
                    log_error(
                        f"{date_string} {PUZZLE_TYPE}: HTTP "
                        f"{response.status_code}"
                    )
                    print(f"Skipped {date_string}: HTTP {response.status_code}")
                    continue

                puzzle_rows = extract_clue_answer_pairs(response.json(), PUZZLE_TYPE)
                rows.extend(puzzle_rows)
                print(f"Fetched {date_string}: {len(puzzle_rows)} rows")
            except Exception as exc:
                log_error(f"{date_string} {PUZZLE_TYPE}: {exc}")
                print(f"Skipped {date_string}: {exc}")
            finally:
                time.sleep(random.uniform(1.0, 2.0))

    write_rows(rows)
    print(f"Wrote {len(rows)} rows to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
