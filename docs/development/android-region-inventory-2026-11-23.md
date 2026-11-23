# Android 기존 지역 구조 확인 — 2026-11-23

출처: GitHub Actions `AI Living World stability gates`, run 45104964491, `android-source-inventory` job 137464056053. 원본 ZIP `source/AI_Living_World_Android_v1.3.zip`을 풀어 `tools/inspect_android_brena_regions.py` 실행.

## 검증된 원본 초기 상태

- Fixture: `live_demo_world.json`
- `DEMO-CAMP` — 테스트 야영지; 이웃 `DEMO-FOREST`
- `DEMO-FOREST` — 테스트 숲; 이웃 `DEMO-CAMP`
- `DEMO-GUIDE` NPC — `DEMO-FOREST`
- 플레이어 시작 위치 — `DEMO-FOREST`

## 통합 결정

이 데이터는 **테스트용 2개 지역**이다. 확정 브레나 장소 6곳(광장·잡화점·여관·대장간·촌장 집·경비대 훈련장)과 대응하지 않는다. 따라서 `DEMO-CAMP`나 `DEMO-FOREST`를 브레나 장소로 이름만 바꿔 사용하지 않는다.

실제 1차 플레이본에는 원본 엔진의 `validate_state`를 통과하는 **별도의 브레나 초기 세계 데이터**, 각 장소의 고유 지역 ID, 연결 그래프, 플레이어 시작 위치, NPC 위치가 필요하다. 이후 `EventStore` 생성·이동·저장·재실행 회귀 검사를 통과시켜야 한다.

이는 **세계관 변경이 아닌 기술적 확인**이며, 실제 브레나 초기 데이터 생성이나 Android 런타임 적용이 완료됐다는 뜻이 아니다.
