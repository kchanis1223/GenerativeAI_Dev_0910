import inspect

import pytest

from badaro.schemas import (
    DispatchRuntimeContext,
    Order,
    OrderItem,
    Priority,
    StorageType,
    ToolErrorCode,
    ToolErrorException,
    Vehicle,
)
from badaro.tools import (
    geocode_address,
    get_available_vehicles,
    get_delivery_orders,
    optimize_dispatch,
)
from badaro.tools.optimize_dispatch import execute_optimize_dispatch


@pytest.mark.parametrize(
    ("tool", "parameters"),
    [
        (get_delivery_orders, ["depot_id", "delivery_date", "destination_ids", "product_names"]),
        (
            get_available_vehicles,
            ["depot_id", "delivery_date", "vehicle_count", "excluded_vehicle_ids"],
        ),
        (geocode_address, ["address"]),
        (
            optimize_dispatch,
            ["order_ids", "vehicle_ids", "constraints"],
        ),
    ],
)
def test_b03_tool_signatures_are_importable(tool, parameters) -> None:
    assert list(inspect.signature(tool).parameters) == parameters


@pytest.mark.parametrize(
    "tool",
    [get_delivery_orders, get_available_vehicles, geocode_address],
)
def test_b03_tools_are_stubs(tool) -> None:
    with pytest.raises(NotImplementedError):
        tool(*([None] * len(inspect.signature(tool).parameters)))


def test_optimize_dispatch_does_not_expose_runtime_context() -> None:
    with pytest.raises(NotImplementedError):
        optimize_dispatch([], [], None)


def test_execute_optimize_dispatch_rejects_missing_runtime_context_data() -> None:
    with pytest.raises(ToolErrorException) as exc_info:
        execute_optimize_dispatch([], [], None, DispatchRuntimeContext())

    assert exc_info.value.error.code is ToolErrorCode.INVALID_INPUT
    assert exc_info.value.error.retryable is False


def test_execute_optimize_dispatch_requires_origin_context() -> None:
    context = DispatchRuntimeContext(
        depot_id="DEPOT-001",
        orders={
            "ORDER-001": Order(
                order_id="ORDER-001",
                destination_id="STORE-001",
                address="서울시 중구 세종대로 1",
                items=[OrderItem(product_name="광어", weight_kg=10)],
                weight_kg=10,
                storage_type=StorageType.LIVE,
                priority=Priority.NORMAL,
                service_seconds=300,
            )
        },
        vehicles={
            "VEHICLE-001": Vehicle(
                vehicle_id="VEHICLE-001",
                capacity_weight_kg=1000,
                supported_storage_types=[StorageType.LIVE],
                available=True,
                shift_start="2026-09-11T05:00:00",
                shift_end="2026-09-11T18:00:00",
            )
        },
    )

    with pytest.raises(ToolErrorException) as exc_info:
        execute_optimize_dispatch(
            ["ORDER-001"],
            ["VEHICLE-001"],
            None,
            context,
        )

    assert exc_info.value.error.code is ToolErrorCode.MISSING_CONTEXT
    assert "출발지 좌표" in exc_info.value.error.message
