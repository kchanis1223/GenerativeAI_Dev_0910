"""ResultValidation — 설계서 3.2 / 3.2.2 (이슈 #14)

TMS 결과와 최종 설명의 차량·방문 순서·시간·미배정 정보를 대조한다.
불일치는 1회 재생성하고, 재검증에도 실패하면 구조화 오류를 반환한다.

v1.3 반영: DispatchResult(status, routes, unassigned_orders),
           VehicleRoute(vehicle_id, stops, estimated_duration_seconds, distance_meters),
           Stop(sequence, order_id, destination_id, eta),
           UnassignedOrder(order_id, reason_code, reason_message).

배차 사실의 기준은 routes 다. 가용 차량 목록에 있다는 이유만으로 인정하지 않는다.
설계서에 아직 반영되지 않은 검사(제약 표기·확정 상태)는 해당 State 가 있을 때만 수행한다.
"""
from __future__ import annotations

import re
from typing import Any

MAX_REGENERATE = 1

VEHICLE_RE = re.compile(r"\b[Vv]-?\d{1,3}\b|\d{1,2}\s*번\s*차")
TIME_RE = re.compile(r"\b\d{1,2}:\d{2}\b|\d+\s*분\s*(소요|후|뒤)")
COMPLETE_RE = re.compile(r"(전체|모두|전부|다)\s*(배정|완료|처리)|빠짐없이")
GUARANTEE_RE = re.compile(r"(보장|확실|반드시|틀림없)")
CONFIRMED_RE = re.compile(r"(확정(했|됐|되었|입니다|합니다))|배차\s*완료|기사(님)?(에게|께)\s*(전달|배포)")
HEDGE_RE = re.compile(r"사전검증|TMS\s*미보장|미보장")
PENDING_RE = re.compile(r"(승인\s*대기|확정\s*전|아직\s*확정)")


def _norm_vehicle(token: str) -> str:
    digits = re.sub(r"\D", "", token)
    return f"V-{int(digits):02d}" if digits else token


def as_dict(obj: Any) -> dict[str, Any]:
    """pydantic 모델과 dict 를 같은 형태로 다룬다."""
    if obj is None:
        return {}
    if isinstance(obj, dict):
        return obj
    dump = getattr(obj, "model_dump", None)
    return dump(mode="json") if callable(dump) else {}


def extract_routes(result: Any) -> list[dict[str, Any]]:
    """DispatchResult 에서 routes 를 꺼낸다. 없으면 빈 목록."""
    routes = as_dict(result).get("routes")
    if not isinstance(routes, list):
        return []
    return [as_dict(r) for r in routes if r is not None]


def dispatched_vehicles(routes: list[dict[str, Any]]) -> set[str]:
    """실제로 배차된 차량. routes 의 vehicle_id 만 인정한다."""
    return {_norm_vehicle(str(r["vehicle_id"])) for r in routes if r.get("vehicle_id")}


def visit_sequence(routes: list[dict[str, Any]]) -> list[str]:
    """TMS 가 정한 방문 순서를 차량 순서대로 펼친다. Stop.sequence 기준."""
    seq: list[str] = []
    for r in routes:
        stops = [as_dict(s) for s in (r.get("stops") or []) if s is not None]
        for s in sorted(stops, key=lambda x: x.get("sequence", 0)):
            if s.get("destination_id"):
                seq.append(str(s["destination_id"]))
    return seq


def has_reported_eta(routes: list[dict[str, Any]]) -> bool:
    """TMS 가 도착시간을 반환했는가. Stop.eta 또는 경로 소요시간."""
    for r in routes:
        if r.get("estimated_duration_seconds") is not None:
            return True
        for s in r.get("stops") or []:
            if as_dict(s).get("eta"):
                return True
    return False


def validate_response(text: str, *, tms_result: Any,
                      state: dict[str, Any] | None = None,
                      destination_names: dict[str, str] | None = None
                      ) -> list[dict[str, Any]]:
    """최종 설명을 DispatchResult 와 대조하고 위반 목록을 반환한다.

    destination_names 는 destination_id 를 표시명으로 잇는 표다. 없으면 이름 대조는 건너뛴다.
    """
    state = state or {}
    result = as_dict(tms_result)
    routes = extract_routes(result)
    names = destination_names or {}
    v: list[dict[str, Any]] = []

    known_vehicles = dispatched_vehicles(routes)
    sequence = visit_sequence(routes)
    unassigned = result.get("unassigned_orders") or []

    for veh in sorted({_norm_vehicle(t) for t in VEHICLE_RE.findall(text)} - known_vehicles):
        v.append({"criterion": "vehicle", "found": veh,
                  "action": "remove_and_regenerate",
                  "message": f"routes 에 배차되지 않은 차량 '{veh}' 을 언급했습니다."})

    if names:
        label_to_id = {label: did for did, label in names.items()}
        mentioned = [lb for lb in label_to_id if lb in text]
        mentioned.sort(key=lambda lb: text.index(lb))
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

    if TIME_RE.search(text) and not has_reported_eta(routes):
        v.append({"criterion": "eta", "action": "replace_with_no_eta",
                  "message": "TMS 가 도착시간을 반환하지 않았는데 응답에 시간이 있습니다."})

    claims_complete = COMPLETE_RE.search(text) and "미배정" not in text
    if unassigned and claims_complete:
        v.append({"criterion": "unassigned", "count": len(unassigned),
                  "action": "list_unassigned",
                  "message": f"미배정 {len(unassigned)}건이 있는데 전체 완료로 서술했습니다."})
    if result.get("status") in ("partial", "failed") and claims_complete:
        v.append({"criterion": "dispatch_result_status", "status": result.get("status"),
                  "action": "state_partial_result",
                  "message": f"DispatchResult.status 가 {result['status']} 인데 전체 완료로 서술했습니다."})

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
