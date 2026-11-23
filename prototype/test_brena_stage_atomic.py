"""Atomic Brena staging regressions using temporary Android source fixtures."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.stage_brena_android import MODULES, stage


class StageAtomicTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.prototype = root / "prototype"
        self.android = root / "src"
        self.packaged = self.android / "android_native/app/src/main/python"
        self.prototype.mkdir()
        self.packaged.mkdir(parents=True)
        (self.android / "world_engine.py").write_text("original")
        (self.packaged / "world_engine.py").write_text("original")
        for name in MODULES:
            (self.prototype / name).write_text(name)

    def test_success_and_repeat_are_idempotent(self):
        self.assertEqual(len(stage(self.prototype, self.android)), len(MODULES) * 2)
        self.assertEqual(len(stage(self.prototype, self.android)), len(MODULES) * 2)

    def test_missing_source_leaves_no_new_modules(self):
        (self.prototype / MODULES[-1]).unlink()
        with self.assertRaises(FileNotFoundError):
            stage(self.prototype, self.android)
        self.assertFalse((self.android / MODULES[0]).exists())

    def test_existing_identical_module_survives_failed_publish(self):
        existing = self.android / MODULES[0]
        existing.write_text(MODULES[0])
        from tools import stage_brena_android
        original_link = stage_brena_android.os.link
        calls = 0

        def fail_second(source, destination):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise OSError("simulated interruption")
            return original_link(source, destination)

        with patch.object(stage_brena_android.os, "link", side_effect=fail_second):
            with self.assertRaises(OSError):
                stage(self.prototype, self.android)
        self.assertEqual(existing.read_text(), MODULES[0])
        self.assertFalse((self.packaged / MODULES[0]).exists())

    def test_conflicting_existing_module_is_never_overwritten(self):
        existing = self.packaged / MODULES[0]
        existing.write_text("keep-original")
        with self.assertRaises(FileExistsError):
            stage(self.prototype, self.android)
        self.assertEqual(existing.read_text(), "keep-original")
        self.assertFalse((self.android / MODULES[0]).exists())

    def test_publish_failure_rolls_back_all_new_files(self):
        from tools import stage_brena_android
        original_link = stage_brena_android.os.link
        calls = 0

        def fail_second(source, destination):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise OSError("simulated publish interruption")
            return original_link(source, destination)

        with patch.object(stage_brena_android.os, "link", side_effect=fail_second):
            with self.assertRaisesRegex(OSError, "interruption"):
                stage(self.prototype, self.android)
        for name in MODULES:
            self.assertFalse((self.android / name).exists())
            self.assertFalse((self.packaged / name).exists())
        self.assertFalse(list(self.android.glob(".brena-stage-*")))
        self.assertFalse(list(self.packaged.glob(".brena-stage-*")))


if __name__ == "__main__":
    unittest.main()
