"""One consented GPT turn -> validate -> atomic append-only world commit.

Uses existing Sign in with ChatGPT OAuth. No API-key / paid fallback.
Canonical character sheets and production saves must not be used in demo mode.
"""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Callable

from ai_adapter import build_model_context, parse_ai_response, apply_ai_turn
from connect_once import CREDENTIALS_DIR, _NoRedirect, _safe_http_error
from siwc_client import (SIWCError, SCOPE_REQUIRED, read_credentials,
                         refresh_credentials, list_models, collect_response_events)
from world_engine import EventStore, WorldError, transition, render_contract, resolve_explicit_movement

API_URL = 'https://api.openai.com/v1/responses'
MAX_CONTEXT = 40000

SYSTEM_INSTRUCTIONS = """너는 AI Living World의 한국어 서사 엔진이야. 제시된 게임 상태를 벗어나지 마.
응답은 마크다운 없이 JSON 객체 하나만 작성해. 최상위 키는 events와 scene뿐이야.
형식 예시: {"events":[],"scene":{"id":"SCENE-NEXT-1","beats":[{"kind":"narration","text":"서술"},{"kind":"dialogue","speaker_id":"허용된NPC_ID","text":"인물 대사"}],"choices":[{"id":"c1","label":"행동","effect":{"type":"none"}}],"awaiting_player":true,"event_image_id":null,"character_image_id":null}}
- 각 장면에는 상황에 맞는 서술과 대사를 충분히 작성하되 군더더기는 피해. beats는 대략 3~7개를 우선 고려해.
- 대사 화자는 반드시 현재 장면 지역의 NPC ID여야 해. NPC가 없으면 서술만 작성해.
- 직접 입력한 플레이어의 문장과 의도를 존중하고 플레이어 감정/대사/행동을 임의로 추가하지 마.
- NPC 행동만 events로 기록해. events는 빈 배열이어도 돼. 플레이어 행동을 이벤트로 만들지 마.
- 인물의 능력/인격/기억/관계는 제공된 현재 상태만 참고해. 타인의 비밀을 알게 하지 마.
- NPC는 플레이어가 직접 말하거나 그 NPC가 자신의 위치에서 독립적으로 관찰하지 않은 사실을 자동으로 알게 되면 안 돼. 플레이어가 단지 돌아왔다는 이유로 이전 지역에서 발견한 단서를 NPC에게 말했다고 가정하지 마.
- 이미 발견한 단서를 NPC에게 직접 전해주었다면 authorized_clue_share의 npc_id/clue_id가 제시된 경우에만 events에 {"type":"clue_share","npc_id":"해당NPC","clue_id":"기존단서"}를 기록해. 권한 정보가 없으면 절대 만들지 마.
- repeated_no_discovery가 true이면 같은 설명을 되풀이하거나 가짜 단서를 만들지 말고, 이미 조사한 범위를 명시하고 다른 행동을 제안해.
- 새로운 지역, 인물, 이미지 ID를 임의로 등록하지 마. 이미 존재하는 ID만 사용해.
- 선택지는 2~4개 정도. 각 선택지 effect는 정확히 {"type":"none"} 또는 {"type":"player_move","destination":"이웃지역ID"} 둘 중 하나만 사용해.
- 둘러보기·조사·화덕 살피기·대화·기다리기·수색·물건 관찰 등 이동 없는 행동에는 반드시 {"type":"none"}을 사용해. inspect / look / search / talk / examine / interact / wait 같은 새로운 effect.type을 만들지 마.
- 이동 효과는 제공된 이웃 지역 ID로만 사용하고, 플레이어가 실제로 누르기 전에는 이동을 실행하지 마.
- 예시 choices: [{"id":"look","label":"화덕을 조사한다","effect":{"type":"none"}},{"id":"go","label":"테스트 숲으로 돌아간다","effect":{"type":"player_move","destination":"DEMO-FOREST"}}].
- player_submission이 choice_id이면 실제 선택의 효과는 엔진이 처리하니 중복 행동시키지 마.
- player_submission이 free_text인 경우 엔진이 selected_player_effect로 명시적으로 승인한 지역 이동만 확정돼. 그 외 위치/인벤토리/감정을 멋대로 바꾸지 마.
- 현재 지역의 이전 조사 기록 previous_actions_here와 already_explored_here를 반드시 참고해. 같은 화덕의 재/솔잎을 반복 묘사하지 마. 새로운 관찰이 없다면 정보가 더 없다고 명확히 말하고 다른 목적을 제시해.
- 플레이어가 실제로 발견한 현장의 새로운 사실이 있다면 events에 {"type":"clue_discover","id":"고유단서ID","region":"현재지역ID","title":"짧은 제목","detail":"관찰 가능한 사실"}를 추가해. 이미 알려진 단서는 다시 등록하지 마. 물건 획득이나 전투 승리 같은 플레이어 행동을 단서로 위장하지 마.
- 기존 인물·목표·지역 연결과 인과관계를 활용해 사건을 한 단계씩 진전시켜. 아무 근거 없는 새 지역/인물/비밀을 만들어 정답을 강요하지 마.
- 이미지가 없는 사건에서는 이미지가 있다고 말하지 마. JSON 밖 설명이나 코드펜스를 쓰지 마."""


