#!/usr/bin/env python3
"""Extract one gate result from the test VM's guest evidence stream.

kiwi/test/guest/live-gate.sh and installed-gate.sh stream each section of
evidence between `### BEGIN <tool> <section> ...` and
`### END <tool> <section> exit=N` markers through the QEMU virtio port into
vm/upgrade-guest-evidence.jsonl. For the sections whose body is a smoke-test
JSON report (live-session, live-session-offline, installer, first-boot,
uefi-secure-boot) this tool takes the last occurrence, requires exit 0 and a
passed report, optionally validates it against scripts/image-build.py for
the candidate ISO and writes it as the gate's `<name>-result.json`. Any
section can also be exported verbatim as a text transcript.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BEGIN = re.compile(r"^### BEGIN (?P<tool>[a-z-]+) (?P<section>[a-z-]+)(?: (?P<rest>.*))?$")
END = re.compile(r"^### END (?P<tool>[a-z-]+) (?P<section>[a-z-]+) exit=(?P<exit>-?\d+)$")
JSON_SECTIONS = {
    "live-session": "live-session",
    "live-session-offline": "live-session",
    "installer": "installer",
    "first-boot": "first-boot",
    "uefi-secure-boot": "uefi-secure-boot",
}


class EvidenceError(Exception):
    pass


def parse_blocks(text: str) -> list[dict]:
    blocks: list[dict] = []
    current: dict | None = None
    body: list[str] = []
    for line in text.splitlines():
        begin = BEGIN.match(line)
        end = END.match(line)
        if begin:
            current = {"tool": begin["tool"], "section": begin["section"], "header": line}
            body = []
        elif end and current is not None and end["section"] == current["section"]:
            current["exit"] = int(end["exit"])
            current["body"] = "\n".join(body)
            blocks.append(current)
            current = None
        elif current is not None:
            body.append(line)
    return blocks


def last_block(blocks: list[dict], section: str) -> dict:
    matches = [block for block in blocks if block["section"] == section]
    if not matches:
        raise EvidenceError(f"section {section} not found in the guest stream")
    return matches[-1]


def json_body(block: dict) -> dict:
    body = block["body"]
    # live-gate.sh prefixes the installer report with a listing; keep the JSON object only.
    start = body.find("{")
    if start < 0:
        raise EvidenceError(f"section {block['section']} carries no JSON report")
    depth = 0
    for index in range(start, len(body)):
        if body[index] == "{":
            depth += 1
        elif body[index] == "}":
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(body[start:index + 1])
                except json.JSONDecodeError as error:
                    raise EvidenceError(f"section {block['section']} report is not valid JSON: {error}") from error
    raise EvidenceError(f"section {block['section']} report is truncated")


def check_report(section: str, report: dict) -> None:
    role = JSON_SECTIONS[section]
    if report.get("schema") != 1:
        raise EvidenceError(f"{section}: report is not schema 1")
    if report.get("mode") != role:
        raise EvidenceError(f"{section}: report mode is {report.get('mode')!r}, expected {role!r}")
    if report.get("status") != "passed":
        raise EvidenceError(f"{section}: report status is {report.get('status')!r}, not passed")
    checks = report.get("checks")
    if not isinstance(checks, list) or not checks:
        raise EvidenceError(f"{section}: report has no checks")
    failed = [check.get("id") for check in checks if check.get("status") != "passed"]
    if failed:
        raise EvidenceError(f"{section}: checks failed: {failed}")


def validate_with_release_policy(section: str, report: dict, iso_dir: Path) -> None:
    isos = sorted(iso_dir.glob("*.iso"))
    if len(isos) != 1:
        raise EvidenceError(f"expected exactly one ISO in {iso_dir}")
    spec = importlib.util.spec_from_file_location("lyra_image_build", ROOT / "scripts/image-build.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    try:
        module.validate_test_result(JSON_SECTIONS[section], report, iso_path=isos[0])
    except module.PolicyError as error:
        raise EvidenceError(f"release policy rejected {section}: {error}") from error


def extract(stream: Path, section: str) -> tuple[dict, dict | None]:
    block = last_block(parse_blocks(stream.read_text(encoding="utf-8", errors="replace")), section)
    if section not in JSON_SECTIONS:
        return block, None
    if block["exit"] != 0:
        raise EvidenceError(f"{section}: guest command exited with {block['exit']}")
    report = json_body(block)
    check_report(section, report)
    return block, report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--guest-evidence", required=True, type=Path, help="vm/upgrade-guest-evidence.jsonl written by QEMU")
    parser.add_argument("--section", required=True, help="section name streamed by the guest script")
    parser.add_argument("--output", type=Path, help="JSON result file (sections: %s)" % ", ".join(sorted(JSON_SECTIONS)))
    parser.add_argument("--transcript", type=Path, help="verbatim text of the section, including its markers")
    parser.add_argument("--iso-dir", type=Path, help="also validate the result with scripts/image-build.py against this candidate")
    args = parser.parse_args()
    if args.output is None and args.transcript is None:
        parser.error("give --output and/or --transcript")
    if args.output is not None and args.section not in JSON_SECTIONS:
        parser.error(f"--output needs a JSON section: {', '.join(sorted(JSON_SECTIONS))}")
    try:
        block, report = extract(args.guest_evidence, args.section)
        if args.output is not None and args.iso_dir is not None:
            validate_with_release_policy(args.section, report, args.iso_dir.resolve())
    except EvidenceError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    if args.transcript is not None:
        args.transcript.write_text(f"{block['header']}\n{block['body']}\n### END {block['tool']} {block['section']} exit={block['exit']}\n", encoding="utf-8")
    if args.output is not None:
        args.output.write_text(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"{args.section}: passed ({len(report['checks'])} checks) -> {args.output}")
    else:
        print(f"{args.section}: exit {block['exit']} -> {args.transcript}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
