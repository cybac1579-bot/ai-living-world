"""Apply deterministic UI sizing to the offline-only Android debug source.

The archive is a preserved v1.3 baseline, so do not rewrite the original ZIP.
The published debug APK is generated from a patched working copy.
"""
from pathlib import Path
import sys

def replace_exact(text: str, old: str, new: str, expected: int = 1) -> str:
    actual = text.count(old)
    if actual != expected:
        raise AssertionError(f"Unexpected Android source structure: {old!r} ({actual} matches, expected {expected})")
    return text.replace(old, new)

def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("Usage: patch_android_debug_ui.py path/to/MainActivity.java")
    path = Path(sys.argv[1])
    text = path.read_text(encoding="utf-8")
    text = replace_exact(
        text,
        "        super.onCreate(savedInstanceState);",
        "        super.onCreate(savedInstanceState);\n"
        "        // LayoutParams sizes are physical pixels, not dp. Convert for modern high-density screens.\n"
        "        final float density = getResources().getDisplayMetrics().density;\n"
        "        final int toolbarHeight = Math.round(56f * density);\n"
        "        final int statusHeight = Math.round(72f * density);"
    )
    text = replace_exact(
        text,
        "new LinearLayout.LayoutParams(0, 56, 1f)",
        "new LinearLayout.LayoutParams(0, toolbarHeight, 1f)",
        expected=3
    )
    text = replace_exact(text, "status.setPadding(12, 0, 12, 0);",
        "status.setPadding(Math.round(12f * density), 0, Math.round(12f * density), 0);\n"
        "        status.setTextSize(14f);\n"
        "        status.setMaxLines(3);")
    text = replace_exact(text, "root.addView(status,new LinearLayout.LayoutParams(-1,48));",
        "root.addView(status,new LinearLayout.LayoutParams(-1,statusHeight));")
    path.write_text(text, encoding="utf-8")
    assert "toolbarHeight" in text and "statusHeight" in text
    print("ANDROID_UI_DENSITY_PATCH=PASS")

if __name__ == "__main__":
    main()
