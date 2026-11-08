"""Apply this repo's patches to the game mod in mod/DLC_MOD_ArchipelagoME1.

usage: python tools/le1mod/build_mod.py <LE1 game folder> [--base <released mod>]
  <LE1 game folder>: ...\\Mass Effect Legendary Edition\\Game\\ME1 (vanilla packages and the Oodle DLL come from it)
  --base: first replace mod/DLC_MOD_ArchipelagoME1 with the one in a release's MassEffectAPSetup-<version>-ME1.zip,
          ArchipelagoME1-mod-<version>.zip, or a folder holding DLC_MOD_ArchipelagoME1
Running it again gives the same files: vanilla packages are read from the game, and a patch finds nothing left to do
in a package it already patched. No game file is changed.

Patches (squadmates join only through Archipelago items):
- the vanilla transition map (PlotManagerAuto.StateTransitionMap, in BIOC_Materials.pcc, shipped in the mod as an
  override) and the mod's own map (PlotManagerAutoAPME1.pcc): every element that sets a squadmate's in-party bool
  (3939-3944) sets SQUAD_JOIN_SUPPRESSED instead. The in-squad bools stay, so scripted scenes still spawn their
  squadmate for that scene.
- shop stock (BIOG_2DA_APME1_Treasure_X.pcc, Treasure_Tables_TreasureTables_part_1): a merchant's stock draws `drops`
  entries from its treasure table, and the mod's Archipelago Item entries are extra entries in those tables, so each
  such table draws all its entries (vanilla and Archipelago); every shop slot is then stocked.
- landing gates (BIOG_2DA_APME1_GalaxyMap_X.pcc, GalaxyMap_Planet_part_1): planets with a section that needs two
  squadmates (Agebinium) are landable only while the client's two-squadmates bool is set; planets whose landing puts
  the Mako in reach are usable only while the client's Mako bool is set.
- story recruitment (PlotManager.pcc conditionals, and Citadel conversations in each language): checks that read
  Garrus's, Wrex's or Tali's in-party bool as "recruited in the story" read the story's own flag instead, since the
  client sets the in-party bool when the item arrives (CONDITIONAL_SWAPS, CONVERSATION_PATCHES).
- The Look (PlotManagerAutoAPME1.pcc, the Council's Spectre induction in each language): mod transition 20103 sets
  bool 20103, and the induction runs it right after the asari Councilor's look (BOOL_TRANSITIONS, TRANSITION_NODES).
"""
from __future__ import annotations

import argparse
import os
import shutil
import struct
import sys
import tempfile
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import conversation as conversation_mod  # noqa: E402
import le1pkg  # noqa: E402
import transitions  # noqa: E402
import twoda  # noqa: E402

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
MOD_FOLDER = "DLC_MOD_ArchipelagoME1"
MOD_DIR = os.path.join(REPO, "mod", MOD_FOLDER)
IN_PARTY_BOOLS = set(range(3939, 3945))  # Kaidan, Ashley, Garrus, Wrex, Liara, Tali
SQUAD_JOIN_SUPPRESSED = 20199  # set where vanilla would add a squadmate to the party; read by nothing
TRANSITION_MAPS = {  # package -> its StateTransitionMap export, and whether it comes from the game or the mod
    "BIOC_Materials.pcc": ("PlotManagerAuto.StateTransitionMap", "game"),
    "PlotManagerAutoAPME1.pcc": ("StateTransitionMap", "mod"),
}


def extract_mod(source: str, dest: str) -> str:
    """Copy the released mod into dest; returns the folder that holds DLC_MOD_ArchipelagoME1."""
    if os.path.isdir(source):
        root = source
    else:
        with zipfile.ZipFile(source) as z:
            z.extractall(dest)
        root = dest
    for folder, dirs, _ in os.walk(root):
        if MOD_FOLDER in dirs and os.path.isfile(os.path.join(folder, MOD_FOLDER, "AutoLoad.ini")):
            return folder
    raise SystemExit(f"no {MOD_FOLDER}/AutoLoad.ini in {source}")


