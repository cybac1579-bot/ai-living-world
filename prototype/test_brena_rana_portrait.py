"""Rana portrait staging and rendering guards."""
import tempfile
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from stage_approved_rana_portrait import stage
from patch_brena_rana_portrait import patch


class RanaPortraitTests(unittest.TestCase):
    def test_explicit_webp_staged_to_both_web_trees(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            for parent in (root/"web", root/"android_native/app/src/main/assets/web"):
                parent.mkdir(parents=True)
                (parent/"app.js").write_text(
                    "    else delete $('panel').dataset.brenaSpeaker;\n", encoding="utf-8")
                (parent/"style.css").write_text("", encoding="utf-8")
            approved=root/"approved.webp"
            approved.write_bytes(b"RIFF"+b"\x0c\x00\x00\x00"+b"WEBP"+b"VP8 "+b"1234")
            outputs=stage(root,approved)
            self.assertEqual(len(outputs),2)
            for output in outputs:
                self.assertEqual(output.read_bytes(),approved.read_bytes())
            patch(root)
            for parent in (root/"web",root/"android_native/app/src/main/assets/web"):
                js=(parent/"app.js").read_text(encoding="utf-8")
                css=(parent/"style.css").read_text(encoding="utf-8")
                self.assertIn("speakerKey === 'rana' && dialogue === true",js)
                self.assertIn("ranaPortrait.hidden=true",js)
                self.assertEqual(js.count("addEventListener('load'"),1)
                self.assertIn("position: fixed",css)

    def test_no_implicit_or_invalid_portrait(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            (root/"web").mkdir()
            (root/"web/app.js").write_text("app",encoding="utf-8")
            invalid=root/"not-approved.webp"
            invalid.write_bytes(b"not a webp")
            with self.assertRaises(ValueError):
                stage(root,invalid)
            self.assertFalse(list(root.rglob("neutral.webp")))


if __name__=="__main__":
    unittest.main()
