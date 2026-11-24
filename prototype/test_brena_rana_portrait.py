"""Rana portrait staging and executable JavaScript rendering guards."""
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from stage_approved_rana_portrait import stage
from patch_brena_rana_portrait import patch, SCRIPT


class RanaPortraitTests(unittest.TestCase):
    def test_explicit_webp_staged_to_both_web_trees(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for parent in (root / "web", root / "android_native/app/src/main/assets/web"):
                parent.mkdir(parents=True)
                (parent / "app.js").write_text(
                    "    else delete $('panel').dataset.brenaSpeaker;\n", encoding="utf-8")
                (parent / "style.css").write_text("", encoding="utf-8")
            approved = root / "approved.webp"
            approved.write_bytes(b"RIFF" + bytes((12, 0, 0, 0)) + b"WEBP" + b"VP8 " + b"1234")
            outputs = stage(root, approved)
            self.assertEqual(len(outputs), 2)
            for output in outputs:
                self.assertEqual(output.read_bytes(), approved.read_bytes())
            patch(root)
            for parent in (root / "web", root / "android_native/app/src/main/assets/web"):
                js = (parent / "app.js").read_text(encoding="utf-8")
                css = (parent / "style.css").read_text(encoding="utf-8")
                self.assertIn("speakerKey === 'rana' && dialogue === true", js)
                self.assertIn("ranaPortrait.hidden=true", js)
                self.assertIn("brenaExpectedVisible", js)
                self.assertIn("ranaPortrait.dataset.brenaExpectedVisible==='true'", js)
                self.assertIn("ranaSpeaking ? 'true' : 'false'", js)
                self.assertEqual(js.count("addEventListener('load'"), 1)
                self.assertIn("position: fixed", css)

    @unittest.skipUnless(shutil.which("node"), "Node.js required for JS behavior test")
    def test_rana_portrait_js_does_not_reappear_after_speaker_change(self):
        js = """
const assert = require('node:assert/strict');
let portrait;
const panel = {dataset:{brenaSpeaker:'rana'},classList:{contains:()=>true},insertAdjacentElement:(_,el)=>{portrait=el}};
const document = {getElementById:()=>portrait||null,createElement:()=>({
  hidden:true,dataset:{},naturalWidth:0,complete:false,attrs:{},listeners:{},
  addEventListener(k,fn){this.listeners[k]=fn},
  getAttribute(k){return this.attrs[k]||null},
  setAttribute(k,v){this.attrs[k]=v}
})};
const render = new Function('speakerKey','dialogue','$','document',process.env.RANA_SCRIPT);
render('rana',true,()=>panel,document);
assert.equal(portrait.hidden,true);
portrait.naturalWidth=200;portrait.complete=true;portrait.listeners.load();
assert.equal(portrait.hidden,false);
panel.dataset.brenaSpeaker='leticia';
render('leticia',true,()=>panel,document);
assert.equal(portrait.hidden,true);
portrait.listeners.load();
assert.equal(portrait.hidden,true);
panel.dataset.brenaSpeaker='rana';
render('rana',true,()=>panel,document);
assert.equal(portrait.hidden,false);
render('',false,()=>panel,document);
assert.equal(portrait.hidden,true);
console.log('RANA_DOM_TRANSITIONS=PASS');
"""
        result = subprocess.run(
            ["node", "-e", js], env={**os.environ, "RANA_SCRIPT": SCRIPT},
            capture_output=True, text=True, check=True, timeout=10)
        self.assertIn("RANA_DOM_TRANSITIONS=PASS", result.stdout)

    def test_existing_portrait_cannot_be_replaced(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            parent = root / "web"
            parent.mkdir(parents=True)
            (parent / "app.js").write_text("app", encoding="utf-8")
            approved = root / "approved.webp"
            approved.write_bytes(b"RIFF" + bytes((12, 0, 0, 0)) + b"WEBP" + b"VP8 " + b"1234")
            target = parent / "assets/characters/rana/neutral.webp"
            target.parent.mkdir(parents=True)
            target.write_bytes(b"already-approved")
            with self.assertRaises(FileExistsError):
                stage(root, approved)
            self.assertEqual(target.read_bytes(), b"already-approved")

    def test_no_implicit_or_invalid_portrait(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "web").mkdir()
            (root / "web/app.js").write_text("app", encoding="utf-8")
            invalid = root / "not-approved.webp"
            invalid.write_bytes(b"not a webp")
            with self.assertRaises(ValueError):
                stage(root, invalid)
            self.assertFalse(list(root.rglob("neutral.webp")))


if __name__ == "__main__":
    unittest.main()
