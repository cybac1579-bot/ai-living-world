"""Show the offline visual novel, not the native D4 debug dashboard.

Applied to the unpacked build candidate *after* density and D4 diagnostics.
Keeps startup error information available on failure; hides diagnostic UI on success.
"""
from pathlib import Path
import sys

def replace_once(source, old, new):
    count=source.count(old)
    if count != 1:
        raise AssertionError(f"Unexpected activity shape: {old[:85]!r}, occurrences={count}")
    return source.replace(old,new)

def main():
    if len(sys.argv)!=2:
        raise SystemExit("Usage: patch_android_presentation_ui.py <MainActivity.java>")
    java=Path(sys.argv[1])
    source=java.read_text(encoding="utf-8")
    assert 'AI Living World / 진단 D4' in source, "Diagnostic patch must be applied first"
    source=replace_once(
        source,
        "    private volatile boolean pageFailed = false;",
        "    private volatile boolean pageFailed = false;\n"
        "    private TextView bootBanner;\n"
        "    private LinearLayout bar;"
    )
    source=replace_once(
        source, "        TextView bootBanner = new TextView(this);",
        "        bootBanner = new TextView(this);"
    )
    source=replace_once(
        source, "        final LinearLayout bar = new LinearLayout(this);",
        "        bar = new LinearLayout(this);"
    )
    source=replace_once(
        source,
        '        setContentView(root);\n        offline.setOnClickListener(v -> startEngine(true));',
        '        setContentView(root);\n'
        '        // Playable preview: native debug controls are hidden unless startup fails.\n'
        '        bootBanner.setVisibility(View.GONE);\n'
        '        bar.setVisibility(View.GONE);\n'
        '        status.setVisibility(View.GONE);\n'
        '        offline.setOnClickListener(v -> startEngine(true));'
    )
    source=replace_once(
        source,
        '                    uiError("진단 D4 | WebView 오류 (" + error.getErrorCode() + "): " + error.getDescription());',
        '                    bootBanner.setVisibility(View.VISIBLE);\n'
        '                    bar.setVisibility(View.VISIBLE);\n'
        '                    status.setVisibility(View.VISIBLE);\n'
        '                    uiError("진단 D4 | WebView 오류 (" + error.getErrorCode() + "): " + error.getDescription());'
    )
    source=replace_once(
        source,
        '                uiError("진단 D4 | 오류 단계 [" + bootStage + "] " + ex.getClass().getSimpleName() + ": " + details);',
        '                final String diagnostic = "진단 D4 | 오류 단계 [" + bootStage + "] " + ex.getClass().getSimpleName() + ": " + details;\n'
        '                runOnUiThread(() -> {\n'
        '                    bootBanner.setVisibility(View.VISIBLE);\n'
        '                    bar.setVisibility(View.VISIBLE);\n'
        '                    status.setVisibility(View.VISIBLE);\n'
        '                    status.setText(diagnostic);\n'
        '                });'
    )
    assert source.count('bootBanner.setVisibility(View.GONE)')==1
    assert source.count('bar.setVisibility(View.VISIBLE)')==2
    java.write_text(source,encoding="utf-8")
    print("ANDROID_PRESENTATION_FULLSCREEN=PASS")

if __name__=="__main__":
    main()
