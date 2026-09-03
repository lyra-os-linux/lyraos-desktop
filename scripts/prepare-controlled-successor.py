#!/usr/bin/env python3
"""Prepare isolated RPM sources and a signed-manifest input for upgrade rehearsal."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "packaging/lyra-release"
TARGET_VERSION = "1.2-beta.1"
TARGET_RPM_VERSION = "1.2~beta.1"
TARGET_BUILD_ID = "lyra-release-1.2-beta.1"
REQUIRED_REPOSITORIES = {
    "repo-oss", "repo-non-oss", "repo-packman-essentials", "repo-lyra",
    "repo-vega", "repo-fina", "lyra-controlled-successor",
}


class PreparationError(ValueError):
    pass


def timestamp(value: str) -> dt.datetime:
    try:
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise PreparationError("validity timestamps must be RFC3339") from error
    if parsed.tzinfo is None:
        raise PreparationError("validity timestamps must include a timezone")
    return parsed


def prepare(args: argparse.Namespace) -> Path:
    repositories = json.loads(args.repositories.read_text(encoding="utf-8"))
    if not isinstance(repositories, list) or any(not isinstance(item, dict) for item in repositories):
        raise PreparationError("repositories input must be a JSON array of objects")
    aliases = {item.get("alias") for item in repositories}
    if aliases != REQUIRED_REPOSITORIES or len(repositories) != len(REQUIRED_REPOSITORIES):
        raise PreparationError("repositories input must contain the exact controlled target alias set")
    if args.sequence < 1:
        raise PreparationError("sequence must be positive")
    if timestamp(args.valid_from) >= timestamp(args.valid_until):
        raise PreparationError("valid_until must be later than valid_from")
    if args.output_dir.exists() or args.output_dir.is_symlink():
        raise PreparationError("output directory must not already exist")

    rpm_dir = args.output_dir / "rpm"
    rpm_dir.mkdir(parents=True, mode=0o755)
    spec = (BASE / "lyra-release.spec").read_text(encoding="utf-8")
    spec = spec.replace("Version:        1.1", f"Version:        {TARGET_RPM_VERSION}", 1)
    spec = spec.replace(
        'grep -Fx "LYRA_VERSION_ID=\'%{version}\'" %{SOURCE0}',
        f'grep -Fx "LYRA_VERSION_ID=\'{TARGET_VERSION}\'" %{{SOURCE0}}',
        1,
    )
    spec = spec.replace(
        'grep -Fx "LYRA_BUILD_ID=\'lyra-release-%{version}\'" %{SOURCE0}',
        f'grep -Fx "LYRA_BUILD_ID=\'{TARGET_BUILD_ID}\'" %{{SOURCE0}}',
        1,
    )
    if TARGET_RPM_VERSION not in spec or TARGET_BUILD_ID not in spec:
        raise PreparationError("canonical lyra-release spec no longer matches the rehearsal template")
    (rpm_dir / "lyra-release.spec").write_text(spec, encoding="utf-8")
    (rpm_dir / "lyra-product-release").write_text(
        f"LYRA_VERSION_ID='{TARGET_VERSION}'\n"
        "LYRA_EDITION='desktop'\n"
        "LYRA_ARCHITECTURE='x86_64'\n"
        f"LYRA_BUILD_ID='{TARGET_BUILD_ID}'\n",
        encoding="utf-8",
    )
    (rpm_dir / "lyra-release.changes").write_text(
        "-------------------------------------------------------------------\n"
        "Mon Aug 31 17:00:00 UTC 2026 - Lyra controlled rehearsal\n\n"
        "- Controlled successor identity for the 1.1 to 1.2-beta.1 rehearsal.\n",
        encoding="utf-8",
    )

    manifest = {
        "schema_version": 1,
        "sequence": args.sequence,
        "status": "testing",
        "valid_from": args.valid_from,
        "valid_until": args.valid_until,
        "source": {
            "version": "1.0", "edition": "desktop", "architecture": "x86_64",
            "build_id": "lyra-release-1.1",
        },
        "target": {
            "version": TARGET_VERSION, "edition": "desktop", "architecture": "x86_64",
            "build_id": TARGET_BUILD_ID,
        },
        "minimum_updater_version": "0.2.3",
        "minimum_free_space_bytes": 8589934592,
        "repositories": repositories,
        "allowed_removals": [],
        "allowed_vendor_transitions": [],
        "lockstep_packages": [],
    }
    manifest_input = args.output_dir / "release-manifest-input.json"
    manifest_input.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    command = [sys.executable, str(args.manifest_tool), str(manifest_input), "--output-dir", str(args.output_dir / "manifest")]
    if args.signing_key:
        command.extend(["--signing-key", args.signing_key])
    subprocess.run(command, check=True)
    return args.output_dir


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--manifest-tool", required=True, type=Path)
    parser.add_argument("--repositories", required=True, type=Path)
    parser.add_argument("--sequence", required=True, type=int)
    parser.add_argument("--valid-from", required=True)
    parser.add_argument("--valid-until", required=True)
    parser.add_argument("--signing-key")
    try:
        output = prepare(parser.parse_args())
    except (PreparationError, OSError, subprocess.CalledProcessError) as error:
        parser.error(str(error))
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
