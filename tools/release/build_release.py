"""Build the player release of Archipelago for Mass Effect 1 (LE) into build/release-<version>/.

usage: python tools/release/build_release.py <version>
Release assets, each uploaded on its own (the release notes link the setup guide, which is not packaged):
  mass_effect_le1.apworld, the YAML template, ArchipelagoME1-mod-<version>.zip (ME3Tweaks Mod Manager import:
  moddesc.ini + DLC_MOD_ArchipelagoME1), ArchipelagoME1-bridge-<version>.zip (ASI/ with the bridge and checks table,
  install-bridge.ps1), options-me1.json (the option schema the launcher's Options page reads), SHA256SUMS.
Everything is read from the repo: the world (worlds/), the game mod (mod/), the bridge (tools/le1apbridge/) and
Archipelago (the vendor/Archipelago submodule, with its .venv set up). Nothing under the game folder is touched.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import zipfile

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
WORLD = os.path.join(REPO, "worlds", "mass_effect_le1")
MOD = os.path.join(REPO, "mod")
BRIDGE = os.path.join(REPO, "tools", "le1apbridge")
AP = os.path.join(REPO, "vendor", "Archipelago")
YAML = "Mass Effect Legendary Edition 1.yaml"
MOD_FOLDER = "DLC_MOD_ArchipelagoME1"
MOD_VERSION_FILE = "ArchipelagoME1.version"
# Docs links to this repository's own pages (releases, issues), relative so they work on any fork; made absolute in the
# packaged apworld, whose docs Archipelago's website renders outside the repository.
REPO_LINK = re.compile(r"\]\((?:\.\./)+((?:releases|issues)\b[^)]*)\)")
OPTIONS = os.path.join(REPO, "tools", "setup", "options-me1.json")  # the world's option schema
# The galaxy-map travel videos (mass relay jump, FTL flyby) are replaced by empty files, as the "Fully Skipped" option
# of Nexus mod 2422 does (needs Mod Manager's enhanced Bink, requested below). Each one can be kept at install time.
SKIPPED_MOVIES = (("GLO_01_Relay.bik", "Mass Relay Jump Video", "mass relay jump video"),
                  ("UCW_Loading_Flyby.bik", "FTL Flyby Video", "FTL flyby video"))
MOVIE_OPTIONS = ",".join(
    f'(OptionGroup="{group}", Condition=COND_MANUAL, ModOperation=OP_NOTHING, CheckedByDefault=TRUE, FriendlyName="Skip", '
    f'Description="Skip the {noun} on the galaxy map."),'
    f'(OptionGroup="{group}", Condition=COND_MANUAL, ModOperation=OP_NOINSTALL, ModFile=\\BIOGame\\Movies\\{movie}, '
    f'FriendlyName="Keep", Description="Keep the vanilla {noun}.")'
    for movie, group, noun in SKIPPED_MOVIES)
MODDESC = """[ModManager]
cmmver = 8.0

[ModInfo]
game = LE1
modname = Archipelago for Mass Effect 1
moddesc = Archipelago multiworld randomizer support for Mass Effect 1 (LE). Start a NEW career after installing. Also install the LE1APBridge ASI (install-bridge.ps1 in the bridge zip) and run the Mass Effect LE1 Client from the Archipelago Launcher. Setup guide: {setup_url}
modver = {version}
moddev = Jerrod, Tyler Kessler
requiresenhancedbink = true

[CUSTOMDLC]
sourcedirs = {mod}
destdirs = {mod}

[BASEGAME]
moddir = BASEGAME
newfiles = Movies
replacefiles = BIOGame\\Movies\\
gamedirectorystructure = true
altfiles = ({movie_options})
"""


def github_repo() -> str:
    """https://github.com/<owner>/<name> of the remote the current branch tracks (else origin)."""
    def git(*args: str) -> str:
        return subprocess.run(["git", *args], cwd=REPO, capture_output=True, text=True).stdout.strip()
    upstream = git("rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}")
    remote = upstream.split("/", 1)[0] if "/" in upstream else "origin"
    url = git("remote", "get-url", remote)
    match = re.search(r"github\.com[:/]([^/]+)/([^/]+?)(?:\.git)?/?$", url)
    if match is None:
        raise SystemExit(f"remote {remote} ({url or 'not set'}) is not a GitHub repository: the release links need one")
    return f"https://github.com/{match.group(1)}/{match.group(2)}"


def zip_dir(src: str, zip_path: str, arc_root: str, skip=lambda rel: False, transform=lambda rel, data: data) -> None:
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for base, dirs, files in os.walk(src):
            dirs[:] = sorted(d for d in dirs if not skip(os.path.relpath(os.path.join(base, d), src)))
            for f in sorted(files):
                rel = os.path.relpath(os.path.join(base, f), src)
                if not skip(rel):
                    with open(os.path.join(base, f), "rb") as handle:
                        data = transform(rel, handle.read())
                    z.writestr(zipfile.ZipInfo.from_file(os.path.join(base, f), os.path.join(arc_root, rel).replace("\\", "/")),
                               data, zipfile.ZIP_DEFLATED)


