# Android emulator smoke alignment — 2026-11-23

## 확인된 출발 상태
- 최근 offline APK CI는 성공한 실행이 있었으나, Android 에뮬레이터 워크플로는 이전 실행에서 실패함.
- 실기기 Galaxy S25+에서 D4 진단 APK의 숲 배경/대사창 표시가 사용자에 의해 확인됨. 이것은 GPT 온라인 플레이, 저장 복원, 장시간 플레이 성공을 의미하지 않음.
- 최신 offline APK 빌드 파이프라인은 D4 진단 UI에 **presentation UI patch**를 적용해 정상 화면에서는 진단 상단바를 숨기지만, emulator 워크플로는 해당 패치를 누락하고 기존 D4 상단바 노출을 성공 조건으로 검사했음. 두 빌드는 서로 다른 UI를 검증하고 있었음.

## 이번 변경
1. `.github/workflows/android-runtime-emulator.yml`에 presentation patch 적용을 추가. 관련 패치 파일 변경 시 워크플로가 다시 실행되도록 트리거 추가.
2. `tools/android_emulator_smoke.sh`는 성공 화면에 진단 상단바가 없어야 한다고 검사. WebView 페이지 완료 여부는 UI의 '단계 5' 텍스트 대신 `ALW_BOOT: WebView pageFinished` 로그로 검사.
3. 진단 오류 문구, AndroidRuntime 충돌 로그, 스크린샷 수집은 유지. WebView pageFinished 로그만으로 숲 장면의 실제 렌더링이나 플레이 가능성을 증명하지 못한다는 한계를 명시.

## 검증 기준 및 주의
- GitHub 커밋과 YAML/스크립트 내용 검사는 수행 가능. 실제 에뮬레이터 부팅/실행 PASS는 Actions 결과를 확인해야만 주장할 수 있음.
- Android 온라인 로그인/GPT는 계속 비활성화. 비밀키/토큰 추가, 유료 API 연동, 인증 범위 확대 없음.
- 남성 NPC 개별 일러스트는 만들지 않고 텍스트 외형만 관리. `docs/art/character-illustration-policy.md` 참조.
- 라나/촌장 설정은 각각 `docs/characters/rana-v0.5.md`, `docs/characters/village-chief-v0.2.md` 참조.

## 남은 큰 작업 (6개)
1. Android 에뮬레이터 CI 실행 성공 및 숲 장면 스크린샷 확인
2. Galaxy S25+ 세로 UI·키보드·저장/복원 실기기 검증
3. Android 인증/암호화 보안 검증 및 승인된 온라인 GPT 연결
4. 실제 NPC 선택지·자유입력·기억·자율성·행동 승인 루프 통합
5. 사건 1개와 여러 NPC를 포함하는 20~30분 분량 수직 슬라이스
6. 장시간 플레이/회귀 테스트와 UX 안정화

## 다음 우선순위
- 새 Android emulator workflow 실행 결과의 실패 단계/로그를 먼저 확인하고 에뮬레이터 부팅 문제면 부팅 진단을 분리.
- 렌더링 검증이 가능해지면 UI/저장 복원에 집중. 온라인 GPT 버튼은 보안 검증 전까지 계속 비활성화.
- 진행률은 **약 40% (낮은 신뢰도의 목표 기반 추정)**로 유지. APK 컴파일과 D4 실기기 장면 확인을 첫 AI 플레이본 완성으로 오인하지 말 것.
