"""Prepare a separate, non-debuggable consent-test application before offline staging."""
from pathlib import Path
import shutil
import sys

from stage_rana_dialogue import replace

source, target = map(Path, sys.argv[1:])
shutil.copytree(source / "android_native", target)
app = target / "app"
main = app / "src/main"
fixtures = Path(__file__).parent / "plan_check"
package = Path("com/ailivingworld/mobile")
identity = target / "plan-identity"
classes = identity / "src/main/java" / package
classes.mkdir(parents=True)
shutil.copy(fixtures / "PlanIdentity.java", classes)
shutil.copy(fixtures / "PlanAuthHttp.java", classes)
shutil.copy(fixtures / "android_auth_http.py", main / "python")
tests = identity / "src/test/java" / package
tests.mkdir(parents=True, exist_ok=True)
shutil.copy(fixtures / "PlanIdentityTest.java", tests)
with (target / "settings.gradle").open("a") as settings:
    settings.write("\ninclude ':plan-identity'\n")
(identity / "build.gradle").write_text("""plugins { id 'java-library' }
dependencies {
    implementation 'com.nimbusds:nimbus-jose-jwt:10.10'
    testImplementation 'junit:junit:4.13.2'
}
java {
    sourceCompatibility = JavaVersion.VERSION_17
    targetCompatibility = JavaVersion.VERSION_17
}
""")
gradle = app / "build.gradle"
replace(gradle, "applicationId 'com.ailivingworld.mobile'", "applicationId 'com.ailivingworld.mobile.plancheck'")
replace(gradle, "    compileOptions {", """    buildTypes {
        release {
            debuggable false
            signingConfig signingConfigs.debug
        }
    }
    compileOptions {""")
start = gradle.read_text().index('        pip {')
end = gradle.read_text().index('        }',start) + len('        }')
gradle.write_text(gradle.read_text()[:start] + gradle.read_text()[end:] + """
dependencies {
    implementation project(':plan-identity')
}
""")
replace(main/"res/xml/network_security_config.xml", "<domain>127.0.0.1</domain>",
        '<domain includeSubdomains="false">127.0.0.1</domain>')
replace(main/"AndroidManifest.xml", 'android:label="AI Living World"', 'android:label="라나 구독 연결 확인"')
java = main / "java" / package / "MainActivity.java"
replace(java, 'login.setText("로그인")', 'login.setText("Continue with ChatGPT")')
replace(java, 'webView = new WebView(this);', 'webView = new WebView(this);\n        webView.setWebChromeClient(new android.webkit.WebChromeClient());')
replace(java, '비공식 DEMO · 실제 저장 여부는 게임의 rev로 확인해', '구독 연결 확인용 · 모델 요청마다 승인')
from subprocess import run
run([sys.executable, str(fixtures.parent/"patch_android_debug_ui.py"), str(java)], check=True)
client = main / "python/siwc_client.py"
s = client.read_text()
a = s.index("    \"\"\"Validate OIDC signature", s.index("def validate_identity("))
b = s.index("def exchange_authorization_code", a)
client.write_text(s[:a] + '''    from java import jclass
    try:
        verifier = jclass("com.ailivingworld.mobile.PlanIdentity")
        subject = verifier.verify(id_token, client_id, nonce, json.dumps(jwks))
        return {"subject": str(subject), "email": ""}
    except Exception:
        raise SIWCError("ID-token verification failed") from None


''' + s[b:])
replace(client, 'with urllib.request.urlopen(request, timeout=timeout) as response:',
        'from connect_once import _NoRedirect\n        with urllib.request.build_opener(_NoRedirect()).open(request, timeout=timeout) as response:')

replace(client, '    headers = {"Accept": "application/json"}',
        '    if url.startswith(AUTH_BASE + "/") and bearer is None:\n'
        '        from android_auth_http import request as auth_request\n'
        '        return auth_request(url, data, timeout)\n'
        '    headers = {"Accept": "application/json"}')

# Provide a reference for comparison against ChatGPT's account-side usage entry.
js = main / "assets/web/app.js"
replace(js, "      renderScene(result);\n      $('free-input').value='';", """      renderScene(result);
      if (app.connected && submission.rana_speech) {
        $('model-tag').textContent = model+' · 대화 '+result.world.revision+' · '+new Date().toLocaleTimeString('ko-KR');
      }
      $('free-input').value='';""")

