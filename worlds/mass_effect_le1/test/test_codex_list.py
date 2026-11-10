import os
import unittest

from ..codex import CODEX_ENTRIES
from ..regions import AUTOMATIC_CODEX, MISSABLE_CODEX

CODEX_LIST = os.path.join(os.path.dirname(__file__), "..", "docs", "ME1_codex_entries.md")


def missable_column() -> dict[int, str]:
    """Page ID -> its Missable value in docs/ME1_codex_entries.md."""
    column = {}
    with open(CODEX_LIST, encoding="utf-8") as f:
        for line in f:
            cells = [cell.strip() for cell in line.split("|")]
            if len(cells) > 4 and cells[1].isdigit():
                column[int(cells[1])] = cells[3]
    return column


class TestCodexList(unittest.TestCase):
    def test_code_matches_the_codex_list(self) -> None:
        column = missable_column()
        for entry in CODEX_ENTRIES:
            with self.subTest(entry.name):
                value = column[entry.plot_bool]
                self.assertEqual(entry.name in AUTOMATIC_CODEX, value == "Automatic")
                self.assertEqual(entry.name in MISSABLE_CODEX, value == "Yes")
                self.assertNotEqual(value, "Unobtainable")
