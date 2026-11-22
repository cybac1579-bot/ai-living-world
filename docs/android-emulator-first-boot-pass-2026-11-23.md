# Android x86_64 에뮬레이터 첫 실행 성공과 시각 검증 증거 보존 — 2026-11-23

## 재조회한 기준
- 시작 main: `e9bd48be838e6fa3a54ec6ff8342808c099fc877`.
- 확인된 실행: [Android runtime emulator smoke #45048239566](https://github.com/cybac1579-bot/ai-living-world/actions/runs/45048239566), 최종 **success** (2026-11-22 17:13 UTC 시작).
- 실행 job `137287433742`의 `Compile x86_64 debug APK for emulator` 및 `Boot Android 15 emulator and check local world startup` 단계 **success**.
- 로그 근거: `WebView pageFinished`, `EMULATOR_PRESENTATION_UI=PASS`, `EMULATOR_WEBVIEW_PAGE_FINISHED=PASS`, `EMULATOR_BOOT_SMOKE=PASS`. `alw-screen.png` 스크린샷도 adb로 수집(341137 bytes).
- 이전 #45042332320 / #45042324752의 부팅 실패와 달리 이번에는 **에뮬레이터 자체가 부팅되고 앱의 WebView 페이지 완료 신호까지 확인**되었다.
- 열린 이슈 #1: 실기기 D4 시작 화면 확인 이후 온라인 GPT/장기 테스트 미완료.

## 이번 변경
- `.github/workflows/android-runtime-emulator.yml`에 `actions/upload-artifact@v4` 단계 추가.
- 오프라인 x86_64 에뮬레이터 실행 시 캡처한 `alw-screen.png`, UI XML, `ALW_BOOT` 로그를 `android-emulator-visual-smoke` 아티팩트로 최대 3일 보관.
- `if: always()`로 실행 실패 시 수집된 부분 진단도 남기고, `if-no-files-found: warn`으로 파일 미생성 상황을 기록한다.
- 이 변경은 테스트 증거 보존만 다룬다. 인증, 토큰, 유료 API 키, 온라인 로그인/GPT 기능은 변경하지 않는다.

## 검증 범위와 한계
- **실제 성공**: Android 15 x86_64 에뮬레이터 부팅, APK 설치/앱 시작, WebView `pageFinished`, 개발용 진단 상단바 숨김(네이티브 UI XML 검사), 크래시 탐지 스모크 통과.
- **아직 미검증**: 캡처 이미지에 실제 숲 장면과 대사창이 올바르게 렌더링됐는지 시각 판독. WebView `pageFinished`만으로 이를 증명할 수 없음. 새 아티팩트 업로드 단계도 다음 CI 결과 확인 필요.
- **별도 미검증**: Galaxy S25+ 최신 변경 빌드, 세로 UX 장시간 테스트, 온라인 인증/암호화, 실제 GPT 대화, NPC 기억/선택/사건 인과/저장·복원, 20~30분 플레이.
- Android 온라인 버튼은 보안 검증 및 사용자 승인 전까지 비활성화 상태 유지.

## 다음 우선순위
1. 신규 CI 실행의 아티팩트 업로드 결과 확인 및 `alw-screen.png` 시각 점검. 화면이 비거나 검정색이면 앱의 렌더링 원인을 먼저 분석.
2. 실제 화면 기준으로 세로 비주얼 노벨 UI(화자 이름, 은은한 인물별 대사창, 상황 묘사 분리, 디버그 UI 비노출) 확인.
3. 저장/복원·자유 입력·선택지와 NPC 기억·인과를 실제 루프로 연결. 온라인 인증/GPT는 별도 보안 승인 전 차단.

## 진행률
- 첫 AI 플레이본 **약 40% (보수적 기능 범위 추정, 실제 플레이 완료율 아님)**.
- 남은 큰 작업 **6개 범주**: Android 반복 실행/시각 검증, 세로 UX/저장, 인증·보안·GPT, NPC 기억·선택·자유 입력, 20~30분 사건 수직 슬라이스, 실기기 장시간 검증.
