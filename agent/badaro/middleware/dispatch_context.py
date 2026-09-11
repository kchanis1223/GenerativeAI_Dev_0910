"""DispatchContext — 설계서 3.2 (이슈 #12)

State 의 현재 배차 조건을 필요한 만큼만 프롬프트에 주입한다.
지점 전체 목록을 매 turn 반복 주입하지 않고 요약과 참조 ID 로 전달한다.

v1.3 반영: DispatchRequest 필드는 depot_id, destination_ids, delivery_date, vehicle_count,
           storage_types, deadline 등이다. destination_ids 가 null 이면 조회 범위 미지정이다.

State 가 없는 신규 요청과 저장소 조회 실패를 구분한다.
조회 실패 상태에서 기존 조건을 전제한 재배차는 중단한다.
"""
from __future__ import annotations

import hashlib
from typing import Any, Literal

from ._compat import ai_message, before_model

STATE_LOAD_ERROR_KEY = "state_load_error"

ContextMode = Literal["new", "resume", "load_failed"]

_STORAGE_LABEL = {
    "live": "활어", "refrigerated": "냉장", "frozen": "냉동", "ambient": "일반",
}

LOAD_FAILED_MESSAGE = (
    "이전 배차 조건을 불러오지 못했습니다. 기존 조건을 전제한 재배차는 진행하지 않았습니다. "
    "물류센터·배송일·배송지 조건을 다시 알려주시면 이어서 진행하겠습니다."
)


def resolve_mode(state: dict[str, Any]) -> ContextMode:
    """이번 turn 을 어떻게 다룰지 판정한다.

    load_failed 를 신규 요청으로 처리하면 사용자가 조건이 사라진 사실을 모른다.
    """
    if state.get(STATE_LOAD_ERROR_KEY):
        return "load_failed"
    if state.get("dispatch_request"):
        return "resume"
    return "new"


def request_ref(dispatch_request: dict[str, Any] | None) -> str:
    """배차 조건의 짧은 참조 ID. 같은 조건이면 항상 같은 값이 나온다."""
    if not dispatch_request:
        return "req-none"
    raw = repr(sorted(dispatch_request.items())).encode("utf-8")
    return "req-" + hashlib.sha256(raw).hexdigest()[:8]


def summarize_request(state: dict[str, Any]) -> str | None:
    """현재 배차 조건의 요약문. 신규 요청이거나 조회 실패면 None."""
    if resolve_mode(state) != "resume":
        return None

    req = state["dispatch_request"]
    parts = [f"ref={request_ref(req)}"]
    if req.get("depot_id"):
        parts.append(f"센터 {req['depot_id']}")

    dests = req.get("destination_ids")
    if dests is None:
        parts.append("배송지 전체")
    else:
        parts.append(f"배송지 {len(dests)}건")

    storages = req.get("storage_types")
    if storages:
        parts.append("보관 " + "/".join(_STORAGE_LABEL.get(s, s) for s in storages))
    if req.get("vehicle_count") is not None:
        parts.append(f"차량 {req['vehicle_count']}대")
    if req.get("delivery_date"):
        parts.append(f"배송일 {req['delivery_date']}")
    if req.get("deadline"):
        parts.append(f"마감 {req['deadline']}")

    lines = ["[현재 배차 조건] " + " | ".join(parts)]
    counts = [
        f"주문 {len(state.get('orders') or {})}건",
        f"차량 {len(state.get('vehicles') or {})}대",
        f"확정 좌표 {len(state.get('geocodes') or {})}건",
    ]
    lines.append("[조회 결과] " + " | ".join(counts))
    status = state.get("approval_status")
    if status:
        lines.append(f"[승인 상태] {status}")
    lines.append("[주의] 위 요약에 없는 개별 주문·주소는 추측하지 말고 Tool 로 조회할 것.")
    return "\n".join(lines)


@before_model
def dispatch_context(state: dict[str, Any], runtime: Any) -> dict[str, Any] | None:
    """요약본을 주입한다. 조회 실패면 재배차를 중단하고 조건 확인을 요청한다."""
    if resolve_mode(state) == "load_failed":
        return {"messages": [ai_message(LOAD_FAILED_MESSAGE)], "jump_to": "end"}
    summary = summarize_request(state)
    if summary is None:
        return None
    return {"messages": [ai_message(summary)]}
