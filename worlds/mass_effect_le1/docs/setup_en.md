# Mass Effect Legendary Edition 1 Setup Guide

Version 0.2 (beta test). Tested on the Steam release of Mass Effect Legendary Edition, English.

## Requirements

- Mass Effect Legendary Edition (Steam or EA app), Mass Effect 1 installed.
- [Archipelago](https://github.com/ArchipelagoMW/Archipelago/releases) 0.6.8 or newer.
- [ME3Tweaks Mod Manager](https://me3tweaks.com/modmanager/), once, for its ASI Manager (the ASI loader and LE1
  Autoload Enabler). With the setup app you do not need it for anything else.
- From the [latest release](https://gitlab.com/unowa001/ArchipelagoME1/-/releases/permalink/latest): either
  `MassEffectAPSetup-<version>-ME1.zip` (the setup app, recommended), or the four separate files for a manual install
  (see "Manual install").

## 1. One-time: the ASI loader and LE1 Autoload Enabler

Open ME3Tweaks Mod Manager, select Mass Effect 1 (Legendary Edition), open *Tools > ASI Manager* and install **LE1
Autoload Enabler** (this also installs the ASI loader). These are not ours to ship, so the setup app checks for them and
tells you if they are missing.

## 2. Install with the setup app (recommended)

1. Close Mass Effect, the Archipelago Launcher and any Archipelago client.
2. Unzip `MassEffectAPSetup-<version>-ME1.zip` anywhere and run **Mass Effect AP Setup.exe** (keep the `ME1` folder
   next to it). Pick **Mass Effect 1**.
3. **1. Folders**: check the Mass Effect Legendary Edition and Archipelago folders (found automatically).
4. **2. Install**: choose whether to skip the two galaxy-map travel videos, then **Install / Repair**. It installs the
   world into Archipelago, the bridge into the game's ASI folder and the mod with the game's file table (no AutoTOC
   needed). Everything it replaces is backed up; **Uninstall** puts every file back as it was.
5. **3. Options**: set your slot name and options (or a preset), then **Save to Archipelago Players**, or **Save +
   Generate seed** to generate right away (it uses every YAML in Archipelago's Players folder and opens the output
   folder). Host the seed as in "4. Generate and host".
6. **2. Install > Launch Mass Effect 1** checks that the world, bridge and mod match, starts the game and (ticked) the
   **Mass Effect LE1 Client**. If the Legendary Edition launcher opens, pick Mass Effect 1. Then go on with "5. Play".

No save import is needed for Mass Effect 1: start a new career.

## Manual install (without the setup app)

Download `mass_effect_le1.apworld`, `ArchipelagoME1-mod-<version>.zip` (do not unzip it),
`ArchipelagoME1-bridge-<version>.zip` (unzip it) and, optionally, `Mass Effect Legendary Edition 1.yaml`.

### The world

Double-click `mass_effect_le1.apworld` (or copy it into `Archipelago/custom_worlds`). The Archipelago Launcher then
lists **Mass Effect LE1 Client**.

### The game mod

1. Open ME3Tweaks Mod Manager and select Mass Effect 1 (Legendary Edition).
2. Drag `ArchipelagoME1-mod-<version>.zip` onto Mod Manager (or *Mod Management > Import mod from archive*), then apply
   **Archipelago for Mass Effect 1**. The installer asks whether to skip the mass relay and FTL travel videos.
3. In *Tools > ASI Manager* (Mass Effect 1 LE), install **LE1 Autoload Enabler** and **LE1 AutoTOC** if they are not
   installed yet. This also installs the ASI loader.

### The bridge

The bridge (`LE1APBridge.asi`) lets the client read and write the game's plot state and hand over items. Unzip
`ArchipelagoME1-bridge-<version>.zip` first, then:

- Right-click `install-bridge.ps1` > *Run with PowerShell*. It finds the game in the usual Steam and EA folders; if it
  does not, run it from a PowerShell window with `-GamePath "<folder that contains Game\ME1>"`.
- Or copy both files from the `ASI` folder into `<Mass Effect Legendary Edition>\Game\ME1\Binaries\Win64\ASI\` by
  hand (delete any older `LE1APBridge*.asi` there).

## 3. Recommended

[Proper Convo-Cutscene Skipper](https://www.nexusmods.com/masseffectlegendaryedition/mods/1681) lets you skip
conversations and cutscenes. Install it through Mod Manager.

## 4. Generate and host

Mass Effect 1 is a custom world, so seeds are generated on your own PC; archipelago.gg can host them.

1. Make your YAML: Archipelago Launcher > **Options Creator** > Mass Effect Legendary Edition 1 (or edit the template
   `Mass Effect Legendary Edition 1.yaml`).
2. Whoever generates puts every player's YAML in `Archipelago/Players` (and installs every custom world in the
   multiworld), then clicks **Generate** in the Launcher. The seed is written to `Archipelago/output/AP_<seed>.zip`.
3. Host it: upload that zip at [archipelago.gg > Host Game](https://archipelago.gg/uploads) (use the latest Archipelago
   release to generate), or click **Host** in the Launcher to host on your own PC (port 38281).

## 5. Play

1. Start the game and start a **new career**. After character creation you are a Spectre on the Normandy.
2. Open the Archipelago Launcher > **Mass Effect LE1 Client** and connect with your slot name. The client says
   "Connected to LE1APBridge with a game world loaded" once a save is loaded.
3. Connect before you open any shop: a shop fills its stock on your first visit, and the client tells the game how many
   shop slots your seed has.
4. Press **F7** in game for a route summary, and check the **Archipelago** assignment in the journal. Keep the client
   running: it keeps the journal and the galaxy-map markers up to date. (To use another key than F7, put its Windows
   virtual-key code, e.g. `0x77` for F8, in a file `LE1APBridge.hotkey` next to `LE1APBridge.asi`.)

The client must run on the same PC as the game. Checks you make while the client is closed are kept in your save and
sent the next time it connects; items you receive while the game is closed arrive when you load your save.

## Updating

With the setup app: unzip the new version and click **Install / Repair** (close the Archipelago Launcher first).
Manually: download the new apworld, mod zip and bridge zip. Replace the apworld, import and apply the new mod zip in Mod Manager,
and run `install-bridge.ps1` from the new bridge zip. Install all three: from 0.2.4 the client checks the bridge (v13 from
0.2.5) and the mod version and stops with a message naming what to update.

From 0.2.4 each save is bound to its seed and slot the first time the client connects to it, and the client refuses a
save from another seed (it changes nothing in it). A career started before 0.2.4 is not bound yet: load its save,
connect, and type `/bind` in the client once. From 0.2.0, an existing career should keep working (shops you already
visited have no slots); from 0.1.x, start a new career.

## Troubleshooting

- **"Error -5 while decompressing data"** in the Archipelago Launcher after you double-click a new apworld: close the
  Launcher completely and start it again. The world was installed; the Launcher cannot reload an apworld it had already
  loaded.
- **"Inventory full" / "N items waiting"**: the squad inventory holds 300 items. Sell gear or convert it to omni-gel;
  the waiting items then arrive in order (from 0.2.5; nothing is lost).
- **The client says the bridge or the mod is out of date**: install the bridge zip and the mod zip of the same release
  as the apworld (see Updating).

## Mass Effect 2 (experimental)

The setup app also has a Mass Effect 2 profile. **It is EXPERIMENTAL**: its install and uninstall are tested in scratch
folders only, not in game with this app. To try it, download `MassEffectAPSetup-<version>-ME2-experimental.zip` from the
release, unzip it next to (or instead of) the ME1 zip, and pick Mass Effect 2. Its payload is the
[ArchipelagoME2 0.2.2](https://gitlab.com/unowa001/ArchipelagoME2/-/releases/v0.2.2) release: the ME2 apworld (with its
client), the LE2 bridge, the ME2 mod and its ASI loader. Please report problems at
https://gitlab.com/unowa001/ArchipelagoME1/-/issues. Mass Effect 3 is not supported yet.

## Uninstall

With the setup app: **2. Install > Uninstall** puts back every file it changed. After a manual install: in Mod Manager, *Restore* the game (this also brings back the travel videos) (or delete `BioGame\DLC\DLC_MOD_ArchipelagoME1`), then delete `LE1APBridge*.asi`
and `LE1APBridge.checks.tsv` from `Game\ME1\Binaries\Win64\ASI\`.
