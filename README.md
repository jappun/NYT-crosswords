# NYT Crossword Word Frequency Dashboard

I kept seeing **OREO** in the Midi. After the third or fourth time I wondered whether that was just me, or whether the NYT really leans on it that hard. So I pulled ~30 years of crossword data and built a dashboard to find out.

**Answer:** OREO shows up **428 times** in this dataset (402 Daily, 24 Mini, 2 Midi) — about **3.4 times per 100 Daily puzzles**. It's the 37th most common answer overall. Not imaginary.

This repo scrapes NYT Daily / Mini / Midi puzzles, cleans the clue–answer rows, aggregates word frequencies (raw + per-100-puzzle rates), and serves them in a Streamlit app.

**Repo:** [github.com/jappun/NYT-crosswords](https://github.com/jappun/NYT-crosswords)

---

## What's in the data

| Coverage | Range |
|----------|--------|
| Daily | 1993-11-21 → 2026-06-28 (~11.9k puzzles) |
| Mini | 2014-08-21 → 2026-06-28 (~4.3k puzzles) |
| Midi | 2026-02-25 → 2026-06-28 (~124 puzzles) |

- **~1.04M** clue–answer rows
- **~132k** unique answers
- Frequencies include raw counts **and** rates per 100 puzzles (so Midi isn't unfairly dwarfed by decades of Daily)

Committed frequency files:

- `data/word_frequencies.csv` — one row per answer
- `data/word_frequencies_by_year.csv` — same breakdown by year

Raw/clean clue–answer CSVs are generated locally (gitignored; large).

---

## How I made it

- Noticed OREO repeating in Midi and wanted a real count across Daily / Mini / Midi
- Mapped the NYT crossword JSON API (cookie-auth) and how answers are reconstructed from grid cells + clues
- Wrote an extractor (`extract.py`), validated on Midi, then scraped the full date ranges with retries / resume (`scrape_full.py`)
- Cleaned blanks, handled a few weird historical / visual / letter-swap puzzles (`process.py`, notes in `NOTES.md`)
- Aggregated overall + yearly frequencies with per-type normalized rates
- Built a Streamlit dashboard to browse top answers, filter by type/year/length, and look up any word (`dashboard.py`)

---

## Quick start

```bash
python -m venv venv
# Windows
venv\Scripts\activate
# macOS/Linux
# source venv/bin/activate

pip install -r requirements.txt
streamlit run dashboard.py
```

The dashboard reads the committed frequency CSVs — no scrape required to explore.

### Rebuilding the dataset (optional)

1. Copy `.env.example` → `.env` and set `NYT_S_COOKIE` (from browser DevTools → Network → any puzzle `.json` request → Cookie header).
2. `python scrape_validation.py` — small Midi smoke test
3. `python scrape_full.py` — full scrape (long-running; resumes if interrupted)
4. `python process.py` — clean + aggregate frequencies

Cookie expires every few weeks; a fresh 403 usually means refresh it.

---

## Project layout

```
extract.py              # JSON → clue/answer rows
scrape_validation.py    # Midi validation scrape
scrape_full.py          # Full Daily / Mini / Midi scrape
process.py              # Clean + frequency tables
dashboard.py            # Streamlit UI
NOTES.md                # Edge cases in the data
PLAN.md                 # Build plan / phase checklist
data/
  word_frequencies.csv
  word_frequencies_by_year.csv
```

---

## License

Code is MIT (see `LICENSE`). Puzzle content belongs to The New York Times — this project is for personal / research exploration of derived frequencies, not redistribution of NYT puzzles.
