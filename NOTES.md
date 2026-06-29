# Dataset Notes

This project extracts clue and answer rows from NYT crossword puzzle JSON. Most puzzles use standard Across and Down clues, but a few historical puzzles use visual or otherwise non-standard clue mechanics. These notes document the known cases found during scraping and cleaning.

## Dropped Rows

Phase 2 cleaning drops rows where `answer` or `clue` is empty after trimming whitespace. In the current raw dataset, this removes 15 rows:

- `1995-12-10` daily, puzzle id `8960`: six theme rows have answer text but blank clue text in the API response.
- `2006-03-09` daily, puzzle id `2731`: nine rows have blank clue text and non-standard-looking answer strings. This appears to be a special puzzle representation that does not map cleanly to normal clue-answer rows.

These rows are excluded from `data/nyt_crosswords_clean.csv` and downstream frequency files because keeping blank clues would make the row-level dataset misleading.

## Letter-Swap Midi Clues

The `2026-03-09` midi puzzle, "Run It Back", includes clue text with right-arrow and left-arrow readings. The grid answer is the rightward answer typed by the solver, while the leftward reading describes an alternate word produced by swapping two letters.

For these rows, extraction keeps the grid answer as `answer` and stores both clue readings in `clue`, using this format:

```text
right-side clue / left-side clue (swap two letters for alternate answer)
```

Example:

```text
answer: UNITED
clue: Together / Loose (swap two letters for alternate answer)
```

The alternate readings, such as `UNTIED`, are not counted as separate answers because they are not grid entries.

## Visual Daily Clues

The `2018-09-27` daily puzzle uses visual print-only clue elements for four theme answers. In the JSON, those clues have formatted blank text (`&nbsp;`) plus a puzzle-level `notes` field explaining the visual elements.

Extraction stores these as normal rows and prefixes the note-derived clue text with `visual clue:`.

Example:

```text
answer: FILLINTHEBLANKS
clue: visual clue: each square in the answer has a thick underscore at the bottom
```

## Non-Standard Directions

Some historical daily puzzles include directions beyond `Across` and `Down`, such as `Diagonal`, `Diamond`, `Heart`, and `Around`. These are intentional NYT puzzle mechanics, not extraction errors.

Phase 2 deduplicates rows using:

```text
date + puzzle_type + clue_number + direction + answer
```

The `answer` field is included because some special puzzles have multiple distinct answers sharing the same date, clue number, and direction. For example, the `2007-07-01` daily Diamond puzzle has four distinct Diamond answers with clue number `0`; all should remain in the cleaned dataset.
