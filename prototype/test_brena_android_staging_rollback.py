"""Failure-injection regressions for Brena Android staging rollback.

These tests operate only on temporary fake Android source trees.
"""
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase, main
from unittest.mock import patch

from tools.stage_brena_android import MODULES, stage
import tools.stage_brena_android as staging


class StagingRollbackTests(TestCase):
    def make_tree(self, root):
        prototype = root / "prototype"
        android = root / "android"
        packaged = android / "android_native/app/src/main/python"
        prototype.mkdir()
        packaged.mkdir(parents=True)
        (android / "world_engine.py").write_text("# engine", encoding="utf-8")
        (packaged / "world_engine.py").write_text("# engine", encoding="utf-8")
        for name in MODULES:
            (prototype / name).write_text(name, encoding="utf-8")
        return prototype, android, packaged

    def test_publish_failure_rolls_back_only_new_files_and_allows_retry(self):
        with TemporaryDirectory() as temp:
            prototype, android, packaged = self.make_tree(Path(temp))
            preserved = android / MODULES[0]
            preserved.write_bytes((prototype / MODULES[0]).read_bytes())
            real_link = staging.os.link
            calls = 0

            def fail_after_partial_publish(source, target):
                nonlocal calls
                calls += 1
                if calls == 4:
                    raise OSError("injected publication failure")
                return real_link(source, target)

            with patch.object(staging.os, "link", side_effect=fail_after_partial_publish):
                with self.assertRaisesRegex(OSError, "injected publication failure"):
                    stage(prototype, android)

            self.assertEqual(preserved.read_bytes(), (prototype / MODULES[0]).read_bytes())
            for name in MODULES:
                if name != MODULES[0]:
                    self.assertFalse((android / name).exists(), name)
                self.assertFalse((packaged / name).exists(), name)
            for directory in (android, packaged):
                self.assertEqual(list(directory.glob(".brena-stage-*")), [])

            self.assertEqual(len(stage(prototype, android)), len(MODULES) * 2)
            for name in MODULES:
                self.assertEqual((android / name).read_bytes(), (prototype / name).read_bytes())
                self.assertEqual((packaged / name).read_bytes(), (prototype / name).read_bytes())

    def test_temp_write_failure_leaves_no_published_files(self):
        with TemporaryDirectory() as temp:
            prototype, android, packaged = self.make_tree(Path(temp))
            with patch.object(staging.os, "fsync", side_effect=OSError("injected fsync failure")):
                with self.assertRaisesRegex(OSError, "injected fsync failure"):
                    stage(prototype, android)
            for directory in (android, packaged):
                for name in MODULES:
                    self.assertFalse((directory / name).exists())
                self.assertEqual(list(directory.glob(".brena-stage-*")), [])


if __name__ == "__main__":
    main()
