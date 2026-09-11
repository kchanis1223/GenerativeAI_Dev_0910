"""DispatchRuntimeContext 조립 — 설계서 3.1 (이슈 #11)

depot_profile 의 센터 ID·확정 출발 좌표와 State 의 orders·vehicles·geocodes 를 모아
내부 배차 함수에 넘길 실행 컨텍스트를 만든다. LLM Tool 스키마에는 노출하지 않는다.

누락·미확정 검사는 badaro.tools.optimize_dispatch._validate_runtime_context 가 수행한다.
여기서 같은 검사를 중복하지 않는다.
"""
from __future__ import annotations

from typing import Any

from badaro.schemas import DispatchRuntimeContext


def build_runtime_context(context: Any, state: dict[str, Any]) -> DispatchRuntimeContext:
    """실행 계층에 넘길 DispatchRuntimeContext 를 만든다."""
    depot = getattr(context, "depot_profile", None)
    return DispatchRuntimeContext(
        depot_id=getattr(depot, "depot_id", None),
        origin=getattr(depot, "origin", None),
        orders=dict(state.get("orders") or {}),
        vehicles=dict(state.get("vehicles") or {}),
        geocodes=dict(state.get("geocodes") or {}),
    )