def patch_transition_map(src: str, dest: str, export_name: str, dll: str) -> list[transitions.BoolWrite]:
    pkg = le1pkg.read(src, dll)
    export = pkg.find("BioStateEventMap", export_name)
    none = pkg.name_index("None")
    start = export.offset + 4  # net index
    if struct.unpack_from("<ii", pkg.image, start) != (none, 0):
        raise SystemExit(f"{export_name}: expected an empty property list")
    changed = transitions.retarget_bool_sets(pkg.image, start + 8, IN_PARTY_BOOLS, SQUAD_JOIN_SUPPRESSED)
    le1pkg.write(pkg, dest, dll)
    check = le1pkg.read(dest, dll)  # round trip: the written package decompresses to the patched image
    if check.image != pkg.image:
        raise SystemExit(f"{dest}: written package does not match the patched image")
    return changed


def override_rows(path: str, export_name: str, rows: dict[int, dict[str, object]], dll: str) -> None:
    """Write `rows` into the mod's Bio2DANumberedRows export `export_name` (rows already there with other numbers
    stay), adding the names they need, and check that the table reads back."""
    pkg = le1pkg.read(path, dll)
    export = pkg.find("Bio2DANumberedRows", export_name)
    columns, table = twoda.read(pkg, export)
    table.update(rows)
    names = ["m_lstRowNumbers", "ArrayProperty", "None"]
    names += [twoda.split_name(row[c])[0] for row in rows.values() for c in row if isinstance(row[c], str)]
    added = le1pkg.add_names(pkg, list(dict.fromkeys(names)))
    pkg.names.extend(added)
    net_index = struct.unpack_from("<i", pkg.image, export.offset)[0]
    data = twoda.build(pkg, net_index, columns, table)
    del pkg.names[len(pkg.names) - len(added):]
    le1pkg.write_image(pkg, le1pkg.relayout(pkg, added, {export.index: data}), path, dll)
    check = le1pkg.read(path, dll)
    if twoda.read(check, check.find("Bio2DANumberedRows", export_name))[1] != table:
        raise SystemExit(f"{path}: {export_name} does not read back")


SHOP_PACKAGE = "BIOG_2DA_APME1_Treasure_X.pcc"
VANILLA_TREASURE_TABLES = "BIOG_2DA_TreasureTables_X.Treasure_Tables_TreasureTables"  # in Engine.pcc
VANILLA_TREASURE_ENTRIES = "BIOG_2DA_TreasureTables_X.Treasure_Tables_TreasureEntries"


def patch_shop_draws(path: str, engine: str, dll: str) -> dict[int, dict[str, object]]:
    """Override rows for every treasure table the mod's shop entries are in: its vanilla row with drops set to all its
    entries (vanilla and the mod's). Returns the rows written."""
    pkg = le1pkg.read(path, dll)
    _, entries = twoda.read(pkg, pkg.find("Bio2DANumberedRows", "Treasure_Tables_TreasureEntries_part_1"))
    slots: dict[int, int] = {}
    for entry in entries.values():
        slots[entry["tid"]] = slots.get(entry["tid"], 0) + 1
    vanilla_pkg = le1pkg.read(engine, dll)
    _, vanilla = twoda.read(vanilla_pkg, vanilla_pkg.find("Bio2DANumberedRows", VANILLA_TREASURE_TABLES))
    _, vanilla_entries = twoda.read(vanilla_pkg, vanilla_pkg.find("Bio2DANumberedRows", VANILLA_TREASURE_ENTRIES))
    entry_counts: dict[int, int] = {}
    for entry in vanilla_entries.values():
        entry_counts[entry["tid"]] = entry_counts.get(entry["tid"], 0) + 1
    rows = {tid: {**vanilla[tid], "drops": entry_counts.get(tid, 0) + count} for tid, count in sorted(slots.items())}
    override_rows(path, "Treasure_Tables_TreasureTables_part_1", rows, dll)
    return rows


