# NYT Crossword Word Frequency Dashboard — Project Plan

This file is the single source of truth for Cursor. Work through each phase and step in order.
**Stop and wait for human approval before moving to the next step.**
Commit at the end of every step with the suggested commit message.

---

## Project structure

```
nyt-crossword-data/
  .env                        # NYT_S_COOKIE=... (never committed)
  .env.example                # placeholder, committed
  .gitignore
  README.md
  PLAN.md                     # this file
  scrape_validation.py        # Phase 1.2
  scrape_full.py              # Phase 1.3
  process.py                  # Phase 2
  dashboard.py                # Phase 3
  data/
    validation.csv            # Phase 1.2 output
    nyt_crosswords_raw.csv    # Phase 1.3 output
    nyt_crosswords_clean.csv  # Phase 2 output
    word_frequencies.csv      # Phase 2 output
  logs/
    scrape_errors.log
```

---

## Data source

All puzzle data comes from the NYT's unofficial API (the same one their app uses):

```
https://www.nytimes.com/svc/crosswords/v6/puzzle/{puzzle_type}/{YYYY-MM-DD}.json
```

Where `puzzle_type` is one of: `daily`, `mini`, `midi`.

Authentication is via the `NYT-S` cookie, passed as a request header:
```python
headers = {"Cookie": f"NYT-S={NYT_S_COOKIE}"}
```

The cookie is stored in `.env` as `NYT_S_COOKIE` and loaded with `python-dotenv`. It expires every few weeks — if requests start returning 403, grab a fresh one from browser devtools (Network tab → any `.json` request → Cookie header).

---

## API response structure (critical — read before writing any extraction code)

The JSON response has this shape (simplified):

```
{
  "id": 23938,
  "publicationDate": "2026-06-02",
  "subcategory": 2,
  "body": [
    {
      "cells": [...],   // array of cell objects, one per grid square, indexed by position
      "clues": [...],   // flat array of all clue objects (both Across and Down)
      "clueLists": [
        { "name": "Across", "clues": [0, 1, 2, ...] },
        { "name": "Down",   "clues": [5, 6, 7, ...] }
      ]
    }
  ]
}
```

### Cell objects

Black/blocked squares are empty objects `{}`. Non-black cells look like:

```json
{
  "answer": "S",
  "clues": [1, 8],
  "label": "4",
  "type": 1
}
```

- `answer`: single letter
- `clues`: array of exactly 2 integers — these are **indices into `body[0].clues`**, one for the Across clue this cell belongs to, one for the Down clue

### Clue objects

```json
{
  "cells": [5, 6, 7, 8, 9],
  "direction": "Across",
  "label": "4",
  "text": [{ "plain": "Turn down an offer" }]
}
```

- `cells`: array of cell indices (into `body[0].cells`) that make up this word, in order
- `text[0].plain`: the clue string
- `direction`: "Across" or "Down"
- `label`: clue number as a string (e.g. "4")

### How to reconstruct a word's answer

The answer is **not stored directly on the clue**. Reconstruct it like this:

```python
answer = "".join(body["cells"][i]["answer"] for i in clue["cells"])
```

Example: clue with `cells: [2, 3, 4]` → `cells[2].answer + cells[3].answer + cells[4].answer` → `"SUP"`

### Extraction function signature

```python
def extract_clue_answer_pairs(data: dict, puzzle_type: str) -> list[dict]:
    """
    Returns a list of row dicts with keys:
      date, puzzle_type, puzzle_id, clue_number, direction, answer, clue
    """
```

Where:
- `date` comes from `data["publicationDate"]`
- `puzzle_id` comes from `data["id"]`
- `clue_number` is `clue["label"]`
- `direction` is `clue["direction"]`
- `answer` is reconstructed from cells as above
- `clue` is `clue["text"][0]["plain"]`

Skip any clue where any referenced cell is missing an `answer` key (black square or edge case).

---

## Output CSV schema

```
date, puzzle_type, puzzle_id, clue_number, direction, answer, clue
```

`date + puzzle_type + clue_number + direction` is the natural unique key.
`puzzle_id` enables deduplication and joining back to raw API data.

---

## Puzzle type date ranges

| puzzle_type | Start date  | Notes |
|-------------|-------------|-------|
| `daily`     | 1993-11-21  | Daily launched November 1993 |
| `mini`      | 2014-08-21  | Mini launched August 2014 |
| `midi`      | 2026-02-25  | Midi launched February 2026 |

---

## PHASE 0 — Project setup

**Prompt:**
> "I have set up a folder project `NYT-crossword-data`. Create the folder structure shown in PLAN.md. Create a `.gitignore` that excludes `.env`, `__pycache__/`, `*.csv`, `venv/`, and `logs/`. Create a `.env.example` with `NYT_S_COOKIE=your_cookie_here`. Create a minimal `README.md`. Initialize a git repo and make the first commit."

**Human step:** Copy `.env.example` to `.env` and paste your real `NYT-S` cookie value.

**Checkpoint:** Confirm `.env` exists locally and is listed in `.gitignore` before proceeding.

**Commit:** `chore: initial project setup`

---

## PHASE 1 — Dataset collection

### Step 1.1 — Extraction function

