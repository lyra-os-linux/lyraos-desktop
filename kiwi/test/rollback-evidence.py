#!/usr/bin/env python3
"""Assemble the rollback gate evidence from the test VM's guest stream.

kiwi/test/guest/rollback-gate.sh runs each lyra-update-smoke phase inside the
installed VM and streams the JSON report through the QEMU virtio port into
vm/upgrade-guest-evidence.jsonl. This tool reads that stream, requires every
phase of the exercise (baseline, update, verify-updated, prepare-rollback,
verify-rollback) in order, takes the final verify-rollback report, checks it
the way scripts/image-build.py does for the `rollback` role and writes it as
rollback-result.json together with a transcript of the phases.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PHASES = ("baseline", "update", "verify-updated", "prepare-rollback", "verify-rollback")
BEGIN = "### BEGIN rollback-gate "
END = "### END rollback-gate "


class EvidenceError(Exception):
    pass


def parse_blocks(text: str) -> list[dict]:
    blocks: list[dict] = []
    current: dict | None = None
    body: list[str] = []
    for line in text.splitlines():
        if line.startswith(BEGIN):
            fields = line[len(BEGIN):].split()
            current = {"phase": fields[0], "stamp": fields[1] if len(fields) > 1 else None, "header": line}
            body = []
        elif line.startswith(END) and current is not None:
            fields = line[len(END):].split()
            exit_code = next((item.split("=", 1)[1] for item in fields if item.startswith("exit=")), None)
            try:
                report = json.loads("\n".join(body))
            except json.JSONDecodeError as error:
                raise EvidenceError(f"phase {current['phase']} report is not valid JSON: {error}") from error
            current["exit"] = int(exit_code) if exit_code is not None and exit_code.isdigit() else None
            current["report"] = report
            blocks.append(current)
            current = None
        elif current is not None:
            body.append(line)
    return blocks


def final_run(blocks: list[dict]) -> list[dict]:
    """Return the last complete exercise: one block per phase, in order."""
    starts = [index for index, block in enumerate(blocks) if block["phase"] == "baseline"]
    if not starts:
        raise EvidenceError("no baseline phase found in the guest stream")
    run = blocks[starts[-1]:]
    selected: list[dict] = []
    for phase in PHASES:
        matches = [block for block in run if block["phase"] == phase]
        if not matches:
            raise EvidenceError(f"phase {phase} is missing from the last exercise")
        selected.append(matches[-1])
    order = [run.index(block) for block in selected]
    if order != sorted(order):
        raise EvidenceError("phases of the last exercise are out of order")
    return selected


def check_rollback_result(report: dict) -> None:
    if report.get("schema") != 1 or report.get("mode") != "rollback":
        raise EvidenceError("verify-rollback report is not a schema-1 rollback result")
    if report.get("status") != "passed":
        raise EvidenceError(f"verify-rollback status is {report.get('status')!r}, not passed")
    if report.get("phase") != "rollback-verified":
        raise EvidenceError(f"verify-rollback phase is {report.get('phase')!r}, not rollback-verified")
    checks = report.get("checks")
    if not isinstance(checks, list) or not checks:
        raise EvidenceError("verify-rollback report has no checks")
    failed = [check.get("id") for check in checks if check.get("status") != "passed"]
    if failed:
        raise EvidenceError(f"verify-rollback checks failed: {failed}")


def validate_with_release_policy(report: dict, iso_dir: Path) -> None:
    isos = sorted(iso_dir.glob("*.iso"))
    if len(isos) != 1:
        raise EvidenceError(f"expected exactly one ISO in {iso_dir}")
    spec = importlib.util.spec_from_file_location("lyra_image_build", ROOT / "scripts/image-build.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    try:
        module.validate_test_result("rollback", report, iso_path=isos[0])
    except module.PolicyError as error:
        raise EvidenceError(f"release policy rejected the rollback result: {error}") from error


def assemble(stream: Path) -> tuple[dict, list[dict]]:
    blocks = parse_blocks(stream.read_text(encoding="utf-8", errors="replace"))
    run = final_run(blocks)
    for block in run[:-1]:
        if block["exit"] != 0 or block["report"].get("status") == "failed":
            raise EvidenceError(f"phase {block['phase']} failed (exit {block['exit']}, status {block['report'].get('status')!r})")
    final = run[-1]
    if final["exit"] != 0:
        raise EvidenceError(f"verify-rollback exited with {final['exit']}")
    check_rollback_result(final["report"])
    return final["report"], run


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--guest-evidence", required=True, type=Path, help="vm/upgrade-guest-evidence.jsonl written by QEMU")
    parser.add_argument("--output", required=True, type=Path, help="rollback-result.json for artifact-manifest")
    parser.add_argument("--transcript", type=Path, help="optional JSON transcript of every phase of the final exercise")
    parser.add_argument("--iso-dir", type=Path, help="also validate the result with scripts/image-build.py against this candidate")
    args = parser.parse_args()
    try:
        report, run = assemble(args.guest_evidence)
        if args.iso_dir is not None:
            validate_with_release_policy(report, args.iso_dir.resolve())
    except EvidenceError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    if args.transcript is not None:
        transcript = [
            {"phase": block["phase"], "recorded_at": block["stamp"], "exit": block["exit"], "header": block["header"], "report": block["report"]}
            for block in run
        ]
        args.transcript.write_text(json.dumps(transcript, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"rollback-result: passed ({len(run)} phases, final {report.get('phase')}) -> {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
