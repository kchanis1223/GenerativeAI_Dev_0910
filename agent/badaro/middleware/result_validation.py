"""이전 설계의 ResultValidation — 정확성 회귀 테스트용으로 유지한다.

현재 v2 Agent에는 등록하지 않는다. 현재 결과 검증은 tools/optimize_dispatch.py,
구조화 결과 표시는 runtime/graph.py와 agent.py에서 처리한다.

TMS 결과와 최종 설명의 차량·방문 순서·시간·미배정 정보를 대조한다.
불일치는 1회 재생성하고, 재검증에도 실패하면 구조화 오류를 반환한다.

배차 사실의 기준은 DispatchResult.routes 다. 가용 차량 목록에 있다는 이유만으로 인정하지 않는다.
도착시간은 존재 여부가 아니라 값을 대조한다. TMS 가 반환하지 않은 시각은 통과시키지 않는다.

차량 ID 는 형식을 가정하지 않는다. 샘플 데이터의 LIVE01·COLD02·GENERAL01 처럼
접두어+번호 형태와 V-01, "2번차" 표기를 모두 후보로 잡은 뒤 routes 와 대조한다.
"""
from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from ._compat import after_model, ai_message

MAX_REGENERATE = 1
RETRY_KEY = "result_validation_retries"

VEHICLE_TOKEN_RE = re.compile(r"\b[A-Z]{2,12}\d{1,3}\b|\b[Vv]-\d{1,3}\b|\d{1,2}\s*번\s*차")
CLOCK_RE = re.compile(r"\b([01]?\d|2[0-3]):([0-5]\d)\b")
DURATION_RE = re.compile(r"\d+\s*분\s*(소요|후|뒤)")
COMPLETE_RE = re.compile(r"(전체|모두|전부|다)\s*(배정|완료|처리)|빠짐없이")
GUARANTEE_RE = re.compile(r"(보장|확실|반드시|틀림없)")
CONFIRMED_RE = re.compile(
    r"(확정(했|됐|되었|입니다|합니다))|배차\s*완료|기사(님)?(에게|께)\s*(전달|배포)"
)
HEDGE_RE = re.compile(r"사전검증|TMS\s*미보장|미보장|정보\s*없음")
PENDING_RE = re.compile(r"(승인\s*대기|확정\s*전|아직\s*확정)")


def as_dict(obj: Any) -> dict[str, Any]:
    """pydantic 모델과 dict 를 같은 형태로 다룬다."""
    if obj is None:
        return {}
    if isinstance(obj, dict):
        return obj
    dump = getattr(obj, "model_dump", None)
    return dump(mode="json") if callable(dump) else {}


def _hhmm(value: Any) -> str | None:
    """ISO 문자열·datetime·'HH:MM' 을 'HH:MM' 으로 통일한다. 해석 불가면 None.

    ISO 문자열을 정규식으로 훑으면 '2026-09-12T10:20:00' 에서 '20:00' 을 집는다.
    날짜 파싱을 먼저 시도하고, 실패할 때만 시각 형식으로 해석한다.
    """
    if value is None:
        return None
    if hasattr(value, "strftime"):
        return value.strftime("%H:%M")
    text = str(value).strip()
    try:
        return datetime.fromisoformat(text).strftime("%H:%M")
    except ValueError:
        pass
    m = CLOCK_RE.fullmatch(text)
    return f"{int(m.group(1)):02d}:{m.group(2)}" if m else None


def extract_routes(result: Any) -> list[dict[str, Any]]:
    """DispatchResult 에서 routes 를 꺼낸다. 없으면 빈 목록."""
    routes = as_dict(result).get("routes")
    if not isinstance(routes, list):
        return []
    return [as_dict(r) for r in routes if r is not None]


def dispatched_vehicles(routes: list[dict[str, Any]]) -> set[str]:
    """실제로 배차된 차량. routes 의 vehicle_id 만 인정한다."""
    return {str(r["vehicle_id"]) for r in routes if r.get("vehicle_id")}


