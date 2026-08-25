#!/usr/bin/env python3
"""Audit a Lyra ISO for build-host data embedded in its live SquashFS."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path


class AuditError(RuntimeError):
    pass


SENSITIVE_NAMES = re.compile(
    r"(^|/)(\.ssh|\.gnupg|\.aws|\.kube|\.docker|\.config/gh|"
    r"id_(rsa|dsa|ecdsa|ed25519)(\.pub)?|authorized_keys|known_hosts|"
    r"credentials|\.git-credentials|\.netrc|\.npmrc|\.pypirc|"
    r".*history|hosts\.yml)$",
    re.IGNORECASE,
)
SECRET_CONTENT = re.compile(
    rb"(-----BEGIN (?:OPENSSH |RSA |EC |DSA )?PRIVATE KEY-----|"
    rb"gh[opusr]_[A-Za-z0-9_]{20,}|github_pat_[A-Za-z0-9_]{20,}|"
    rb"AKIA[0-9A-Z]{16}|(?i:(?:password|passwd|token|secret|api[_-]?key))\s*[:=]\s*[^\s]{8,})"
)
HOST_PATH = re.compile(rb"/(?:home|Users)/[A-Za-z0-9._-]+/(?:Git|Projects|src|workspace)/")
TEXT_SCAN_LIMIT = 8 * 1024 * 1024


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def require_commands() -> None:
    missing = [name for name in ("xorriso", "unsquashfs") if shutil.which(name) is None]
    if missing:
        raise AuditError(f"missing required commands: {', '.join(missing)}")


def extract_rootfs(iso: Path, destination: Path) -> Path:
    require_commands()
    squashfs = destination / "squashfs.img"
    rootfs = destination / "rootfs"
    subprocess.run(
        ["xorriso", "-osirrox", "on", "-indev", str(iso), "-extract", "/LiveOS/squashfs.img", str(squashfs)],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )
    subprocess.run(
        ["unsquashfs", "-processors", "1", "-no-xattrs", "-no-exit-code", "-f", "-d", str(rootfs), str(squashfs)],
        check=True,
        stdout=subprocess.DEVNULL,
    )
    return rootfs


def relative(path: Path, rootfs: Path) -> str:
    return "/" + path.relative_to(rootfs).as_posix()


def scan_rootfs(rootfs: Path) -> dict[str, object]:
    if not rootfs.is_dir():
        raise AuditError(f"rootfs does not exist: {rootfs}")

    findings: list[dict[str, str]] = []
    inventory: dict[str, list[str]] = {"homes": [], "root": [], "caches": [], "logs": []}
    home = rootfs / "home"
    if home.is_dir():
        inventory["homes"] = sorted(relative(path, rootfs) for path in home.iterdir())
        for path in home.iterdir():
            if path.name != "liveuser":
                findings.append({"severity": "critical", "kind": "unexpected-home", "path": relative(path, rootfs)})

    root_home = rootfs / "root"
    if root_home.is_dir():
        inventory["root"] = sorted(relative(path, rootfs) for path in root_home.iterdir())

    for base in (rootfs / "home", root_home):
        if base.is_dir():
            for cache in base.glob("**/.cache"):
                inventory["caches"].append(relative(cache, rootfs))
    system_cache = rootfs / "var/cache"
    if system_cache.is_dir():
        inventory["caches"].extend(relative(path, rootfs) for path in system_cache.iterdir())
    log_dir = rootfs / "var/log"
    if log_dir.is_dir():
        inventory["logs"] = sorted(relative(path, rootfs) for path in log_dir.iterdir())

    for path in rootfs.rglob("*"):
        try:
            rel = relative(path, rootfs)
            if path.is_symlink():
                target = os.readlink(path)
                if HOST_PATH.search(target.encode(errors="replace")):
                    findings.append({"severity": "critical", "kind": "host-path-symlink", "path": rel})
                continue
            if not path.is_file():
                continue
            is_host_owned = rel.startswith(("/home/", "/root/", "/tmp/", "/var/tmp/"))
            is_mutable_evidence = is_host_owned or rel.startswith(("/var/log/", "/var/cache/"))
            if is_host_owned and SENSITIVE_NAMES.search(rel.lstrip("/")):
                findings.append({"severity": "critical", "kind": "sensitive-path", "path": rel})
            size = path.stat().st_size
            if size > TEXT_SCAN_LIMIT:
                continue
            data = path.read_bytes()
            if HOST_PATH.search(data):
                findings.append({"severity": "critical", "kind": "host-path-content", "path": rel})
            # System packages legitimately ship test certificates, key-shaped
            # fixtures and credential examples under /usr and /etc. Treat
            # secret-shaped content as a leak only in mutable host-owned trees;
            # absolute build-host paths remain forbidden everywhere.
            if is_mutable_evidence and SECRET_CONTENT.search(data):
                findings.append({"severity": "critical", "kind": "secret-content", "path": rel})
        except (OSError, PermissionError):
            findings.append({"severity": "error", "kind": "unreadable", "path": relative(path, rootfs)})

    findings.sort(key=lambda item: (item["path"], item["kind"]))
    for values in inventory.values():
        values.sort()
    return {"result": "fail" if findings else "pass", "findings": findings, "inventory": inventory}


def audit(iso: Path, *, rootfs: Path | None = None) -> dict[str, object]:
    if not iso.is_file():
        raise AuditError(f"ISO does not exist: {iso}")
    if rootfs is not None:
        scan = scan_rootfs(rootfs)
    else:
        with tempfile.TemporaryDirectory(prefix="lyra-iso-audit-") as temporary:
            scan = scan_rootfs(extract_rootfs(iso, Path(temporary)))
    return {
        "schema_version": 1,
        "audited_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "iso": {"name": iso.name, "size": iso.stat().st_size, "sha256": sha256(iso)},
        **scan,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("iso", type=Path)
    parser.add_argument("--rootfs", type=Path, help="audit an already extracted rootfs (tests/debugging)")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        report = audit(args.iso, rootfs=args.rootfs)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"{report['result']}: {args.iso} -> {args.output}")
        return 0 if report["result"] == "pass" else 1
    except (AuditError, subprocess.CalledProcessError) as error:
        print(f"audit failed: {error}", file=os.sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
