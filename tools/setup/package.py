r"""Package Mass Effect AP Setup with its ME1 payload (and optionally ME2) into release/MassEffectAPSetup-<version>/.

usage: python tools/setup/package.py <app version> [--me1-release <dir>] [--me2-release <dir> --me2-loader <bink2w64.dll>]
  --me1-release: a folder written by tools/release/build_release.py (default: the newest build/release-<version>)
  --me2-release, --me2-loader: the ME2 payload (an ArchipelagoME2 release folder and its ASI loader); left out when not given
Layout: "Mass Effect AP Setup.exe" (self-contained, single file), ME1\ (and ME2\) payloads (see Profiles.cs), SHA256SUMS.
"""
import argparse
import hashlib
import pathlib
import shutil
import subprocess
import sys
import zipfile

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[1]


def me1_payload(release: pathlib.Path, dest: pathlib.Path) -> None:
    """ME1\\: apworld, ASI\\ (bridge + checks table), ArchipelagoME1\\ (moddesc.ini, DLC_MOD_ArchipelagoME1, BASEGAME)."""
    version = release.name.split("-", 1)[1]
    dest.mkdir(parents=True)
    shutil.copy(release / "mass_effect_le1.apworld", dest / "mass_effect_le1.apworld")
    (dest / "ASI").mkdir()
    with zipfile.ZipFile(release / f"ArchipelagoME1-bridge-{version}.zip") as z:
        for name in ("LE1APBridge.asi", "LE1APBridge.checks.tsv"):
            (dest / "ASI" / name).write_bytes(z.read(f"ArchipelagoME1-bridge-{version}/ASI/{name}"))
    with zipfile.ZipFile(release / f"ArchipelagoME1-mod-{version}.zip") as z:
        z.extractall(dest)


def me2_payload(release: pathlib.Path, loader: pathlib.Path, dest: pathlib.Path) -> None:
    """ME2\\: apworld, ASI\\LE2APBridge.asi, ArchipelagoME2\\ (moddesc.ini, DLC_MOD_ArchipelagoME2), the AP ASI Loader."""
    dest.mkdir(parents=True)
    shutil.copytree(release / "ArchipelagoME2", dest / "ArchipelagoME2")
    shutil.copy(release / "mass_effect_le2.apworld", dest / "mass_effect_le2.apworld")
    (dest / "ASI").mkdir()
    shutil.copy(release / "LE2APBridge.asi", dest / "ASI" / "LE2APBridge.asi")
    shutil.copy(loader, dest / "bink2w64.dll")


def newest_release() -> pathlib.Path | None:
    """The newest build/release-<version> folder (by version), or None."""
    def key(path: pathlib.Path) -> tuple[int, ...]:
        return tuple(int(part) if part.isdigit() else -1 for part in path.name.split("-", 1)[1].split("."))
    releases = sorted((REPO / "build").glob("release-*"), key=key)
    return releases[-1] if releases else None


def defaults(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--me1-release", default=newest_release(), type=pathlib.Path)
    parser.add_argument("--me2-release", type=pathlib.Path)
    parser.add_argument("--me2-loader", type=pathlib.Path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("version")
    parser.add_argument("--out", type=pathlib.Path, help="output folder (default: release/MassEffectAPSetup-<version>)")
    defaults(parser)
    args = parser.parse_args()
    if args.me1_release is None:
        parser.error("no build/release-<version> folder: run tools/release/build_release.py first, or pass --me1-release")
    if (args.me2_release is None) != (args.me2_loader is None):
        parser.error("--me2-release and --me2-loader go together")
    out = args.out or REPO / "release" / f"MassEffectAPSetup-{args.version}"
    if out.exists():
        shutil.rmtree(out)
    publish = HERE / "bin" / "publish"
    subprocess.run(["dotnet", "publish", str(HERE / "APSetup.csproj"), "-c", "Release", "-r", "win-x64", "--self-contained", "true",
                    "-p:PublishSingleFile=true", "-p:IncludeNativeLibrariesForSelfExtract=true", "-p:EnableCompressionInSingleFile=true", f"-p:Version={args.version}",
                    "-o", str(publish)], check=True)
    out.mkdir(parents=True)
    shutil.copy(publish / "Mass Effect AP Setup.exe", out / "Mass Effect AP Setup.exe")
    me1_payload(args.me1_release, out / "ME1")
    if args.me2_release is not None:
        me2_payload(args.me2_release, args.me2_loader, out / "ME2")
    sums = [f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.relative_to(out).as_posix()}"
            for p in sorted(out.rglob("*")) if p.is_file()]
    (out / "SHA256SUMS").write_text("\n".join(sums) + "\n", newline="\n")
    print(f"packaged {out} ({len(sums)} files)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
