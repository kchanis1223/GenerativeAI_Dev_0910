"""State — 설계서 3.1 (이슈 #11)

한 대화(thread) 안에서 변하는 값. checkpointer 가 thread_id 별로 저장한다.

geocodes 는 GeocodeResult.input_address 를 키로 보관한다.
주문·차량 조회 결과는 orders·vehicles 에 요청별로 둔다.

state_load_error 는 저장소 조회 실패 신호다. 값이 있으면 기존 조건을 전제한 재배차를 중단한다.
result_validation_retries 는 결과 재생성 횟수다. 두 키 모두 이름을 #17 과 맞춰야 한다.

ApprovalStatus 는 배차 승인 절차의 상태이며, badaro.schemas.DispatchStatus
(success/partial/failed)와 다른 개념이라 이름을 분리했다. 아직 합의 전 항목이다.
설계서에 없는 항목은 값이 없으면 동작하지 않는다.
"""
from __future__ import annotations

import operator
from typing import Annotated, Any, Literal

from badaro.schemas import GeocodeStatus

try:
    from langchain.agents.middleware import AgentState
except ImportError:
    try:
        from langgraph.prebuilt.chat_agent_executor import AgentState
    except ImportError:
        from typing import TypedDict

        class AgentState(TypedDict, total=False):
            messages: list

ApprovalStatus = Literal["draft", "pending_approval", "confirmed", "cancelled"]


class BadaroState(AgentState, total=False):
    """설계서 3.1 State. create_agent(state_schema=BadaroState) 로 등록한다."""

    dispatch_request: Any
    last_dispatch_result: Any
    geocodes: dict[str, Any]
    orders: dict[str, Any]
    vehicles: dict[str, Any]

    state_load_error: str | None
    result_validation_retries: int

    approval_status: ApprovalStatus
    confirmed_snapshot: Annotated[list[Any], operator.add]
    constraint_warnings: Annotated[list[dict[str, Any]], operator.add]
    pending_clarifications: list[dict[str, Any]]
    tms_call_count: int


def initial_state() -> dict[str, Any]:
    """새 대화의 기본값. 설계서 3.1 항목만 채운다."""
    return {
        "dispatch_request": None,
        "last_dispatch_result": None,
        "geocodes": {},
        "orders": {},
        "vehicles": {},
        "state_load_error": None,
        "result_validation_retries": 0,
    }


def _field(obj: Any, name: str) -> Any:
    """pydantic 모델과 dict 를 같은 방식으로 읽는다."""
    if isinstance(obj, dict):
        return obj.get(name)
    return getattr(obj, name, None)


def is_confirmed_geocode(result: Any) -> bool:
    """확정 좌표로 쓸 수 있는 지오코딩 결과인가.

    상태가 ok 이고 후보가 정확히 1개일 때만 확정으로 본다.
    not_found·ambiguous 는 보관하더라도 확정 좌표로 취급하지 않는다.
    """
    if not result:
        return False
    status = _field(result, "status")
    candidates = _field(result, "candidates") or []
    return status == GeocodeStatus.OK and len(candidates) == 1


def confirmed_coord(state: dict[str, Any], address: str) -> dict[str, float] | None:
    """확정 조건을 만족하는 좌표만 돌려준다. 아니면 None."""
    result = (state.get("geocodes") or {}).get(address)
    if not is_confirmed_geocode(result):
        return None
    c = (_field(result, "candidates") or [])[0]
    return {"lat": _field(c, "lat"), "lon": _field(c, "lon")}


def is_approved(state: dict[str, Any]) -> bool:
    """운영자 승인이 끝난 배차인가. approval_status 는 합의 전 항목이라 없으면 False."""
    return state.get("approval_status") == "confirmed"


def latest_snapshot(state: dict[str, Any]) -> Any | None:
    """가장 최근 확정본. 없으면 None."""
    snaps = state.get("confirmed_snapshot") or []
    return snaps[-1] if snaps else None
