"""Bio2DANumberedRows (2DA table) exports: read rows and columns, and build an export's data from rows.

Export data: net index (int), properties (m_lstRowNumbers: an ArrayProperty of row numbers, then None), the cells,
then the columns (count, then per column: name and index). Cells come in two layouts: plain (cell count > 0; per cell
a type byte and its value, row by row, then a zero int) or indexed (a zero int, a count, then per cell its index,
type byte and value). Cell types: 0 int, 1 name, 2 float.
"""
from __future__ import annotations

import struct

import le1pkg

INT, NAME, FLOAT = 0, 1, 2


def _name(pkg: le1pkg.Package, data: bytes | bytearray, o: int) -> str:
    index, number = struct.unpack_from("<ii", data, o)
    return pkg.names[index] + (f"_{number - 1}" if number > 0 else "")


def read(pkg: le1pkg.Package, export: le1pkg.Export) -> tuple[list[str], dict[int, dict[str, object]]]:
    """(column names, {row number: {column: value}}) of a Bio2DANumberedRows export."""
    d, o = pkg.image, export.offset + 4
    rows: list[int] = []
    while True:  # properties: only m_lstRowNumbers matters
        prop = _name(pkg, d, o)
        if prop == "None":
            o += 8
            break
        size = struct.unpack_from("<i", d, o + 16)[0]
        if prop == "m_lstRowNumbers":
            count = struct.unpack_from("<i", d, o + 24)[0]
            rows = list(struct.unpack_from(f"<{count}i", d, o + 28))
        o += 24 + size
    cells: dict[int, object] = {}

    def value(at: int) -> tuple[object, int]:
        kind = d[at]
        if kind == NAME:
            return _name(pkg, d, at + 1), at + 9
        return struct.unpack_from("<f" if kind == FLOAT else "<i", d, at + 1)[0], at + 5

    count = struct.unpack_from("<i", d, o)[0]
    o += 4
    if count > 0:
        for i in range(count):
            cells[i], o = value(o)
        o += 4
    else:
        count = struct.unpack_from("<i", d, o)[0]
        o += 4
        for _ in range(count):
            index = struct.unpack_from("<i", d, o)[0]
            cells[index], o = value(o + 4)
    columns_count = struct.unpack_from("<i", d, o)[0]
    o += 4
    columns: dict[int, str] = {}
    for _ in range(columns_count):
        columns[struct.unpack_from("<i", d, o + 8)[0]] = _name(pkg, d, o)
        o += 12
    names = [columns[i] for i in sorted(columns)]
    table = {row: {names[c]: cells[r * len(names) + c] for c in range(len(names)) if r * len(names) + c in cells}
             for r, row in enumerate(rows)}
    return names, table


def build(pkg: le1pkg.Package, net_index: int, columns: list[str], rows: dict[int, dict[str, object]],
          kinds: dict[str, int]) -> bytes:
    """Export data for these rows (indexed layout, every cell written); names must already be in pkg.names."""
    def name_ref(name: str) -> bytes:
        return struct.pack("<ii", pkg.names.index(name), 0)
    numbers = sorted(rows)
    out = bytearray(struct.pack("<i", net_index))
    if numbers:
        out += name_ref("m_lstRowNumbers") + name_ref("ArrayProperty")
        out += struct.pack("<ii", 4 + 4 * len(numbers), 0) + struct.pack(f"<i{len(numbers)}i", len(numbers), *numbers)
    out += name_ref("None")
    cells = bytearray()
    written = 0
    for r, number in enumerate(numbers):
        for c, column in enumerate(columns):
            kind = kinds[column]
            cells += struct.pack("<iB", r * len(columns) + c, kind)
            value = rows[number][column]
            cells += name_ref(value) if kind == NAME else struct.pack("<f" if kind == FLOAT else "<i", value)
            written += 1
    out += struct.pack("<ii", 0, written) + cells
    out += struct.pack("<i", len(columns))
    for c, column in enumerate(columns):
        out += name_ref(column) + struct.pack("<i", c)
    return bytes(out)
