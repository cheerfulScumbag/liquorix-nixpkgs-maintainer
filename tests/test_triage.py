import importlib.util
import unittest
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "triage.py"
SPEC = importlib.util.spec_from_file_location("triage", SCRIPT)
triage = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(triage)


class TriageTests(unittest.TestCase):
    def test_sanitize(self):
        raw = (
            "Authorization: Bearer secret\n"
            "token=value\n"
            "/home/kenn/project\n"
            "/nix/store/0123456789abcdfghijklmnpqrsvwxyz-package"
        )
        clean = triage.sanitize(raw)
        self.assertNotIn("secret", clean)
        self.assertNotIn("token=value", clean)
        self.assertNotIn("/home/kenn", clean)
        self.assertIn("/nix/store/<hash>-package", clean)

    def test_response_text(self):
        payload = {
            "output": [
                {
                    "type": "message",
                    "content": [{"type": "output_text", "text": "diagnosis"}],
                }
            ]
        }
        self.assertEqual(triage.response_text(payload), "diagnosis")


if __name__ == "__main__":
    unittest.main()
