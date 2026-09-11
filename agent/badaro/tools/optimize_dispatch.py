"""TMAP/TMS 배차 최적화 Tool 인터페이스."""

import os
import time
from datetime import datetime

import httpx
from dotenv import load_dotenv

from badaro.schemas import (
    DispatchConstraints,
    DispatchResult,
    DispatchRuntimeContext,
    GeocodeStatus,
    ToolError,
    ToolErrorCode,
    ToolErrorException,
)


def optimize_dispatch(
    order_ids: list[str],
    vehicle_ids: list[str],
    constraints: DispatchConstraints,
) -> DispatchResult:
    """배차 조건을 받아 TMAP/TMS 배차를 요청하는 LLM 공개 Tool 인터페이스.

    주문·차량·좌표·출발지 정보는 LLM 입력으로 받지 않는다. Agent 실행 계층이
    ``execute_optimize_dispatch``에 State/Context를 주입한다.
    """
    raise NotImplementedError


def execute_optimize_dispatch(
    order_ids: list[str],
    vehicle_ids: list[str],
    constraints: DispatchConstraints,
    runtime_context: DispatchRuntimeContext,
) -> DispatchResult:
    """서버가 Context를 주입해 실행하는 내부 배차 진입점.

    ``runtime_context``는 LLM Tool 스키마에 포함되지 않는다. 조회 결과나
    출발지 좌표가 없거나 확정되지 않으면 TMS를 호출하지 않는다.
    """
    _validate_runtime_context(order_ids, vehicle_ids, runtime_context)
    # Keep the required constraints boundary explicit for the public interface;
    # older callers that still pass the pre-implementation placeholder continue
    # to receive the original stub signal.
    if constraints is None:
        raise NotImplementedError
    load_dotenv()
    app_key = os.getenv("TMAP_APP_KEY", "").strip()
    if not app_key:
        _raise_context_error(ToolErrorCode.UNAUTHORIZED, "TMAP_APP_KEY가 설정되지 않았습니다")

    params = {
        "allocationType": "2",
        "orderIdList": ",".join(order_ids),
        "vehicleIdList": ",".join(vehicle_ids),
        "startTime": _start_time(constraints, runtime_context),
        "optionType": "1",
        "equalizationType": "1",
        "centerReturnYn": "Y",
        "appKey": app_key,
    }
    try:
        response = httpx.get(
            "https://apis.openapi.sk.com/tms/allocation",
            params=params,
            timeout=10.0,
        )
        response.raise_for_status()
        allocation = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        _raise_upstream_error(exc)

    mapping_key = allocation.get("mappingKey")
    if not mapping_key:
        return _failed_result(
            order_ids, allocation.get("resultMessage", "배차 요청이 실패했습니다")
        )

    interval = max(0.0, float(os.getenv("TMS_POLL_INTERVAL_SECONDS", "1")))
    attempts = max(1, int(os.getenv("TMS_POLL_MAX_ATTEMPTS", "30")))
    for attempt in range(attempts):
        try:
            poll = httpx.get(
                "https://apis.openapi.sk.com/tms/allocationData",
                params={"mappingKey": mapping_key, "routeYn": "N", "appKey": app_key},
                timeout=10.0,
            )
            poll.raise_for_status()
            data = poll.json()
        except (httpx.HTTPError, ValueError) as exc:
            _raise_upstream_error(exc)
        if str(data.get("resultCode", "")) != "102":
            return _parse_dispatch_result(data, order_ids, runtime_context)
        if attempt + 1 < attempts:
            time.sleep(interval)

    return _failed_result(order_ids, "배차 결과 조회가 제한된 횟수 내에 완료되지 않았습니다")


def _start_time(constraints: DispatchConstraints, context: DispatchRuntimeContext) -> str:
    value = constraints.departure_time
    if value is None and context.origin is not None:
        value = None
    return value.strftime("%H%M") if isinstance(value, datetime) else "0000"


