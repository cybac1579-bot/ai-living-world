"""Apply offline-only restrictions to the unpacked Android debug build."""
from pathlib import Path
java = Path("src/android_native/app/src/main/java/com/ailivingworld/mobile/MainActivity.java")
s = java.read_text(encoding="utf-8")
before = 'login.setOnClickListener(v -> doLogin());'
assert s.count(before) == 1, 'Unexpected login button implementation'
s = s.replace(before, 'login.setOnClickListener(v -> uiError("오프라인 테스트 APK: 로그인 비활성화"));')
before = 'online.setOnClickListener(v -> startEngine(false));'
assert s.count(before) == 1, 'Unexpected GPT button implementation'
s = s.replace(before, 'online.setOnClickListener(v -> uiError("오프라인 테스트 APK: GPT 호출 비활성화"));')
before = 'bar.addView(offline,new LinearLayout.LayoutParams(0, 56, 1f));'
assert s.count(before) == 1, 'Unexpected button layout'
s = s.replace(before, 'login.setEnabled(false); online.setEnabled(false);\n        ' + before)
java.write_text(s, encoding="utf-8")

# No outdated Android native cryptography libraries ship in the offline-only APK.
gradle = Path("src/android_native/app/build.gradle")
g = gradle.read_text(encoding="utf-8")
for dep in ("install 'PyJWT[crypto]==2.15.1'", "install 'cryptography==42.0.8'", "install 'cffi==1.17.1'"):
    assert g.count(dep) == 1, f"Unexpected dependency: {dep}"
g = g.replace("install 'PyJWT[crypto]==2.15.1'", "install 'PyJWT==2.15.1'")
g = g.replace("install 'cryptography==42.0.8'", "// Omitted: login disabled in offline-only APK")
g = g.replace("install 'cffi==1.17.1'", "// Omitted: login disabled in offline-only APK")
gradle.write_text(g, encoding="utf-8")
assert "login.setEnabled(false); online.setEnabled(false);" in java.read_text(encoding="utf-8")
assert "install 'cryptography==" not in gradle.read_text(encoding="utf-8")
print("OFFLINE_ONLY_MODE=enabled; no live ChatGPT authentication available in this APK")