def ap_python(ap: str) -> str:
    for rel in (("Scripts", "python.exe"), ("bin", "python")):
        path = os.path.join(ap, ".venv", *rel)
        if os.path.exists(path):
            return path
    raise SystemExit(f"no .venv in {ap}: set up Archipelago's virtual environment (see README.md, Development)")


def template_and_verify(out: str, version: str, ap: str) -> None:
    """Write the YAML template and fail the build unless every archive reads back whole and the packaged apworld loads
    and generates on its own. Both run with the packaged apworld as Archipelago's only copy of the world: it is put in
    custom_worlds, and a worlds/mass_effect_le1 folder, if present, is moved aside (both always undone)."""
    for name in sorted(os.listdir(out)):
        if name.endswith((".zip", ".apworld")):
            with zipfile.ZipFile(os.path.join(out, name)) as z:
                bad = z.testzip()
            if bad is not None:
                raise SystemExit(f"{name}: damaged member {bad}")
    world_dir = os.path.join(ap, "worlds", "mass_effect_le1")
    aside = world_dir + ".release-check"
    custom = os.path.join(ap, "custom_worlds")
    packaged = os.path.join(custom, "mass_effect_le1.apworld")
    owned = os.path.join(ap, "custom_worlds.release-check")   # exists while `packaged` is this check's copy

    def put_back_world() -> None:
        if os.path.exists(aside) and not os.path.exists(world_dir):
            os.rename(aside, world_dir)

    def remove_packaged() -> None:
        if os.path.exists(owned):
            if os.path.exists(packaged):
                os.remove(packaged)
            os.remove(owned)

    def restore() -> list[str]:
        """Undo this check's changes, each step on its own (safe to repeat; also repairs an interrupted earlier run).
        Only a packaged copy this check put there is removed. Returns the errors."""
        errors = []
        for step in (put_back_world, remove_packaged):
            for _attempt in range(3):
                try:
                    step()
                    break
                except BaseException as error:   # retried if interrupted; the other step runs regardless
                    errors.append(f"{step.__name__}: {error!r}")
        return errors

    restore()
    if os.path.exists(aside) or os.path.exists(owned):
        raise SystemExit(f"leftover from an earlier check that cannot be undone automatically: {aside} / {owned}")
    if os.path.exists(packaged):
        raise SystemExit(f"{packaged} is installed: move it out of the way for the release check")
    scratch = os.path.join(out, "_check")
    python = ap_python(ap)
    env = {**os.environ, "SKIP_REQUIREMENTS_UPDATE": "1"}
    # The world must come from the packaged archive: Archipelago skips a world whose game is already registered.
    origin_check = ("import inspect, worlds\n"
                    "from worlds.AutoWorld import AutoWorldRegister\n"
                    "w = AutoWorldRegister.world_types.get('Mass Effect Legendary Edition 1')\n"
                    "print('ORIGIN', inspect.getfile(w) if w else None)\n")
    templates = os.path.join(scratch, "templates")
    try:
        os.makedirs(os.path.join(scratch, "players"))
        os.makedirs(custom, exist_ok=True)
        open(owned, "w").close()
        shutil.copyfile(os.path.join(out, "mass_effect_le1.apworld"), packaged)
        if os.path.exists(world_dir):
            os.rename(world_dir, aside)
        origin = subprocess.run([python, "-c", origin_check], cwd=ap, env=env, capture_output=True, text=True)
        template = subprocess.run([python, "-c", f"from Options import generate_yaml_templates; "
                                                 f"generate_yaml_templates(r'{templates}', False)"],
                                  cwd=ap, env=env, capture_output=True, text=True)
        if template.returncode == 0 and os.path.exists(os.path.join(templates, YAML)):
            shutil.copyfile(os.path.join(templates, YAML), os.path.join(out, YAML))
            shutil.copyfile(os.path.join(out, YAML), os.path.join(scratch, "players", "Check.yaml"))
            result = subprocess.run([python, "Generate.py", "--player_files_path", os.path.join(scratch, "players"),
                                     "--outputpath", os.path.join(scratch, "output")], cwd=ap, env=env,
                                    capture_output=True, text=True)
        else:
            result = None
        seeds = os.listdir(os.path.join(scratch, "output")) if os.path.isdir(os.path.join(scratch, "output")) else []
    finally:
        problems = restore()   # a run that still stops here is repaired by the next one
        shutil.rmtree(scratch, ignore_errors=True)
        if os.path.exists(aside) or os.path.exists(owned):
            raise SystemExit(f"could not restore {world_dir} / remove {packaged}: {problems}")
    loaded_from = next((line[7:] for line in origin.stdout.splitlines() if line.startswith("ORIGIN ")), "None")
    if os.path.normcase(os.path.abspath(packaged)) not in os.path.normcase(loaded_from):
        raise SystemExit(f"the world was not loaded from the packaged apworld (loaded from {loaded_from}):\n{origin.stderr[-2000:]}")
    if result is None:
        raise SystemExit(f"no YAML template was written:\n{template.stdout[-2000:]}\n{template.stderr[-2000:]}")
    if result.returncode != 0 or not seeds:
        raise SystemExit(f"the packaged apworld did not generate on its own:\n{result.stdout[-2000:]}\n{result.stderr[-2000:]}")
    print(f"verified: archives read back whole; the packaged {version} apworld loads, writes its template and generates")


