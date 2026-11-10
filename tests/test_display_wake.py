import importlib.machinery
import importlib.util
import os
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "packaging/lyra-display-wake/lyra-display-wake"


def load():
    loader = importlib.machinery.SourceFileLoader("lyra_display_wake", str(SCRIPT))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


def mode(mode_id, width, height, refresh, current=False):
    return (mode_id, width, height, refresh, 1.0, [1.0], {"is-current": current} if current else {})


MONITORS = [
    (("eDP-1", "BOE", "0x0", "0x0"),
     [mode("1920x1080@144.003", 1920, 1080, 144.003, True),
      mode("1920x1080@119.877", 1920, 1080, 119.877)],
     {"is-builtin": True}),
    (("HDMI-1", "SAM", "LC34G55T", "x"),
     [mode("3440x1440@99.982", 3440, 1440, 99.982, True),
      mode("3440x1440@59.973", 3440, 1440, 59.973),
      mode("3440x1440@49.987", 3440, 1440, 49.987),
      mode("2560x1440@99.946", 2560, 1440, 99.946)],
     {"color-mode": 0}),
]
LOGICAL = [
    (0, 0, 1.0, 0, True, [("eDP-1", "BOE", "0x0", "0x0")], {}),
    (1920, 0, 1.0, 0, False, [("HDMI-1", "SAM", "LC34G55T", "x")], {}),
]


class DisplayWakeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.wake = load()

    def test_kernel_connector_names_map_to_mutter(self) -> None:
        self.assertEqual(self.wake.mutter_connector("HDMI-A-1"), "HDMI-1")
        self.assertEqual(self.wake.mutter_connector("DP-2"), "DP-2")
        self.assertEqual(self.wake.mutter_connector("eDP-1"), "eDP-1")

    def test_only_active_nvidia_connectors_are_targets(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            drivers = Path(tmp, "drivers")
            for name in ("nvidia", "i915"):
                (drivers / name).mkdir(parents=True)
            drm = Path(tmp, "drm")
            for card, driver in (("card0", "nvidia"), ("card1", "i915")):
                (drm / card / "device").mkdir(parents=True)
                os.symlink(drivers / driver, drm / card / "device" / "driver")
            for name, card, status, enabled in (
                    ("card0-HDMI-A-1", "card0", "connected", "enabled"),
                    ("card0-DP-1", "card0", "disconnected", "disabled"),
                    ("card1-eDP-1", "card1", "connected", "enabled")):
                connector = drm / card / name
                connector.mkdir()
                (connector / "status").write_text(status + "\n")
                (connector / "enabled").write_text(enabled + "\n")
                os.symlink(connector, drm / name)
            self.assertEqual(self.wake.nvidia_connectors(str(drm)), {"HDMI-1"})

    def test_alternate_mode_keeps_resolution_and_picks_closest_rate(self) -> None:
        current, options = self.wake.current_modes(MONITORS)["HDMI-1"]
        self.assertEqual(current, "3440x1440@99.982")
        self.assertEqual(self.wake.alternate_mode(current, options), "3440x1440@59.973")

    def test_no_alternate_without_another_rate(self) -> None:
        options = [("2560x1440@59.951", 2560, 1440, 59.951), ("1920x1080@60.000", 1920, 1080, 60.0)]
        self.assertIsNone(self.wake.alternate_mode("2560x1440@59.951", options))

    def test_config_is_temporary_and_keeps_layout(self) -> None:
        state = (8, MONITORS, LOGICAL, {})
        serial, method, logical, props = self.wake.build_config(state, {"HDMI-1": "3440x1440@59.973"})
        self.assertEqual((serial, method, props), (8, 1, {}))
        self.assertEqual([(lm[0], lm[1], lm[4]) for lm in logical], [(0, 0, True), (1920, 0, False)])
        self.assertEqual(logical[0][5][0][:2], ("eDP-1", "1920x1080@144.003"))
        self.assertEqual(logical[1][5][0][:2], ("HDMI-1", "3440x1440@59.973"))
        self.assertEqual(logical[1][5][0][2]["color-mode"].unpack(), 0)

    def test_package_is_standalone_and_in_the_image(self) -> None:
        package = ROOT / "packaging/lyra-display-wake"
        spec = (package / "lyra-display-wake.spec").read_text(encoding="utf-8")
        requires = [line for line in spec.splitlines() if line.startswith("Requires:")]
        self.assertFalse([line for line in requires if "lyra" in line])
        unit = (package / "lyra-display-wake.service").read_text(encoding="utf-8")
        self.assertIn("ConditionPathExists=/sys/module/nvidia_drm\n", unit)
        self.assertIn("WantedBy=graphical-session.target\n", unit)
        self.assertIn('<package name="lyra-display-wake"/>',
                      (ROOT / "kiwi/config.xml").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
