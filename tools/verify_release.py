"""Verify a published wheel in a disposable Python environment; never publish."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from urllib.request import Request, urlopen
from zipfile import ZipFile
from email.parser import Parser

REPO = "metabolism-tools/workspace-metabolism"


def fetch(url):
    with urlopen(Request(url, headers={"User-Agent": "wm-release-verifier"}), timeout=60) as response:
        return response.read()


def distribution(version, source):
    name = f"workspace_metabolism-{version}-py3-none-any.whl"
    if source == "pypi":
        payload = json.loads(fetch(f"https://pypi.org/pypi/workspace-metabolism/{version}/json"))
        if payload["info"]["version"] != version:
            raise ValueError("PyPI version mismatch")
        matches = [item for item in payload["urls"] if item["filename"] == name and not item.get("yanked")]
        if len(matches) != 1:
            raise ValueError("expected one unyanked universal wheel")
        return name, matches[0]["url"], matches[0]["digests"]["sha256"]
    payload = json.loads(fetch(f"https://api.github.com/repos/{REPO}/releases/tags/v{version}"))
    if payload["tag_name"] != f"v{version}" or payload.get("draft"):
        raise ValueError("GitHub release/tag mismatch")
    assets = {item["name"]: item["browser_download_url"] for item in payload["assets"]}
    sums = fetch(assets["SHA256SUMS"]).decode("utf-8")
    matches = [parts[0] for line in sums.splitlines()
               if len(parts := line.split()) == 2 and parts[1].lstrip("*") == name]
    if len(matches) != 1:
        raise ValueError("expected exactly one wheel digest in SHA256SUMS")
    return name, assets[name], matches[0]


def verify_wheel(wheel, expected, version):
    if not re.fullmatch(r"[0-9a-f]{64}", expected) or hashlib.sha256(wheel.read_bytes()).hexdigest() != expected:
        raise ValueError("published wheel digest mismatch")
    with ZipFile(wheel) as archive:
        metadata = [name for name in archive.namelist() if name.endswith(".dist-info/METADATA")]
        if len(metadata) != 1:
            raise ValueError("ambiguous wheel metadata")
        info = Parser().parsestr(archive.read(metadata[0]).decode("utf-8"))
    if info["Name"] != "workspace-metabolism" or info["Version"] != version:
        raise ValueError("wheel name/version mismatch")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", required=True)
    parser.add_argument("--source", choices=["github", "pypi"], default="github")
    parser.add_argument("--wheel", type=Path, help="verify a locally built wheel instead of a published channel")
    args = parser.parse_args(argv)
    if not re.fullmatch(r"\d+\.\d+\.\d+(?:(?:a|b|rc)\d+|\.dev\d+)?", args.version):
        parser.error("use a complete package version without the v prefix")
    if args.wheel:
        wheel_bytes = args.wheel.read_bytes()
        name = args.wheel.name
        digest = hashlib.sha256(wheel_bytes).hexdigest()
    else:
        name, url, digest = distribution(args.version, args.source)
        wheel_bytes = fetch(url)
    with tempfile.TemporaryDirectory(prefix="wm-release-") as temporary:
        directory = Path(temporary)
        wheel = directory / name
        wheel.write_bytes(wheel_bytes)
        verify_wheel(wheel, digest, args.version)
        subprocess.run([sys.executable, "-m", "pip", "install", "--no-deps", "--force-reinstall", str(wheel)], check=True)
        command = [sys.executable, "-I", "-m", "workspace_metabolism"]
        output = subprocess.check_output(command + ["--version"], cwd=directory, text=True).strip()
        if output.split()[-1] != args.version:
            raise ValueError("running CLI version does not match downloaded wheel")
        workspace = directory / "workspace"
        workspace.mkdir()
        common = command + ["--root", str(workspace), "--state-dir", str(directory / "state")]
        subprocess.run(common + ["init"], cwd=directory, check=True)
        report = json.loads(subprocess.check_output(common + ["doctor", "--json"], cwd=directory, text=True))
        if not report["registry_valid"]:
            raise ValueError("installed doctor did not accept its own policy")
        subprocess.run(command + ["retain", "--help"], cwd=directory, check=True, stdout=subprocess.DEVNULL)
    print(json.dumps({"verified_version": args.version, "source": "local_build" if args.wheel else args.source, "wheel_sha256": digest}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
