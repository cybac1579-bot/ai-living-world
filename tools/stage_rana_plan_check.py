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
shutil.copy(fixtures / "PlanIdentity.java", main / "java" / package)
tests = app / "src/test/java" / package
tests.mkdir(parents=True, exist_ok=True)
shutil.copy(fixtures / "PlanIdentityTest.java", tests)
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
    implementation 'com.nimbusds:nimbus-jose-jwt:10.10'
    testImplementation 'junit:junit:4.13.2'
}
""")
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