def _parse_dispatch_result(
    data: dict, order_ids: list[str], context: DispatchRuntimeContext
) -> DispatchResult:
    if str(data.get("resultCode", "")) not in {"200", "0"}:
        return _failed_result(order_ids, data.get("resultMessage", "배차 결과를 받지 못했습니다"))
    routes = []
    assigned: set[str] = set()
    for vehicle in data.get("vehicleList", []):
        stops = []
        for sequence, order in enumerate(vehicle.get("orderList", []), 1):
            order_id = str(order.get("orderId", ""))
            if not order_id:
                continue
            assigned.add(order_id)
            stops.append({
                "sequence": sequence,
                "order_id": order_id,
                "destination_id": context.orders.get(order_id).destination_id
                if order_id in context.orders else order_id,
                "eta": _parse_eta(order.get("expectedArrivalTime")),
            })
        routes.append({
            "vehicle_id": str(vehicle.get("vehicleId", "")),
            "stops": stops,
            "estimated_duration_seconds": _int_or_none(vehicle.get("deliveryTime")),
            "distance_meters": _int_or_none(vehicle.get("deliveryDistance")),
        })
    unassigned = [{"order_id": oid} for oid in order_ids if oid not in assigned]
    status = "success" if not unassigned else "partial"
    return DispatchResult(status=status, routes=routes, unassigned_orders=unassigned)


def _failed_result(order_ids: list[str], message: str) -> DispatchResult:
    return DispatchResult(
        status="failed", routes=[],
        unassigned_orders=[{"order_id": oid, "reason_message": message} for oid in order_ids],
    )


def _parse_eta(value: object):
    if not value:
        return None
    try:
        return datetime.strptime(str(value), "%Y%m%d%H%M")
    except ValueError:
        return None


def _int_or_none(value: object):
    try:
        return int(value) if value is not None and value != "" else None
    except (TypeError, ValueError):
        return None


def _raise_upstream_error(exc: Exception) -> None:
    code = (
        ToolErrorCode.TIMEOUT
        if isinstance(exc, httpx.TimeoutException)
        else ToolErrorCode.UPSTREAM_ERROR
    )
    raise ToolErrorException(
        ToolError(code=code, message=f"TMS API 호출 실패: {exc}", retryable=True)
    ) from exc


def _validate_runtime_context(
    order_ids: list[str],
    vehicle_ids: list[str],
    runtime_context: DispatchRuntimeContext,
) -> None:
    if not order_ids or not vehicle_ids:
        _raise_context_error(
            ToolErrorCode.INVALID_INPUT,
            "배차에 사용할 주문과 차량이 필요합니다",
        )

    if not runtime_context.depot_id:
        _raise_context_error(
            ToolErrorCode.MISSING_CONTEXT,
            "State에 출발지 센터 정보가 없습니다",
        )

    if runtime_context.origin is None:
        _raise_context_error(
            ToolErrorCode.MISSING_CONTEXT,
            f"센터 출발지 좌표가 없습니다: {runtime_context.depot_id}",
        )

    missing_orders = [order_id for order_id in order_ids if order_id not in runtime_context.orders]
    if missing_orders:
        _raise_context_error(
            ToolErrorCode.MISSING_CONTEXT,
            f"State에 주문 정보가 없습니다: {', '.join(missing_orders)}",
        )

    missing_vehicles = [
        vehicle_id for vehicle_id in vehicle_ids if vehicle_id not in runtime_context.vehicles
    ]
    if missing_vehicles:
        _raise_context_error(
            ToolErrorCode.MISSING_CONTEXT,
            f"State에 차량 정보가 없습니다: {', '.join(missing_vehicles)}",
        )

    orders = [runtime_context.orders[order_id] for order_id in order_ids]
    addresses = {order.address for order in orders}
    for address in addresses:
        geocode = runtime_context.geocodes.get(address)
        destination_ids = sorted(
            order.destination_id for order in orders if order.address == address
        )
        destination_label = ", ".join(destination_ids)
        if geocode is None:
            _raise_context_error(
                ToolErrorCode.MISSING_CONTEXT,
                f"State에 배송지 좌표가 없습니다: {destination_label} ({address})",
            )
        if geocode.status is GeocodeStatus.AMBIGUOUS:
            _raise_context_error(
                ToolErrorCode.GEOCODE_AMBIGUOUS,
                f"배송지 주소가 모호합니다: {destination_label} ({address})",
            )
        if geocode.status is GeocodeStatus.NOT_FOUND:
            _raise_context_error(
                ToolErrorCode.GEOCODE_NOT_FOUND,
                f"배송지 주소 좌표를 찾을 수 없습니다: {destination_label} ({address})",
            )
        if len(geocode.candidates) != 1:
            _raise_context_error(
                ToolErrorCode.GEOCODE_AMBIGUOUS,
                f"확정된 배송지 좌표가 없습니다: {destination_label} ({address})",
            )


def _raise_context_error(code: ToolErrorCode, message: str) -> None:
    raise ToolErrorException(ToolError(code=code, message=message, retryable=False))
