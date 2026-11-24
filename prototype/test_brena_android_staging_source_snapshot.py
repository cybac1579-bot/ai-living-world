"""Regression: staging must use bytes validated during preflight."""
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase, main
from unittest.mock import patch

import tools.stage_brena_android as staging


class SourceSnapshotTests(TestCase):
    def test_source_changes_after_preflight_do_not_change_staged_bytes(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            prototype = root / "prototype"
            android = root / "android"
            packaged = android / "android_native/app/src/main/python"
            prototype.mkdir()
            packaged.mkdir(parents=True)
            (android / "world_engine.py").write_text("# engine", encoding="utf-8")
            (packaged / "world_engine.py").write_text("# engine", encoding="utf-8")
            for name in staging.MODULES:
                (prototype / name).write_bytes(b"validated")
            original_mkstemp = staging.tempfile.mkstemp
            mutated = False

            def mutate_after_preflight(*args, **kwargs):
                nonlocal mutated
                if not mutated:
                    mutated = True
                    (prototype / staging.MODULES[0]).write_bytes(b"changed")
                return original_mkstemp(*args, **kwargs)

            with patch.object(staging.tempfile, "mkstemp", side_effect=mutate_after_preflight):
                staging.stage(prototype, android)
            self.assertTrue(mutated)
            for name in staging.MODULES:
                self.assertEqual((android / name).read_bytes(), b"validated")
                self.assertEqual((packaged / name).read_bytes(), b"validated")


if __name__ == "__main__":
    main()
