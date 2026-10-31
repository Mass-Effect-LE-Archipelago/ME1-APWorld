# Mass Effect Legendary Edition 1 Setup Guide

Version 0.2.5 (beta test). Tested on the Steam release of Mass Effect Legendary Edition, English.

## Requirements

- Mass Effect Legendary Edition (Steam or EA app), Mass Effect 1 installed.
- [Archipelago](https://github.com/ArchipelagoMW/Archipelago/releases) 0.6.8 or newer.
- The [Mass Effect Archipelago Launcher](https://github.com/Mass-Effect-LE-Archipelago/ME-Archipelago-Launcher/releases/latest)
  (`Mass-Effect-Archipelago-Launcher.exe`, also attached to each
  [ME1 release](https://github.com/Mass-Effect-LE-Archipelago/ME1-APWorld/releases/latest)). It is self-contained:
  nothing else needs to be installed to run it.
- [ME3Tweaks Mod Manager](https://me3tweaks.com/modmanager/), once, for its ASI Manager (see step 1).

## 1. One-time: the ASI loader and LE1 Autoload Enabler

Open ME3Tweaks Mod Manager, select Mass Effect 1 (Legendary Edition), open *Tools > ASI Manager* and install **LE1
Autoload Enabler** (this also installs the ASI loader). These are not ours to ship, so the launcher checks for them and
tells you if they are missing. You do not need Mod Manager for anything else: the launcher installs the mod itself.

## 2. Install with the launcher

1. Close Mass Effect, the Archipelago Launcher and any Archipelago client.
2. Run `Mass-Effect-Archipelago-Launcher.exe` and pick **Mass Effect 1** on the left.
3. **Folders**: check that the Mass Effect Legendary Edition folder (the one that contains `Game\ME1`) and the
   Archipelago folder were found. They are shared by all three games and remembered.
4. **Deploy**: the System Status panel shows what is installed. Under *Install choices*, untick a travel video if you
   want to keep it (both are skipped by default). Then click **Download + Install**. The launcher downloads the newest
   ME1 release from GitHub, checks it against its SHA-256 sums, and installs the world into Archipelago, the bridge into
   the game's ASI folder and the mod with the game's file table (no AutoTOC needed). Every file it replaces is backed up.
5. **Options**: set your slot name and pick a preset or set each option (hover an option to read about it), then
   **Save to Players**. **Save + generate seed** also generates a seed right away (see "3. Generate and host").
6. **Deploy > Launch Mass Effect 1** checks that the world, bridge and mod match, starts the game and, if *Also start the
   Mass Effect LE1 Client* is ticked, the client. Steam (or the EA app) must be running. If the Legendary Edition
   launcher opens, pick Mass Effect 1. Then go on with "4. Play".

The **Intel** page has a short how-to and the notes of the newest release. No save import is needed for Mass Effect 1:
start a new career.

## 3. Generate and host

Mass Effect 1 is a custom world, so seeds are generated on your own PC; archipelago.gg can host them.

1. Every player makes a YAML: the launcher's **Options > Save to Players** (or **Save as...** to send it to someone),
   or Archipelago Launcher > **Options Creator** > Mass Effect Legendary Edition 1.
2. Whoever generates puts every player's YAML in `Archipelago/Players`, installs every custom world in the multiworld,
   then clicks **Save + generate seed** in the launcher (or **Generate** in the Archipelago Launcher). The seed is
   written to `Archipelago/output/AP_<seed>.zip`.
3. Host it: upload that zip at [archipelago.gg > Host Game](https://archipelago.gg/uploads) (use the latest Archipelago
   release to generate), or click **Host** in the Archipelago Launcher to host on your own PC (port 38281).

## 4. Play

1. Start the game and start a **new career**. After character creation you are a Spectre on the Normandy.
2. In the **Mass Effect LE1 Client**, connect with your room's address and your slot name. The client says
   "Connected to LE1APBridge with a game world loaded" once a save is loaded.
3. Connect before you open any shop: a shop fills its stock on your first visit, and the client tells the game how many
   shop slots your seed has.
4. Press **F7** in game for a route summary, and check the **Archipelago** assignment in the journal. Keep the client
   running: it keeps the journal and the galaxy-map markers up to date. (To use another key than F7, put its Windows
   virtual-key code, e.g. `0x77` for F8, in a file `LE1APBridge.hotkey` next to `LE1APBridge.asi`.)

The client must run on the same PC as the game. Checks you make while the client is closed are kept in your save and
sent the next time it connects; items you receive while the game is closed arrive when you load your save.

Each save is bound to its seed and slot the first time the client connects to it, and the client refuses a save from
another seed (it changes nothing in it). A career started before 0.2.4 is not bound yet: load its save, connect, and
type `/bind` in the client once.

## Updating

When a new ME1 release is out, the launcher's Deploy button says **Update**: close the game and the Archipelago Launcher
and click it. When a new version of the launcher itself is out, a button at the top of its window says so.

If you installed with Mass Effect AP Setup (0.3.x) before, the launcher recognises that install and its backups: just
click **Update** or **Install / Repair**. If you installed by hand with Mod Manager, *Restore* the game in Mod Manager
first (or delete `BioGame\DLC\DLC_MOD_ArchipelagoME1`), then install with the launcher.

From 0.2.4 the client checks the bridge (v13 from 0.2.5) and the mod version and stops with a message naming what to
update; **Install / Repair** in the launcher fixes it.

## Recommended

[Proper Convo-Cutscene Skipper](https://www.nexusmods.com/masseffectlegendaryedition/mods/1681) lets you skip
conversations and cutscenes. Install it through Mod Manager.

## Troubleshooting

- **The launcher says LE1 Autoload Enabler or the ASI loader is missing**: do step 1 in Mod Manager, then click
  **Install / Repair** again.
- **"Error -5 while decompressing data"** in the Archipelago Launcher after an install or update: close the Archipelago
  Launcher completely and start it again. The world was installed; the Launcher cannot reload an apworld it had already
  loaded.
- **"Inventory full" / "N items waiting"**: the squad inventory holds 300 items. Sell gear or convert it to omni-gel;
  the waiting items then arrive in order (from 0.2.5; nothing is lost).
- **The client says the bridge or the mod is out of date**: click **Install / Repair** (or **Update**) in the launcher.

Downloads are kept in `%LOCALAPPDATA%\MassEffectAPSetup\downloads`, install records and backups in
`%LOCALAPPDATA%\MassEffectAPSetup\ME1`.

## Uninstall

In the launcher, pick Mass Effect 1 and click **Deploy > Uninstall**. It puts back every file it changed (this also
brings back the travel videos) and removes the world, the bridge and the mod.

## Other games

The same launcher installs Mass Effect 2 and Mass Effect 3 from their own projects,
[ME2-APWorld](https://github.com/Mass-Effect-LE-Archipelago/ME2-APWorld) and
[ME3-AP-World](https://github.com/Mass-Effect-LE-Archipelago/ME3-AP-World). See those pages for their status.
