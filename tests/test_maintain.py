import importlib.util
import unittest
from pathlib import Path
from unittest.mock import patch


SCRIPT = Path(__file__).parents[1] / "scripts" / "maintain.py"
SPEC = importlib.util.spec_from_file_location("maintain", SCRIPT)
maintain = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(maintain)


class MaintainTests(unittest.TestCase):
    def test_release_line(self):
        self.assertEqual(maintain.release_line("7.1.4"), "7.1")

    @patch.object(maintain, "updater")
    def test_check_marks_new_line(self, updater):
        updater.return_value = {
            "current": False,
            "oldVersion": "6.18.9",
            "newVersion": "7.1.0",
        }
        result = maintain.check(Path("/tmp/nixpkgs"))
        self.assertTrue(result["updateAvailable"])
        self.assertTrue(result["newKernelLine"])

    @patch.object(maintain, "updater")
    def test_check_marks_point_release(self, updater):
        updater.return_value = {
            "current": False,
            "oldVersion": "7.1.3",
            "newVersion": "7.1.4",
        }
        result = maintain.check(Path("/tmp/nixpkgs"))
        self.assertTrue(result["updateAvailable"])
        self.assertFalse(result["newKernelLine"])

    @patch.object(maintain, "updater")
    def test_config_drift_stops_before_update(self, updater):
        updater.side_effect = [
            {
                "current": False,
                "oldVersion": "7.1.3",
                "newVersion": "7.1.4",
            },
            {"drift": {"CONFIG_HZ": {"expected": "1000", "actual": "500"}}},
        ]
        with self.assertRaises(RuntimeError):
            maintain.update(Path("/tmp/nixpkgs"))
        self.assertEqual(updater.call_count, 2)


if __name__ == "__main__":
    unittest.main()
