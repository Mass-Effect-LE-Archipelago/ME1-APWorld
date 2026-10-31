# Archipelago for Mass Effect 1 (Legendary Edition)

An [Archipelago](https://archipelago.gg) multiworld randomizer for Mass Effect 1 in Mass Effect Legendary Edition.

**Status: beta test (0.2.5).** It's playable from start to finish on the Steam release (English). Expect bugs.

## What changes

Shepard starts as a Spectre on the Normandy with no squad. Eden Prime, Therum, Feros, Noveria, Virmire and Asteroid X57
stay locked on the galaxy map until you find their coordinates. Squadmates, weapons, armor, bio-amps, omni-tools and
upgrades are all items. Ilos opens once Virmire is done and you've collected enough Prothean Beacon Fragments. You win
by defeating Saren and Sovereign on the Citadel.

Checks include story milestones, recruitments, Codex pages, journal entries, shop slots, and (optionally) containers and
Aid Stations. Sent and received items show as notices on the HUD, infinite storm can be enabled, and the galaxy-map
travel videos can be skipped.

**In-game tracker:** the client works out your seed's logic as you play. Press **F7** for a summary box (checks in logic
per region, every uncharted planet worth visiting, what each locked world still needs), check the **Archipelago**
assignment in the journal (fragments, coordinates, squad, checks in logic), and look for "Archipelago" callouts on the
galaxy map. See the [game page](worlds/mass_effect_le1/docs/en_Mass%20Effect%20Legendary%20Edition%201.md) for the details.

## Play it

Use the **[Mass Effect Archipelago Launcher](https://github.com/Mass-Effect-LE-Archipelago/ME-Archipelago-Launcher/releases/latest)**.
It downloads this project's newest release, installs the world, the mod and the game bridge (with backups), writes your
YAML, can generate a seed, and starts the game together with the Mass Effect LE1 Client.

1. Install [Archipelago](https://github.com/ArchipelagoMW/Archipelago/releases) 0.6.8 or newer.
2. Once: in [ME3Tweaks Mod Manager](https://me3tweaks.com/modmanager/), pick Mass Effect 1 (Legendary Edition), open
   *Tools > ASI Manager* and install **LE1 Autoload Enabler** (this adds the ASI loader). That is the only thing Mod
   Manager is needed for.
3. Download `Mass-Effect-Archipelago-Launcher.exe` and run it. Pick **Mass Effect 1**, click **Download + Install**,
   set your options and **Save to Players**, then **Launch**.
4. Start a **new career** and connect the client to your room before you open any shop.

The **[setup guide](worlds/mass_effect_le1/docs/setup_en.md)** has every step, including generating and hosting a seed,
updating, and troubleshooting.

Mass Effect 1 is a custom world, so seeds are generated on your own PC (the launcher's **Save + generate seed** or
**Generate** in the Archipelago Launcher) and can then be hosted on [archipelago.gg](https://archipelago.gg/uploads).

## Reporting bugs

Open an [issue](https://github.com/Mass-Effect-LE-Archipelago/ME1-APWorld/issues) and include:

- What you did and what happened (the planet or mission, what you picked up or talked to).
- The newest `ME1Client_*.txt` from Archipelago's `logs` folder (for example `C:\ProgramData\Archipelago\logs`).
- Your YAML and the seed, if the problem is about logic (something unreachable, or reachable too early).

Problems with installing or the launcher itself go to the
[launcher's issues](https://github.com/Mass-Effect-LE-Archipelago/ME-Archipelago-Launcher/issues).

## Repository layout

- `worlds/mass_effect_le1/`: the Archipelago world (logic, items, locations, options) and the client.
- `tools/release/`: the release packaging script and the bridge installer.
- `tools/setup/`: the source of Mass Effect AP Setup, the older standalone installer (replaced by the launcher).

The game mod and the bridge ship as built files on the [release page](https://github.com/Mass-Effect-LE-Archipelago/ME1-APWorld/releases).
