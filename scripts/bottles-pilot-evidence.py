#!/usr/bin/env python3
"""Collect read-only evidence for the optional Bottles pilot in Alpha 7."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import pathlib
import subprocess
import sys
from typing import Sequence


APP_ID = "com.usebottles.bottles"
PHASE_EXPECTATION = {"before": False, "installed": True, "removed": False}


def run(command: Sequence[str]) -> dict[str, object]:
    env = os.environ.copy()
    env.update({"LC_ALL": "C.UTF-8", "LANG": "C.UTF-8"})
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            check=False,
            env=env,
            text=True,
            timeout=20,
        )
    except FileNotFoundError:
        return {"command": list(command), "returncode": 127, "stdout": "", "stderr": "command not found"}
    except subprocess.TimeoutExpired as error:
        return {
            "command": list(command),
            "returncode": 124,
            "stdout": error.stdout or "",
            "stderr": "command timed out",
        }
    return {
        "command": list(command),
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


def collect(phase: str) -> dict[str, object]:
    app_info = run(["flatpak", "info", APP_ID])
    installed = app_info["returncode"] == 0
    expected = PHASE_EXPECTATION[phase]
    checks = {
        "flatpak_available": run(["flatpak", "--version"])["returncode"] == 0,
        "installation_state_matches_phase": installed is expected,
    }
    return {
        "schema_version": 1,
        "kind": "bottles-pilot-snapshot",
        "phase": phase,
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "app_id": APP_ID,
        "installed": installed,
        "status": "observed" if all(checks.values()) else "failed",
        "checks": checks,
        "observations": {
            "flatpak_info": app_info,
            "flatpak_permissions": run(["flatpak", "info", "--show-permissions", APP_ID]),
            "flatpak_overrides": run(["flatpak", "override", "--show", APP_ID]),
            "flatpak_apps": run(
                ["flatpak", "list", "--app", "--columns=application,version,branch,origin"]
            ),
            "user_services": run(
                ["systemctl", "--user", "--no-pager", "--plain", "--type=service", "--state=running"]
            ),
            "listening_sockets": run(["ss", "-lntupH"]),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=tuple(PHASE_EXPECTATION))
    parser.add_argument("--output", required=True, type=pathlib.Path)
    args = parser.parse_args()

    document = collect(args.phase)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(args.output)
    return 0 if document["status"] == "observed" else 1


if __name__ == "__main__":
    sys.exit(main())

