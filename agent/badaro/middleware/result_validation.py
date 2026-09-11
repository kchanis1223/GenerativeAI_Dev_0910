"""ResultValidationMiddleware — 설계서 3.2 / 3.2.3, G-04 (이슈 #14, P0)

Hook: after_model
대조 기준 6항목(3.2.3)으로 모델 최종 응답을 검사한다.
위반 시 1회 재생성, 계속 실패하면 구조화 오류를 반환한다.
"""
from __future__ import annotations

import re
from typing import Any

MAX_REGENERATE = 1

VEHICLE_RE = re.compile(r"\b[Vv]-?\d{1,3}\b|\d{1,2}\s*번\s*차")
TIME_RE = re.compile(r"\b\d{1,2}:\d{2}\b|\d+\s*분\s*(소요|후|뒤)")
COMPLETE_RE = re.compile(r"(전체|모두|전부|다)\s*(배정|완료|처리)|빠짐없이")
GUARANTEE_RE = re.compile(r"(보장|확실|반드시|틀림없)")
CONFIRMED_RE = re.compile(r"(확정(했|됐|되었|입니다|합니다))|배차\s*완료|기사(님)?(에게|께)\s*(전달|배포|전송)")
HEDGE_RE = re.compile(r"사전검증|TMS\s*미보장|미보장")
PENDING_RE = re.compile(r"(승인\s*대기|확정\s*전|아직\s*확정)")


def _norm_vehicle(token: str) -> str:
    digits = re.sub(r"\D", "", token)
    return f"V-{int(digits):02d}" if digits else token


def validate_response(text: str, *, tms_result: dict[str, Any] | None,
                      state: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """응답을 6항목으로 대조하고 위반 목록을 돌려준다. 빈 리스트면 통과."""
    state = state or {}
    tms = tms_result or {}
    v: list[dict[str, Any]] = []

    known_vehicles = {_norm_vehicle(str(x)) for x in (tms.get("vehicle_ids") or [])}
    route = tms.get("route") or []
    known_stops = [str(s) for s in route]
    has_eta = bool(tms.get("eta")) or any(
        isinstance(s, dict) and s.get("eta") for s in route if isinstance(s, dict))
    unassigned = tms.get("unassigned_orders") or []

    if known_vehicles:
        for token in set(VEHICLE_RE.findall(text)):
            norm = _norm_vehicle(token)
            if norm not in known_vehicles:
                v.append({"criterion": "vehicle", "guardrail": "G-04", "found": token,
                          "action": "remove_and_regenerate",
                          "message": f"TMS 결과에 없는 차량 '{token}' 이 응답에 있습니다."})

    for stop in re.findall(r"[가-힣]{2,10}점", text):
        if known_stops and stop not in known_stops:
            v.append({"criterion": "stop", "guardrail": "G-04", "found": stop,
                      "action": "replace_with_tms_order",
                      "message": f"TMS 경로에 없는 방문지 '{stop}' 이 응답에 있습니다."})

    if TIME_RE.search(text) and not has_eta:
        v.append({"criterion": "eta", "guardrail": "G-04", "action": "replace_with_no_eta",
                  "message": "TMS 가 도착시간을 반환하지 않았는데 응답에 시간이 있습니다."})

    if unassigned and COMPLETE_RE.search(text) and "미배정" not in text:
        v.append({"criterion": "unassigned", "guardrail": "G-04", "count": len(unassigned),
                  "action": "list_unassigned",
                  "message": f"미배정 {len(unassigned)}건이 있는데 전체 완료로 서술했습니다."})

    claims_guarantee = GUARANTEE_RE.search(text) and not HEDGE_RE.search(text)
    if state.get("constraint_warnings") is not None and claims_guarantee:
        v.append({"criterion": "constraint_label", "guardrail": "G-13",
                  "action": "add_precheck_label",
                  "message": "사전검증 결과를 TMS 보장처럼 서술했습니다. "
                             "'사전검증 통과(TMS 미보장)' 표기 필요."})

    claims_confirmed = CONFIRMED_RE.search(text) and not PENDING_RE.search(text)
    if state.get("dispatch_status") != "confirmed" and claims_confirmed:
        v.append({"criterion": "dispatch_status", "guardrail": "G-11",
                  "status": state.get("dispatch_status", "draft"),
                  "action": "mark_pending_approval",
                  "message": "승인 전 계획을 확정된 것처럼 서술했습니다."})

    return v


def build_regenerate_instruction(violations: list[dict[str, Any]]) -> str:
    """재생성 시 모델에 주는 교정 지시. 위반별 조치를 그대로 나열한다."""
    lines = ["직전 응답이 결과 검증을 통과하지 못했습니다. 아래를 반영해 다시 작성하세요."]
    lines += [f"- {x['message']} (조치: {x['action']})" for x in violations]
    lines.append("TMS 결과에 없는 값은 새로 만들지 말고 '정보 없음'으로 두세요.")
    return "\n".join(lines)


def build_error_response(violations: list[dict[str, Any]]) -> dict[str, Any]:
    """재생성 후에도 실패했을 때 반환하는 구조화 오류 (3.4 fail-closed)."""
    return {
        "error": "result_validation_failed",
        "guardrails": sorted({x["guardrail"] for x in violations}),
        "violations": violations,
        "message": "검증을 통과하는 응답을 만들지 못해 결과를 반환하지 않았습니다.",
    }