PLANET_PACKAGE = "BIOG_2DA_APME1_GalaxyMap_X.pcc"
VANILLA_PLANETS = "BIOG_2DA_GalaxyMap_X.GalaxyMap_Planet"  # in Engine.pcc
VANILLA_MAPS = "BIOG_2DA_GalaxyMap_X.GalaxyMap_Map"
TWO_SQUADMATES = 20194  # set by the client while two squadmates are in the party
MAKO = 20193  # set by the client while the M35 Mako is received (always, when the Mako is not shuffled)
# GalaxyMap_Planet row -> plot bool its landing needs (UsablePlanet); the world's logic has the same planets (uncharted.py)
PLANET_GATES = {89: TWO_SQUADMATES}  # Agebinium
# Levels whose landing puts the Mako in reach: Noveria, Feros, Virmire, Therum, Asteroid X57 and every uncharted planet.
# Their planets are usable only while MAKO is set (Usable; UsablePlanet keeps the vanilla or coordinate gate).
MAKO_LEVELS = frozenset({"BIOA_ICE00", "BIOA_WAR00", "BIOA_JUG00", "BIOA_LAV00", "BIOA_PRC2"})
MAKO_LEVEL_PREFIX = "BIOA_UNC"


def planet_gate_rows(planets: dict[int, dict[str, object]], maps: dict[int, dict[str, object]]
                     ) -> dict[int, dict[str, object]]:
    """The GalaxyMap_Planet rows to override: each planet in PLANET_GATES or on a Mako level, from its vanilla row."""
    mako_maps = {number for number, row in maps.items()
                 if row.get("Map") in MAKO_LEVELS or str(row.get("Map", "")).startswith(MAKO_LEVEL_PREFIX)}
    rows: dict[int, dict[str, object]] = {}
    for number, planet in planets.items():
        row = dict(planet)
        if number in PLANET_GATES:
            row.update(UsablePlanetConditional=0, UsablePlanetFunction=PLANET_GATES[number], UsablePlanetParameter=1)
        if planet.get("Map") in mako_maps:
            row.update(UsableConditional=0, UsableFunction=MAKO, UsableParameter=1)
        if row != planet:
            rows[number] = row
    return rows


def patch_planet_gates(path: str, engine: str, dll: str) -> dict[int, dict[str, object]]:
    """Override rows for the planets planet_gate_rows picks. A Conditional of 0 makes its Function a plot bool and its
    Parameter the value it must have (the mod's Eden Prime row: bool 20000, 1). Returns the rows."""
    vanilla_pkg = le1pkg.read(engine, dll)
    columns, vanilla = twoda.read(vanilla_pkg, vanilla_pkg.find("Bio2DANumberedRows", VANILLA_PLANETS))
    _, maps = twoda.read(vanilla_pkg, vanilla_pkg.find("Bio2DANumberedRows", VANILLA_MAPS))
    mod_pkg = le1pkg.read(path, dll)
    if twoda.read(mod_pkg, mod_pkg.find("Bio2DANumberedRows", "GalaxyMap_Planet_part_1"))[0] != columns:
        raise SystemExit(f"{path}: GalaxyMap_Planet_part_1 columns differ from the game's")
    rows = planet_gate_rows(vanilla, maps)
    override_rows(path, "GalaxyMap_Planet_part_1", rows, dll)
    return rows


