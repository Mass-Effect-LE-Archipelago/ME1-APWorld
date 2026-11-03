# LE1APBridge

The bridge the client talks to: an ASI plugin that reads and writes the game's plot state, hands over items and shows
HUD notices. This folder holds it as built files; its source is not part of this repository.

- `LE1APBridge.asi`: bridge v13 (from the 0.2.5 release). The client refuses an older bridge (`BRIDGE_VERSION` in
  `worlds/mass_effect_le1/client.py`).
- `LE1APBridge.checks.tsv`: the bridge's checks table, `<package>.<actor path>` to the plot bool it sets when that
  container or Aid Station is used. It is read next to the `.asi`.

`tools/release/build_release.py` packs both into the bridge zip, and the setup app installs them into the game's
`Binaries\Win64\ASI` folder.
