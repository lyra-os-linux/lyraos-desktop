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
RISK_MARKERS = (
    "devices=all",
    "shared=network;ipc;",
    "sockets=x11;wayland;pulseaudio;",
    "features=devel;multiarch;",
    "org.freedesktop.UDisks2",
)


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


def load_snapshot(path: pathlib.Path, expected_phase: str) -> dict[str, object]:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"cannot read snapshot {path}: {error}") from error
    if document.get("schema_version") != 1 or document.get("kind") != "bottles-pilot-snapshot":
        raise ValueError(f"invalid Bottles snapshot: {path}")
    if document.get("phase") != expected_phase:
        raise ValueError(f"expected phase {expected_phase} in {path}")
    return document


def output_lines(document: dict[str, object], observation: str) -> set[str]:
    observations = document.get("observations", {})
    record = observations.get(observation, {}) if isinstance(observations, dict) else {}
    stdout = record.get("stdout", "") if isinstance(record, dict) else ""
    return {line.strip() for line in str(stdout).splitlines() if line.strip()}


def review(before: dict[str, object], installed: dict[str, object], removed: dict[str, object]) -> dict[str, object]:
    installed_permissions = "\n".join(sorted(output_lines(installed, "flatpak_permissions")))
    residual_services = sorted(
        output_lines(removed, "user_services") - output_lines(before, "user_services")
    )
    residual_sockets = sorted(
        output_lines(removed, "listening_sockets") - output_lines(before, "listening_sockets")
    )
    residual_overrides = sorted(output_lines(removed, "flatpak_overrides"))
    checks = {
        "snapshots_observed": all(item.get("status") == "observed" for item in (before, installed, removed)),
        "installed_only_in_installed_phase": (
            before.get("installed") is False
            and installed.get("installed") is True
            and removed.get("installed") is False
        ),
        "no_residual_overrides": not residual_overrides,
        "no_new_user_services_after_removal": not residual_services,
        "no_new_listening_sockets_after_removal": not residual_sockets,
    }
    automatic_blockers = sorted(name for name, passed in checks.items() if not passed)
    return {
        "schema_version": 1,
        "kind": "bottles-pilot-review",
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "app_id": APP_ID,
        "status": "failed" if automatic_blockers else "review-required",
        "checks": checks,
        "automatic_blockers": automatic_blockers,
        "risk_markers": [marker for marker in RISK_MARKERS if marker in installed_permissions],
        "residuals": {
            "overrides": residual_overrides,
            "user_services": residual_services,
            "listening_sockets": residual_sockets,
        },
        "manual_review_required": [
            "filesystem isolation and negative access test",
            "device and UDisks2 exposure",
            "network behavior while a Windows application is running",
            "audio, clipboard, Wayland/XWayland and file portal behavior",
            "user-data retention or deletion matched the explicit choice",
        ],
    }
def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="action", required=True)
    for phase in PHASE_EXPECTATION:
        collector = subparsers.add_parser(phase, help=f"collect the {phase} snapshot")
        collector.add_argument("--output", required=True, type=pathlib.Path)
    reviewer = subparsers.add_parser("review", help="compare before, installed and removed snapshots")
    reviewer.add_argument("--before", required=True, type=pathlib.Path)
    reviewer.add_argument("--installed", required=True, type=pathlib.Path)
    reviewer.add_argument("--removed", required=True, type=pathlib.Path)
    reviewer.add_argument("--output", required=True, type=pathlib.Path)
    args = parser.parse_args()

    try:
        if args.action == "review":
            document = review(
                load_snapshot(args.before, "before"),
                load_snapshot(args.installed, "installed"),
                load_snapshot(args.removed, "removed"),
            )
        else:
            document = collect(args.action)
    except ValueError as error:
        parser.error(str(error))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(args.output)
    return 1 if document["status"] == "failed" else 0


if __name__ == "__main__":
    sys.exit(main())
