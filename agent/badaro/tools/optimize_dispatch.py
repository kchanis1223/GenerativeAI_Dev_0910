"""TMAP/TMS 배차 최적화 Tool 인터페이스."""

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
    raise NotImplementedError


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
