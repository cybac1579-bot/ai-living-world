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
