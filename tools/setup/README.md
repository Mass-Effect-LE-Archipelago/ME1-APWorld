# Mass Effect AP Setup (source)

The setup app that installs Archipelago for Mass Effect 1 (LE) without ME3Tweaks Mod Manager: the world into
Archipelago, the bridge into the game's ASI folder, the mod into the game with its file table (the game TOC that
AutoTOC would otherwise write), and the optional travel-video skip. Every file it changes is backed up; Uninstall puts
them back. It also writes your YAML into Archipelago's Players folder, runs Generate, and launches the game and client.
The ME2 profile is experimental (tested in scratch folders only); its payload (the ArchipelagoME2 0.2.2 release files) is
published as the separate `MassEffectAPSetup-<version>-ME2-experimental.zip` release asset.

License: GPL-3.0 (`LICENSE`), because it is built with LegendaryExplorerCore. Third-party components and their licenses:
`THIRD-PARTY-NOTICES.md`, `licenses/`.

## Build

1. .NET 10 SDK on Windows.
2. LegendaryExplorerCore source: the `vendor/LegendaryExplorer` submodule (`git submodule update --init`), pinned to
   the commit the app is built with.
3. `dotnet build tools/setup/APSetup.csproj -c Release`, or `python tools/setup/package.py <version> --me1-release <release folder>`
   for the self-contained single-file exe next to its `ME1\` payload.

## Tests

`python tools/setup/test_setup.py --me1-release <release folder>` installs into fake game and Archipelago folders in a
temporary directory, checks the result, uninstalls, and requires every file to be byte-identical (SHA-256) afterwards.
`options-me1.json` is exported from the world by `export_options.py`; the world test `test_setup_options.py` keeps it in
sync.
