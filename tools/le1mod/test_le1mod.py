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
import twoda  # noqa: E402


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


class TestTwoDA(unittest.TestCase):
    def test_build_reads_back(self) -> None:
        names = ["None", "m_lstRowNumbers", "ArrayProperty", "tid", "drops", "Name", "csid", "QMPremium", "Other"]
        pkg = le1pkg.Package("fake", b"", None, bytearray(), names=names)
        rows = {307: {"tid": 307, "drops": 22, "Name": "QMPremium", "csid": 1},
                168: {"tid": 168, "drops": 14, "Name": "Other", "csid": 1}}
        data = twoda.build(pkg, 2, ["tid", "drops", "Name", "csid"], rows)
        pkg.image = bytearray(data)
        export = le1pkg.Export(1, 0, 0, "table", len(data), 0, 0)
        columns, read_rows = twoda.read(pkg, export)
        self.assertEqual(columns, ["tid", "drops", "Name", "csid"])
        self.assertEqual(read_rows, rows)

    def test_numbered_names_mixed_cells_and_empty_cells(self) -> None:
        names = ["None", "m_lstRowNumbers", "ArrayProperty", "Shader", "Bump", "Event", "GXM_Planet"]
        pkg = le1pkg.Package("fake", b"", None, bytearray(), names=names)
        rows = {89: {"Shader": "GXM_Planet_178", "Bump": 0.25, "Event": 7}, 90: {"Shader": "GXM_Planet", "Bump": 0}}
        data = twoda.build(pkg, 2, ["Shader", "Bump", "Event"], rows)
        self.assertIn(struct.pack("<ii", names.index("GXM_Planet"), 179), data)  # base name and number, as UE3 stores it
        pkg.image = bytearray(data)
        _, read_rows = twoda.read(pkg, le1pkg.Export(1, 0, 0, "table", len(data), 0, 0))
        self.assertEqual(read_rows, rows)
        self.assertIsInstance(read_rows[90]["Bump"], int)


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

    def test_relayout(self) -> None:
        """Nothing added or replaced gives the same image; an added name reads back and the tables still parse."""
        dll = os.path.join(os.environ["LE1_GAME"], "Binaries", "Win64", "oo2core_8_win64.dll")
        src = os.path.join(build_mod.MOD_DIR, "CookedPCConsole", build_mod.SHOP_PACKAGE)
        pkg = le1pkg.read(src, dll)
        self.assertEqual(le1pkg.relayout(pkg, [], {}), bytes(pkg.image))
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, build_mod.SHOP_PACKAGE)
            le1pkg.write_image(pkg, le1pkg.relayout(pkg, ["APTestName"], {}), out, dll)
            again = le1pkg.read(out, dll)
            self.assertEqual(again.names, pkg.names + ["APTestName"])
            self.assertEqual([e.name for e in again.exports], [e.name for e in pkg.exports])
            for a, b in zip(pkg.exports, again.exports):
                self.assertEqual(pkg.image[a.offset:a.offset + a.size], again.image[b.offset:b.offset + b.size], a.name)


if __name__ == "__main__":
    unittest.main()
