import re
from pprint import pprint


def _build_visual_clue_lookup(notes: list[dict]) -> dict[tuple[str, str], str]:
    """
    Parse the notes block into a dict keyed by (label, direction) → description.
    Handles lines like: "At 17-Across, each square in the answer has a thick underscore..."
    """
    lookup: dict[tuple[str, str], str] = {}
    if not notes:
        return lookup
    text = notes[0].get("text", "")
    for match in re.finditer(
        r"At (\d+)-(Across|Down),\s*(.+?)(?=\s*At \d+-(?:Across|Down)|$)",
        text,
        re.DOTALL,
    ):
        label, direction, description = match.group(1), match.group(2), match.group(3)
        lookup[(label, direction)] = description.strip().rstrip(".")
    return lookup


def _get_clue_text(
    clue: dict,
    visual_lookup: dict[tuple[str, str], str],
) -> str | None:
    """
    Return the clue string, handling three text formats:
      - plain: normal clue text
      - formatted with ➡️/⬅️: letter-swap puzzle clue
      - formatted &nbsp;: visual/print-only clue resolved via notes lookup
    Returns None if no usable text can be extracted.
    """
    text_list = clue.get("text")
    if not text_list:
        return None

    first = text_list[0]

    if "plain" in first:
        return first["plain"]

    formatted = first.get("formatted", "")

    if "➡️" in formatted or "\u27a1" in formatted:
        lines = [ln.strip() for ln in formatted.splitlines() if ln.strip()]
        cleaned = []
        for ln in lines:
            ln = ln.replace("➡️", "").replace("⬅️", "").replace("\u27a1\ufe0f", "").replace("\u2b05\ufe0f", "").strip()
            if ln:
                cleaned.append(ln)
        joined = " / ".join(cleaned)
        return f"{joined} (swap two letters for alternate answer)"

    if not formatted or formatted.strip() in ("&nbsp;", ""):
        label = clue.get("label", "")
        direction = clue.get("direction", "")
        description = visual_lookup.get((label, direction))
        if description:
            return f"visual clue: {description}"

    return None


def extract_clue_answer_pairs(data: dict, puzzle_type: str) -> list[dict]:
    """
    Returns row dicts with keys:
      date, puzzle_type, puzzle_id, clue_number, direction, answer, clue
    """
    body = data["body"][0]
    cells = body["cells"]
    visual_lookup = _build_visual_clue_lookup(data.get("notes", []))
    rows = []

    for clue in body["clues"]:
        answer_letters = []
        skip_clue = False

        for cell_index in clue["cells"]:
            cell = cells[cell_index]
            if "answer" not in cell:
                skip_clue = True
                break
            answer_letters.append(cell["answer"])

        if skip_clue:
            continue

        clue_text = _get_clue_text(clue, visual_lookup)
        if clue_text is None:
            continue

        rows.append(
            {
                "date": data["publicationDate"],
                "puzzle_type": puzzle_type,
                "puzzle_id": data["id"],
                "clue_number": clue["label"],
                "direction": clue["direction"],
                "answer": "".join(answer_letters),
                "clue": clue_text,
            }
        )

    return rows


if __name__ == "__main__":
    sample_data = {
        "body": [
            {
                "cells": [
                    {},
                    {},
                    {"answer": "S", "clues": [0, 5], "label": "1", "type": 1},
                    {"answer": "U", "clues": [0, 6], "label": "2", "type": 1},
                    {"answer": "P", "clues": [0, 7], "label": "3", "type": 1},
                    {"answer": "S", "clues": [1, 8], "label": "4", "type": 1},
                    {"answer": "A", "clues": [1, 9], "label": "5", "type": 1},
                    {"answer": "Y", "clues": [1, 5], "type": 1},
                    {"answer": "N", "clues": [1, 6], "type": 1},
                    {"answer": "O", "clues": [1, 7], "type": 1},
                    {"answer": "E", "clues": [2, 8], "label": "6", "type": 1},
                    {"answer": "U", "clues": [2, 9], "type": 1},
                    {"answer": "R", "clues": [2, 5], "type": 1},
                    {"answer": "O", "clues": [2, 6], "type": 1},
                    {"answer": "S", "clues": [2, 7], "type": 1},
                    {"answer": "C", "clues": [3, 8], "label": "7", "type": 1},
                    {"answer": "R", "clues": [3, 9], "type": 1},
                    {"answer": "U", "clues": [3, 5], "type": 1},
                    {"answer": "S", "clues": [3, 6], "type": 1},
                    {"answer": "T", "clues": [3, 7], "type": 1},
                    {"answer": "T", "clues": [4, 8], "label": "8", "type": 1},
                    {"answer": "A", "clues": [4, 9], "type": 1},
                    {"answer": "P", "clues": [4, 5], "type": 1},
                    {},
                    {},
                ],
                "clues": [
                    {
                        "cells": [2, 3, 4],
                        "direction": "Across",
                        "label": "1",
                        "text": [{"plain": "Slangy greeting"}],
                    },
                    {
                        "cells": [5, 6, 7, 8, 9],
                        "direction": "Across",
                        "label": "4",
                        "text": [{"plain": "Turn down an offer"}],
                    },
                    {
                        "cells": [10, 11, 12, 13, 14],
                        "direction": "Across",
                        "label": "6",
                        "text": [{"plain": "Banknotes across the Atlantic"}],
                    },
                    {
                        "cells": [15, 16, 17, 18, 19],
                        "direction": "Across",
                        "label": "7",
                        "text": [
                            {
                                "plain": (
                                    "Part of pizza that roughly 20% of people don't "
                                    "eat, according to YouGov polling"
                                )
                            }
                        ],
                    },
                    {
                        "cells": [20, 21, 22],
                        "direction": "Across",
                        "label": "8",
                        "text": [{"plain": "Interact with a smartphone screen"}],
                    },
                    {
                        "cells": [2, 7, 12, 17, 22],
                        "direction": "Down",
                        "label": "1",
                        "list": 1,
                        "text": [{"plain": "Many a Starbucks flavoring"}],
                    },
                    {
                        "cells": [3, 8, 13, 18],
                        "direction": "Down",
                        "label": "2",
                        "list": 1,
                        "text": [
                            {
                                "plain": (
                                    "\"___, dos, tres, catorce!\" (famously "
                                    "inaccurate start to U2's \"Vertigo\")"
                                )
                            }
                        ],
                    },
                    {
                        "cells": [4, 9, 14, 19],
                        "direction": "Down",
                        "label": "3",
                        "list": 1,
                        "text": [{"plain": "Tweet, e.g."}],
                    },
                    {
                        "cells": [5, 10, 15, 20],
                        "direction": "Down",
                        "label": "4",
                        "list": 1,
                        "text": [{"plain": "Religious offshoot"}],
                    },
                    {
                        "cells": [6, 11, 16, 21],
                        "direction": "Down",
                        "label": "5",
                        "list": 1,
                        "text": [{"plain": "Overall vibe"}],
                    },
                ],
            }
        ],
        "id": 23938,
        "publicationDate": "2026-06-02",
        "subcategory": 2,
    }

    pprint(extract_clue_answer_pairs(sample_data, "mini"))
