"""Instrument the Android offline-debug bootstrap without touching the canonical ZIP.
Only this local-test APK gets explicit stage/status/error information.
"""
from pathlib import Path
import sys

def exact(source, before, after, n=1):
    actual=source.count(before)
    if actual!=n:
        raise AssertionError(f"Expected {n} copies of {before[:90]!r}, found {actual}")
    return source.replace(before,after)

def main():
    if len(sys.argv)!=2:
        raise SystemExit("Usage: patch_android_startup_diagnostics.py <MainActivity.java>")
    path=Path(sys.argv[1])
    s=path.read_text(encoding="utf-8")
    s=exact(s, "import android.webkit.WebViewClient;",
       "import android.webkit.WebViewClient;\n"
       "import android.webkit.WebResourceError;\n"
       "import android.webkit.WebResourceRequest;\n"
       "import android.util.Log;")
    s=exact(s, '    private String localOrigin = "";',
       '    private String localOrigin = "";\n'
       '    private volatile boolean pageFailed = false;')
    s=exact(s, "        final LinearLayout bar = new LinearLayout(this);",
       '        TextView bootBanner = new TextView(this);\n'
       '        bootBanner.setText("AI Living World / 진단 D4");\n'
       '        bootBanner.setTextColor(Color.YELLOW);\n'
       '        bootBanner.setTextSize(19f);\n'
       '        bootBanner.setGravity(Gravity.CENTER);\n'
       '        bootBanner.setBackgroundColor(Color.rgb(22, 34, 50));\n'
       '        root.addView(bootBanner, new LinearLayout.LayoutParams(-1, Math.round(48f * density)));\n'
       "        final LinearLayout bar = new LinearLayout(this);")
    s=exact(s, '        status.setText("모의 화면 준비 중 · 공식 게임 저장과 분리돼");',
       '        status.setText("진단 D4 | 단계 0: Android 화면 초기화 완료");\n'
       '        status.setBackgroundColor(Color.rgb(28, 38, 51));')
    s=exact(s, '        status.setMaxLines(3);',
       '        status.setMaxLines(6);')
    s=exact(s, "root.addView(status,new LinearLayout.LayoutParams(-1,statusHeight));",
       "root.addView(status,new LinearLayout.LayoutParams(-1,Math.round(128f * density)));")
    s=exact(s, '        webView = new WebView(this);',
       '        webView = new WebView(this);\n'
       '        webView.setBackgroundColor(Color.rgb(16, 21, 30));')
    s=exact(s,
       '            @Override public void onPageFinished(WebView view, String url) {\n'
       '                status.setText("비공식 DEMO · 실제 저장 여부는 게임의 rev로 확인해");\n'
       '            }',
       '            @Override public void onPageFinished(WebView view, String url) {\n'
       '                Log.i("ALW_BOOT", "WebView pageFinished");\n'
       '                if (!pageFailed) uiError("진단 D4 | 단계 5: 페이지 로드 완료 (화면이 비면 WebView 렌더링 확인 필요)");\n'
       '            }\n'
       '            @Override public void onReceivedError(WebView view, WebResourceRequest request, WebResourceError error) {\n'
       '                if (request.isForMainFrame()) {\n'
       '                    pageFailed = true;\n'
       '                    uiError("진단 D4 | WebView 오류 (" + error.getErrorCode() + "): " + error.getDescription());\n'
       '                    Log.e("ALW_BOOT", "WebView main frame error: " + error.getErrorCode());\n'
       '                }\n'
       '            }')
    s=exact(s, "        worker.execute(() -> {\n            try {\n                File assetsDir = prepareResources();",
       '        worker.execute(() -> {\n'
       '            String bootStage = "1/resources";\n'
       '            try {\n'
       '                uiError("진단 D4 | 단계 1: 리소스 준비");\n'
       '                File assetsDir = prepareResources();')
    s=exact(s, '                PyObject module = Python.getInstance().getModule("mobile_embedded");\n'
       '                PyObject url = module.callAttr("start_engine",getFilesDir().getCanonicalPath(),',
       '                bootStage = "2/python-import";\n'
       '                uiError("진단 D4 | 단계 2: Python 엔진 불러오는 중");\n'
       '                PyObject module = Python.getInstance().getModule("mobile_embedded");\n'
       '                bootStage = "3/server-start";\n'
       '                uiError("진단 D4 | 단계 3: 내부 서버 시작 중");\n'
       '                PyObject url = module.callAttr("start_engine",getFilesDir().getCanonicalPath(),')
    s=exact(s, '                Uri u = Uri.parse(result);',
       '                bootStage = "4/validate-url";\n'
       '                Uri u = Uri.parse(result);')
    s=exact(s, '                    webView.loadUrl(result);',
       '                    pageFailed = false;\n'
       '                    uiError("진단 D4 | 단계 4: 내부 페이지 로딩 중");\n'
       '                    webView.loadUrl(result);')
    s=exact(s,
       '            } catch (Exception ex) {\n'
       '                uiError("실행 실패: Android 런타임/인증/리소스를 확인해야 해. (" + ex.getClass().getSimpleName() + ")");\n'
       '            }',
       '            } catch (Throwable ex) {\n'
       '                Log.e("ALW_BOOT", "startup failure at " + bootStage, ex);\n'
       '                String details = String.valueOf(ex.getMessage()).replace((char) 10, (char) 32).replace((char) 13, (char) 32);\n'
       '                if (details.length() > 220) details = details.substring(0, 220);\n'
       '                uiError("진단 D4 | 오류 단계 [" + bootStage + "] " + ex.getClass().getSimpleName() + ": " + details);\n'
       '            }')
    path.write_text(s,encoding="utf-8")
    assert s.count("진단 D4") >= 7
    print("ANDROID_BOOT_DIAGNOSTICS_PATCH=PASS")

if __name__=="__main__":
    main()