GARRUS_RECRUITED = 20101  # the mod's recruit transitions set these where vanilla set the in-party bool
WREX_RECRUITED = 20102
QUARIAN_SAVED = 3721  # Tali's recruitment (the Recruit Tali check)
GARRUS_IN_PARTY, WREX_IN_PARTY, TALI_IN_PARTY = 3941, 3942, 3944
INT_CONST = 0x1D  # UnrealScript IntConst token, followed by an int32
CONDITIONALS_PACKAGE = "PlotManager.pcc"
# Conditionals that read an in-party bool as "recruited in the story": they read the story flag instead, since the
# client sets the in-party bool when the squadmate's item arrives, which can be before the story recruits them.
CONDITIONAL_SWAPS = {
    1632: {GARRUS_IN_PARTY: GARRUS_RECRUITED, WREX_IN_PARTY: WREX_RECRUITED},  # Harkin_HasNothingToSay
    1368: {GARRUS_IN_PARTY: GARRUS_RECRUITED},  # Garrus_waiting_at_CSec
    790: {GARRUS_IN_PARTY: GARRUS_RECRUITED},  # Garrus_at_hangar_elevator
    1229: {GARRUS_IN_PARTY: GARRUS_RECRUITED},  # Can_ask_Executor_about_Garrus
    1742: {GARRUS_IN_PARTY: GARRUS_RECRUITED, TALI_IN_PARTY: QUARIAN_SAVED},  # Garrus_no_longer_needed
    1367: {WREX_IN_PARTY: WREX_RECRUITED},  # Wrex_waiting_in_Choras
    792: {WREX_IN_PARTY: WREX_RECRUITED},  # Wrex_at_hangar_elevator
}
NPC_IN_PARTY = 418  # NPCInParty(argument): 3 Garrus, 4 Wrex
# Citadel conversation nodes that check NPCInParty for the story's recruitment: package (each language) -> the
# conversation and its (node list, index, argument, story flag); the node checks the story flag instead.
CONVERSATION_PATCHES = {
    "BIOA_STA20_04A_DSG": ("sta20_banker_D.sta20_banker_dlg", [  # Barla Von: the Saren lead, unless Wrex told you
        ("m_EntryList", 18, 4, WREX_RECRUITED)]),
    "BIOA_STA30_01_DSG": ("sta30_krogan_cutscene_D.sta30_krogan_cutscene_dlg", [  # Wrex at C-Sec, Garrus along
        ("m_EntryList", 0, 3, GARRUS_RECRUITED)]),
    "BIOA_STA60_08A_DSG": ("sta60_garrus_doctor_D.sta60_garrus_doctor_dlg", [  # Dr. Michel, Wrex along
        ("m_EntryList", 12, 4, WREX_RECRUITED), ("m_EntryList", 30, 4, WREX_RECRUITED)]),
}
LANGUAGES = ("INT", "DE", "FR", "IT", "PLPC", "RA")


def swap_int_consts(code: bytes | bytearray, swaps: dict[int, int]) -> bytearray | None:
    """`code` with each IntConst old -> new of `swaps` (each old exactly once), None when already swapped."""
    out = bytearray(code)
    if all(out.count(bytes([INT_CONST]) + struct.pack("<i", new)) == 1 and
           out.count(bytes([INT_CONST]) + struct.pack("<i", old)) == 0 for old, new in swaps.items()):
        return None
    for old, new in swaps.items():
        token = bytes([INT_CONST]) + struct.pack("<i", old)
        if out.count(token) != 1:
            raise ValueError(f"IntConst {old} appears {out.count(token)} times")
        at = out.index(token)
        out[at + 1:at + 5] = struct.pack("<i", new)
    return out


def patch_conditionals(path: str, dll: str) -> list[int]:
    """Apply CONDITIONAL_SWAPS to the mod's PlotManager.pcc; returns the conditionals changed."""
    pkg = le1pkg.read(path, dll)
    changed = []
    for number, swaps in CONDITIONAL_SWAPS.items():
        export = pkg.find("Function", f"BioAutoConditionals.F{number}")
        try:
            code = swap_int_consts(pkg.image[export.offset:export.offset + export.size], swaps)
        except ValueError as error:
            raise SystemExit(f"{path}: F{number}: {error}")
        if code is not None:
            pkg.image[export.offset:export.offset + export.size] = code
            changed.append(number)
    if changed:
        le1pkg.write(pkg, path, dll)
        if le1pkg.read(path, dll).image != pkg.image:
            raise SystemExit(f"{path}: written package does not match the patched image")
    return changed


