"""TMAP/TMS 배차 최적화 Tool 인터페이스."""

import os
import time
from datetime import datetime, timedelta, timezone

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
    if constraints is None:
        _raise_context_error(ToolErrorCode.INVALID_INPUT, "배차 제약조건이 필요합니다")
    load_dotenv()
    app_key = os.getenv("TMAP_APP_KEY", "").strip()
    if not app_key:
        _raise_context_error(ToolErrorCode.UNAUTHORIZED, "TMAP_APP_KEY가 설정되지 않았습니다")

    selected_order_ids = [
        order_id
        for order_id in order_ids
        if runtime_context.orders[order_id].destination_id
        not in constraints.excluded_destination_ids
    ]
    if not selected_order_ids:
        _raise_context_error(ToolErrorCode.INVALID_INPUT, "제외 조건을 적용할 배송지가 없습니다")
    if constraints.departure_time is None:
        _raise_context_error(ToolErrorCode.INVALID_INPUT, "배차 시작 시간이 필요합니다")

    params = {
        "allocationType": "2",
        "orderIdList": ",".join(selected_order_ids),
        "vehicleIdList": ",".join(vehicle_ids),
        "startTime": constraints.departure_time.strftime("%H%M"),
        "optionType": "1",
        "equalizationType": "1",
        "centerReturnYn": "Y",
        "appKey": app_key,
    }
    allocation = _request_json(
        "https://apis.openapi.sk.com/tms/allocation", params, phase="allocation"
    )

    mapping_key = allocation.get("mappingKey")
    if not mapping_key:
        _raise_context_error(
            ToolErrorCode.UPSTREAM_ERROR,
            "TMS 배차 요청이 mappingKey를 반환하지 않았습니다",
        )

    interval = max(0.0, float(os.getenv("TMS_POLL_INTERVAL_SECONDS", "1")))
    attempts = max(1, int(os.getenv("TMS_POLL_MAX_ATTEMPTS", "30")))
    for attempt in range(attempts):
        data = _request_json(
            "https://apis.openapi.sk.com/tms/allocationData",
            {"mappingKey": mapping_key, "routeYn": "N", "appKey": app_key},
            phase="poll",
        )
        if str(data.get("resultCode", "")) != "102":
            return _parse_dispatch_result(data, selected_order_ids, runtime_context)
        if attempt + 1 < attempts:
            time.sleep(interval)

    _raise_context_error(
        ToolErrorCode.TIMEOUT, "TMS 배차 결과가 제한된 횟수 내에 완료되지 않았습니다"
    )


def _parse_dispatch_result(
    data: dict, order_ids: list[str], context: DispatchRuntimeContext
) -> DispatchResult:
    if str(data.get("resultCode", "")) not in {"200", "0"}:
        _raise_context_error(ToolErrorCode.UPSTREAM_ERROR, "TMS 배차 결과를 받지 못했습니다")
    routes = []
    assigned: set[str] = set()
    for vehicle in data.get("vehicleList", []):
        stops = []
        for sequence, order in enumerate(vehicle.get("orderList", []), 1):
            order_id = str(order.get("orderId", ""))
            if not order_id:
                continue
            if order_id not in context.orders:
                continue
            assigned.add(order_id)
            stops.append({
                "sequence": sequence,
                "order_id": order_id,
                "destination_id": context.orders[order_id].destination_id,
                "eta": _parse_eta(order.get("expectedArrivalTime")),
            })
        routes.append({
            "vehicle_id": str(vehicle.get("vehicleId", "")),
            "stops": stops,
            "estimated_duration_seconds": _int_or_none(vehicle.get("deliveryTime")),
            "distance_meters": _int_or_none(vehicle.get("deliveryDistance")),
        })
    unassigned = [{"order_id": oid} for oid in order_ids if oid not in assigned]
    status = "failed" if not assigned else ("success" if not unassigned else "partial")
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
        return datetime.strptime(str(value), "%Y%m%d%H%M").replace(
            tzinfo=timezone(timedelta(hours=9))
        )
    except ValueError:
        return None


def _int_or_none(value: object):
    try:
        return int(value) if value is not None and value != "" else None
    except (TypeError, ValueError):
        return None


def _request_json(url: str, params: dict[str, str], *, phase: str) -> dict:
    """단일 호출 후 쿼리 파라미터를 노출하지 않고 오류를 분류한다."""
    try:
        response = httpx.get(url, params=params, timeout=10.0)
    except httpx.TimeoutException as exc:
        _raise_context_error(ToolErrorCode.TIMEOUT, f"TMS {phase} 요청 시간이 초과되었습니다")
        raise AssertionError("unreachable") from exc
    except httpx.HTTPError as exc:
        _raise_context_error(ToolErrorCode.UPSTREAM_ERROR, f"TMS {phase} 요청에 실패했습니다")
        raise AssertionError("unreachable") from exc

    status = response.status_code
    if status == 429:
        _raise_context_error(ToolErrorCode.RATE_LIMITED, "TMS API 호출 한도를 초과했습니다")
    if status in (401, 403):
        _raise_context_error(ToolErrorCode.UNAUTHORIZED, "TMS 앱키 인증에 실패했습니다")
    if 400 <= status < 500:
        _raise_context_error(ToolErrorCode.INVALID_INPUT, f"TMS 요청이 거부되었습니다 ({status})")
    if status >= 500:
        _raise_context_error(
            ToolErrorCode.UPSTREAM_ERROR, f"TMS 서버 오류가 발생했습니다 ({status})"
        )
    try:
        payload = response.json()
    except ValueError as exc:
        _raise_context_error(ToolErrorCode.UPSTREAM_ERROR, "TMS 응답이 올바른 JSON이 아닙니다")
        raise AssertionError("unreachable") from exc
    if not isinstance(payload, dict):
        _raise_context_error(ToolErrorCode.UPSTREAM_ERROR, "TMS 응답 구조가 올바르지 않습니다")
    return payload


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
