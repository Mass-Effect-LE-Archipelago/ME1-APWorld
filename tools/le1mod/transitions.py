"""BioStateEventMap (plot transition map) binary: read its elements and retarget bool writes in place.

Layout after the export's net index and empty property list: int count, then per transition: int id, int version,
int element count, elements. An element starts with its type: 0 bool (5 ints: type, version, bool, value, useParam),
4 int (6), 7 function call (9), 8 substate bool (8 ints, the last a sibling count, then that many ints).
"""
from __future__ import annotations

import struct
from dataclasses import dataclass

BOOL, INT, FUNCTION, SUBSTATE = 0, 4, 7, 8
FIXED_INTS = {BOOL: 5, INT: 6, FUNCTION: 9}


@dataclass(frozen=True)
class BoolWrite:
    transition: int
    offset: int  # of the bool index in the buffer
    bool_index: int
    value: int


def bool_writes(data: bytes | bytearray, start: int) -> list[BoolWrite]:
    """Every bool element of the map that begins at `start` (its transition count)."""
    count = struct.unpack_from("<i", data, start)[0]
    o, writes = start + 4, []
    for _ in range(count):
        transition, _version, elements = struct.unpack_from("<3i", data, o)
        o += 12
        for _ in range(elements):
            kind = struct.unpack_from("<i", data, o)[0]
            if kind == SUBSTATE:
                ints = 8 + struct.unpack_from("<i", data, o + 28)[0]
            elif kind in FIXED_INTS:
                ints = FIXED_INTS[kind]
            else:
                raise ValueError(f"transition {transition}: unknown element type {kind} at {o}")
            if kind in (BOOL, SUBSTATE):
                bool_index, value = struct.unpack_from("<2i", data, o + 8)
                writes.append(BoolWrite(transition, o + 8, bool_index, value))
            o += 4 * ints
    return writes


def retarget_bool_sets(data: bytearray, start: int, bools: set[int], target: int) -> list[BoolWrite]:
    """Point every element that sets one of `bools` to true at `target` instead; returns the elements changed."""
    changed = [w for w in bool_writes(data, start) if w.bool_index in bools and w.value == 1]
    for w in changed:
        struct.pack_into("<i", data, w.offset, target)
    return changed
