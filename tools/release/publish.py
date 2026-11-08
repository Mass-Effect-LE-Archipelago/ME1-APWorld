"""Publish the release built by build_release.py and tools/setup/package.py on the fork's GitHub.

usage: python tools/release/publish.py [--dry-run]
The release version is the world's (worlds/mass_effect_le1/archipelago.json), the setup app's is APSetup.csproj's.
Steps, each skipped when already done:
  1. release/MassEffectAPSetup-<app>-ME1.zip from the package.py folder (when missing or older than the folder).
  2. build/release-<version>/: copy the setup zip in, write SHA256SUMS over every asset.
  3. Push the current branch to the fork, open a pull request from it to main (title: the version) and merge it.
  4. Tag the merge commit v<version> and push the tag.
  5. Create the pre-release v<version> (body: build/release-<version>/RELEASE_NOTES.md) and upload the assets.
Prints the links to the pull request and the release. --dry-run prints the steps it would take and changes nothing.
GitHub token: GITHUB_TOKEN, else the one git uses for github.com (git credential fill); --dry-run reads without one.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
import zipfile

REPO = pathlib.Path(__file__).resolve().parents[2]
REMOTE = "fork"
BASE = "main"
API = "https://api.github.com"
UPLOADS = "https://uploads.github.com"


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=REPO, capture_output=True, text=True, check=True).stdout.strip()


def versions() -> tuple[str, str]:
    """(world version, setup app version) from the working tree."""
    world = json.loads((REPO / "worlds" / "mass_effect_le1" / "archipelago.json").read_text(encoding="utf-8-sig"))
    app = re.search(r"<Version>([^<]+)</Version>", (REPO / "tools" / "setup" / "APSetup.csproj").read_text(encoding="utf-8"))
    if app is None:
        raise SystemExit("no <Version> in tools/setup/APSetup.csproj")
    return world["world_version"], app.group(1)


def slug() -> str:
    """owner/name of the fork remote."""
    url = git("remote", "get-url", REMOTE)
    match = re.search(r"github\.com[:/]([^/]+)/([^/]+?)(?:\.git)?/?$", url)
    if match is None:
        raise SystemExit(f"remote {REMOTE} ({url}) is not a GitHub repository")
    return f"{match.group(1)}/{match.group(2)}"


def token() -> str:
    if os.environ.get("GITHUB_TOKEN"):
        return os.environ["GITHUB_TOKEN"]
    out = subprocess.run(["git", "credential", "fill"], input="protocol=https\nhost=github.com\n\n", cwd=REPO,
                         capture_output=True, text=True, check=True).stdout
    for line in out.splitlines():
        if line.startswith("password="):
            return line.split("=", 1)[1]
    raise SystemExit("no GitHub token: set GITHUB_TOKEN or sign in to github.com with git")


class GitHub:
    def __init__(self, repo: str, auth: str | None) -> None:
        self.repo = repo
        self.auth = auth

    def call(self, method: str, url: str, body: dict | None = None, data: bytes | None = None,
             content_type: str = "application/json") -> dict | list | None:
        if body is not None:
            data = json.dumps(body).encode("utf-8")
        headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28",
                   "User-Agent": "ME1-APWorld-publish", "Content-Type": content_type}
        if self.auth is not None:
            headers["Authorization"] = f"Bearer {self.auth}"
        request = urllib.request.Request(url, data=data, method=method, headers=headers)
        try:
            with urllib.request.urlopen(request) as response:
                payload = response.read()
        except urllib.error.HTTPError as error:
            if error.code == 404 and method == "GET":
                return None
            raise SystemExit(f"{method} {url}: {error.code} {error.read().decode('utf-8', 'replace')}")
        return json.loads(payload) if payload else None

    def api(self, method: str, path: str, body: dict | None = None) -> dict | list | None:
        return self.call(method, f"{API}/repos/{self.repo}{path}", body)


def sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def newest_mtime(folder: pathlib.Path) -> float:
    return max(p.stat().st_mtime for p in folder.rglob("*") if p.is_file())


def setup_zip(app: str, dry: bool) -> pathlib.Path:
    """Step 1: release/MassEffectAPSetup-<app>-ME1.zip holding the package.py folder's files at its root."""
    folder = REPO / "release" / f"MassEffectAPSetup-{app}"
    archive = REPO / "release" / f"MassEffectAPSetup-{app}-ME1.zip"
    if not folder.is_dir():
        if archive.exists():
            return archive
        raise SystemExit(f"no {folder.relative_to(REPO)}: run python tools/setup/package.py {app}")
    if archive.exists() and archive.stat().st_mtime >= newest_mtime(folder):
        print(f"1. {archive.name}: up to date")
        return archive
    print(f"1. {archive.name}: zip {folder.relative_to(REPO)}")
    if not dry:
        tmp = archive.with_suffix(".zip.tmp")
        with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as z:
            for path in sorted(folder.rglob("*")):
                if path.is_file():
                    z.write(path, path.relative_to(folder).as_posix())
        tmp.replace(archive)
    return archive


