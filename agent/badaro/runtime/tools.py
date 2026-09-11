"""공개 Tool 4개에 요청별 서버 State를 연결한다."""

import json
import operator
from dataclasses import dataclass, field
from datetime import date
from threading import Lock
from typing import Annotated, Any

from langchain.tools import ToolRuntime, tool
from langchain_core.messages import ToolMessage
from langgraph.types import Command

from badaro.middleware import BadaroContext, BadaroState, build_runtime_context
from badaro.schemas import DispatchConstraints, DispatchRequest, ToolErrorCode
from badaro.tools.optimize_dispatch import _validate_runtime_context

from .backend import Backend, fail


def merge_maps(left, right):
    return {**(left or {}), **(right or {})}


class RunState(BadaroState):
    geocodes: Annotated[dict[str, Any], merge_maps]
    errors: Annotated[list[dict], operator.add]
    model_calls: int


@dataclass
class RunContext(BadaroContext):
    backend: Backend | None = None
    request: DispatchRequest | None = None
    corrections: dict[str, str] = field(default_factory=dict)
    allocation_attempted: bool = False
    allocation_lock: Lock = field(default_factory=Lock)


def constraints_for(request):
    return DispatchConstraints.model_validate(
        {name: getattr(request, name) for name in DispatchConstraints.model_fields}
    )


def update(runtime, **values):
    serial = {
        k: {key: item.model_dump(mode="json") for key, item in v.items()}
        if isinstance(v, dict)
        else v.model_dump(mode="json")
        for k, v in values.items()
    }
    # 배차 결과는 모델에 다시 보내지 않고 서버의 고정 응답으로 반환한다.
    visible = serial if "last_dispatch_result" not in values else {"status": "completed"}
    return Command(
        update={
            **values,
            "messages": [
                ToolMessage(
                    content=json.dumps(visible, ensure_ascii=False),
                    tool_call_id=runtime.tool_call_id,
                )
            ],
        }
    )


def checked_scope(runtime, depot_id, delivery_date):
    req = runtime.context.request
    if depot_id != req.depot_id or delivery_date != req.delivery_date:
        fail("조회 조건이 확인된 요청과 다릅니다")
    return req


@tool
def get_delivery_orders(
    depot_id: str,
    delivery_date: date,
    destination_ids: list[str] | None,
    product_names: list[str] | None,
    runtime: ToolRuntime[RunContext, RunState],
) -> Command:
    """확인된 센터·날짜·배송지·품목의 주문을 조회하고 요청 State에 저장한다."""
    req = checked_scope(runtime, depot_id, delivery_date)
    if destination_ids != req.destination_ids or product_names != req.product_names:
        fail("주문 조회 범위를 임의로 변경할 수 없습니다")
    orders = runtime.context.backend.orders(depot_id, delivery_date, destination_ids, product_names)
    corrections = runtime.context.corrections
    if set(corrections) - {o.address for o in orders}:
        fail("주소 수정 대상이 현재 주문에 없습니다")
    orders = [
        o.model_copy(update={"address": corrections.get(o.address, o.address)})
        for o in orders
        if o.destination_id not in req.excluded_destination_ids
        and (not req.storage_types or o.storage_type in req.storage_types)
    ]
    if not orders:
        fail("조건에 맞는 주문이 없습니다")
    return update(runtime, orders={o.order_id: o for o in orders})


@tool
def get_available_vehicles(
    depot_id: str,
    delivery_date: date,
    vehicle_count: int | None,
    excluded_vehicle_ids: list[str],
    runtime: ToolRuntime[RunContext, RunState],
) -> Command:
    """확인된 조건의 가용 차량을 조회하고 요청 State에 저장한다."""
    req = checked_scope(runtime, depot_id, delivery_date)
    if vehicle_count != req.vehicle_count or excluded_vehicle_ids != req.excluded_vehicle_ids:
        fail("차량 조회 범위를 임의로 변경할 수 없습니다")
    vehicles = runtime.context.backend.vehicles(
        depot_id,
        delivery_date,
        vehicle_count,
        excluded_vehicle_ids,
    )
    if not vehicles:
        fail("조건에 맞는 차량이 없습니다")
    return update(runtime, vehicles={v.vehicle_id: v for v in vehicles})


@tool
def geocode_address(address: str, runtime: ToolRuntime[RunContext, RunState]) -> Command:
    """조회한 주문의 주소를 확인한다. 모호한 결과는 배차에 사용하지 않는다."""
    if address not in {o.address for o in runtime.state.get("orders", {}).values()}:
        fail("현재 주문에서 확인하지 않은 주소입니다")
    geo = runtime.context.backend.geocode(address)
    if geo.status != "ok" or len(geo.candidates) != 1:
        code = (
            ToolErrorCode.GEOCODE_AMBIGUOUS
            if geo.status == "ambiguous"
            else (ToolErrorCode.GEOCODE_NOT_FOUND)
        )
        fail("배송지 주소를 확정하지 못했습니다. 정확한 주소를 알려주세요", code)
    return update(runtime, geocodes={address: geo})


@tool(return_direct=True)
def optimize_dispatch(
    order_ids: list[str],
    vehicle_ids: list[str],
    constraints: DispatchConstraints,
    runtime: ToolRuntime[RunContext, RunState],
) -> Command:
    """State의 주문·차량·확정 좌표를 주입해 배차하고 검증된 결과를 직접 반환한다."""
    context = runtime.context
    state = runtime.state
    if set(order_ids) != set(state.get("orders", {})):
        fail("조회한 주문을 누락하거나 추가한 배차 요청입니다")
    if constraints != constraints_for(context.request):
        fail("배차 제약조건이 확인된 요청과 다릅니다")
    dispatch_context = build_runtime_context(context, state)
    _validate_runtime_context(order_ids, vehicle_ids, dispatch_context)
    vehicles = [dispatch_context.vehicles[v] for v in vehicle_ids]
    for order in dispatch_context.orders.values():
        if not any(
            v.available
            and order.storage_type in v.supported_storage_types
            and order.weight_kg <= v.capacity_weight_kg
            and (v.capacity_volume_m3 is None or (order.volume_m3 or 0) <= v.capacity_volume_m3)
            for v in vehicles
        ):
            fail("주문의 보관유형·적재량에 맞는 차량이 없습니다")
    with context.allocation_lock:
        if context.allocation_attempted:
            fail("이 요청은 이미 배차를 시도했습니다. 상태를 확인해 주세요")
        context.allocation_attempted = True
    result = context.backend.dispatch(order_ids, vehicle_ids, constraints, dispatch_context)
    return update(runtime, last_dispatch_result=result)


TOOLS = [get_delivery_orders, get_available_vehicles, geocode_address, optimize_dispatch]