def build_request(model: str, context: dict) -> dict:
    if not isinstance(model, str) or not model.strip():
        raise SIWCError('계정의 모델 목록에서 모델을 선택해야 해.')
    if not isinstance(context, dict) or not context.get('world_id'):
        raise WorldError('세계 문맥이 올바르지 않아.')
    serialized = json.dumps(context, ensure_ascii=False, separators=(',', ':'))
    if len(serialized) > MAX_CONTEXT:
        raise WorldError('현재 모델 문맥이 너무 커. 저장된 기억을 정리해야 해.')
    return {
        'model': model,
        'instructions': SYSTEM_INSTRUCTIONS,
        'input': [{'role': 'user', 'content': serialized}],
        'store': False,
        'stream': True,
    }


def request_story(access_token: str, model: str, context: dict, *, urlopen=None, timeout=120) -> str:
    """Use only a scope-authorized OAuth access token; completion is mandatory."""
    if not isinstance(access_token, str) or not access_token:
        raise SIWCError('ChatGPT 로그인 인증이 없어 요청하지 않았어.')
    payload = build_request(model, context)
    req = urllib.request.Request(
        API_URL, data=json.dumps(payload, ensure_ascii=False).encode('utf-8'),
        headers={'Authorization': 'Bearer ' + access_token,
                 'Content-Type': 'application/json', 'Accept': 'text/event-stream'},
        method='POST')
    opener = urlopen or urllib.request.build_opener(_NoRedirect()).open
    try:
        with opener(req, timeout=timeout) as response:
            text = collect_response_events(response)
            if not text.strip():
                raise SIWCError('실제 GPT 응답이 비어 있어 세계를 변경하지 않았어.')
            return text
    except urllib.error.HTTPError as exc:
        detail = _safe_http_error(exc)
        raise SIWCError(f'ChatGPT 플랜 사용량 요청 거부 ({detail}). 다른 유료 경로로 전환하지 않았어.') from None
    except (urllib.error.URLError, TimeoutError, UnicodeError):
        raise SIWCError('통신 오류로 요청을 완료하지 못했어. 세계 기록은 그대로야.') from None


def authorized_catalog(*, credentials_dir: str | Path = CREDENTIALS_DIR,
                       now: Callable[[], float] = time.time,
                       refresh=refresh_credentials, catalog=list_models):
    path = Path(credentials_dir) / 'credentials.json'
    if not path.is_file():
        raise SIWCError('로그인 정보가 없어. 먼저 기존 연결 검사에서 ChatGPT 로그인을 완료해줘.')
    credentials = read_credentials(path)
    if SCOPE_REQUIRED not in credentials.get('scopes', []):
        raise SIWCError('ChatGPT 구독 사용량 공유 권한이 없어 중단했어.')
    if credentials.get('expires_at', 0) <= now() + 60:
        credentials = refresh(path, credentials)
    models = catalog(credentials['access_token'])
    return credentials['access_token'], models


# These are NON-STATE-CHANGING proposals. The actual look/talk/inspection
# result is narrated by GPT only AFTER the player chooses the option.
# Everything with a persistent effect (moving, inventory, combat, flags)
# remains subject to the strict world_engine schema; no generic fallback.
READ_ONLY_CHOICE_EFFECTS = frozenset({
    'inspect', 'examine', 'observe', 'look', 'look_around', 'look_at',
    'inspect_area', 'examine_object', 'survey', 'search', 'investigate',
    'explore', 'explore_area', 'talk', 'speak', 'ask', 'wait', 'listen',
    'interact', 'inspect_environment', 'examine_area', 'survey_area',
    'inspect_object', 'observe_area', 'investigate_area', 'search_area',
})
READ_ONLY_HINT_KEYS = frozenset({'type', 'target', 'subject', 'object'})


