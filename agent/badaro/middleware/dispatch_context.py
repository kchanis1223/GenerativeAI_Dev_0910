"""DispatchContextMiddleware — 3.2 (이슈 #12 B-12 · 우선순위 P0)

Hook  : before_model (모델 호출 전, 매 iteration)
목적  : State 의 현재 배차 조건을 '필요한 만큼만' 프롬프트에 주입한다.
v2 보완: 20개 지점 전체를 매 turn 반복 주입하지 않고 **요약 + 참조 ID**로 전달 (설계서 1.5 성능)

왜 요약인가:
  배송지 20건을 매 turn 통째로 넣으면 재배차를 5번만 해도 같은 목록이 5번 들어간다.
  목록 원본은 State 에 그대로 두고, 모델에는 "20건 있고 ref 는 이것" 만 알려준 뒤
  실제 내용이 필요하면 Tool 로 조회하게 한다.
"""
from __future__ import annotations

import hashlib
from typing import Any

from ._compat import before_model

_STORAGE_LABEL = {
    "live_fish": "활어", "chilled": "냉장", "frozen": "냉동", "normal": "일반",
}


def request_ref(dispatch_request: dict[str, Any] | None) -> str:
    """배차 조건에 짧은 참조 ID를 붙인다. 조건이 같으면 항상 같은 값이 나온다.

    같은 조건 = 같은 ref 라서, QuotaCache(#P1) 의 '동일 조건 해시 캐시' 키로도 그대로 쓸 수 있다.
    """
    if not dispatch_request:
        return "req-none"
    raw = repr(sorted(dispatch_request.items())).encode("utf-8")
    return "req-" + hashlib.sha256(raw).hexdigest()[:8]


def summarize_request(state: dict[str, Any]) -> str | None:
    """현재 배차 조건을 한 덩어리 요약문으로 만든다. 조건이 없으면 None (= 신규 요청으로 처리)."""
    req = state.get("dispatch_request")
    if not req:
        return None

    dests = req.get("destinations") or []
    counts: dict[str, int] = {}
    for d in dests:
        if isinstance(d, dict):
            k = d.get("storage_type", "normal")
            counts[k] = counts.get(k, 0) + 1
    mix = " / ".join(f"{_STORAGE_LABEL.get(k, k)} {v}" for k, v in counts.items()) or "미분류"

    parts = [
        f"ref={request_ref(req)}",
        f"배송지 {len(dests)}건 ({mix})",
    ]
    if req.get("vehicle_count") is not None:
        parts.append(f"차량 {req['vehicle_count']}대")
    if req.get("delivery_date"):
        parts.append(f"배송일 {req['delivery_date']}")
    if req.get("deadline"):
        parts.append(f"마감 {req['deadline']}")

    status = state.get("dispatch_status", "draft")
    warn_n = len(state.get("constraint_warnings") or [])
    calls = state.get("tms_call_count", 0)

    return (
        "[현재 배차 조건] " + " | ".join(parts) + "\n"
        f"[상태] {status} | 사전검증 경고 {warn_n}건 | TMS 호출 {calls}회\n"
        "[주의] 위 요약에 없는 개별 배송지 정보는 추측하지 말고 Tool 로 조회할 것."
    )


@before_model
def dispatch_context(state: dict[str, Any], runtime: Any) -> dict[str, Any] | None:
    """요약본을 시스템 메시지로 한 줄 덧붙인다. 조건이 없으면 아무것도 안 한다."""
    summary = summarize_request(state)
    if summary is None:
        return None
    from ._compat import ai_message
    return {"messages": [ai_message(summary)]}
