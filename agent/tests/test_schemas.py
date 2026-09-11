from datetime import date

import pytest
from pydantic import ValidationError

from badaro.schemas import (
    DispatchRequest,
    DispatchResult,
    DispatchStatus,
    Priority,
    UnassignedOrder,
)


def test_dispatch_request_uses_agreed_defaults() -> None:
    request = DispatchRequest(depot_id="DEPOT-001", delivery_date=date(2026, 9, 11))

    assert request.priority is Priority.NORMAL
    assert request.destination_ids is None
    assert request.excluded_vehicle_ids == []


def test_dispatch_request_rejects_zero_vehicle_count() -> None:
    with pytest.raises(ValidationError):
        DispatchRequest(
            depot_id="DEPOT-001",
            delivery_date=date(2026, 9, 11),
            vehicle_count=0,
        )


def test_dispatch_result_allows_missing_tms_optional_values() -> None:
    result = DispatchResult(
        status=DispatchStatus.PARTIAL,
        routes=[],
        unassigned_orders=[UnassignedOrder(order_id="ORDER-001")],
    )

    assert result.unassigned_orders[0].reason_code is None