def patch_conversation(path: str, conversation: str, nodes: list[tuple[str, int, int, int]], dll: str) -> int:
    """Point each node's NPCInParty(argument) check at its story flag; returns how many nodes changed."""
    pkg = le1pkg.read(path, dll)
    export = pkg.find("BioConversation", conversation)
    data = pkg.image[export.offset:export.offset + export.size]
    changed = 0
    for list_name, index, argument, flag in nodes:
        cond = conversation_mod.node_condition(pkg.names, data, list_name, index)
        if (cond.func, cond.fire, cond.param) == (flag, False, 1):
            continue
        if (cond.func, cond.fire, cond.param) != (NPC_IN_PARTY, True, argument):
            raise SystemExit(f"{path}: {conversation} {list_name}[{index}] is not NPCInParty({argument})")
        conversation_mod.set_bool_condition(data, cond, flag, True)
        changed += 1
    if changed:
        pkg.image[export.offset:export.offset + export.size] = data
        le1pkg.write(pkg, path, dll)
        if le1pkg.read(path, dll).image != pkg.image:
            raise SystemExit(f"{path}: written package does not match the patched image")
    return changed


def patch_conversations(cooked: str, mod_cooked: str, dll: str) -> dict[str, int]:
    """CONVERSATION_PATCHES in every language; a package the mod does not ship yet is copied from the game."""
    changed = {}
    for base, (conversation, nodes) in CONVERSATION_PATCHES.items():
        for language in LANGUAGES:
            name = f"{base}_LOC_{language}.pcc"
            path = os.path.join(mod_cooked, name)
            if not os.path.isfile(path):
                shutil.copyfile(os.path.join(cooked, name), path)
            changed[name] = patch_conversation(path, conversation, nodes, dll)
    return changed


MOD_TRANSITIONS_PACKAGE = "PlotManagerAutoAPME1.pcc"
THE_LOOK = 20103  # transition and plot bool: the Citadel: The Look check
# Mod transitions that set a plot bool of the same number: transition -> bool.
BOOL_TRANSITIONS = {THE_LOOK: THE_LOOK}
# Conversation nodes that run a mod transition: package (each language) -> the conversation and its (node list,
# index, transition). Each node runs no transition in the game.
TRANSITION_NODES = {
    # The Council makes Shepard a Spectre: the silent beat after "Commander Shepard - step forward", which every path
    # reaches right after the asari Councilor's look.
    "BIOA_STA70_02council_DSG": ("sta90_council_spectre_induction_D.sta90_council_spectre_induction_dlg", [
        ("m_EntryList", 23, THE_LOOK)]),
}


def add_mod_transitions(path: str, dll: str) -> list[int]:
    """Add BOOL_TRANSITIONS missing from the mod's StateTransitionMap; returns the transitions added."""
    pkg = le1pkg.read(path, dll)
    export = pkg.find("BioStateEventMap", "StateTransitionMap")
    data = bytes(pkg.image[export.offset:export.offset + export.size])
    start = 4 + 8  # net index, empty property list
    present = set(transitions.transition_ids(data, start))
    added = [t for t in BOOL_TRANSITIONS if t not in present]
    for transition in added:
        data = transitions.add_bool_transition(data, start, transition, BOOL_TRANSITIONS[transition])
    if added:
        le1pkg.write_image(pkg, le1pkg.relayout(pkg, [], {export.index: data}), path, dll)
        check = le1pkg.read(path, dll)
        written = check.find("BioStateEventMap", "StateTransitionMap")
        if bytes(check.image[written.offset:written.offset + written.size]) != data:
            raise SystemExit(f"{path}: StateTransitionMap does not read back")
    return added


