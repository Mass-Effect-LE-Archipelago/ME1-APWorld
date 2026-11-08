# LE1 game mod build

The game mod lives in `mod/DLC_MOD_ArchipelagoME1`. This tool applies this repo's patches to it. Vanilla packages
are read from the developer's own LE1 install; no game file is changed.

```
python tools/le1mod/build_mod.py <LE1 game folder> [--base <released mod>]
```

- `<LE1 game folder>`: `...\Mass Effect Legendary Edition\Game\ME1`.
- `--base`: first replace `mod/DLC_MOD_ArchipelagoME1` with the mod in a release's `MassEffectAPSetup-<version>-ME1.zip`
  or `ArchipelagoME1-mod-<version>.zip`, or in a folder holding `DLC_MOD_ArchipelagoME1`.

Running it again gives the same files, so it is safe to rerun after changing a patch. Commit the changed packages in
`mod/`; `tools/release/build_release.py` packs that folder into the release.

Runs on Windows, or in WSL with `powershell.exe` available: packages are Oodle-compressed, and `oodle.ps1` runs the
game's own `oo2core_8_win64.dll` to read and write them.

## Patches

| Package | Change |
|---|---|
| `BIOC_Materials.pcc` (vanilla, shipped as an override) | `PlotManagerAuto.StateTransitionMap`: every element that sets an in-party bool (3939-3944) sets 20199 instead |
| `PlotManagerAutoAPME1.pcc` (mod) | `StateTransitionMap`: the same for 20101 and 20102 (Recruit Garrus, Recruit Wrex) |
| `BIOG_2DA_APME1_Treasure_X.pcc` (mod) | `Treasure_Tables_TreasureTables_part_1`: each merchant table that holds Archipelago Item entries draws all its entries (vanilla `drops` left out every entry beyond the vanilla stock, so shop slots could be missing) |
| `BIOG_2DA_APME1_GalaxyMap_X.pcc` (mod) | `GalaxyMap_Planet_part_1`: Agebinium's vanilla row (89), landable only while bool 20194 is set (the client sets it while two squadmates are in the party; a section there only works with two) |

The first two make squadmates join only through Archipelago items (the client sets the in-party bool on delivery, and
adds Kaidan and Ashley itself with Kaidan and Ashley Join at the Citadel). The in-squad bools (3817-3822) are left alone,
so scripted scenes still bring their squadmate along for that scene.

## Tests

`python -m unittest tools/le1mod/test_le1mod.py`; set `LE1_GAME` to the game folder to include the package round trip.