def _stops(route: dict[str, Any]) -> list[dict[str, Any]]:
    stops = [as_dict(s) for s in (route.get("stops") or []) if s is not None]
    return sorted(stops, key=lambda x: x.get("sequence", 0))


def visit_sequence(routes: list[dict[str, Any]]) -> list[str]:
    """TMS 가 정한 방문 순서를 차량 순서대로 펼친다. Stop.sequence 기준."""
    return [str(s["destination_id"]) for r in routes for s in _stops(r) if s.get("destination_id")]


def reported_etas(routes: list[dict[str, Any]]) -> set[str]:
    """TMS 가 반환한 도착시각을 HH:MM 집합으로 모은다."""
    out: set[str] = set()
    for r in routes:
        for s in _stops(r):
            hhmm = _hhmm(s.get("eta"))
            if hhmm:
                out.add(hhmm)
    return out


def has_reported_eta(routes: list[dict[str, Any]]) -> bool:
    """TMS 가 도착시간 또는 소요시간을 반환했는가."""
    if reported_etas(routes):
        return True
    return any(r.get("estimated_duration_seconds") is not None for r in routes)


def mentioned_vehicles(text: str) -> set[str]:
    """응답에서 차량 식별자로 보이는 토큰을 뽑는다."""
    return {m.group(0).strip() for m in VEHICLE_TOKEN_RE.finditer(text)}


def validate_response(text: str, *, tms_result: Any,
                      state: dict[str, Any] | None = None,
                      destination_names: dict[str, str] | None = None,
                      allowed_times: set[str] | None = None) -> list[dict[str, Any]]:
    """최종 설명을 DispatchResult 와 대조하고 위반 목록을 반환한다.

    allowed_times 는 마감·출발처럼 TMS 도착시각이 아니지만 설명에 쓸 수 있는 시각이다.
    """
    state = state or {}
    result = as_dict(tms_result)
    routes = extract_routes(result)
    names = destination_names or {}
    allowed_times = allowed_times or set()
    v: list[dict[str, Any]] = []

    known_vehicles = dispatched_vehicles(routes)
    available = {str(k) for k in (state.get("vehicles") or {})}
    sequence = visit_sequence(routes)
    etas = reported_etas(routes)
    unassigned = result.get("unassigned_orders") or []

    for token in sorted(mentioned_vehicles(text)):
        if token in known_vehicles:
            continue
        reason = "available_not_dispatched" if token in available else "unknown_vehicle"
        v.append({"criterion": "vehicle", "found": token, "reason": reason,
                  "action": "remove_and_regenerate",
                  "message": f"routes 에 배차되지 않은 차량 '{token}' 을 언급했습니다."})

    if names:
        label_to_id = {label: did for did, label in names.items()}
        mentioned = sorted((lb for lb in label_to_id if lb in text), key=text.index)
        mentioned_ids = [label_to_id[lb] for lb in mentioned]
        for did in sorted(set(mentioned_ids) - set(sequence)):
            v.append({"criterion": "stop", "found": did,
                      "action": "replace_with_tms_order",
                      "message": f"routes 에 없는 방문지 '{names[did]}' 을 언급했습니다."})
        in_route = [d for d in mentioned_ids if d in sequence]
        expected = [d for d in sequence if d in set(in_route)]
        if in_route and in_route != expected:
            v.append({"criterion": "stop_order", "action": "replace_with_tms_order",
                      "message": "방문 순서가 TMS 결과와 다릅니다.",
                      "expected": expected, "found": in_route})

    said_times = {f"{int(m.group(1)):02d}:{m.group(2)}" for m in CLOCK_RE.finditer(text)}
    if not has_reported_eta(routes) and (said_times or DURATION_RE.search(text)):
        v.append({"criterion": "eta", "action": "replace_with_no_eta",
                  "message": "TMS 가 도착시간을 반환하지 않았는데 응답에 시간이 있습니다."})
    else:
        for t in sorted(said_times - etas - allowed_times):
            v.append({"criterion": "eta_value", "found": t, "expected": sorted(etas),
                      "action": "replace_with_tms_eta",
                      "message": f"TMS 가 반환하지 않은 시각 '{t}' 을 응답에 사용했습니다."})

    claims_complete = COMPLETE_RE.search(text) and "미배정" not in text
    if unassigned and claims_complete:
        v.append({"criterion": "unassigned", "count": len(unassigned),
                  "action": "list_unassigned",
                  "message": f"미배정 {len(unassigned)}건이 있는데 전체 완료로 서술했습니다."})
    if result.get("status") in ("partial", "failed") and claims_complete:
        v.append({"criterion": "dispatch_result_status", "status": result.get("status"),
                  "action": "state_partial_result",
                  "message": f"DispatchResult.status 가 {result['status']} 인데 "
                             f"전체 완료로 서술했습니다."})

    if "constraint_warnings" in state:
        if GUARANTEE_RE.search(text) and not HEDGE_RE.search(text):
            v.append({"criterion": "constraint_label", "action": "add_precheck_label",
                      "message": "사전검증 결과를 TMS 보장처럼 서술했습니다."})

    if "approval_status" in state:
        claims_confirmed = CONFIRMED_RE.search(text) and not PENDING_RE.search(text)
        if state.get("approval_status") != "confirmed" and claims_confirmed:
            v.append({"criterion": "approval_status", "status": state.get("approval_status"),
                      "action": "mark_pending_approval",
                      "message": "승인 전 계획을 확정된 것처럼 서술했습니다."})

    return v


