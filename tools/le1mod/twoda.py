"""Bio2DANumberedRows (2DA table) exports: read rows and columns, and build an export's data from rows.

Export data: net index (int), properties (m_lstRowNumbers: an ArrayProperty of row numbers, then None), the cells,
then the columns (count, then per column: name and index). Cells come in two layouts: plain (cell count > 0; per cell
a type byte and its value, row by row, then a zero int) or indexed (a zero int, a count, then per cell its index,
type byte and value; cells left out are empty). Cell types: 0 int, 1 name, 2 float; a column can hold more than one.

Names are read as text: a numbered name is its base name, "_", then its number - 1 (UE3 name numbers). Writing splits
such text the same way, so `split_name` gives the base names a package needs.
"""
from __future__ import annotations

import re
import struct

import le1pkg

INT, NAME, FLOAT = 0, 1, 2
_NUMBERED = re.compile(r"(.+)_(0|[1-9]\d*)")


def split_name(text: str) -> tuple[str, int]:
    """(base name, name number) of a name read as text."""
    match = _NUMBERED.fullmatch(text)
    return (match.group(1), int(match.group(2)) + 1) if match else (text, 0)


def _name(pkg: le1pkg.Package, data: bytes | bytearray, o: int) -> str:
    index, number = struct.unpack_from("<ii", data, o)
    return pkg.names[index] + (f"_{number - 1}" if number > 0 else "")


def _parse(pkg: le1pkg.Package, export: le1pkg.Export) -> tuple[list[str], list[int], dict[int, tuple[int, object]]]:
    """(column names, row numbers, {cell index: (type, value)})."""
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
    cells: dict[int, tuple[int, object]] = {}

    def value(at: int) -> tuple[tuple[int, object], int]:
        kind = d[at]
        if kind == NAME:
            return (kind, _name(pkg, d, at + 1)), at + 9
        return (kind, struct.unpack_from("<f" if kind == FLOAT else "<i", d, at + 1)[0]), at + 5

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
    return [columns[i] for i in sorted(columns)], rows, cells


def read(pkg: le1pkg.Package, export: le1pkg.Export) -> tuple[list[str], dict[int, dict[str, object]]]:
    """(column names, {row number: {column: value}}) of a Bio2DANumberedRows export; empty cells are left out."""
    names, rows, cells = _parse(pkg, export)
    width = len(names)
    table = {row: {names[c]: cells[r * width + c][1] for c in range(width) if r * width + c in cells}
             for r, row in enumerate(rows)}
    return names, table


def kind_of(value: object) -> int:
    """A cell's type from its value as `read` gives it: str is a name, float a float, int an int."""
    return NAME if isinstance(value, str) else FLOAT if isinstance(value, float) else INT


def build(pkg: le1pkg.Package, net_index: int, columns: list[str], rows: dict[int, dict[str, object]]) -> bytes:
    """Export data for these rows (indexed layout; a column missing from a row is an empty cell; each cell's type
    comes from its value, kind_of). Base names (split_name) must already be in pkg.names."""
    def name_ref(name: str) -> bytes:
        base, number = split_name(name)
        return struct.pack("<ii", pkg.names.index(base), number)
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
            if column not in rows[number]:
                continue
            value = rows[number][column]
            kind = kind_of(value)
            cells += struct.pack("<iB", r * len(columns) + c, kind)
            cells += name_ref(value) if kind == NAME else struct.pack("<f" if kind == FLOAT else "<i", value)
            written += 1
    out += struct.pack("<ii", 0, written) + cells
    out += struct.pack("<i", len(columns))
    for c, column in enumerate(columns):
        out += name_ref(column) + struct.pack("<i", c)
    return bytes(out)
