"""Conversation nodes in an LE1 BioConversation export (tagged properties, LE1 layout): conditions and transitions.

A node is an element of m_EntryList or m_ReplyList. It runs state transition nStateTransition (-1: none). Its
condition: bFireConditional true runs conditional F<nConditionalFunc> with argument nConditionalParam; false checks
plot bool nConditionalFunc against nConditionalParam (0 or 1).
"""
from __future__ import annotations

import struct
from dataclasses import dataclass

CONDITION_FIELDS = ("nConditionalFunc", "bFireConditional", "nConditionalParam")


@dataclass
class Condition:
    func: int
    fire: bool
    param: int
    offsets: dict[str, int]  # field -> offset of its value in the export data


def _skip_property(names: list[str], data: bytes, o: int) -> tuple[str | None, str, int, int]:
    """(name, type, value offset, next offset) of the tagged property at `o`; name None at the None terminator."""
    name = names[struct.unpack_from("<i", data, o)[0]]
    if name == "None":
        return None, "", o + 8, o + 8
    kind = names[struct.unpack_from("<i", data, o + 8)[0]]
    size = struct.unpack_from("<i", data, o + 16)[0]
    value = o + 24
    if kind == "BoolProperty":
        return name, kind, value, value + 1
    if kind in ("StructProperty", "ByteProperty"):  # a struct or enum name comes first
        value += 8
    return name, kind, value, value + size


def node_fields(names: list[str], data: bytes, list_name: str, index: int, fields: tuple[str, ...]) -> dict[str, int]:
    """Offsets of the values of `fields` in node `index` of `list_name` (m_EntryList or m_ReplyList); `data` starts at
    the net index."""
    o = 4
    while True:
        name, kind, value, o = _skip_property(names, data, o)
        if name is None:
            raise KeyError(f"no {list_name}")
        if name == list_name and kind == "ArrayProperty":
            break
    count = struct.unpack_from("<i", data, value)[0]
    if not 0 <= index < count:
        raise IndexError(f"{list_name} has {count} nodes, not {index + 1}")
    o = value + 4
    for element in range(count):
        found: dict[str, int] = {}
        while True:
            name, kind, value, o = _skip_property(names, data, o)
            if name is None:
                break
            if element == index and name in fields:
                found[name] = value
        if element == index:
            missing = [f for f in fields if f not in found]
            if missing:
                raise KeyError(f"{list_name}[{index}] has no {', '.join(missing)}")
            return found
    raise AssertionError("unreachable")


def node_condition(names: list[str], data: bytes, list_name: str, index: int) -> Condition:
    """The condition of node `index` in `list_name`."""
    found = node_fields(names, data, list_name, index, CONDITION_FIELDS)
    return Condition(struct.unpack_from("<i", data, found["nConditionalFunc"])[0], bool(data[found["bFireConditional"]]),
                     struct.unpack_from("<i", data, found["nConditionalParam"])[0], found)


def node_transition(names: list[str], data: bytes, list_name: str, index: int) -> tuple[int, int]:
    """(state transition the node runs, -1 for none; offset of that value)."""
    offset = node_fields(names, data, list_name, index, ("nStateTransition",))["nStateTransition"]
    return struct.unpack_from("<i", data, offset)[0], offset


def set_bool_condition(data: bytearray, condition: Condition, plot_bool: int, value: bool) -> None:
    """Make the node check plot bool `plot_bool` == `value` (same-size writes)."""
    struct.pack_into("<i", data, condition.offsets["nConditionalFunc"], plot_bool)
    data[condition.offsets["bFireConditional"]] = 0
    struct.pack_into("<i", data, condition.offsets["nConditionalParam"], int(value))
