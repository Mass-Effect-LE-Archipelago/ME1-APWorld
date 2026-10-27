"""Install / repair / uninstall tests of Mass Effect AP Setup in scratch folders (never the real game).

usage: python tools/setup/test_setup.py [--exe <Mass Effect AP Setup.exe>] [--me1-release <dir>] [--me2-release <dir>]
                                        [--me2-loader <bink2w64.dll>] [--rad-bink <RAD bink2w64.dll>]
Each test builds a fake Legendary Edition + Archipelago install, installs from a real release payload, checks the
result, uninstalls, and requires every file to be byte-identical (SHA-256) to before, with nothing added.
"""
import argparse
import hashlib
import pathlib
import shutil
import subprocess
import sys
import tempfile
import zipfile

from package import defaults, me1_payload, me2_payload

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[1]


def tree(root: pathlib.Path) -> dict[str, str]:
    """Relative path -> SHA-256 of every file under root (directories as "<dir>")."""
    out = {}
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root).as_posix()
        out[rel] = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else "<dir>"
    return out


def write(path: pathlib.Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


class Run:
    def __init__(self, exe: pathlib.Path, base: pathlib.Path, game: str):
        self.exe, self.game = exe, game
        self.le, self.ap, self.payload, self.state = (base / n for n in ("LE", "AP", "payload", "state"))
        self.failures: list[str] = []

    def cli(self, command: str, *extra: str, ok: bool = True) -> str:
        args = [str(self.exe), command, self.game, "--game", str(self.le), "--ap", str(self.ap),
                "--payload", str(self.payload / self.game), "--state", str(self.state), *extra]
        result = subprocess.run(args, capture_output=True, text=True)
        if (result.returncode == 0) != ok:
            self.fail(f"{command} {extra}: exit {result.returncode}: {result.stdout} {result.stderr}")
        return result.stdout + result.stderr

    def check(self, condition: bool, what: str) -> None:
        if not condition:
            self.fail(what)

    def fail(self, what: str) -> None:
        self.failures.append(what)
        print(f"  FAIL {self.game}: {what}")

    def toc_entries(self, toc: pathlib.Path) -> dict[str, int]:
        out = subprocess.run([str(self.exe), "--toc-list", str(toc)], capture_output=True, text=True).stdout.split("\n")
        return {line.split(" ", 1)[1]: int(line.split(" ", 1)[0]) for line in out if line.strip()}

    def snapshot(self) -> dict[str, str]:
        return {**{"LE/" + k: v for k, v in tree(self.le).items()}, **{"AP/" + k: v for k, v in tree(self.ap).items()}}

    def round_trip(self, label: str, *install_args: str, installs: int = 1, verify=None) -> None:
        before = self.snapshot()
        for _ in range(installs):
            self.cli("--install", *install_args)
        if verify:
            verify()
        self.cli("--uninstall")
        after = self.snapshot()
        if before != after:
            changed = sorted(k for k in before.keys() | after.keys() if before.get(k) != after.get(k))
            self.fail(f"{label}: uninstall left {len(changed)} difference(s): {changed[:8]}")
        self.check(not self.state.exists(), f"{label}: state folder left behind")
        print(f"  {self.game} {label}: {'ok' if not self.failures else 'FAILED'}")


def me1(exe: pathlib.Path, release: pathlib.Path, base: pathlib.Path) -> list[str]:
    run = Run(exe, base, "ME1")
    p = run.payload / "ME1"
    me1_payload(release, p)
    version = release.name.split("-", 1)[1]

    me = run.le / "Game" / "ME1"
    win64 = me / "Binaries" / "Win64"
    write(win64 / "MassEffect1.exe", b"exe")
    write(win64 / "bink2w64.dll", b"Mod Manager's loader")
    write(win64 / "bink2w64_original.dll", b"RAD bink")
    write(win64 / "ASI" / "LE1AutoloadEnabler-v13.asi", b"autoload")
    write(win64 / "ASI" / "LE1APBridge-v10.asi", b"old bridge")   # an older bridge: removed on install, back on uninstall
    for name in ("SFXGame.pcc", "BIOA_NOR00.pcc", "Startup_INT.pcc"):
        write(me / "BioGame" / "CookedPCConsole" / name, name.encode() * 50)
    write(me / "BioGame" / "Movies" / "GLO_01_Relay.bik", b"relay video" * 100)
    write(me / "BioGame" / "Movies" / "UCW_Loading_Flyby.bik", b"flyby video" * 100)
    write(me / "BioGame" / "PCConsoleTOC.bin", b"vanilla toc")
    write(me / "Engine" / "Shaders" / "ShaderCache.upk", b"shaders")   # the game TOC also lists Engine\Shaders
    write(me / "BioGame" / "DLC" / "DLC_MOD_ArchipelagoME1" / "CookedPCConsole" / "Stale.pcc", b"an older mod file")
    write(run.ap / "ArchipelagoLauncher.exe", b"launcher")
    write(run.ap / "custom_worlds" / "mass_effect_le1.apworld", b"world 0.2.1")

    dlc = me / "BioGame" / "DLC" / "DLC_MOD_ArchipelagoME1"

    def installed() -> None:
        run.check((run.ap / "custom_worlds" / "mass_effect_le1.apworld").read_bytes() == (p / "mass_effect_le1.apworld").read_bytes(), "apworld")
        run.check((win64 / "ASI" / "LE1APBridge.asi").read_bytes() == (p / "ASI" / "LE1APBridge.asi").read_bytes(), "bridge")
        run.check((win64 / "ASI" / "LE1APBridge.checks.tsv").exists(), "checks.tsv")
        run.check(not (win64 / "ASI" / "LE1APBridge-v10.asi").exists(), "old bridge removed")
        run.check(not (dlc / "CookedPCConsole" / "Stale.pcc").exists(), "stale mod file removed")
        src = p / "ArchipelagoME1" / "DLC_MOD_ArchipelagoME1"
        run.check(tree(dlc) == tree(src), "DLC folder equals the payload")
        run.check((dlc / "ArchipelagoME1.version").read_text().strip() == version, "mod version file")
        entries = run.toc_entries(me / "BioGame" / "PCConsoleTOC.bin")
        for f in src.rglob("*.pcc"):
            key = f"BioGame\\DLC\\DLC_MOD_ArchipelagoME1\\CookedPCConsole\\{f.name}"
            run.check(entries.get(key) == f.stat().st_size, f"TOC lists {f.name}")
        run.check(entries.get("BioGame\\CookedPCConsole\\SFXGame.pcc") == len("SFXGame.pcc") * 50, "TOC keeps basegame files")
        run.check(entries.get("BioGame\\PCConsoleTOC.bin") == (me / "BioGame" / "PCConsoleTOC.bin").stat().st_size, "TOC lists itself")
        run.check("ready to launch" in run.cli("--check"), "--check ready after install")

    def movies(skip_relay: bool, skip_flyby: bool):
        def verify() -> None:
            installed()
            for name, skipped in (("GLO_01_Relay.bik", skip_relay), ("UCW_Loading_Flyby.bik", skip_flyby)):
                size = (me / "BioGame" / "Movies" / name).stat().st_size
                run.check((size == 0) == skipped, f"{name} {'skipped' if skipped else 'kept'}")
        return verify

    run.round_trip("install + uninstall", verify=movies(True, True))
    run.round_trip("repair (install twice)", installs=2, verify=movies(True, True))
    run.round_trip("keep the relay video", "--keep-movie", "GLO_01_Relay.bik", verify=movies(False, True))
    # skip first, then repair keeping both: the movies come back at once, and uninstall still restores everything
    before = run.snapshot()
    run.cli("--install")
    run.cli("--install", "--keep-movie", "GLO_01_Relay.bik", "--keep-movie", "UCW_Loading_Flyby.bik")
    movies(False, False)()
    run.cli("--uninstall")
    run.check(run.snapshot() == before, "skip then keep: uninstall restores everything")
    # requirements missing: install still works, --check refuses to launch
    (win64 / "ASI" / "LE1AutoloadEnabler-v13.asi").unlink()
    run.cli("--install")
    out = run.cli("--check", ok=False)
    run.check("LE1 Autoload Enabler" in out, "--check names the missing Autoload Enabler")
    run.cli("--uninstall")
    run.cli("--uninstall", ok=False)   # nothing left to uninstall
    return run.failures


def me2(exe: pathlib.Path, release: pathlib.Path, loader: pathlib.Path, rad: pathlib.Path, base: pathlib.Path) -> list[str]:
    run = Run(exe, base, "ME2")
    p = run.payload / "ME2"
    me2_payload(release, loader, p)

    win64 = run.le / "Game" / "ME2" / "Binaries" / "Win64"
    write(win64 / "MassEffect2.exe", b"exe")
    shutil.copy(rad, win64 / "bink2w64.dll")   # the game's own RAD Bink DLL (no loader yet)
    write(run.le / "Game" / "ME2" / "BioGame" / "CookedPCConsole" / "SFXGame.pcc", b"game")
    write(run.ap / "ArchipelagoLauncher.exe", b"launcher")
    dlc = run.le / "Game" / "ME2" / "BioGame" / "DLC" / "DLC_MOD_ArchipelagoME2"

    def installed() -> None:
        # what ME2 AP Setup 0.2.1 (+ AP ASI Loader) does: world, bridge, loader, the DLC folder copied with its own TOC
        run.check((run.ap / "custom_worlds" / "mass_effect_le2.apworld").read_bytes() == (release / "mass_effect_le2.apworld").read_bytes(), "apworld")
        run.check((win64 / "ASI" / "LE2APBridge.asi").read_bytes() == (release / "LE2APBridge.asi").read_bytes(), "bridge")
        run.check((win64 / "bink2w64.dll").read_bytes() == loader.read_bytes(), "AP ASI Loader in place")
        run.check((win64 / "bink2w64_original.dll").read_bytes() == rad.read_bytes(), "RAD Bink kept as bink2w64_original.dll")
        src = release / "ArchipelagoME2" / "DLC_MOD_ArchipelagoME2"
        got = {k: v for k, v in tree(dlc).items() if k != "PCConsoleTOC.bin"}
        run.check(got == tree(src), "DLC folder equals the release's")
        entries = run.toc_entries(dlc / "PCConsoleTOC.bin")
        expected = {"CookedPCConsole\\" + f.name: f.stat().st_size for f in (src / "CookedPCConsole").glob("*.pcc")}
        run.check(set(expected) <= set(entries) and all(entries[k] == v for k, v in expected.items()), "DLC TOC lists the mod files")
        run.check("ready to launch" in run.cli("--check"), "--check ready after install")

    run.round_trip("install + uninstall", verify=installed)
    run.round_trip("repair (install twice)", installs=2, verify=installed)

    before = run.snapshot()
    run.cli("--install")
    (win64 / "bink2w64.dll").unlink()   # the loader went missing after installing
    run.check("ASI loader" in run.cli("--check", ok=False), "--check refuses without the loader")
    run.cli("--install")                # Repair puts it back
    run.check((win64 / "bink2w64.dll").read_bytes() == loader.read_bytes() and "ready to launch" in run.cli("--check"),
              "Repair restores a missing loader")
    other = run.ap.parent / "AP-other"
    write(other / "ArchipelagoLauncher.exe", b"launcher")
    real_ap, run.ap = run.ap, other
    run.cli("--install", ok=False)   # another Archipelago folder while installed: refused
    run.cli("--uninstall")           # uninstall works on the recorded folders, whatever is selected now
    run.ap = real_ap
    shutil.rmtree(other)
    run.check(run.snapshot() == before, "uninstall with another folder selected restores the recorded install")
    print(f"  ME2 missing loader / other folder: {'ok' if not run.failures else 'FAILED'}")
    return run.failures


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--exe", default=HERE / "bin" / "Release" / "net10.0-windows" / "Mass Effect AP Setup.exe", type=pathlib.Path)
    defaults(parser)
    parser.add_argument("--rad-bink", default=pathlib.Path(r"C:\Steam\steamapps\common\Mass Effect Legendary Edition\Game\ME2\Binaries\Win64\bink2w64_original.dll"), type=pathlib.Path)
    args = parser.parse_args()
    failures = []
    with tempfile.TemporaryDirectory(prefix="apsetup-") as scratch:
        failures += me1(args.exe, args.me1_release, pathlib.Path(scratch) / "me1")
        if all(p.exists() for p in (args.me2_release, args.me2_loader, args.rad_bink)):
            failures += me2(args.exe, args.me2_release, args.me2_loader, args.rad_bink, pathlib.Path(scratch) / "me2")
        else:
            print("  ME2: skipped (no ME2 release, AP ASI Loader build or RAD bink2w64.dll; see --me2-*)")
    print(f"{len(failures)} failure(s)")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
