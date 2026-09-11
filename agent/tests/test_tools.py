import inspect
from datetime import datetime

import pytest

from badaro.schemas import (
    DispatchRuntimeContext,
    GeocodeCandidate,
    GeocodeResult,
    GeocodeStatus,
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
    [geocode_address],
)
def test_b03_tools_are_stubs(tool) -> None:
    with pytest.raises(NotImplementedError):
        tool(*([None] * len(inspect.signature(tool).parameters)))


def test_b10_vehicle_storage_types_support_pipe_separator() -> None:
    from importlib import import_module

    sample_data = import_module("badaro.tools._sample_data")
    assert sample_data._storage("냉장") is StorageType.REFRIGERATED
    assert [
        sample_data._storage(item)
        for item in "냉장|냉동".split("|")
    ] == [StorageType.REFRIGERATED, StorageType.FROZEN]


def test_b10_missing_csv_raises_tool_error(monkeypatch, tmp_path) -> None:
    from importlib import import_module

    sample_data = import_module("badaro.tools._sample_data")
    monkeypatch.setattr(sample_data, "_DATA_DIR", tmp_path)
    with pytest.raises(ToolErrorException) as exc_info:
        get_delivery_orders("CENTER-NR", datetime(2026, 9, 11).date(), None, None)
    assert exc_info.value.error.code is ToolErrorCode.INTERNAL_ERROR


def test_b10_get_delivery_orders_reads_and_filters_sample_csv() -> None:
    orders = get_delivery_orders(
        "CENTER-NR",
        datetime(2026, 9, 11).date(),
        ["S01"],
        ["냉장 연어"],
    )

    assert [order.order_id for order in orders] == ["ORD-20260911-002"]
    assert orders[0].deadline.isoformat() == "2026-09-11T10:30:00+09:00"
    assert orders[0].service_seconds == 600


def test_b10_get_available_vehicles_filters_excluded_and_limits_count() -> None:
    vehicles = get_available_vehicles(
        "CENTER-NR",
        datetime(2026, 9, 11).date(),
        2,
        ["LIVE01"],
    )

    assert len(vehicles) == 2
    assert [vehicle.vehicle_id for vehicle in vehicles] == ["LIVE02", "COLD01"]
    assert all(vehicle.available for vehicle in vehicles)


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


def _context_with_delivery_geocode(geocodes: dict[str, GeocodeResult]) -> DispatchRuntimeContext:
    return DispatchRuntimeContext(
        depot_id="DEPOT-001",
        origin=GeocodeCandidate(
            matched_address="서울시 동작구 노량진로 1",
            lat=37.513,
            lon=126.942,
        ),
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
        geocodes=geocodes,
    )


def test_execute_optimize_dispatch_uses_input_address_as_geocode_key() -> None:
    address = "서울시 중구 세종대로 1"
    context = _context_with_delivery_geocode(
        {
            address: GeocodeResult(
                status=GeocodeStatus.OK,
                input_address=address,
                candidates=[
                    GeocodeCandidate(
                        matched_address=address,
                        lat=37.566,
                        lon=126.978,
                    )
                ],
            )
        }
    )

    with pytest.raises(NotImplementedError):
        execute_optimize_dispatch(["ORDER-001"], ["VEHICLE-001"], None, context)


def test_execute_optimize_dispatch_does_not_use_destination_id_as_geocode_key() -> None:
    address = "서울시 중구 세종대로 1"
    context = _context_with_delivery_geocode(
        {
            "STORE-001": GeocodeResult(
                status=GeocodeStatus.OK,
                input_address=address,
                candidates=[
                    GeocodeCandidate(
                        matched_address=address,
                        lat=37.566,
                        lon=126.978,
                    )
                ],
            )
        }
    )

    with pytest.raises(ToolErrorException) as exc_info:
        execute_optimize_dispatch(["ORDER-001"], ["VEHICLE-001"], None, context)

    assert exc_info.value.error.code is ToolErrorCode.MISSING_CONTEXT