def check_setup_payload(archive: pathlib.Path, out: pathlib.Path) -> None:
    """The setup zip's ME1 apworld is the one in build/release-<version>/."""
    with zipfile.ZipFile(archive) as z:
        packed = z.read("ME1/mass_effect_le1.apworld")
    if hashlib.sha256(packed).hexdigest() != sha256(out / "mass_effect_le1.apworld"):
        raise SystemExit(f"{archive.name} holds a different apworld than {out.relative_to(REPO)}: run package.py again")


def release_folder(version: str, archive: pathlib.Path, dry: bool) -> list[pathlib.Path]:
    """Step 2: the setup zip and SHA256SUMS in build/release-<version>/; returns every asset to upload."""
    out = REPO / "build" / f"release-{version}"
    names = ["mass_effect_le1.apworld", "Mass Effect Legendary Edition 1.yaml", f"ArchipelagoME1-mod-{version}.zip",
             f"ArchipelagoME1-bridge-{version}.zip", "options-me1.json"]
    missing = [name for name in names if not (out / name).is_file()]
    if missing:
        raise SystemExit(f"missing from {out.relative_to(REPO)}: {', '.join(missing)} (run build_release.py {version})")
    if not (out / "RELEASE_NOTES.md").is_file():
        raise SystemExit(f"write {out.relative_to(REPO)}/RELEASE_NOTES.md first")
    if not dry or archive.exists():
        check_setup_payload(archive, out)
    copy = out / archive.name
    if copy.exists() and sha256(copy) == sha256(archive):
        print(f"2. {copy.name} in {out.relative_to(REPO)}: up to date")
    else:
        print(f"2. copy {archive.name} into {out.relative_to(REPO)}")
        if not dry:
            shutil.copyfile(archive, copy)
    assets = sorted([out / name for name in names] + [copy], key=lambda p: p.name)
    print("2. write SHA256SUMS")
    if not dry:
        sums = "".join(f"{sha256(p)}  {p.name}\n" for p in assets)
        (out / "SHA256SUMS").write_text(sums, encoding="ascii", newline="\n")
    return assets + [out / "SHA256SUMS"]


