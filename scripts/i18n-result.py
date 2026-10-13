#!/usr/bin/env python3
"""Generate `i18n-result.json` for a candidate ISO from the localization inventory.

The Alpha 8 `i18n` gate (docs/alpha8-evidence.md) needs one check per
Lyra-owned package that ships in the candidate, bound to the exact ISO. Until
now that file was assembled by hand. This script derives it deterministically:

- the candidate identity comes from `<iso>.manifest.json` next to the ISO;
- the shipped packages come from the KIWI `.packages` manifest;
- every inventory entry present in the ISO becomes a check whose scope is the
  inventory status (`complete` or `not-applicable`); a `scheduled` package
  that still ships fails the gate, because its localization is incomplete;
- catalog evidence recorded in `docs/evidence/i18n-catalogs-*.json` is linked
  when the package is listed there;
- `--package-review ID=FILE` binds a per-package candidate review (for
  example the lyra-vms binary review) to the check; the review must be
  `passed` and name the same package version the ISO ships;
- inventory entries absent from the ISO are listed under
  `excluded_not_in_candidate` and never produce a check.

The result is validated with `scripts/image-build.py` before it is written,
so a file that would be rejected at `artifact-manifest` time is never
produced. Evidence is bound to one ISO: regenerate it for every candidate.
"""

from __future__ import annotations

import argparse
import datetime as dt
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INVENTORY = ROOT / "i18n/inventory.json"
CATALOG_EVIDENCE_DIR = ROOT / "docs/evidence"
LOCALES = ["en-US", "pt-BR", "es-ES"]


class GenerationError(Exception):
    pass


