import importlib.util
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def load_check_setup():
    spec = importlib.util.spec_from_file_location("check_setup", ROOT / "scripts" / "check_setup.py")
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class CheckSetupRuntimeTests(unittest.TestCase):
    def test_canonical_python_prefers_project_override(self):
        check_setup = load_check_setup()

        with patch.dict("os.environ", {"INVESTMENT_AGENT_PYTHON": "/custom/python.exe"}, clear=False):
            self.assertEqual(check_setup.resolve_canonical_python().as_posix(), "/custom/python.exe")

    def test_canonical_python_falls_back_to_mine_work_python(self):
        check_setup = load_check_setup()

        with patch.dict("os.environ", {"MINE_WORK_PYTHON": "/mine/work/python.exe"}, clear=False):
            self.assertEqual(check_setup.resolve_canonical_python().as_posix(), "/mine/work/python.exe")

    def test_should_reexec_detects_wrong_interpreter(self):
        check_setup = load_check_setup()
        canonical = ROOT / "_tmp_canonical_python_for_test.exe"
        canonical.write_text("stub")
        try:
            self.assertTrue(check_setup.should_reexec(current_python="/other/python", canonical_python=canonical, already_reexeced=False))
            self.assertFalse(check_setup.should_reexec(current_python=str(canonical), canonical_python=canonical, already_reexeced=False))
            self.assertFalse(check_setup.should_reexec(current_python="/other/python", canonical_python=canonical, already_reexeced=True))
        finally:
            canonical.unlink(missing_ok=True)

    def test_build_windows_wslenv_exposes_present_secret_vars(self):
        check_setup = load_check_setup()

        merged = check_setup.build_windows_wslenv(
            existing="PATH/l",
            environ={
                "JQ_USER": "set",
                "JQ_PASS": "set",
                "OPENAI_API_KEY": "set",
                "BROWSER_USE_API_KEY": "",
            },
        )

        self.assertIn("PATH/l", merged.split(":"))
        self.assertIn("JQ_USER/w", merged.split(":"))
        self.assertIn("JQ_PASS/w", merged.split(":"))
        self.assertIn("OPENAI_API_KEY/w", merged.split(":"))
        self.assertNotIn("BROWSER_USE_API_KEY/w", merged.split(":"))


if __name__ == "__main__":
    unittest.main()
