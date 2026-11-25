#!/usr/bin/env python3
"""Receive a checksum-addressed static release over the forced SSH command."""

import fcntl
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile

ROOT = Path("/opt/podborkns/public/.releases")
MAX_UPLOAD = 64 * 1024 * 1024
MAX_EXTRACTED = 192 * 1024 * 1024
MAX_ENTRIES = 10_000
MAIN_HOST = "podborkns.ru"


def receive(destination: Path, expected: str) -> None:
    digest = hashlib.sha256()
    size = 0
    with destination.open("wb") as artifact:
        while chunk := sys.stdin.buffer.read(1024 * 1024):
            size += len(chunk)
            if size > MAX_UPLOAD:
                raise ValueError("artifact exceeds compressed size limit")
            artifact.write(chunk)
            digest.update(chunk)
    if digest.hexdigest() != expected:
        raise ValueError("artifact checksum mismatch")


def unpack(source: Path, target: Path) -> None:
    size = 0
    with tarfile.open(source, mode="r|gz") as archive:
        for index, entry in enumerate(archive, start=1):
            path = PurePosixPath(entry.name)
            if index > MAX_ENTRIES or path.is_absolute() or ".." in path.parts:
                raise ValueError("archive contains an invalid path or too many entries")
            if path.parts and path.parts[0] in {".releases", "__release.txt"}:
                raise ValueError("archive contains a reserved path")
            destination = target.joinpath(*path.parts)
            if entry.isdir():
                destination.mkdir(parents=True, exist_ok=True)
                continue
            if not entry.isfile() or not path.parts:
                raise ValueError("only regular files and directories are allowed")
            size += entry.size
            if size > MAX_EXTRACTED:
                raise ValueError("artifact exceeds extracted size limit")
            destination.parent.mkdir(parents=True, exist_ok=True)
            with archive.extractfile(entry) as raw, destination.open("xb") as output:
                shutil.copyfileobj(raw, output)
    for required in ("index.html", "project/index.html"):
        if not (target / required).is_file() or not (target / required).stat().st_size:
            raise ValueError(f"artifact is missing {required}")


def set_current(root: Path, target: str) -> None:
    with tempfile.TemporaryDirectory(dir=root, prefix=".pointer-") as staging:
        pointer = Path(staging) / "current"
        pointer.symlink_to(target)
        os.replace(pointer, root / "current")


def get(path: str) -> str:
    return subprocess.run(
        ["curl", "--noproxy", "*", "--fail", "--silent", "--show-error",
         "--max-time", "8", "--resolve", f"{MAIN_HOST}:443:127.0.0.1",
         f"https://{MAIN_HOST}{path}"],
        check=True, capture_output=True, text=True,
    ).stdout


def smoke(release: str) -> None:
    if get("/__release.txt").strip() != release or not get("/") or not get("/project/"):
        raise RuntimeError("static release smoke check failed")
    api = json.loads(get("/api/backend/health"))
    if api.get("status") != "ok" or api.get("pumps_in_db", 0) < 1:
        raise RuntimeError("calculator API health check failed")


def publish(root: Path, release: str, digest: str) -> None:
    os.umask(0o022)
    with (root / ".deploy.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        previous = os.readlink(root / "current")
        if not re.fullmatch(r"(?:initial|[a-f0-9]{40}-[a-f0-9]{64})", previous):
            raise ValueError("current release pointer is invalid")
        if not (root / previous / "index.html").is_file():
            raise ValueError("previous release is incomplete")

        name = f"{release}-{digest}"
        destination = root / name
        with tempfile.TemporaryDirectory(dir=root, prefix=".incoming-") as staging:
            incoming = Path(staging)
            receive(incoming / "upload.tar.gz", digest)
            if not destination.exists():
                site = incoming / "site"
                site.mkdir()
                unpack(incoming / "upload.tar.gz", site)
                (site / "__release.txt").write_text(release + "\n", encoding="ascii")
                site.rename(destination)

        set_current(root, name)
        try:
            smoke(release)
        except Exception:
            set_current(root, previous)
            print("Smoke check failed; previous release restored.", file=sys.stderr)
            raise
        print(f"Published and verified {release}")


def main() -> None:
    command = os.environ.get("SSH_ORIGINAL_COMMAND", "")
    match = re.fullmatch(r"publish ([a-f0-9]{40}) ([a-f0-9]{64})", command)
    if match is None:
        sys.exit("Only a signed-in release upload is accepted")
    try:
        publish(ROOT, *match.groups())
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError, tarfile.TarError) as error:
        sys.exit(f"Deploy failed: {error}")


if __name__ == "__main__":
    main()