def build_regenerate_instruction(violations: list[dict[str, Any]]) -> str:
    """재생성 시 모델에 주는 교정 지시."""
    lines = ["직전 응답이 결과 검증을 통과하지 못했습니다. 아래를 반영해 다시 작성하세요."]
    lines += [f"- {x['message']} (조치: {x['action']})" for x in violations]
    lines.append("TMS 결과에 없는 값은 새로 만들지 말고 '정보 없음'으로 두세요.")
    return "\n".join(lines)


def build_error_response(violations: list[dict[str, Any]]) -> dict[str, Any]:
    """재생성 후에도 실패했을 때 반환하는 구조화 오류."""
    return {
        "error": "result_validation_failed",
        "criteria": sorted({x["criterion"] for x in violations}),
        "violations": violations,
        "message": "검증을 통과하는 응답을 만들지 못해 결과를 반환하지 않았습니다.",
    }


def _last_ai_text(state: dict[str, Any]) -> str:
    """최종 설명만 검증 대상으로 삼는다. Tool 호출 메시지는 제외한다."""
    for m in reversed(state.get("messages") or []):
        if getattr(m, "tool_calls", None):
            continue
        role = getattr(m, "type", getattr(m, "role", ""))
        content = getattr(m, "content", None)
        if content and role in ("ai", "assistant"):
            return str(content)
    return ""


def _allowed_times(state: dict[str, Any]) -> set[str]:
    """마감·출발 시각은 TMS 도착시각이 아니어도 설명에 쓸 수 있다."""
    req = state.get("dispatch_request") or {}
    req = as_dict(req) if not isinstance(req, dict) else req
    out = set()
    for key in ("deadline", "departure_time"):
        hhmm = _hhmm(req.get(key))
        if hhmm:
            out.add(hhmm)
    return out


@after_model(can_jump_to=["model"])
def result_validation(state: dict[str, Any], runtime: Any) -> dict[str, Any] | None:
    """최종 응답을 대조한다. 위반이 있으면 1회 재생성하고, 그래도 실패하면 오류를 반환한다."""
    text = _last_ai_text(state)
    if not text:
        return None

    violations = validate_response(
        text,
        tms_result=state.get("last_dispatch_result"),
        state=state,
        destination_names=state.get("destination_names"),
        allowed_times=_allowed_times(state),
    )
    if not violations:
        return None

    tried = state.get(RETRY_KEY, 0)
    if tried < MAX_REGENERATE:
        return {
            "messages": [ai_message(build_regenerate_instruction(violations))],
            RETRY_KEY: tried + 1,
            "jump_to": "model",
        }
    return {"messages": [ai_message(build_error_response(violations)["message"])]}