def main(version: str) -> None:
    out = os.path.join(REPO, "build", f"release-{version}")
    if os.path.exists(out):
        shutil.rmtree(out)
    os.makedirs(out)

    def world_skip(rel: str) -> bool:
        parts = rel.replace("\\", "/").split("/")
        return "__pycache__" in parts or parts[0] == "test"
    repo_url = github_repo()

    def absolute_links(rel: str, data: bytes) -> bytes:
        if not rel.endswith(".md"):
            return data
        return REPO_LINK.sub(lambda m: f"]({repo_url}/{m.group(1)})", data.decode("utf-8")).encode("utf-8")
    apworld = os.path.join(out, "mass_effect_le1.apworld")
    zip_dir(WORLD, apworld, "mass_effect_le1", lambda rel: world_skip(rel) or rel == "archipelago.json", absolute_links)
    # .apworld manifest: the folder's archipelago.json plus the container fields Archipelago's own packer writes
    # (APWorldContainer.get_manifest: compatible_version 7, container version 7).
    with open(os.path.join(WORLD, "archipelago.json"), encoding="utf-8-sig") as f:
        manifest = {**json.load(f), "compatible_version": 7, "version": 7}
    with zipfile.ZipFile(apworld, "a", zipfile.ZIP_DEFLATED) as z:
        z.writestr("mass_effect_le1/archipelago.json", json.dumps(manifest, indent=4))

    shutil.copyfile(OPTIONS, os.path.join(out, "options-me1.json"))

    mod_src = os.path.join(MOD, MOD_FOLDER)
    if not os.path.isfile(os.path.join(mod_src, "AutoLoad.ini")):
        raise SystemExit(f"no {MOD_FOLDER}/AutoLoad.ini in {MOD}")
    tmp = os.path.join(out, "_mod")
    shutil.copytree(mod_src, os.path.join(tmp, MOD_FOLDER))
    # Build identity (R13): bridge v12+ reads this file (MODVER) and the client refuses a mod older than it needs.
    with open(os.path.join(tmp, MOD_FOLDER, MOD_VERSION_FILE), "w", encoding="ascii", newline="\n") as f:
        f.write(version + "\n")
    movies = os.path.join(tmp, "BASEGAME", "Movies")
    os.makedirs(movies)
    for movie, _group, _noun in SKIPPED_MOVIES:
        open(os.path.join(movies, movie), "wb").close()  # empty: the game skips the video
    with open(os.path.join(tmp, "moddesc.ini"), "w", encoding="utf-8", newline="\r\n") as f:
        f.write(MODDESC.format(version=version, mod=MOD_FOLDER, movie_options=MOVIE_OPTIONS,
                               setup_url=f"{repo_url}/blob/main/worlds/mass_effect_le1/docs/setup_en.md"))
    zip_dir(tmp, os.path.join(out, f"ArchipelagoME1-mod-{version}.zip"), "ArchipelagoME1")
    shutil.rmtree(tmp)

    # Bridge zip: install-bridge.ps1 copies from the ASI folder next to it.
    tmp = os.path.join(out, "_bridge")
    os.makedirs(os.path.join(tmp, "ASI"))
    for name in ("LE1APBridge.asi", "LE1APBridge.checks.tsv"):
        shutil.copyfile(os.path.join(BRIDGE, name), os.path.join(tmp, "ASI", name))
    shutil.copyfile(os.path.join(REPO, "tools", "release", "install-bridge.ps1"), os.path.join(tmp, "install-bridge.ps1"))
    zip_dir(tmp, os.path.join(out, f"ArchipelagoME1-bridge-{version}.zip"), f"ArchipelagoME1-bridge-{version}")
    shutil.rmtree(tmp)

    template_and_verify(out, version, AP)

    sums = [f"{hashlib.sha256(open(os.path.join(out, f), 'rb').read()).hexdigest()}  {f}" for f in sorted(os.listdir(out))]
    with open(os.path.join(out, "SHA256SUMS"), "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(sums) + "\n")
    print("\n".join(sums))
    print(f"release assets: {out}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    main(sys.argv[1])
