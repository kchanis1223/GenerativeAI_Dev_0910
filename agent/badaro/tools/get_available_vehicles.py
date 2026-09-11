"""가용 차량 조회 Tool 인터페이스."""

from datetime import date

from badaro.schemas import Vehicle


def get_available_vehicles(
    depot_id: str,
    delivery_date: date,
    vehicle_count: int | None,
    excluded_vehicle_ids: list[str],
) -> list[Vehicle]:
    """배송일에 사용할 수 있는 차량을 조회한다.

    조회 실패 시 Tool 실행 계층이 ``ToolError.retryable``을 기준으로
    제한적으로 재시도하고, 최종 실패를 사용자에게 전달한다.
    """
    raise NotImplementedError
