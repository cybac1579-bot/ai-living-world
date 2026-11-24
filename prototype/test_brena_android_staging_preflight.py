"""Preflight regression for staging Brena into the existing Android source tree."""
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from tools.stage_brena_android import MODULES, stage


class StagingSafetyTests(unittest.TestCase):
    def make_tree(self, root):
        prototype = root / "prototype"
        android = root / "android"
        packaged = android / "android_native/app/src/main/python"
        prototype.mkdir()
        packaged.mkdir(parents=True)
        (android / "world_engine.py").write_text("# engine", encoding="utf-8")
        (packaged / "world_engine.py").write_text("# packaged engine", encoding="utf-8")
        for name in MODULES:
            (prototype / name).write_text(name, encoding="utf-8")
        return prototype, android, packaged

    def test_missing_late_module_copies_nothing(self):
        with TemporaryDirectory() as temp:
            prototype, android, packaged = self.make_tree(Path(temp))
            (prototype / MODULES[-1]).unlink()
            with self.assertRaises(FileNotFoundError):
                stage(prototype, android)
            for name in MODULES:
                self.assertFalse((android / name).exists())
                self.assertFalse((packaged / name).exists())

    def test_late_conflict_copies_nothing(self):
        with TemporaryDirectory() as temp:
            prototype, android, packaged = self.make_tree(Path(temp))
            conflict = packaged / MODULES[-1]
            conflict.write_text("different", encoding="utf-8")
            with self.assertRaises(FileExistsError):
                stage(prototype, android)
            self.assertEqual(conflict.read_text(encoding="utf-8"), "different")
            for name in MODULES:
                self.assertFalse((android / name).exists())
                if name != MODULES[-1]:
                    self.assertFalse((packaged / name).exists())

    def test_success_and_idempotent_repeat(self):
        with TemporaryDirectory() as temp:
            prototype, android, packaged = self.make_tree(Path(temp))
            self.assertEqual(len(stage(prototype, android)), 2 * len(MODULES))
            self.assertEqual(len(stage(prototype, android)), 2 * len(MODULES))
            for name in MODULES:
                expected = (prototype / name).read_bytes()
                self.assertEqual((android / name).read_bytes(), expected)
                self.assertEqual((packaged / name).read_bytes(), expected)


if __name__ == "__main__":
    unittest.main()