**Prompt:**
> "Using the data structure described in PLAN.md, write a function `extract_clue_answer_pairs(data, puzzle_type)` in a file called `extract.py`. It should return a list of row dicts with the schema in PLAN.md. Skip cells missing an `answer` key. After writing the function, test it on the following hardcoded JSON (paste the mini JSON below) and print all extracted rows.: {
  "body": [
    {
      "board": "\u003Csvg xmlns=\"http://www.w3.org/2000/svg\" xmlns:xlink=\"http://www.w3.org/1999/xlink\" viewBox=\"0 0 506 506\" style=\"font-family:helvetica,arial,sans-serif;\"\u003E\u003Cdefs\u003E\u003Cg id=\"checked\"\u003E\u003Cpath d=\"M103 3 3 103z\" class=\"slash\" /\u003E\u003C/g\u003E\u003Cg id=\"modified\"\u003E\u003Cpath d=\"M103 3H69.67L103 36.33z\" class=\"flag\" /\u003E\u003C/g\u003E\u003Cg id=\"revealed\"\u003E\u003Cpath d=\"M103 3H69.67L103 36.33z\" class=\"flag\" /\u003E\u003Ccircle cx=\"93.24\" cy=\"12.76\" r=\"4.88\" class=\"tatter\" /\u003E\u003C/g\u003E\u003C/defs\u003E\u003Cg class=\"cells\"\u003E\u003Cg data-index=\"0\"\u003E\u003Cpath d=\"M3 3h1e2v1e2H3z\" fill=\"#000\" class=\"cell\"/\u003E\u003C/g\u003E\u003Cg data-index=\"1\"\u003E\u003Cpath d=\"M103 3h1e2v1e2H103z\" fill=\"#000\" class=\"cell\"/\u003E\u003C/g\u003E\u003Cg data-index=\"2\"\u003E\u003Cpath d=\"M203 3h1e2v1e2H203z\" fill=\"none\" class=\"cell\"/\u003E\u003Ctext x=\"205\" y=\"36.83\" text-anchor=\"start\" font-size=\"33.33\" class=\"label\" \u003E1\u003C/text\u003E\u003Ctext x=\"253\" y=\"94.67\" text-anchor=\"middle\" font-size=\"66.67\" class=\"guess\"/\u003E\u003C/g\u003E\u003Cg data-index=\"3\"\u003E\u003Cpath d=\"M303 3h1e2v1e2H303z\" fill=\"none\" class=\"cell\"/\u003E\u003Ctext x=\"305\" y=\"36.83\" text-anchor=\"start\" font-size=\"33.33\" class=\"label\" \u003E2\u003C/text\u003E\u003Ctext x=\"353\" y=\"94.67\" text-anchor=\"middle\" font-size=\"66.67\" class=\"guess\"/\u003E\u003C/g\u003E\u003Cg data-index=\"4\"\u003E\u003Cpath d=\"M403 3h1e2v1e2H403z\" fill=\"none\" class=\"cell\"/\u003E\u003Ctext x=\"405\" y=\"36.83\" text-anchor=\"start\" font-size=\"33.33\" class=\"label\" \u003E3\u003C/text\u003E\u003Ctext x=\"453\" y=\"94.67\" text-anchor=\"middle\" font-size=\"66.67\" class=\"guess\"/\u003E\u003C/g\u003E\u003Cg data-index=\"5\"\u003E\u003Cpath d=\"M3 103h1e2v1e2H3z\" fill=\"none\" class=\"cell\"/\u003E\u003Ctext x=\"5\" y=\"136.83\" text-anchor=\"start\" font-size=\"33.33\" class=\"label\" \u003E4\u003C/text\u003E\u003Ctext x=\"53\" y=\"194.67\" text-anchor=\"middle\" font-size=\"66.67\" class=\"guess\"/\u003E\u003C/g\u003E\u003Cg data-index=\"6\"\u003E\u003Cpath d=\"M103 103h1e2v1e2H103z\" fill=\"none\" class=\"cell\"/\u003E\u003Ctext x=\"105\" y=\"136.83\" text-anchor=\"start\" font-size=\"33.33\" class=\"label\" \u003E5\u003C/text\u003E\u003Ctext x=\"153\" y=\"194.67\" text-anchor=\"middle\" font-size=\"66.67\" class=\"guess\"/\u003E\u003C/g\u003E\u003Cg data-index=\"7\"\u003E\u003Cpath d=\"M203 103h1e2v1e2H203z\" fill=\"none\" class=\"cell\"/\u003E\u003Ctext x=\"253\" y=\"194.67\" text-anchor=\"middle\" font-size=\"66.67\" class=\"guess\"/\u003E\u003C/g\u003E\u003Cg data-index=\"8\"\u003E\u003Cpath d=\"M303 103h1e2v1e2H303z\" fill=\"none\" class=\"cell\"/\u003E\u003Ctext x=\"353\" y=\"194.67\" text-anchor=\"middle\" font-size=\"66.67\" class=\"guess\"/\u003E\u003C/g\u003E\u003Cg data-index=\"9\"\u003E\u003Cpath d=\"M403 103h1e2v1e2H403z\" fill=\"none\" class=\"cell\"/\u003E\u003Ctext x=\"453\" y=\"194.67\" text-anchor=\"middle\" font-size=\"66.67\" class=\"guess\"/\u003E\u003C/g\u003E\u003Cg data-index=\"10\"\u003E\u003Cpath d=\"M3 203h1e2v1e2H3z\" fill=\"none\" class=\"cell\"/\u003E\u003Ctext x=\"5\" y=\"236.83\" text-anchor=\"start\" font-size=\"33.33\" class=\"label\" \u003E6\u003C/text\u003E\u003Ctext x=\"53\" y=\"294.67\" text-anchor=\"middle\" font-size=\"66.67\" class=\"guess\"/\u003E\u003C/g\u003E\u003Cg data-index=\"11\"\u003E\u003Cpath d=\"M103 203h1e2v1e2H103z\" fill=\"none\" class=\"cell\"/\u003E\u003Ctext x=\"153\" y=\"294.67\" text-anchor=\"middle\" font-size=\"66.67\" class=\"guess\"/\u003E\u003C/g\u003E\u003Cg data-index=\"12\"\u003E\u003Cpath d=\"M203 203h1e2v1e2H203z\" fill=\"none\" class=\"cell\"/\u003E\u003Ctext x=\"253\" y=\"294.67\" text-anchor=\"middle\" font-size=\"66.67\" class=\"guess\"/\u003E\u003C/g\u003E\u003Cg data-index=\"13\"\u003E\u003Cpath d=\"M303 203h1e2v1e2H303z\" fill=\"none\" class=\"cell\"/\u003E\u003Ctext x=\"353\" y=\"294.67\" text-anchor=\"middle\" font-size=\"66.67\" class=\"guess\"/\u003E\u003C/g\u003E\u003Cg data-index=\"14\"\u003E\u003Cpath d=\"M403 203h1e2v1e2H403z\" fill=\"none\" class=\"cell\"/\u003E\u003Ctext x=\"453\" y=\"294.67\" text-anchor=\"middle\" font-size=\"66.67\" class=\"guess\"/\u003E\u003C/g\u003E\u003Cg data-index=\"15\"\u003E\u003Cpath d=\"M3 303h1e2v1e2H3z\" fill=\"none\" class=\"cell\"/\u003E\u003Ctext x=\"5\" y=\"336.83\" text-anchor=\"start\" font-size=\"33.33\" class=\"label\" \u003E7\u003C/text\u003E\u003Ctext x=\"53\" y=\"394.67\" text-anchor=\"middle\" font-size=\"66.67\" class=\"guess\"/\u003E\u003C/g\u003E\u003Cg data-index=\"16\"\u003E\u003Cpath d=\"M103 303h1e2v1e2H103z\" fill=\"none\" class=\"cell\"/\u003E\u003Ctext x=\"153\" y=\"394.67\" text-anchor=\"middle\" font-size=\"66.67\" class=\"guess\"/\u003E\u003C/g\u003E\u003Cg data-index=\"17\"\u003E\u003Cpath d=\"M203 303h1e2v1e2H203z\" fill=\"none\" class=\"cell\"/\u003E\u003Ctext x=\"253\" y=\"394.67\" text-anchor=\"middle\" font-size=\"66.67\" class=\"guess\"/\u003E\u003C/g\u003E\u003Cg data-index=\"18\"\u003E\u003Cpath d=\"M303 303h1e2v1e2H303z\" fill=\"none\" class=\"cell\"/\u003E\u003Ctext x=\"353\" y=\"394.67\" text-anchor=\"middle\" font-size=\"66.67\" class=\"guess\"/\u003E\u003C/g\u003E\u003Cg data-index=\"19\"\u003E\u003Cpath d=\"M403 303h1e2v1e2H403z\" fill=\"none\" class=\"cell\"/\u003E\u003Ctext x=\"453\" y=\"394.67\" text-anchor=\"middle\" font-size=\"66.67\" class=\"guess\"/\u003E\u003C/g\u003E\u003Cg data-index=\"20\"\u003E\u003Cpath d=\"M3 403h1e2v1e2H3z\" fill=\"none\" class=\"cell\"/\u003E\u003Ctext x=\"5\" y=\"436.83\" text-anchor=\"start\" font-size=\"33.33\" class=\"label\" \u003E8\u003C/text\u003E\u003Ctext x=\"53\" y=\"494.67\" text-anchor=\"middle\" font-size=\"66.67\" class=\"guess\"/\u003E\u003C/g\u003E\u003Cg data-index=\"21\"\u003E\u003Cpath d=\"M103 403h1e2v1e2H103z\" fill=\"none\" class=\"cell\"/\u003E\u003Ctext x=\"153\" y=\"494.67\" text-anchor=\"middle\" font-size=\"66.67\" class=\"guess\"/\u003E\u003C/g\u003E\u003Cg data-index=\"22\"\u003E\u003Cpath d=\"M203 403h1e2v1e2H203z\" fill=\"none\" class=\"cell\"/\u003E\u003Ctext x=\"253\" y=\"494.67\" text-anchor=\"middle\" font-size=\"66.67\" class=\"guess\"/\u003E\u003C/g\u003E\u003Cg data-index=\"23\"\u003E\u003Cpath d=\"M303 403h1e2v1e2H303z\" fill=\"#000\" class=\"cell\"/\u003E\u003C/g\u003E\u003Cg data-index=\"24\"\u003E\u003Cpath d=\"M403 403h1e2v1e2H403z\" fill=\"#000\" class=\"cell\"/\u003E\u003C/g\u003E\u003C/g\u003E\u003Cg class=\"grid\"\u003E\u003Cpath d=\"M3 103h5e2M3 203h5e2M3 303h5e2M3 403h5e2M103 3v5e2M203 3v5e2M303 3v5e2M403 3v5e2\" stroke=\"dimgray\" fill=\"none\" vector-effect=\"non-scaling-stroke\" class=\"lines\" /\u003E\u003Cpath d=\"M1.5 1.5h503v503H1.5z\" fill=\"none\" stroke=\"#000\" stroke-width=\"3\" class=\"frame\" /\u003E\u003C/g\u003E\u003C/svg\u003E",
      "cells": [
        {

        },
        {

        },
        {
          "answer": "S",
          "clues": [0, 5],
          "label": "1",
          "type": 1
        },
        {
          "answer": "U",
          "clues": [0, 6],
          "label": "2",
          "type": 1
        },
        {
          "answer": "P",
          "clues": [0, 7],
          "label": "3",
          "type": 1
        },
        {
          "answer": "S",
          "clues": [1, 8],
          "label": "4",
          "type": 1
        },
        {
          "answer": "A",
          "clues": [1, 9],
          "label": "5",
          "type": 1
        },
        {
          "answer": "Y",
          "clues": [1, 5],
          "type": 1
        },
        {
          "answer": "N",
          "clues": [1, 6],
          "type": 1
        },
        {
          "answer": "O",
          "clues": [1, 7],
          "type": 1
        },
        {
          "answer": "E",
          "clues": [2, 8],
          "label": "6",
          "type": 1
        },
        {
          "answer": "U",
          "clues": [2, 9],
          "type": 1
        },
        {
          "answer": "R",
          "clues": [2, 5],
          "type": 1
        },
        {
          "answer": "O",
          "clues": [2, 6],
          "type": 1
        },
        {
          "answer": "S",
          "clues": [2, 7],
          "type": 1
        },
        {
          "answer": "C",
          "clues": [3, 8],
          "label": "7",
          "type": 1
        },
        {
          "answer": "R",
          "clues": [3, 9],
          "type": 1
        },
        {
          "answer": "U",
          "clues": [3, 5],
          "type": 1
        },
        {
          "answer": "S",
          "clues": [3, 6],
          "type": 1
        },
        {
          "answer": "T",
          "clues": [3, 7],
          "type": 1
        },
        {
          "answer": "T",
          "clues": [4, 8],
          "label": "8",
          "type": 1
        },
        {
          "answer": "A",
          "clues": [4, 9],
          "type": 1
        },
        {
          "answer": "P",
          "clues": [4, 5],
          "type": 1
        },
        {

        },
        {

        }
      ],
      "clueLists": [
        {
          "clues": [0, 1, 2, 3, 4],
          "name": "Across"
        },
        {
          "clues": [5, 6, 7, 8, 9],
          "name": "Down"
        }
      ],
      "clues": [
        {
          "cells": [2, 3, 4],
          "direction": "Across",
          "label": "1",
          "text": [
            {
              "plain": "Slangy greeting"
            }
          ]
        },
        {
          "cells": [5, 6, 7, 8, 9],
          "direction": "Across",
          "label": "4",
          "text": [
            {
              "plain": "Turn down an offer"
            }
          ]
        },
        {
          "cells": [10, 11, 12, 13, 14],
          "direction": "Across",
          "label": "6",
          "text": [
            {
              "plain": "Banknotes across the Atlantic"
            }
          ]
        },
        {
          "cells": [15, 16, 17, 18, 19],
          "direction": "Across",
          "label": "7",
          "text": [
            {
              "plain": "Part of pizza that roughly 20% of people don't eat, according to YouGov polling"
            }
          ]
        },
        {
          "cells": [20, 21, 22],
          "direction": "Across",
          "label": "8",
          "text": [
            {
              "plain": "Interact with a smartphone screen"
            }
          ]
        },
        {
          "cells": [2, 7, 12, 17, 22],
          "direction": "Down",
          "label": "1",
          "list": 1,
          "text": [
            {
              "plain": "Many a Starbucks flavoring"
            }
          ]
        },
        {
          "cells": [3, 8, 13, 18],
          "direction": "Down",
          "label": "2",
          "list": 1,
          "text": [
            {
              "plain": "\"___, dos, tres, catorce!\" (famously inaccurate start to U2's \"Vertigo\")"
            }
          ]
        },
        {
          "cells": [4, 9, 14, 19],
          "direction": "Down",
          "label": "3",
          "list": 1,
          "text": [
            {
              "plain": "Tweet, e.g."
            }
          ]
        },
        {
          "cells": [5, 10, 15, 20],
          "direction": "Down",
          "label": "4",
          "list": 1,
          "text": [
            {
              "plain": "Religious offshoot"
            }
          ]
        },
        {
          "cells": [6, 11, 16, 21],
          "direction": "Down",
          "label": "5",
          "list": 1,
          "text": [
            {
              "plain": "Overall vibe"
            }
          ]
        }
      ],
      "dimensions": {
        "height": 5,
        "width": 5
      },
      "SVG": {
        "name": "svg",
        "attributes": [
          {
            "name": "xmlns",
            "value": "http://www.w3.org/2000/svg"
          },
          {
            "name": "viewBox",
            "value": "0 0 506.00 506.00"
          }
        ],
        "children": [
          {
            "name": "defs",
            "children": [
              {
                "name": "g",
                "attributes": [
                  {
                    "name": "id",
                    "value": "checked"
                  }
                ],
                "children": [
                  {
                    "name": "line",
                    "attributes": [
                      {
                        "name": "x1",
                        "value": "103.00"
                      },
                      {
                        "name": "y1",
                        "value": "3.00"
                      },
                      {
                        "name": "x2",
                        "value": "3.00"
                      },
                      {
                        "name": "y2",
                        "value": "103.00"
                      },
                      {
                        "name": "class",
                        "value": "slash"
                      }
                    ]
                  }
                ]
              },
              {
                "name": "g",
                "attributes": [
                  {
                    "name": "id",
                    "value": "modified"
                  }
                ],
                "children": [
                  {
                    "name": "polygon",
                    "attributes": [
                      {
                        "name": "points",
                        "value": "103.00,3.00 69.67,3.00 103.00,36.33"
                      },
                      {
                        "name": "class",
                        "value": "flag"
                      }
                    ]
                  }
                ]
              },
              {
                "name": "g",
                "attributes": [
                  {
                    "name": "id",
                    "value": "revealed"
                  }
                ],
                "children": [
                  {
                    "name": "polygon",
                    "attributes": [
                      {
                        "name": "points",
                        "value": "103.00,3.00 69.67,3.00 103.00,36.33"
                      },
                      {
                        "name": "class",
                        "value": "flag"
                      }
                    ]
                  },
                  {
                    "name": "circle",
                    "attributes": [
                      {
                        "name": "cx",
                        "value": "93.24"
                      },
                      {
                        "name": "cy",
                        "value": "12.76"
                      },
                      {
                        "name": "r",
                        "value": "4.88"
                      },
                      {
                        "name": "class",
                        "value": "tatter"
                      }
                    ]
                  }
                ]
              }
            ]
          },
          {
            "name": "g",
            "attributes": [
              {
                "name": "data-group",
                "value": "cells"
              }
            ],
            "children": [
              {
                "name": "g",
                "children": [
                  {
                    "name": "rect",
                    "attributes": [
                      {
                        "name": "x",
                        "value": "3.00"
                      },
                      {
                        "name": "y",
                        "value": "3.00"
                      },
                      {
                        "name": "width",
                        "value": "100.00"
                      },
                      {
                        "name": "height",
                        "value": "100.00"
                      },
                      {
                        "name": "fill",
                        "value": "black"
                      }
                    ]
                  }
                ]
              },
              {
                "name": "g",
                "children": [
                  {
                    "name": "rect",
                    "attributes": [
                      {
                        "name": "x",
                        "value": "103.00"
                      },
                      {
                        "name": "y",
                        "value": "3.00"
                      },
                      {
                        "name": "width",
                        "value": "100.00"
                      },
                      {
                        "name": "height",
                        "value": "100.00"
                      },
                      {
                        "name": "fill",
                        "value": "black"
                      }
                    ]
                  }
                ]
              },
              {
                "name": "g",
                "children": [
                  {
                    "name": "rect",
                    "attributes": [
                      {
                        "name": "x",
                        "value": "203.00"
                      },
                      {
                        "name": "y",
                        "value": "3.00"
                      },
                      {
                        "name": "width",
                        "value": "100.00"
                      },
                      {
                        "name": "height",
                        "value": "100.00"
                      },
                      {
                        "name": "fill",
                        "value": "none"
                      }
                    ]
                  },
                  {
                    "name": "text",
                    "attributes": [
                      {
                        "name": "x",
                        "value": "205.00"
                      },
                      {
                        "name": "y",
                        "value": "36.83"
                      },
                      {
                        "name": "text-anchor",
                        "value": "start"
                      },
                      {
                        "name": "font-size",
                        "value": "33.33"
                      }
                    ],
                    "content": "1"
                  },
                  {
                    "name": "text",
                    "attributes": [
                      {
                        "name": "x",
                        "value": "253.00"
                      },
                      {
                        "name": "y",
                        "value": "94.67"
                      },
                      {
                        "name": "text-anchor",
                        "value": "middle"
                      },
                      {
                        "name": "font-size",
                        "value": "66.67"
                      }
                    ]
                  }
                ]
              },
              {
                "name": "g",
                "children": [
                  {
                    "name": "rect",
                    "attributes": [
                      {
                        "name": "x",
                        "value": "303.00"
                      },
                      {
                        "name": "y",
                        "value": "3.00"
                      },
                      {
                        "name": "width",
                        "value": "100.00"
                      },
                      {
                        "name": "height",
                        "value": "100.00"
                      },
                      {
                        "name": "fill",
                        "value": "none"
                      }
                    ]
                  },
                  {
                    "name": "text",
                    "attributes": [
                      {
                        "name": "x",
                        "value": "305.00"
                      },
                      {
                        "name": "y",
                        "value": "36.83"
                      },
                      {
                        "name": "text-anchor",
                        "value": "start"
                      },
                      {
                        "name": "font-size",
                        "value": "33.33"
                      }
                    ],
                    "content": "2"
                  },
                  {
                    "name": "text",
                    "attributes": [
                      {
                        "name": "x",
                        "value": "353.00"
                      },
                      {
                        "name": "y",
                        "value": "94.67"
                      },
                      {
                        "name": "text-anchor",
                        "value": "middle"
                      },
                      {
                        "name": "font-size",
                        "value": "66.67"
                      }
                    ]
                  }
                ]
              },
              {
                "name": "g",
                "children": [
                  {
                    "name": "rect",
                    "attributes": [
                      {
                        "name": "x",
                        "value": "403.00"
                      },
                      {
                        "name": "y",
                        "value": "3.00"
                      },
                      {
                        "name": "width",
                        "value": "100.00"
                      },
                      {
                        "name": "height",
                        "value": "100.00"
                      },
                      {
                        "name": "fill",
                        "value": "none"
                      }
                    ]
                  },
                  {
                    "name": "text",
                    "attributes": [
                      {
                        "name": "x",
                        "value": "405.00"
                      },
                      {
                        "name": "y",
                        "value": "36.83"
                      },
                      {
                        "name": "text-anchor",
                        "value": "start"
                      },
                      {
                        "name": "font-size",
                        "value": "33.33"
                      }
                    ],
                    "content": "3"
                  },
                  {
                    "name": "text",
                    "attributes": [
                      {
                        "name": "x",
                        "value": "453.00"
                      },
                      {
                        "name": "y",
                        "value": "94.67"
                      },
                      {
                        "name": "text-anchor",
                        "value": "middle"
                      },
                      {
                        "name": "font-size",
                        "value": "66.67"
                      }
                    ]
                  }
                ]
              },
              {
                "name": "g",
                "children": [
                  {
                    "name": "rect",
                    "attributes": [
                      {
                        "name": "x",
                        "value": "3.00"
                      },
                      {
                        "name": "y",
                        "value": "103.00"
                      },
                      {
                        "name": "width",
                        "value": "100.00"
                      },
                      {
                        "name": "height",
                        "value": "100.00"
                      },
                      {
                        "name": "fill",
                        "value": "none"
                      }
                    ]
                  },
                  {
                    "name": "text",
                    "attributes": [
                      {
                        "name": "x",
                        "value": "5.00"
                      },
                      {
                        "name": "y",
                        "value": "136.83"
                      },
                      {
                        "name": "text-anchor",
                        "value": "start"
                      },
                      {
                        "name": "font-size",
                        "value": "33.33"
                      }
                    ],
                    "content": "4"
                  },
                  {
                    "name": "text",
                    "attributes": [
                      {
                        "name": "x",
                        "value": "53.00"
                      },
                      {
                        "name": "y",
                        "value": "194.67"
                      },
                      {
                        "name": "text-anchor",
                        "value": "middle"
                      },
                      {
                        "name": "font-size",
                        "value": "66.67"
                      }
                    ]
                  }
                ]
              },
              {
                "name": "g",
                "children": [
                  {
                    "name": "rect",
                    "attributes": [
                      {
                        "name": "x",
                        "value": "103.00"
                      },
                      {
                        "name": "y",
                        "value": "103.00"
                      },
                      {
                        "name": "width",
                        "value": "100.00"
                      },
                      {
                        "name": "height",
                        "value": "100.00"
                      },
                      {
                        "name": "fill",
                        "value": "none"
                      }
                    ]
                  },
                  {
                    "name": "text",
                    "attributes": [
                      {
                        "name": "x",
                        "value": "105.00"
                      },
                      {
                        "name": "y",
                        "value": "136.83"
                      },
                      {
                        "name": "text-anchor",
                        "value": "start"
                      },
                      {
                        "name": "font-size",
                        "value": "33.33"
                      }
                    ],
                    "content": "5"
                  },
                  {
                    "name": "text",
                    "attributes": [
                      {
                        "name": "x",
                        "value": "153.00"
                      },
                      {
                        "name": "y",
                        "value": "194.67"
                      },
                      {
                        "name": "text-anchor",
                        "value": "middle"
                      },
                      {
                        "name": "font-size",
                        "value": "66.67"
                      }
                    ]
                  }
                ]
              },
              {
                "name": "g",
                "children": [
                  {
                    "name": "rect",
                    "attributes": [
                      {
                        "name": "x",
                        "value": "203.00"
                      },
                      {
                        "name": "y",
                        "value": "103.00"
                      },
                      {
                        "name": "width",
                        "value": "100.00"
                      },
                      {
                        "name": "height",
                        "value": "100.00"
                      },
                      {
                        "name": "fill",
                        "value": "none"
                      }
                    ]
                  },
                  {
                    "name": "text",
                    "attributes": [
                      {
                        "name": "x",
                        "value": "253.00"
                      },
                      {
                        "name": "y",
                        "value": "194.67"
                      },
                      {
                        "name": "text-anchor",
                        "value": "middle"
                      },
                      {
                        "name": "font-size",
                        "value": "66.67"
                      }
                    ]
                  }
                ]
              },
              {
                "name": "g",
                "children": [
                  {
                    "name": "rect",
                    "attributes": [
                      {
                        "name": "x",
                        "value": "303.00"
                      },
                      {
                        "name": "y",
                        "value": "103.00"
                      },
                      {
                        "name": "width",
                        "value": "100.00"
                      },
                      {
                        "name": "height",
                        "value": "100.00"
                      },
                      {
                        "name": "fill",
                        "value": "none"
                      }
                    ]
                  },
                  {
                    "name": "text",
                    "attributes": [
                      {
                        "name": "x",
                        "value": "353.00"
                      },
                      {
                        "name": "y",
                        "value": "194.67"
                      },
                      {
                        "name": "text-anchor",
                        "value": "middle"
                      },
                      {
                        "name": "font-size",
                        "value": "66.67"
                      }
                    ]
                  }
                ]
              },
              {
                "name": "g",
                "children": [
                  {
                    "name": "rect",
                    "attributes": [
                      {
                        "name": "x",
                        "value": "403.00"
                      },
                      {
                        "name": "y",
                        "value": "103.00"
                      },
                      {
                        "name": "width",
                        "value": "100.00"
                      },
                      {
                        "name": "height",
                        "value": "100.00"
                      },
                      {
                        "name": "fill",
                        "value": "none"
                      }
                    ]
                  },
                  {
                    "name": "text",
                    "attributes": [
                      {
                        "name": "x",
                        "value": "453.00"
                      },
                      {
                        "name": "y",
                        "value": "194.67"
                      },
                      {
                        "name": "text-anchor",
                        "value": "middle"
                      },
                      {
                        "name": "font-size",
                        "value": "66.67"
                      }
                    ]
                  }
                ]
              },
              {
                "name": "g",
                "children": [
                  {
                    "name": "rect",
                    "attributes": [
                      {
                        "name": "x",
                        "value": "3.00"
                      },
                      {
                        "name": "y",
                        "value": "203.00"
                      },
                      {
                        "name": "width",
                        "value": "100.00"
                      },
                      {
                        "name": "height",
                        "value": "100.00"
                      },
                      {
                        "name": "fill",
                        "value": "none"
                      }
                    ]
                  },
                  {
                    "name": "text",
                    "attributes": [
                      {
                        "name": "x",
                        "value": "5.00"
                      },
                      {
                        "name": "y",
                        "value": "236.83"
                      },
                      {
                        "name": "text-anchor",
                        "value": "start"
                      },
                      {
                        "name": "font-size",
                        "value": "33.33"
                      }
                    ],
                    "content": "6"
                  },
                  {
                    "name": "text",
                    "attributes": [
                      {
                        "name": "x",
                        "value": "53.00"
                      },
                      {
                        "name": "y",
                        "value": "294.67"
                      },
                      {
                        "name": "text-anchor",
                        "value": "middle"
                      },
                      {
                        "name": "font-size",
                        "value": "66.67"
                      }
                    ]
                  }
                ]
              },
              {
                "name": "g",
                "children": [
                  {
                    "name": "rect",
                    "attributes": [
                      {
                        "name": "x",
                        "value": "103.00"
                      },
                      {
                        "name": "y",
                        "value": "203.00"
                      },
                      {
                        "name": "width",
                        "value": "100.00"
                      },
                      {
                        "name": "height",
                        "value": "100.00"
                      },
                      {
                        "name": "fill",
                        "value": "none"
                      }
                    ]
                  },
                  {
                    "name": "text",
                    "attributes": [
                      {
                        "name": "x",
                        "value": "153.00"
                      },
                      {
                        "name": "y",
                        "value": "294.67"
                      },
                      {
                        "name": "text-anchor",
                        "value": "middle"
                      },
                      {
                        "name": "font-size",
                        "value": "66.67"
                      }
                    ]
                  }
                ]
              },
              {
                "name": "g",
                "children": [
                  {
                    "name": "rect",
                    "attributes": [
                      {
                        "name": "x",
                        "value": "203.00"
                      },
                      {
                        "name": "y",
                        "value": "203.00"
                      },
                      {
                        "name": "width",
                        "value": "100.00"
                      },
                      {
                        "name": "height",
                        "value": "100.00"
                      },
                      {
                        "name": "fill",
                        "value": "none"
                      }
                    ]
                  },
                  {
                    "name": "text",
                    "attributes": [
                      {
                        "name": "x",
                        "value": "253.00"
                      },
                      {
                        "name": "y",
                        "value": "294.67"
                      },
                      {
                        "name": "text-anchor",
                        "value": "middle"
                      },
                      {
                        "name": "font-size",
                        "value": "66.67"
                      }
                    ]
                  }
                ]
              },
              {
                "name": "g",
                "children": [
                  {
                    "name": "rect",
                    "attributes": [
                      {
                        "name": "x",
                        "value": "303.00"
                      },
                      {
                        "name": "y",
                        "value": "203.00"
                      },
                      {
                        "name": "width",
                        "value": "100.00"
                      },
                      {
                        "name": "height",
                        "value": "100.00"
                      },
                      {
                        "name": "fill",
                        "value": "none"
                      }
                    ]
                  },
                  {
                    "name": "text",
                    "attributes": [
                      {
                        "name": "x",
                        "value": "353.00"
                      },
                      {
                        "name": "y",
                        "value": "294.67"
                      },
                      {
                        "name": "text-anchor",
                        "value": "middle"
                      },
                      {
                        "name": "font-size",
                        "value": "66.67"
                      }
                    ]
                  }
                ]
              },
              {
                "name": "g",
                "children": [
                  {
                    "name": "rect",
                    "attributes": [
                      {
                        "name": "x",
                        "value": "403.00"
                      },
                      {
                        "name": "y",
                        "value": "203.00"
                      },
                      {
                        "name": "width",
                        "value": "100.00"
                      },
                      {
                        "name": "height",
                        "value": "100.00"
                      },
                      {
                        "name": "fill",
                        "value": "none"
                      }
                    ]
                  },
                  {
                    "name": "text",
                    "attributes": [
                      {
                        "name": "x",
                        "value": "453.00"
                      },
                      {
                        "name": "y",
                        "value": "294.67"
                      },
                      {
                        "name": "text-anchor",
                        "value": "middle"
                      },
                      {
                        "name": "font-size",
                        "value": "66.67"
                      }
                    ]
                  }
                ]
              },
              {
                "name": "g",
                "children": [
                  {
                    "name": "rect",
                    "attributes": [
                      {
                        "name": "x",
                        "value": "3.00"
                      },
                      {
                        "name": "y",
                        "value": "303.00"
                      },
                      {
                        "name": "width",
                        "value": "100.00"
                      },
                      {
                        "name": "height",
                        "value": "100.00"
                      },
                      {
                        "name": "fill",
                        "value": "none"
                      }
                    ]
                  },
                  {
                    "name": "text",
                    "attributes": [
                      {
                        "name": "x",
                        "value": "5.00"
                      },
                      {
                        "name": "y",
                        "value": "336.83"
                      },
                      {
                        "name": "text-anchor",
                        "value": "start"
                      },
                      {
                        "name": "font-size",
                        "value": "33.33"
                      }
                    ],
                    "content": "7"
                  },
                  {
                    "name": "text",
                    "attributes": [
                      {
                        "name": "x",
                        "value": "53.00"
                      },
                      {
                        "name": "y",
                        "value": "394.67"
                      },
                      {
                        "name": "text-anchor",
                        "value": "middle"
                      },
                      {
                        "name": "font-size",
                        "value": "66.67"
                      }
                    ]
                  }
                ]
              },
              {
                "name": "g",
                "children": [
                  {
                    "name": "rect",
                    "attributes": [
                      {
                        "name": "x",
                        "value": "103.00"
                      },
                      {
                        "name": "y",
                        "value": "303.00"
                      },
                      {
                        "name": "width",
                        "value": "100.00"
                      },
                      {
                        "name": "height",
                        "value": "100.00"
                      },
                      {
                        "name": "fill",
                        "value": "none"
                      }
                    ]
                  },
                  {
                    "name": "text",
                    "attributes": [
                      {
                        "name": "x",
                        "value": "153.00"
                      },
                      {
                        "name": "y",
                        "value": "394.67"
                      },
                      {
                        "name": "text-anchor",
                        "value": "middle"
                      },
                      {
                        "name": "font-size",
                        "value": "66.67"
                      }
                    ]
                  }
                ]
              },
              {
                "name": "g",
                "children": [
                  {
                    "name": "rect",
                    "attributes": [
                      {
                        "name": "x",
                        "value": "203.00"
                      },
                      {
                        "name": "y",
                        "value": "303.00"
                      },
                      {
                        "name": "width",
                        "value": "100.00"
                      },
                      {
                        "name": "height",
                        "value": "100.00"
                      },
                      {
                        "name": "fill",
                        "value": "none"
                      }
                    ]
                  },
                  {
                    "name": "text",
                    "attributes": [
                      {
                        "name": "x",
                        "value": "253.00"
                      },
                      {
                        "name": "y",
                        "value": "394.67"
                      },
                      {
                        "name": "text-anchor",
                        "value": "middle"
                      },
                      {
                        "name": "font-size",
                        "value": "66.67"
                      }
                    ]
                  }
                ]
              },
              {
                "name": "g",
                "children": [
                  {
                    "name": "rect",
                    "attributes": [
                      {
                        "name": "x",
                        "value": "303.00"
                      },
                      {
                        "name": "y",
                        "value": "303.00"
                      },
                      {
                        "name": "width",
                        "value": "100.00"
                      },
                      {
                        "name": "height",
                        "value": "100.00"
                      },
                      {
                        "name": "fill",
                        "value": "none"
                      }
                    ]
                  },
                  {
                    "name": "text",
                    "attributes": [
                      {
                        "name": "x",
                        "value": "353.00"
                      },
                      {
                        "name": "y",
                        "value": "394.67"
                      },
                      {
                        "name": "text-anchor",
                        "value": "middle"
                      },
                      {
                        "name": "font-size",
                        "value": "66.67"
                      }
                    ]
                  }
                ]
              },
              {
                "name": "g",
                "children": [
                  {
                    "name": "rect",
                    "attributes": [
                      {
                        "name": "x",
                        "value": "403.00"
                      },
                      {
                        "name": "y",
                        "value": "303.00"
                      },
                      {
                        "name": "width",
                        "value": "100.00"
                      },
                      {
                        "name": "height",
                        "value": "100.00"
                      },
                      {
                        "name": "fill",
                        "value": "none"
                      }
                    ]
                  },
                  {
                    "name": "text",
                    "attributes": [
                      {
                        "name": "x",
                        "value": "453.00"
                      },
                      {
                        "name": "y",
                        "value": "394.67"
                      },
                      {
                        "name": "text-anchor",
                        "value": "middle"
                      },
                      {
                        "name": "font-size",
                        "value": "66.67"
                      }
                    ]
                  }
                ]
              },
              {
                "name": "g",
                "children": [
                  {
                    "name": "rect",
                    "attributes": [
                      {
                        "name": "x",
                        "value": "3.00"
                      },
                      {
                        "name": "y",
                        "value": "403.00"
                      },
                      {
                        "name": "width",
                        "value": "100.00"
                      },
                      {
                        "name": "height",
                        "value": "100.00"
                      },
                      {
                        "name": "fill",
                        "value": "none"
                      }
                    ]
                  },
                  {
                    "name": "text",
                    "attributes": [
                      {
                        "name": "x",
                        "value": "5.00"
                      },
                      {
                        "name": "y",
                        "value": "436.83"
                      },
                      {
                        "name": "text-anchor",
                        "value": "start"
                      },
                      {
                        "name": "font-size",
                        "value": "33.33"
                      }
                    ],
                    "content": "8"
                  },
                  {
                    "name": "text",
                    "attributes": [
                      {
                        "name": "x",
                        "value": "53.00"
                      },
                      {
                        "name": "y",
                        "value": "494.67"
                      },
                      {
                        "name": "text-anchor",
                        "value": "middle"
                      },
                      {
                        "name": "font-size",
                        "value": "66.67"
                      }
                    ]
                  }
                ]
              },
              {
                "name": "g",
                "children": [
                  {
                    "name": "rect",
                    "attributes": [
                      {
                        "name": "x",
                        "value": "103.00"
                      },
                      {
                        "name": "y",
                        "value": "403.00"
                      },
                      {
                        "name": "width",
                        "value": "100.00"
                      },
                      {
                        "name": "height",
                        "value": "100.00"
                      },
                      {
                        "name": "fill",
                        "value": "none"
                      }
                    ]
                  },
                  {
                    "name": "text",
                    "attributes": [
                      {
                        "name": "x",
                        "value": "153.00"
                      },
                      {
                        "name": "y",
                        "value": "494.67"
                      },
                      {
                        "name": "text-anchor",
                        "value": "middle"
                      },
                      {
                        "name": "font-size",
                        "value": "66.67"
                      }
                    ]
                  }
                ]
              },
              {
                "name": "g",
                "children": [
                  {
                    "name": "rect",
                    "attributes": [
                      {
                        "name": "x",
                        "value": "203.00"
                      },
                      {
                        "name": "y",
                        "value": "403.00"
                      },
                      {
                        "name": "width",
                        "value": "100.00"
                      },
                      {
                        "name": "height",
                        "value": "100.00"
                      },
                      {
                        "name": "fill",
                        "value": "none"
                      }
                    ]
                  },
                  {
                    "name": "text",
                    "attributes": [
                      {
                        "name": "x",
                        "value": "253.00"
                      },
                      {
                        "name": "y",
                        "value": "494.67"
                      },
                      {
                        "name": "text-anchor",
                        "value": "middle"
                      },
                      {
                        "name": "font-size",
                        "value": "66.67"
                      }
                    ]
                  }
                ]
              },
              {
                "name": "g",
                "children": [
                  {
                    "name": "rect",
                    "attributes": [
                      {
                        "name": "x",
                        "value": "303.00"
                      },
                      {
                        "name": "y",
                        "value": "403.00"
                      },
                      {
                        "name": "width",
                        "value": "100.00"
                      },
                      {
                        "name": "height",
                        "value": "100.00"
                      },
                      {
                        "name": "fill",
                        "value": "black"
                      }
                    ]
                  }
                ]
              },
              {
                "name": "g",
                "children": [
                  {
                    "name": "rect",
                    "attributes": [
                      {
                        "name": "x",
                        "value": "403.00"
                      },
                      {
                        "name": "y",
                        "value": "403.00"
                      },
                      {
                        "name": "width",
                        "value": "100.00"
                      },
                      {
                        "name": "height",
                        "value": "100.00"
                      },
                      {
                        "name": "fill",
                        "value": "black"
                      }
                    ]
                  }
                ]
              }
            ]
          },
          {
            "name": "g",
            "attributes": [
              {
                "name": "data-group",
                "value": "grid"
              }
            ],
            "children": [
              {
                "name": "path",
                "attributes": [
                  {
                    "name": "d",
                    "value": "M3.00,103.00 l500.00,0.00 M3.00,203.00 l500.00,0.00 M3.00,303.00 l500.00,0.00 M3.00,403.00 l500.00,0.00 M103.00,3.00 l0.00,500.00 M203.00,3.00 l0.00,500.00 M303.00,3.00 l0.00,500.00 M403.00,3.00 l0.00,500.00"
                  },
                  {
                    "name": "stroke",
                    "value": "dimgray"
                  },
                  {
                    "name": "fill",
                    "value": "none"
                  },
                  {
                    "name": "vector-effect",
                    "value": "non-scaling-stroke"
                  }
                ]
              },
              {
                "name": "rect",
                "attributes": [
                  {
                    "name": "x",
                    "value": "1.50"
                  },
                  {
                    "name": "y",
                    "value": "1.50"
                  },
                  {
                    "name": "width",
                    "value": "503.00"
                  },
                  {
                    "name": "height",
                    "value": "503.00"
                  },
                  {
                    "name": "fill",
                    "value": "none"
                  },
                  {
                    "name": "stroke",
                    "value": "black"
                  },
                  {
                    "name": "stroke-width",
                    "value": "3.00"
                  }
                ]
              }
            ]
          }
        ],
        "styles": [
          {
            "name": "font-family",
            "value": "helvetica,arial,sans-serif"
          }
        ]
      }
    }
  ],
  "constructors": [
    "Joel Fagliano"
  ],
  "copyright": "2026",
  "id": 23938,
  "lastUpdated": "0001-01-01 00:00:00 +0000 UTC",
  "publicationDate": "2026-06-02",
  "subcategory": 2
}"