def load_image_build():
    spec = importlib.util.spec_from_file_location("lyra_image_build", ROOT / "scripts/image-build.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def one(directory: Path, pattern: str) -> Path:
    matches = sorted(directory.glob(pattern))
    if len(matches) != 1:
        raise GenerationError(f"expected exactly one {pattern} in {directory}, found {len(matches)}")
    return matches[0]


def read_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise GenerationError(f"cannot read JSON {path}: {error}") from error


def shipped_packages(packages_file: Path) -> dict[str, str]:
    shipped: dict[str, str] = {}
    for line in packages_file.read_text(encoding="utf-8").splitlines():
        if not line:
            continue
        row = line.split("|")
        if len(row) != 7:
            raise GenerationError(f"unexpected KIWI package manifest row: {line}")
        name, _epoch, version, release = row[0], row[1], row[2], row[3]
        shipped[name] = f"{version}-{release}"
    if not shipped:
        raise GenerationError(f"package manifest is empty: {packages_file}")
    return shipped


def catalog_evidence_index(directory: Path) -> dict[str, str]:
    index: dict[str, str] = {}
    for path in sorted(directory.glob("i18n-catalogs-*.json")):
        for entry in read_json(path):
            package = entry.get("package")
            if package:
                index[package] = str(path.relative_to(ROOT))
    return index


def parse_reviews(items: list[str]) -> dict[str, Path]:
    reviews: dict[str, Path] = {}
    for item in items:
        if "=" not in item:
            raise GenerationError("--package-review must use ID=FILE")
        package, filename = item.split("=", 1)
        path = Path(filename).resolve()
        if not package or not path.is_file():
            raise GenerationError(f"invalid package review: {item}")
        if package in reviews:
            raise GenerationError(f"duplicate package review: {package}")
        reviews[package] = path
    return reviews


def review_check(package: str, entry: dict, shipped_version: str, review_path: Path) -> dict:
    review = read_json(review_path)
    problems = []
    if review.get("schema") != 1 or review.get("mode") != "i18n-package-review":
        problems.append("review schema/mode is not i18n-package-review")
    if review.get("package") != package:
        problems.append(f"review is for {review.get('package')!r}, not {package!r}")
    if review.get("version") != shipped_version:
        problems.append(f"review covers version {review.get('version')!r}, ISO ships {shipped_version!r}")
    if review.get("locales") != LOCALES or review.get("fallback") != "en-US":
        problems.append("review locale scope is not en-US, pt-BR, es-ES with en-US fallback")
    checks = review.get("checks")
    if (
        review.get("status") != "passed"
        or not isinstance(checks, list)
        or not checks
        or any(check.get("status") != "passed" for check in checks)
    ):
        problems.append("review did not pass")
    status = "failed" if problems else "passed"
    if problems:
        detail = "; ".join(problems)
    else:
        detail = (
            f"candidate package review {review_path.name} ({review.get('reviewed_at')}): "
            f"{len(checks)} checks passed on {package} {shipped_version}; "
            f"inventory status {entry.get('status')}: {entry.get('rationale')}"
        )
    return {
        "id": f"i18n-{package}",
        "status": status,
        "scope": "candidate-review",
        "version": shipped_version,
        "catalog_evidence": review_path.name,
        "detail": detail,
    }


def inventory_check(package: str, entry: dict, shipped_version: str, catalog_evidence: str | None) -> dict:
    status = entry.get("status")
    if status == "complete":
        detail = f"{entry.get('format')} / {package}: {entry.get('rationale')}"
        result = "passed"
    elif status == "not-applicable":
        detail = f"not-applicable: {entry.get('rationale')}"
        result = "passed"
    else:
        detail = f"inventory status {status!r} is not complete, but the package ships in the candidate"
        result = "failed"
    return {
        "id": f"i18n-{package}",
        "status": result,
        "scope": status,
        "version": shipped_version,
        "catalog_evidence": catalog_evidence,
        "detail": detail,
    }


def generate(iso_dir: Path, inventory_path: Path, reviews: dict[str, Path]) -> tuple[dict, Path]:
    iso_path = one(iso_dir, "*.iso")
    manifest = read_json(one(iso_dir, "*.iso.manifest.json"))
    shipped = shipped_packages(one(iso_dir, "*.packages"))
    inventory = read_json(inventory_path)
    if inventory.get("locales") != LOCALES or inventory.get("fallback_locale") != "en-US":
        raise GenerationError("inventory locale scope must be exactly en-US, pt-BR, es-ES with en-US fallback")
    iso_identity = manifest.get("iso") or {}
    source = manifest.get("source") or {}
    if iso_identity.get("filename") != iso_path.name or not iso_identity.get("sha256") or not source.get("commit"):
        raise GenerationError("ISO manifest does not describe the ISO next to it")
    catalogs = catalog_evidence_index(CATALOG_EVIDENCE_DIR)

    checks: list[dict] = []
    excluded: list[dict] = []
    seen: set[str] = set()
    for entry in inventory.get("packages", []):
        package = entry.get("id")
        if not package or package in seen:
            raise GenerationError(f"invalid or duplicate inventory entry: {package!r}")
        seen.add(package)
        if package not in shipped:
            excluded.append(
                {
                    "id": package,
                    "status": entry.get("status"),
                    "reason": "not selected by the Alpha 8 GNOME recipe (absent from candidate package inventory)",
                }
            )
            continue
        if package in reviews:
            checks.append(review_check(package, entry, shipped[package], reviews[package]))
        else:
            checks.append(inventory_check(package, entry, shipped[package], catalogs.get(package)))
    unknown = sorted(set(reviews) - seen)
    if unknown:
        raise GenerationError(f"package reviews for packages outside the inventory: {unknown}")
    unused = sorted(package for package in reviews if package not in shipped)
    if unused:
        raise GenerationError(f"package reviews for packages absent from the candidate: {unused}")

    status = "passed" if checks and all(check["status"] == "passed" for check in checks) else "failed"
    result = {
        "schema": 1,
        "status": status,
        "mode": "i18n",
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "generated_by": "scripts/i18n-result.py",
        "locales": LOCALES,
        "fallback": "en-US",
        "candidate": {
            "iso": iso_path.name,
            "sha256": iso_identity["sha256"],
            "commit": source["commit"],
        },
        "note": (
            "One check per i18n/inventory.json package shipped in the candidate "
            "(scope = inventory status); catalog evidence linked from docs/evidence; "
            "package reviews bound to the shipped package version. Evidence is bound to "
            "this ISO and must be regenerated for every candidate."
        ),
        "excluded_not_in_candidate": excluded,
        "checks": checks,
    }
    return result, iso_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--iso-dir", required=True, type=Path, help="directory with the candidate .iso, .iso.manifest.json and .packages")
    parser.add_argument("--inventory", type=Path, default=INVENTORY)
    parser.add_argument("--package-review", action="append", default=[], metavar="ID=FILE", help="candidate review JSON bound to one inventory package (repeatable)")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    try:
        result, iso_path = generate(args.iso_dir.resolve(), args.inventory, parse_reviews(args.package_review))
        failed = [check["id"] for check in result["checks"] if check["status"] != "passed"]
        if failed:
            raise GenerationError(f"i18n gate failed for: {', '.join(failed)}")
        load_image_build().validate_test_result("i18n", result, iso_path=iso_path)
    except GenerationError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"i18n-result: {result['status']} ({len(result['checks'])} checks, {len(result['excluded_not_in_candidate'])} excluded) -> {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