def patch_transition_nodes(cooked: str, mod_cooked: str, dll: str) -> dict[str, int]:
    """TRANSITION_NODES in every language; a package the mod does not ship yet is copied from the game."""
    changed = {}
    for base, (conversation, nodes) in TRANSITION_NODES.items():
        for language in LANGUAGES:
            name = f"{base}_LOC_{language}.pcc"
            path = os.path.join(mod_cooked, name)
            if not os.path.isfile(path):
                shutil.copyfile(os.path.join(cooked, name), path)
            pkg = le1pkg.read(path, dll)
            export = pkg.find("BioConversation", conversation)
            data = pkg.image[export.offset:export.offset + export.size]
            count = 0
            for list_name, index, transition in nodes:
                current, offset = conversation_mod.node_transition(pkg.names, data, list_name, index)
                if current == transition:
                    continue
                if current != -1:
                    raise SystemExit(f"{path}: {conversation} {list_name}[{index}] runs transition {current}")
                struct.pack_into("<i", data, offset, transition)
                count += 1
            if count:
                pkg.image[export.offset:export.offset + export.size] = data
                le1pkg.write(pkg, path, dll)
                if le1pkg.read(path, dll).image != pkg.image:
                    raise SystemExit(f"{path}: written package does not match the patched image")
            changed[name] = count
    return changed


def main(game: str, base: str | None = None) -> None:
    cooked = os.path.join(game, "BioGame", "CookedPCConsole")
    dll = os.path.join(game, "Binaries", "Win64", "oo2core_8_win64.dll")
    for path in (cooked, dll):
        if not os.path.exists(path):
            raise SystemExit(f"not found: {path} (pass the LE1 game folder, ...\\Game\\ME1)")
    if base is not None:
        tmp = tempfile.mkdtemp(prefix="le1mod")
        try:
            root = extract_mod(base, tmp)
            shutil.rmtree(MOD_DIR, ignore_errors=True)
            shutil.copytree(os.path.join(root, MOD_FOLDER), MOD_DIR)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    if not os.path.isfile(os.path.join(MOD_DIR, "AutoLoad.ini")):
        raise SystemExit(f"no {MOD_FOLDER} in {os.path.dirname(MOD_DIR)}; pass --base <released mod>")
    mod_cooked = os.path.join(MOD_DIR, "CookedPCConsole")
    for package, (export_name, origin) in TRANSITION_MAPS.items():
        src = os.path.join(cooked if origin == "game" else mod_cooked, package)
        changed = patch_transition_map(src, os.path.join(mod_cooked, package), export_name, dll)
        ids = sorted({w.transition for w in changed})
        print(f"{package}: {len(changed)} in-party writes retargeted (transitions {ids})")
    rows = patch_shop_draws(os.path.join(mod_cooked, SHOP_PACKAGE), os.path.join(cooked, "Engine.pcc"), dll)
    print(f"{SHOP_PACKAGE}: shop draws " + ", ".join(f"{r['Name']} {r['drops']}" for r in rows.values()))
    rows = patch_planet_gates(os.path.join(mod_cooked, PLANET_PACKAGE), os.path.join(cooked, "Engine.pcc"), dll)
    print(f"{PLANET_PACKAGE}: landing gates on rows " + ", ".join(
        f"{number} (map {r['Map']}: usable {r['UsableFunction']}, land {r['UsablePlanetFunction']})"
        for number, r in rows.items()))
    changed = patch_conditionals(os.path.join(mod_cooked, CONDITIONALS_PACKAGE), dll)
    print(f"{CONDITIONALS_PACKAGE}: story recruitment conditionals changed: {changed or 'none (already patched)'}")
    for name, count in patch_conversations(cooked, mod_cooked, dll).items():
        print(f"{name}: {count} conversation nodes changed")
    added = add_mod_transitions(os.path.join(mod_cooked, MOD_TRANSITIONS_PACKAGE), dll)
    print(f"{MOD_TRANSITIONS_PACKAGE}: transitions added: {added or 'none (already there)'}")
    for name, count in patch_transition_nodes(cooked, mod_cooked, dll).items():
        print(f"{name}: {count} conversation nodes now run a mod transition")
    print(f"mod: {MOD_DIR}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("game")
    parser.add_argument("--base")
    args = parser.parse_args()
    main(args.game, args.base)
