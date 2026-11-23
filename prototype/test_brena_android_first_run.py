"""Regression for Android Brena first-run patch and its save-preserving boundary."""
import tempfile
import unittest
from pathlib import Path

from tools.patch_brena_android_first_run import patch


class BrenaAndroidFirstRunTests(unittest.TestCase):
    def test_patch_changes_only_resource_selection_not_save_startup(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            java = root / "android_native/app/src/main/java/com/ailivingworld/mobile/MainActivity.java"
            mobile = root / "android_native/app/src/main/python/mobile_embedded.py"
            asset = root / "android_native/app/src/main/assets/examples/brena_initial_world.json"
            for path in (java, mobile, asset):
                path.parent.mkdir(parents=True, exist_ok=True)
            java.write_text('String[] names={"examples/live_demo_world.json"};\n', encoding="utf-8")
            mobile.write_text(
                "    demo = root / 'examples' / 'live_demo_world.json'\n"
                "    expected = [demo, web / 'index.html']\n"
                "    return private, demo, web\n"
                "    store = initial_demo_store(save,sample_file=sample)\n",
                encoding="utf-8",
            )
            asset.write_text("{}", encoding="utf-8")
            patch(root)
            self.assertIn('"examples/brena_initial_world.json"', java.read_text(encoding="utf-8"))
            result = mobile.read_text(encoding="utf-8")
            self.assertIn("return private, brena, web", result)
            self.assertIn("store = initial_demo_store(save,sample_file=sample)", result)
            self.assertNotIn("unlink(", result)
            self.assertNotIn("rmtree(", result)
            self.assertIn("live_demo_world.json", java.read_text(encoding="utf-8"))

    def test_missing_asset_does_not_change_sources(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            java = root / "android_native/app/src/main/java/com/ailivingworld/mobile/MainActivity.java"
            mobile = root / "android_native/app/src/main/python/mobile_embedded.py"
            java.parent.mkdir(parents=True)
            mobile.parent.mkdir(parents=True)
            java_text = 'String[] names={"examples/live_demo_world.json"};\n'
            mobile_text = (
                "    demo = root / 'examples' / 'live_demo_world.json'\n"
                "    expected = [demo, web / 'index.html']\n"
                "    return private, demo, web\n"
            )
            java.write_text(java_text, encoding="utf-8")
            mobile.write_text(mobile_text, encoding="utf-8")
            with self.assertRaises(FileNotFoundError):
                patch(root)
            self.assertEqual(java.read_text(encoding="utf-8"), java_text)
            self.assertEqual(mobile.read_text(encoding="utf-8"), mobile_text)


if __name__ == "__main__":
    unittest.main()