**Human step:** Read the printed output. Verify that:
- Across answers spell real words
- Clue text matches the answer
- No rows have empty answers or missing fields

**Commit:** `feat: extraction function`

---

### Step 1.2 — Validation scrape (Midi, ~30 puzzles)

**Prompt:**
> "Write `scrape_validation.py` that:
> 1. Loads `NYT_S_COOKIE` from `.env` using `python-dotenv`
> 2. Loops over every date from 2026-06-01 to 2026-06-28
> 3. Fetches `https://www.nytimes.com/svc/crosswords/v6/puzzle/midi/{date}.json` with the cookie header
> 4. Calls `extract_clue_answer_pairs()` from `extract.py` on each response
> 5. Appends rows to a list; writes to `data/validation.csv` at the end
> 6. Logs any non-200 responses to `logs/scrape_errors.log` and skips that date
> 7. Sleeps a random 1.0–2.0 seconds between requests"

**Human step:** Open `data/validation.csv`. Spot-check at least 10 rows:
- Do the answers look like real words?
- Do the clues match the answers?
- Are there any obviously garbled or null rows?

Only proceed to Step 1.3 after this passes.

**Commit:** `feat: validation scrape`

---

### Step 1.3 — Full scrape

**Prompt:**
> "Write `scrape_full.py` that runs three scrape loops using the date ranges in PLAN.md:
> - daily: 1993-11-21 to today
> - mini: 2014-08-21 to today
> - midi: 2026-02-25 to today
>
> For each date and puzzle type, fetch the puzzle JSON, call `extract_clue_answer_pairs()`, and append rows to `data/nyt_crosswords_raw.csv`.
>
> On startup, load existing natural row keys (`date + puzzle_type + clue_number + direction`) from the CSV. For each fetched puzzle, append only rows whose natural key is missing so interrupted puzzle writes can resume without losing partial rows or creating duplicates.
>
> Log all errors and skipped dates to `logs/scrape_errors.log`. Sleep 1.0–2.0 seconds randomly between every request."

