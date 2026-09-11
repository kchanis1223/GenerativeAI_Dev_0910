"""배송 주문 조회 Tool 인터페이스."""

from datetime import date

from badaro.schemas import Order


def get_delivery_orders(
    depot_id: str,
    delivery_date: date,
    destination_ids: list[str] | None,
    product_names: list[str] | None,
) -> list[Order]:
    """배송일과 조건에 해당하는 배송 주문을 조회한다.

    조회 실패 시 Tool 실행 계층이 ``ToolError.retryable``을 기준으로
    제한적으로 재시도하고, 최종 실패를 사용자에게 전달한다.
    """
    raise NotImplementedError
