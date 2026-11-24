# 2026-11-23 — Android /api/state 지식 경계 연결 감사 (11:13 KST)

## 기준 확인
main `acb612f7ea08775cbbac3f4ac4969af49b6b1e53`의 PROJECT_SOURCE_OF_TRUTH 및 세계·브레나·라나·첫 플레이본·장기관계·관계 구조 정본을 직접 재조회했다. 세계관 확정값 변경 없음. PR #2는 main 미병합 상태이며 본 문서는 개발 브랜치에서만 작성한다.

## 실제 코드 경로 대조
- `tools/patch_brena_vn_state.py`는 원본 서버의 `render_contract(engine_state)` 직후 `rana_status_payload(engine_state)`를 호출하여 `/api/state`에 `brena.rana`를 추가한다.
- `prototype/brena_presentation_payload.py`는 `player_place=None`일 때 위치·활동 필드를 모두 `None`으로 마스킹한다.
- 따라서 **현재 연결 경로에서는 player_place가 전달되지 않아 라나 활동 배지가 항상 숨겨지는 기능적 결함**이 있다. 이는 원격 NPC 노출 방지와 별개로 정상적인 동일 장소 표시도 불가능하게 한다.
- `tools/patch_brena_vn_ui.py`는 `player_present===true`와 활동·장소 값이 모두 있어야 배지를 표시한다.
- `prototype/brena_engine_clock_bridge.py`는 `world_minutes`로 읽기 전용 원형을 재구성한다. 원본 엔진의 NPC 상태가 권위 있는 단일 데이터인지, 원형 투영과 어긋날 수 있는지 통합 검증 필요.
- `render_contract(engine_state)`의 전체 원본 응답과 다른 API 경로의 내부 정보 노출은 이번 조회만으로 확인할 수 없다. **API 전체 보안 통과 아님**.

## 수정 전 필수 검증 조건
1. 원본 엔진의 플레이어 위치 키와 실제 브레나 장소 ID 매핑을 ZIP에서 확인한다. 이름만 보고 임의 추론하지 않는다.
2. 서버에서 검증된 현재 플레이어 위치를 전달하되, 미지정·불명확·불일치 시 비노출 기본값을 유지한다.
3. 동일 장소 / 다른 장소 / 위치 미지정 / 악의적 클라이언트 위치 주장 각각의 API 응답 테스트를 추가한다. 클라이언트 제공 위치를 신뢰하지 않는다.
4. 원본 `render_contract`가 숨겨진 NPC 위치·활동을 노출하는지 별도로 검사한다.
5. 저장/복원, 명시적 시간 진행, 플레이어 발언·이동 비생성 회귀 검증 및 Android 빌드·실행을 분리 보고한다.

## 상태
이번 변경은 **코드 수정이 아닌 근거 기반 결함 기록**이다. 정적 코드 읽기 완료. 테스트 실행/CI/Android 실제 실행: 이번 변경에 대해 미검증. 온라인 인증·GPT 비활성화 유지. 사용자 확정 세계관 변경 없음.

## 다음 작업
원본 ZIP의 `vn_server.py`, `world_engine` 및 실제 `/api/state` 응답을 검사한 뒤 안전한 위치 매핑을 구현하고 API 통합 테스트를 작성한다. 검증 전 PR #2를 main에 병합하지 않는다.
