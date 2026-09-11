"""바다로 Dispatch Copilot — 3.1 State (이슈 #11 B-11 / 설계서 v2 3.1)

State = 한 대화(thread) 안에서 변하는 값. checkpointer 가 thread_id 별로 저장한다.
→ 같은 thread_id 로 다시 호출하면 이전 배차 조건이 그대로 남아 있다 (#11 완료 기준).

설계 원칙 ③ 배차 "계획"과 "확정"을 서로 다른 State 로 분리한다.
"""
from __future__ import annotations

import operator
from typing import Annotated, Any, Literal

try:
    from langchain.agents.middleware import AgentState
except ImportError:
    try:
        from langgraph.prebuilt.chat_agent_executor import AgentState
    except ImportError:
        from typing import TypedDict

        class AgentState(TypedDict, total=False):
            messages: list

DispatchStatus = Literal["draft", "pending_approval", "confirmed", "cancelled"]


class BadaroState(AgentState, total=False):
    """3.1 State 8항목. create_agent(state_schema=BadaroState) 로 등록한다.

    Annotated[list, operator.add] 의 뜻:
      노드가 [새 항목] 을 돌려주면 기존 리스트를 '덮어쓰지 않고' 뒤에 이어붙인다.
      → confirmed_snapshot 을 append-only 로 만드는 장치 (로젠택배 송장 유실 사례 근거)
    """
    dispatch_request: dict[str, Any] | None
    last_dispatch_result: dict[str, Any] | None

    dispatch_status: DispatchStatus
    confirmed_snapshot: Annotated[list[dict[str, Any]], operator.add]

    constraint_warnings: Annotated[list[dict[str, Any]], operator.add]
    pending_clarifications: list[dict[str, Any]]

    resolved_locations: dict[str, dict[str, float]]
    tms_call_count: int


def initial_state() -> dict[str, Any]:
    """새 대화를 시작할 때 넣는 기본값. 키가 아예 없으면 미들웨어가 매번 None 검사를 해야 해서 미리 채운다."""
    return {
        "dispatch_request": None,
        "last_dispatch_result": None,
        "dispatch_status": "draft",
        "confirmed_snapshot": [],
        "constraint_warnings": [],
        "pending_clarifications": [],
        "resolved_locations": {},
        "tms_call_count": 0,
    }


def is_confirmed(state: dict[str, Any]) -> bool:
    """확정된 배차인가? ResultValidation 이 '확정된 것처럼 서술'을 잡을 때 쓴다 (3.2.3 확정 상태)."""
    return state.get("dispatch_status") == "confirmed"


def latest_snapshot(state: dict[str, Any]) -> dict[str, Any] | None:
    """가장 최근 확정본 1건. DispatchDiff 가 변경분을 뽑을 때의 기준선."""
    snaps = state.get("confirmed_snapshot") or []
    return snaps[-1] if snaps else None