def merge(github: GitHub, version: str, dry: bool) -> tuple[str, str | None]:
    """Step 3: the current branch merged into the fork's main; returns (merge commit, pull request link)."""
    branch = git("rev-parse", "--abbrev-ref", "HEAD")
    if branch == BASE:
        raise SystemExit(f"run from the release branch, not {BASE}")
    head = git("rev-parse", "HEAD")
    print(f"3. push {branch} to {REMOTE}")
    if not dry:
        git("push", REMOTE, branch)
    git("fetch", REMOTE, BASE)
    owner = github.repo.split("/")[0]
    pulls = github.api("GET", f"/pulls?state=all&head={owner}:{branch}&base={BASE}&per_page=20") or []
    merged = next((p for p in pulls if p["merged_at"] and p["head"]["sha"] == head), None)
    if merged is not None:
        print(f"3. pull request #{merged['number']} already merged")
        return merged["merge_commit_sha"], merged["html_url"]
    if subprocess.run(["git", "merge-base", "--is-ancestor", head, f"{REMOTE}/{BASE}"], cwd=REPO).returncode == 0:
        print(f"3. {branch} is already in {REMOTE}/{BASE}")
        return git("rev-parse", f"{REMOTE}/{BASE}"), None
    pull = next((p for p in pulls if p["state"] == "open"), None)
    if pull is None:
        print(f"3. open a pull request {branch} -> {BASE} titled {version}")
        if dry:
            return "<merge commit>", None
        pull = github.api("POST", "/pulls", {"title": version, "head": branch, "base": BASE,
                                             "body": f"Release {version}."})
    print(f"3. merge pull request #{pull['number']}")
    if dry:
        return "<merge commit>", pull["html_url"]
    result = github.api("PUT", f"/pulls/{pull['number']}/merge", {"merge_method": "merge", "sha": head})
    git("fetch", REMOTE, BASE)
    return result["sha"], pull["html_url"]


def tag(version: str, commit: str, dry: bool) -> str:
    """Step 4: v<version> on the merge commit, pushed to the fork."""
    name = f"v{version}"
    remote = git("ls-remote", "--tags", REMOTE, f"refs/tags/{name}")
    if remote:
        print(f"4. {name} already on {REMOTE} ({remote.split()[0][:7]})")
        return name
    if git("tag", "--list", name):
        local = git("rev-parse", f"{name}^{{commit}}")
        if local != commit:
            raise SystemExit(f"local tag {name} is on {local[:7]}, not the merge commit {commit[:7]}: git tag -d {name}")
    print(f"4. tag {name} on {commit[:7]} and push it to {REMOTE}")
    if not dry:
        if not git("tag", "--list", name):
            git("tag", name, commit)
        git("push", REMOTE, name)
    return name


def publish(github: GitHub, version: str, name: str, assets: list[pathlib.Path], dry: bool) -> str:
    """Step 5: the pre-release with its notes and assets; returns its link."""
    notes = (REPO / "build" / f"release-{version}" / "RELEASE_NOTES.md").read_text(encoding="utf-8")
    release = github.api("GET", f"/releases/tags/{name}")
    if release is None:
        print(f"5. create pre-release {name}")
        if dry:
            for path in assets:
                print(f"5. upload {path.name}")
            return f"https://github.com/{github.repo}/releases/tag/{name}"
        release = github.api("POST", "/releases", {"tag_name": name, "name": name, "body": notes, "prerelease": True})
    else:
        print(f"5. release {name} exists")
    # GitHub stores a name with spaces with dots in their place.
    uploaded = {asset["name"] for asset in release["assets"]}
    for path in assets:
        stored = path.name.replace(" ", ".")
        if stored in uploaded:
            print(f"5. {stored}: already uploaded")
            continue
        print(f"5. upload {path.name} ({path.stat().st_size // (1 << 20)} MB)")
        if not dry:
            github.call("POST", f"{UPLOADS}/repos/{github.repo}/releases/{release['id']}/assets?"
                        + urllib.parse.urlencode({"name": stored}), data=path.read_bytes(),
                        content_type="application/octet-stream")
    return release["html_url"]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dry-run", action="store_true", help="print the steps, change nothing")
    args = parser.parse_args()
    if git("status", "--porcelain"):
        if not args.dry_run:
            raise SystemExit("commit or stash your changes first")
        print("(uncommitted changes: a real run stops here)")
    version, app = versions()
    print(f"release {version}, setup app {app}, to {slug()}")
    github = GitHub(slug(), None if args.dry_run else token())
    archive = setup_zip(app, args.dry_run)
    assets = release_folder(version, archive, args.dry_run)
    commit, pull = merge(github, version, args.dry_run)
    name = tag(version, commit, args.dry_run)
    link = publish(github, version, name, assets, args.dry_run)
    print()
    if pull:
        print(f"pull request: {pull}")
    print(f"release:      {link}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
