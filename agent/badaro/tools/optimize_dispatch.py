"""TMAP/TMS 배차 최적화 Tool 인터페이스."""

from badaro.schemas import DispatchConstraints, DispatchResult


def optimize_dispatch(
    order_ids: list[str],
    vehicle_ids: list[str],
    constraints: DispatchConstraints,
) -> DispatchResult:
    """검증된 주문·차량·좌표 정보를 사용해 TMAP/TMS 배차를 요청한다."""
    raise NotImplementedError