**Human step:** Let it run (expect ~2-3 hours total). Check `logs/scrape_errors.log` when done — a handful of 404s for missing dates is normal; a flood of 403s means the cookie expired and needs refreshing.

**Commit:** `feat: full scrape`

---

## PHASE 2 — Data cleaning and frequency aggregation

**Prompt:**
> "Write `process.py` that does two things:
>
> **Part 1 — Clean:**
> Read `data/nyt_crosswords_raw.csv`. Drop rows where `answer` or `clue` is null or empty. Uppercase all `answer` values. Drop duplicate rows (same `date + puzzle_type + clue_number + direction`). Write to `data/nyt_crosswords_clean.csv`. Print a summary: total rows in, rows dropped, rows out.
>
> **Part 2 — Overall frequency aggregation:**
> From the cleaned data, compute per-word frequency counts. For each unique `answer`, count:
> - `total`: appearances across all puzzle types
> - `daily_count`: appearances in daily puzzles only
> - `mini_count`: appearances in mini puzzles only
> - `midi_count`: appearances in midi puzzles only
> - `avg_per_100_daily`, `avg_per_100_mini`, `avg_per_100_midi`: normalized rate per 100 puzzles of that type (total puzzles of that type = number of distinct dates for that type in the dataset)
>
> Write to `data/word_frequencies.csv` with columns:
> `answer, total, daily_count, mini_count, midi_count, avg_per_100_daily, avg_per_100_mini, avg_per_100_midi`
>
> **Part 3 — Yearly frequency aggregation:**
> Add a `year` derived from `date`. For each `year + answer`, compute the same count and normalized-rate columns as the overall aggregation, where normalized rates use the number of distinct puzzle dates for that puzzle type within that year.
>
> Write to `data/word_frequencies_by_year.csv` with columns:
> `year, answer, total, daily_count, mini_count, midi_count, avg_per_100_daily, avg_per_100_mini, avg_per_100_midi`"

