"""Build LE1APExtras.asi with Visual Studio 2022 Build Tools (Windows, or WSL with powershell.exe).

usage: python tools/le1apextras/build.py [--config Release|Debug]
The sources (this folder and vendor/LExASIs with its submodules) are mirrored into a Windows temp folder, because
MSBuild does not build reliably from a WSL path. The result is copied to tools/le1apextras/LE1APExtras.asi.
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
LEXASIS = os.path.join(REPO, "vendor", "LExASIs")
OUTPUT = os.path.join(HERE, "LE1APExtras.asi")
VS_CMAKE = r"C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\Common7\IDE\CommonExtensions\Microsoft\CMake\CMake\bin\cmake.exe"
SKIP = shutil.ignore_patterns(".git", "Build", "build", "__pycache__", "*.asi", "*.pdb")


def windows_temp() -> str:
    if os.name == "nt":
        return os.environ["TEMP"]
    win = subprocess.check_output(["powershell.exe", "-NoProfile", "-Command", "$env:TEMP"], text=True).strip()
    return subprocess.check_output(["wslpath", "-u", win], text=True).strip()


def to_windows(path: str) -> str:
    return path if os.name == "nt" else subprocess.check_output(["wslpath", "-w", path], text=True).strip()


def run_cmake(args: list[str]) -> None:
    if os.name == "nt":
        subprocess.run([VS_CMAKE, *args], check=True)
        return
    quoted = " ".join("'" + arg.replace("'", "''") + "'" for arg in args)
    subprocess.run(["powershell.exe", "-NoProfile", "-Command", f"& '{VS_CMAKE}' {quoted}; exit $LASTEXITCODE"], check=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="Release", choices=("Release", "Debug"))
    config = parser.parse_args().config
    if not os.path.exists(os.path.join(LEXASIS, "External", "LExSDKv2", "Src")):
        raise SystemExit("vendor/LExASIs is missing its submodules: git submodule update --init --recursive vendor/LExASIs")

    work = os.path.join(windows_temp(), "le1apextras-build")
    src = os.path.join(work, "src")
    shutil.rmtree(src, ignore_errors=True)
    shutil.copytree(HERE, os.path.join(src, "tools", "le1apextras"), ignore=SKIP)
    shutil.copytree(LEXASIS, os.path.join(src, "vendor", "LExASIs"), ignore=SKIP)

    source_dir = to_windows(os.path.join(src, "tools", "le1apextras"))
    build_dir = to_windows(os.path.join(work, "build"))
    run_cmake(["-S", source_dir, "-B", build_dir, "-G", "Visual Studio 17 2022", "-A", "x64"])
    run_cmake(["--build", build_dir, "--config", config, "--target", "APExtras-LE1"])

    built = os.path.join(work, "build", "out", config, "LE1APExtras.asi")
    shutil.copyfile(built, OUTPUT)
    print(f"built {OUTPUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