shutil.copy(fixtures / "android_plan_login.py", main / "python")
replace(java, 'getModule("mobile_embedded");\n                module.callAttr("login",getFilesDir().getCanonicalPath(),this);\n                uiError("인증 확인 완료. GPT 플레이를 눌러줘.");',
        'getModule("android_plan_login");\n                uiError(module.callAttr("login",getFilesDir().getCanonicalPath(),this).toString());')

replace(java, "    private void doLogin()", """    private final Object resumeLock = new Object();
    private boolean resumed;

    @Override protected void onResume() {
        super.onResume();
        synchronized (resumeLock) {
            resumed = true;
            resumeLock.notifyAll();
        }
    }
    @Override protected void onPause() {
        synchronized (resumeLock) { resumed = false; }
        super.onPause();
    }
    public boolean awaitGameResume() throws InterruptedException {
        long deadline = android.os.SystemClock.elapsedRealtime() + 90000;
        synchronized (resumeLock) {
            while (!resumed) {
                long remaining = deadline - android.os.SystemClock.elapsedRealtime();
                if (remaining <= 0) return false;
                resumeLock.wait(remaining);
            }
            return true;
        }
    }
    private void doLogin()""")

# Keep account controls reachable without permanently shrinking the illustrated scene.
replace(java, '        root.addView(bar);', '''        final android.widget.LinearLayout header = new LinearLayout(this);
        header.setGravity(android.view.Gravity.CENTER_VERTICAL);
        header.setBackgroundColor(0xff182921);
        android.widget.TextView title = new TextView(this);
        title.setText("AI Living World");
        title.setTextColor(0xfff4edda);
        title.setTypeface(android.graphics.Typeface.SERIF);
        title.setTextSize(17);
        title.setPadding(Math.round(16*density), 0, 0, 0);
        header.addView(title, new LinearLayout.LayoutParams(0, -2, 1));
        Button account = new Button(this, null, android.R.attr.borderlessButtonStyle);
        account.setText("연결 설정");
        account.setTextColor(0xfff4edda);
        account.setOnClickListener(v -> new android.app.AlertDialog.Builder(this)
            .setTitle("연결 설정")
            .setItems(new String[]{"Continue with ChatGPT", "GPT 플레이", "화면 시험"},
                (dialog, item) -> { if (item == 0) login.performClick();
                    else if (item == 1) online.performClick(); else offline.performClick(); })
            .setNegativeButton("닫기", null).show());
        header.addView(account);
        root.addView(header, new LinearLayout.LayoutParams(-1, Math.round(48*density)));''')
replace(java, 'root.addView(status,new LinearLayout.LayoutParams(-1,statusHeight));',
        'status.setVisibility(android.view.View.GONE);\n        root.addView(status,new LinearLayout.LayoutParams(-1,-2));')
replace(java, 'status.setText("구독 연결 확인용 · 모델 요청마다 승인");',
        'status.setVisibility(android.view.View.GONE);')
replace(java, 'runOnUiThread(() -> status.setText(message));',
        'runOnUiThread(() -> {status.setText(message); status.setVisibility(android.view.View.VISIBLE);});')
web = main / "assets/web"
with (web/"style.css").open("a") as css:
    css.write("\n" + (fixtures/"scene.css").read_text())
html = web/"index.html"
replace(html, '<span class="model-tag" id="model-tag">연결 확인 중</span>', '')
replace(html, '<span id="rev">rev —</span>', '')
replace(html, '</select></div>', '</select><span id="model-tag">연결 확인 중</span><span id="rev">rev —</span></div>')
replace(js, "const travelSummary=document.createElement('summary');",
        """for (const id of ['choices-toggle', 'free-toggle']) {
        $(id).addEventListener('click', () => { travelActions.open = false; });
      }
      const travelSummary=document.createElement('summary');""")
for error in ('이동 실패', '시간 진행 실패'):
    anchor = f"if (!res.ok) throw new Error(data.error||'{error}');"
    replace(js, anchor, anchor + "\n          travelActions.open=false;")
replace(main/"python/android_plan_login.py", "인증 확인 완료. GPT 플레이를 눌러줘.",
        "인증 확인 완료. 연결 설정에서 GPT 플레이를 눌러줘.")
