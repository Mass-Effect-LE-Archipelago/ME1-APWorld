# LE1APExtras

A small ASI next to LE1APBridge (whose source is not in this repository). It adds what the bridge cannot do: read the
player squad's level and grant squad XP exactly once per Experience item. The contract is [PROTOCOL.md](PROTOCOL.md).

- `LE1APExtras/`: the source (an LExASIs-style ASI, built against `vendor/LExASIs` and its LExSDKv2 LE1 target).
- `LE1APExtras.asi`: the built file the release packs into the bridge zip (install-bridge.ps1 and the setup app
  install it with the bridge).

## Build

Needs Visual Studio 2022 Build Tools with the C++ workload and its CMake (Windows, or WSL with `powershell.exe`), and
the LExASIs submodule with its own submodules (`git submodule update --init --recursive vendor/LExASIs`).

```
python tools/le1apextras/build.py [--config Release|Debug]
```

The script mirrors the sources into a Windows temp folder, configures `tools/le1apextras/CMakeLists.txt` (which
builds LExASIs' External and Common libraries without changing the submodule) and copies the result to
`tools/le1apextras/LE1APExtras.asi`. Commit the rebuilt `.asi` with its source change.
