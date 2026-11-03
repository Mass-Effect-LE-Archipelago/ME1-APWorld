"""Tests for the LE1 mod patcher. Pure Python; the package round trip needs the game and runs only when LE1_GAME is
set to the LE1 game folder (...\\Game\\ME1).

usage: python -m unittest tools/le1mod/test_le1mod.py
"""
from __future__ import annotations

import os
import struct
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_mod  # noqa: E402
import le1pkg  # noqa: E402
import transitions  # noqa: E402


def transition_map(*events: tuple[int, list[list[int]]]) -> bytearray:
    data = bytearray(struct.pack("<i", len(events)))
    for transition, elements in events:
        data += struct.pack("<3i", transition, 0, len(elements))
        for element in elements:
            data += struct.pack(f"<{len(element)}i", *element)
    return data


class TestTransitions(unittest.TestCase):
    def test_retargets_only_true_in_party_writes(self) -> None:
        data = transition_map(
            (1992, [[0, 0, 3817, 1, 0], [0, 0, 3939, 1, 0]]),  # in squad + in party
            (2223, [[0, 0, 3939, 0, 0]]),  # leaves the party: kept
            (4057, [[4, 0, 57, 1, 0, 1]]),  # int element
            (188, [[7, 0, 1, 4, 2, 0, 5659, 0, 0]]),  # function element
            (1212, [[8, 0, 3944, 1, 0, 0, 3203, 2, 3205, 3207]]),  # substate with two siblings
        )
        before = bytes(data)
        changed = transitions.retarget_bool_sets(data, 0, build_mod.IN_PARTY_BOOLS, build_mod.SQUAD_JOIN_SUPPRESSED)
        self.assertEqual([(w.transition, w.bool_index) for w in changed], [(1992, 3939), (1212, 3944)])
        self.assertEqual(len(data), len(before))
        after = {(w.transition, w.bool_index, w.value) for w in transitions.bool_writes(data, 0)}
        self.assertEqual(after, {(1992, 3817, 1), (1992, 20199, 1), (2223, 3939, 0), (1212, 20199, 1)})

    def test_unknown_element_type_stops(self) -> None:
        with self.assertRaises(ValueError):
            transitions.bool_writes(transition_map((1, [[5, 0, 0, 0, 0]])), 0)


@unittest.skipUnless(os.environ.get("LE1_GAME"), "set LE1_GAME to the LE1 game folder")
class TestGamePackage(unittest.TestCase):
    def test_round_trip(self) -> None:
        game = os.environ["LE1_GAME"]
        dll = os.path.join(game, "Binaries", "Win64", "oo2core_8_win64.dll")
        src = os.path.join(game, "BioGame", "CookedPCConsole", "PlotManager.pcc")
        pkg = le1pkg.read(src, dll)
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "PlotManager.pcc")
            le1pkg.write(pkg, out, dll)
            self.assertEqual(le1pkg.read(out, dll).image, pkg.image)


if __name__ == "__main__":
    unittest.main()
