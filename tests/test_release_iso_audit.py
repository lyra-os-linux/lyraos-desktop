from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("release_iso_audit", ROOT / "scripts/audit-release-iso.py")
assert SPEC and SPEC.loader
audit = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = audit
SPEC.loader.exec_module(audit)


class ReleaseIsoAuditTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.iso = self.root / "lyra.iso"
        self.iso.write_bytes(b"iso")
        self.rootfs = self.root / "rootfs"
        (self.rootfs / "home/liveuser").mkdir(parents=True)
        (self.rootfs / "root").mkdir()

    def test_clean_live_rootfs_passes_and_records_hash(self) -> None:
        report = audit.audit(self.iso, rootfs=self.rootfs)
        self.assertEqual(report["result"], "pass")
        self.assertEqual(report["iso"]["sha256"], audit.sha256(self.iso))
        self.assertEqual(report["inventory"]["homes"], ["/home/liveuser"])

    def test_unexpected_build_user_home_is_critical(self) -> None:
        (self.rootfs / "home/rodrigo/Git/Lyra").mkdir(parents=True)
        report = audit.audit(self.iso, rootfs=self.rootfs)
        self.assertEqual(report["result"], "fail")
        self.assertIn("unexpected-home", {item["kind"] for item in report["findings"]})

    def test_private_keys_tokens_and_host_paths_fail(self) -> None:
        ssh = self.rootfs / "root/.ssh"
        ssh.mkdir()
        (ssh / "id_ed25519").write_text("-----BEGIN OPENSSH PRIVATE KEY-----\n", encoding="utf-8")
        (self.rootfs / "etc/build-info").parent.mkdir()
        (self.rootfs / "etc/build-info").write_text("/home/builder/Git/Lyra/source\n", encoding="utf-8")
        report = audit.audit(self.iso, rootfs=self.rootfs)
        kinds = {item["kind"] for item in report["findings"]}
        self.assertTrue({"sensitive-path", "secret-content", "host-path-content"} <= kinds)

    def test_inventory_records_root_caches_and_logs(self) -> None:
        (self.rootfs / "root/.cache/tool").mkdir(parents=True)
        (self.rootfs / "var/cache/zypp").mkdir(parents=True)
        (self.rootfs / "var/log").mkdir(parents=True)
        (self.rootfs / "var/log/build.log").write_text("safe log", encoding="utf-8")
        report = audit.audit(self.iso, rootfs=self.rootfs)
        self.assertIn("/root/.cache", report["inventory"]["caches"])
        self.assertIn("/var/cache/zypp", report["inventory"]["caches"])
        self.assertIn("/var/log/build.log", report["inventory"]["logs"])

    def test_tokens_in_logs_and_system_caches_fail(self) -> None:
        log = self.rootfs / "var/log/build.log"
        cache = self.rootfs / "var/cache/builder/state"
        log.parent.mkdir(parents=True)
        cache.parent.mkdir(parents=True)
        log.write_text("token=super-secret-release-token\n", encoding="utf-8")
        cache.write_text("password=unexpected-build-password\n", encoding="utf-8")
        report = audit.audit(self.iso, rootfs=self.rootfs)
        leaked = {item["path"] for item in report["findings"] if item["kind"] == "secret-content"}
        self.assertEqual(leaked, {"/var/cache/builder/state", "/var/log/build.log"})

    def test_packaged_private_key_fixture_is_not_a_host_leak(self) -> None:
        fixture = self.rootfs / "usr/share/tests/private-key.pem"
        fixture.parent.mkdir(parents=True)
        fixture.write_text("-----BEGIN PRIVATE KEY-----\n", encoding="utf-8")
        report = audit.audit(self.iso, rootfs=self.rootfs)
        self.assertEqual(report["result"], "pass")


if __name__ == "__main__":
    unittest.main()
