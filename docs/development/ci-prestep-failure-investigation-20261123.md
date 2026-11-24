# CI 실행 이전 장애 조사 — 2026-11-23 16:13 KST

## 확인 범위
- 기준: main의 PROJECT_SOURCE_OF_TRUTH 및 연결된 세계·브레나·라나·관계·첫 플레이본 문서 직접 재조회. 세계관 설정 변경 없음.
- PR #2 head: fa008bd77a61725ca042dcff3c4d63ac83a80f05 (조사 시작 시점).
- 해당 커밋의 Actions: Brena offline prototype regression 45117896482 실패, stability gates 45117896548 실패.
- 전자는 regression 1개, 후자는 original-engine-regression / android-source-inventory / APK compile / python-prototype 4개 모두 failure.
- 작업 조회 결과 각 job의 steps와 logs_url이 null. job 137504817845 로그 직접 조회도 GitHub 404 BlobNotFound.
- 따라서 어떤 테스트 명령이 실제 시작되었는지, 실패 원인이 코드인지 Actions 인프라인지 **판별 불가**. 실패를 테스트 실패의 증거 또는 테스트 통과의 증거로 오인하지 않는다.
- 과거 보고에 나온 저장공간/아티팩트 할당량 문제와 이번 실패의 인과관계는 아직 입증되지 않았다.

## 안전한 다음 검증
1. GitHub Actions 서비스/계정의 실행 제한 및 결제·사용량, job 생성 시각/러너 할당 여부를 GitHub UI에서 확인한다. 원인 확인 전 무한 재실행 금지.
2. CI와 별개로 원본 Android ZIP의 EventStore 및 /api/state 연결을 검증하고, 동일 장소·다른 장소·위치 불명 상태에서 NPC 정보 비노출 테스트를 수행한다.
3. Android 원본 플레이어 위치의 실제 스키마를 검증하기 전, 클라이언트 입력이나 임의 위치 값을 서버의 권위 있는 위치로 사용하지 않는다.
4. CI 복구 후 전체 회귀/Android APK 빌드/가능한 실행 검사 각각 통과를 확인한 뒤 PR 병합을 판단한다.

## 상태 구분
- 문서 재조회·job 메타데이터 조회: 완료.
- 코드 변경: 없음.
- CI: 실패 (원인 미확정).
- Android 실행: 미검증.
- GPT 연동: 비활성화 유지.
- PR #2: main 병합 보류.

## 17:10 KST 추가 검증 — 실행 단계 없는 실패와 실제 부팅 실패 구분
- main 최신 검색 결과: `acb612f7ea08775cbbac3f4ac4969af49b6b1e53` (이 조사 시점). 정본 및 연결된 세계·라나·브레나·관계·첫 플레이본 문서 재조회; 설정 변경 없음.
- GitHub API 재조회: run [45117896482](https://github.com/cybac1579-bot/ai-living-world/actions/runs/45117896482)의 regression 1개와 run [45117896548](https://github.com/cybac1579-bot/ai-living-world/actions/runs/45117896548)의 4개 job 모두 `completed/failure`이나, 반환된 job에는 실행 단계 목록이 없음. 이는 Python/Gradle 테스트 명령의 실패 증거가 아니다.
- 대조군: 과거 [45071336100](https://github.com/cybac1579-bot/ai-living-world/actions/runs/45071336100)에서는 checkout, SDK 설정, x86_64 APK 컴파일까지 **실제 단계별 성공**했고 `Boot Android 15 emulator` 단계에서 실패했다. 진단 아티팩트 업로드도 실패했다. 따라서 이 과거 실행의 부팅 실패와 이번 5개 job의 실행 전 단계 불명 실패를 하나의 원인으로 단정할 수 없다.
- 안전한 운영 판단: **새 PR 병합/CI 통과 선언 보류**, 기존 Android 온라인 로그인·GPT 비활성화 유지. 동일 실패를 무작정 재실행하지 않고 Actions 사용량·계정 제한·러너 할당 상태를 우선 확인한다. 그동안 Android 원본 엔진의 `/api/state` 위치/지식 경계 검증은 CI와 독립적으로 진행한다.
- 이번 변경은 조사 기록만 추가. 코드 변경 없음, 신규 테스트 실행 없음, Android 실제 실행 미검증. 원본 엔진·저장 스키마·세계관에 영향 없음.