def normalize_read_only_choices(proposal: dict) -> dict:
    """Repair *only* recognizable, effect-free model choice annotations.

    This routine never changes the player's submitted choice and never
    executes a mechanical effect. Unknown/mutating types are left intact,
    to be refused by the strict world validator. Returned data is the same
    canonical object later stored in the event journal for deterministic replay.
    """
    scene = proposal.get('scene')
    if not isinstance(scene, dict):
        return proposal
    choices = scene.get('choices')
    if not isinstance(choices, list):
        return proposal
    for choice in choices:
        if not isinstance(choice, dict):
            continue
        effect = choice.get('effect')
        if not isinstance(effect, dict):
            continue
        effect_type = effect.get('type')
        if not isinstance(effect_type, str) or (effect_type != 'none' and
                effect_type not in READ_ONLY_CHOICE_EFFECTS):
            continue
        if not set(effect).issubset(READ_ONLY_HINT_KEYS):
            continue
        if not all(isinstance(v, str) and 0 < len(v) <= 160
                   for k, v in effect.items() if k != 'type'):
            continue
        choice['effect'] = {'type': 'none'}
    return proposal


def verify_proposed_turn(state: dict, submission: dict, raw: str) -> dict:
    """Reject unsafe model JSON before any commit.

    Model may move an NPC via validated events.  Dialogue must originate from
    a character present in the resulting scene's location, not a remote secret.
    """
    proposal = normalize_read_only_choices(parse_ai_response(raw))
    prospective = transition(state, submission, proposal, mode='player')
    region = prospective['player']['location']
    # A model may only affect NPCs whose facts were made available in this turn.
    context = build_model_context(state, submission=submission)
    visible_ids = {n['id'] for n in context['local_npcs']}
    for evt in proposal['events']:
        if evt['type'].startswith('npc_') and evt.get('npc_id') not in visible_ids:
            raise WorldError('현재 장면의 바깥에 있는 NPC 상태 변경을 차단했어.')
        if evt['type'] == 'npc_move':
            origin = state['npcs'][evt['npc_id']]['location']
            if evt['destination'] not in state['regions'][origin].get('neighbors', []):
                raise WorldError('AI가 연결되지 않은 지역으로 NPC를 순간이동시키려 했어.')
    for choice in prospective['scene'].get('choices', []):
        effect = choice.get('effect') or {}
        if effect.get('type') == 'player_move':
            if effect['destination'] not in prospective['regions'][region].get('neighbors', []):
                raise WorldError('AI가 연결되지 않은 지역을 이동 선택지로 만들었어.')
    for beat in prospective['scene']['beats']:
        if beat['kind'] == 'dialogue':
            npc = prospective['npcs'][beat['speaker_id']]
            if npc['location'] != region:
                raise WorldError('다른 지역에 있는 인물의 대사가 표시되어 검증을 중단했어.')
    # A cutscene must refer to the registered image type or explicitly be empty.
    for key, kind in (('event_image_id', 'event'), ('character_image_id', 'character')):
        image_id = prospective['scene'].get(key)
        if image_id is not None:
            asset = prospective['images'].get(image_id)
            if asset is None or asset['type'] != kind:
                raise WorldError('등록되지 않은 사건/인물 이미지를 AI가 지정했어.')
    return proposal


def run_turn(store: EventStore, *, submission: dict, model: str,
             token: str, sender=request_story) -> dict:
    """One and only one AI call. Never auto-retry or commit on invalid output."""
    state = store.load()
    revision = state['revision']
    # Explicit free-text movements are allowed ONLY for recognized adjacent
    # destinations, and checked before making a billable model request.
    if set(submission) == {"free_text"}:
        dest = resolve_explicit_movement(state, submission["free_text"])
        if dest is not None:
            submission = {"free_text": submission["free_text"], "move_to": dest}
    # Preflight prevents calling model for stale/invalid choices and decides
    # which location's NPC knowledge may be passed to model.
    context = build_model_context(state, submission=submission)
    text = sender(token, model, context)
    validated = verify_proposed_turn(state, submission, text)
    # apply_ai_turn re-parses and EventStore checks revision under file lock.
    rendered = apply_ai_turn(store, expected_revision=revision, submission=submission,
                             ai_response=json.dumps(validated, ensure_ascii=False))
    return rendered


def initial_demo_store(path: Path, *, sample_file: Path) -> EventStore:
    """Creates only a separate DEMO world. Never writes official Drive canon."""
    store = EventStore(path)
    if not store.initial.exists():
        if store.journal.exists():
            raise WorldError('기존 사건 기록이 있는데 최초 저장이 없어 안전하게 중단했어.')
        obj = json.loads(sample_file.read_text(encoding='utf-8'))
        if not str(obj.get('world_id', '')).startswith('DEMO-'):
            raise WorldError('비공식 테스트 세계 파일만 사용할 수 있어.')
        store.create(obj)
    state = store.load()
    if not str(state.get('world_id', '')).startswith('DEMO-'):
        raise WorldError('현재 실행기는 비공식 시험 세계 전용이야.')
    return store
