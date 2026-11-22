# Android 에뮬레이터 부팅 실패 진단 및 재검증 — 2026-11-23

## 기준과 근거
- 확인 당시 main: `00208540477679fe92df0f22ab7d429f2b46ade3` (라나 시트 문서 변경; Android 실행 성공을 뜻하지 않음).
- 이전 실행: [45042332320](https://github.com/cybac1579-bot/ai-living-world/actions/runs/45042332320) 및 [45042324752](https://github.com/cybac1579-bot/ai-living-world/actions/runs/45042324752), 둘 다 **failure**.
- 45042332320의 `Launch offline world on Android x86_64 emulator`: 소스 압축 해제·패치, Gradle `assembleDebug`, KVM 설정은 성공. `Boot Android 15 emulator and check local world startup` 단계에서 실패.
- 로그에는 `adb: device 'emulator-5554' not found`, `could not connect to TCP port 5554: Connection refused`, `Timeout waiting for emulator to boot.` 확인. 따라서 **APK의 앱 코드 충돌로 판단할 근거는 없음**. Android 시스템 자체가 부팅되지 않아 `tools/android_emulator_smoke.sh` 검증이 실행되지 못함.
- arm64 실기기에서 숲/대사창 표시를 확인한 과거 D4 수동 테스트와 x86_64 CI 에뮬레이터 실행은 별개의 검증이다.

## 이번 조치
- `.github/workflows/android-runtime-emulator.yml`의 에뮬레이터 GPU 옵션을 `-gpu swiftshader_indirect`에서 `-gpu swiftshader`로 변경하고 `-no-metrics` 추가.
- `emulator-boot-timeout: 900` 명시, `disable-animations: true` 적용. API 35, x86_64, google_apis, 앱 코드 및 온라인 기능 차단은 그대로.
- 가설: 호스티드 Ubuntu의 그래픽 에뮬레이션/부팅 지연이 문제일 수 있음. **원인 확정이나 해결 성공은 아님**. 새로운 GitHub Actions 실행 결과를 확인해야 한다.

## 후속 검증
1. 이번 워크플로 변경으로 시작된 CI 실행의 최종 결과 확인.
2. 에뮬레이터가 부팅되면 `EMULATOR_WEBVIEW_PAGE_FINISHED`, `EMULATOR_PRESENTATION_UI`, `EMULATOR_BOOT_SMOKE` 로그 확인. 단, WebView `pageFinished`만으로 장면이 보인다고 단정하지 않음.
3. 여전히 부팅 실패 시 에뮬레이터 표준 출력의 치명 오류·KVM 가속·AVD 이미지 확인. 실패를 앱의 실행 실패로 혼동하지 말고, 동시에 정적/오프라인 UI 검증을 진행.
4. 로그인·GPT 온라인 버튼은 별도 인증/암호화 검증 및 사용자 승인 전까지 계속 비활성화. 토큰을 소스나 CI 로그에 삽입하지 않음.

## 첫 AI 플레이본 진행 판단
- 기존 약 40%는 **기능 범위에 대한 임시 추정**일 뿐, 실제 GPT 대화·NPC 기억·사건 분기·장기 저장·20~30분 실기기 플레이의 통합 검증은 미완료.
- 남은 큰 범주 6개: Android 반복 실행, 세로 UX/저장 검증, 인증·보안·GPT 연결, NPC 기억·선택·자유 입력, 사건 수직 슬라이스, 실기기 장시간 검증.
