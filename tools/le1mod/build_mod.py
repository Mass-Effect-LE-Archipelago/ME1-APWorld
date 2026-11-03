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
import le1pkg  # noqa: E402
import transitions  # noqa: E402

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
    print(f"mod: {MOD_DIR}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("game")
    parser.add_argument("--base")
    args = parser.parse_args()
    main(args.game, args.base)
