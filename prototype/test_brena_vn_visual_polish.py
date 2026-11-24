"""Regression tests for actual Android VN visual patching."""
import tempfile
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from patch_brena_vn_visual_polish import patch


class BrenaVisualPatchTests(unittest.TestCase):
    def test_patches_both_web_asset_trees_without_creating_art(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for parent in (root / "web", root / "android_native/app/src/main/assets/web"):
                parent.mkdir(parents=True)
                (parent / "app.js").write_text("    styleSpeaker(dialogue ? p.speaker : null);\n", encoding="utf-8")
                (parent / "style.css").write_text("#panel { color: white; }\n", encoding="utf-8")
            patch(root)
            for parent in (root / "web", root / "android_native/app/src/main/assets/web"):
                js = (parent / "app.js").read_text(encoding="utf-8")
                css = (parent / "style.css").read_text(encoding="utf-8")
                self.assertIn("speakerName === '라나'", js)
                self.assertIn("speakerName === '레티시아'", js)
                self.assertIn("delete $('panel').dataset.brenaSpeaker", js)
                self.assertIn('[data-brena-speaker="leticia"]', css)
                self.assertIn('[data-brena-speaker="rana"]', css)
                self.assertIn("#panel.narration-panel", css)
                self.assertIn("typeof p.speaker === 'string'", js)
                self.assertIn("typeof p.speaker.name === 'string'", js)
                self.assertIn("#brena-rana-status[hidden]", css)
                self.assertIn("#brena-world-clock:not([hidden])", css)
                self.assertIn("#brena-travel-actions > summary", css)
                self.assertIn("#brena-travel-actions:not([open]) > button", css)
                self.assertIn("#brena-time-actions[hidden]", css)
                self.assertIn("position: fixed !important", css)
                self.assertIn("max-height: min(52dvh, 360px)", css)
                self.assertIn("overflow-y: auto", css)
                self.assertIn("#brena-travel-actions[hidden]", css)
            self.assertFalse(list(root.rglob("*.png")))

    def test_travel_request_disables_real_buttons_not_summary(self):
        from patch_brena_vn_ui import patch as patch_ui
        with tempfile.TemporaryDirectory() as folder:
            script = Path(folder) / "app.js"
            script.write_text("    $('place').textContent=app.world.region.name;\n", encoding="utf-8")
            patch_ui(script)
            result = script.read_text(encoding="utf-8")
            self.assertIn(
                "Array.from(travelActions.querySelectorAll('button')).forEach(b=>{b.disabled=true;});",
                result)
            self.assertNotIn(
                "Array.from(travelActions.children).forEach(b=>{b.disabled=true;});",
                result)

    def test_speaker_cards_are_only_engine_authored(self):
        from patch_brena_vn_visual_polish import patch as patch_visual
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            parent = root / "web"
            parent.mkdir(parents=True)
            (parent / "app.js").write_text(
                "    styleSpeaker(dialogue ? p.speaker : null);\n", encoding="utf-8")
            (parent / "style.css").write_text("", encoding="utf-8")
            patch_visual(root)
            js = (parent / "app.js").read_text(encoding="utf-8")
            self.assertIn("speakerName === '라나' ? 'rana'", js)
            self.assertIn("speakerName === '레티시아' ? 'leticia'", js)
            self.assertIn("if (speakerKey) $('panel').dataset.brenaSpeaker = speakerKey;", js)
            self.assertIn("else delete $('panel').dataset.brenaSpeaker;", js)
            css = (parent / "style.css").read_text(encoding="utf-8")
            self.assertIn('rgba(232,244,255,.97)', css)
            self.assertIn('rgba(255,244,238,.97)', css)
            self.assertIn("#panel.narration-panel", css)

    def test_unknown_renderer_fails_closed(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "web").mkdir()
            (root / "web/app.js").write_text("wrong renderer", encoding="utf-8")
            (root / "web/style.css").write_text("", encoding="utf-8")
            with self.assertRaises(AssertionError):
                patch(root)


if __name__ == "__main__":
    unittest.main()