The normalized columns matter because Midi only has ~16 months of data vs. years of Daily and Mini — raw counts would make Midi words look rare even if they repeat constantly.

**Human step:** Sanity check `word_frequencies.csv`:
- OREO should rank very high
- ERA, AREA, ALOE, OREO should all be in the top 20
- Midi normalized rates should be meaningfully comparable to Daily rates despite fewer puzzles

**Commit:** `feat: cleaning and frequency aggregation`

---

## PHASE 3 — Dashboard

**Stack: Streamlit** (single Python file, no frontend build step, free deployment on Streamlit Cloud later).

**Prompt:**
> "Write `dashboard.py` as a Streamlit app that reads `data/word_frequencies.csv` and `data/word_frequencies_by_year.csv`. Build the following UI:
>
> **Sidebar controls:**
> - Multiselect: puzzle type filter — options: Daily, Mini, Midi — defaults to all three selected
> - Selectbox: year filter — options: All years plus only years that have data for the currently selected puzzle type filter. Defaults to All years. Selecting a year shows top/bottom words within that year only.
> - Toggle: Raw count vs. Per 100 puzzles (normalized)
> - Slider: number of words to show N (10–100, default 50)
> - Toggle: Most frequent / Least frequent
>
> **Main area:**
> - A horizontal bar chart (using Plotly or Altair — not Matplotlib) of the top or bottom N words by the selected frequency metric, filtered to selected puzzle types, and selected year The bar length represents the computed frequency for the selected puzzle type combination and year selection.
> - Below the chart: a search box. Type a word (e.g. OREO) and see a small grouped bar chart showing its raw count and normalized rate broken down by Daily / Mini / Midi.
>
> When multiple puzzle types are selected, sum their raw counts for the main chart. For normalized view, average their per-100 rates.
>
> Add a note at the top: 'Midi data starts Feb 2026. Normalized rates (per 100 puzzles) are recommended for cross-type comparisons.'"

**Human step:** Run `streamlit run dashboard.py`, search for OREO, toggle between puzzle types, verify it feels right.

**Commit:** `feat: streamlit dashboard`

---

## Notes for Cursor

- Always read `PLAN.md` before starting any step
- Never commit `.env` or any file in `data/` or `logs/`
- Do not proceed past a checkpoint without explicit human approval
- If a step produces an error, fix it before moving on — do not skip ahead
- The extraction logic in the API Response Structure section above is authoritative; do not simplify or reinterpret it
