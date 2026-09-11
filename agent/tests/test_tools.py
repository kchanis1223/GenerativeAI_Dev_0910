import inspect
from datetime import datetime, timezone

import pytest

from badaro.schemas import (
    DispatchConstraints,
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

    with pytest.raises(ToolErrorException) as exc_info:
        execute_optimize_dispatch(["ORDER-001"], ["VEHICLE-001"], None, context)

    assert exc_info.value.error.code is ToolErrorCode.INVALID_INPUT


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


def test_execute_optimize_dispatch_requests_and_polls_tms(monkeypatch) -> None:
    import importlib

    module = importlib.import_module("badaro.tools.optimize_dispatch")
    context = _context_with_delivery_geocode(
        {
            "서울시 중구 세종대로 1": GeocodeResult(
                status=GeocodeStatus.OK,
                input_address="서울시 중구 세종대로 1",
                candidates=[
                    GeocodeCandidate(
                        matched_address="서울시 중구 세종대로 1", lat=37.5, lon=126.9
                    )
                ],
            )
        }
    )
    responses = iter(
        [
            {"resultCode": "200", "mappingKey": "map-1"},
            {
                "resultCode": "200",
                "vehicleList": [{
                    "vehicleId": "VEHICLE-001",
                    "deliveryTime": "4518",
                    "deliveryDistance": "19423",
                    "orderList": [{
                        "orderId": "ORDER-001",
                        "expectedArrivalTime": "202609111139",
                    }],
                }],
            },
        ]
    )

    class Response:
        status_code = 200

        def raise_for_status(self):
            return None

        def json(self):
            return next(responses)

    monkeypatch.setenv("TMAP_APP_KEY", "test-key")
    monkeypatch.setenv("TMS_POLL_INTERVAL_SECONDS", "0")
    calls = []

    def fake_get(*args, **kwargs):
        calls.append(kwargs["params"])
        return Response()

    monkeypatch.setattr(module.httpx, "get", fake_get)
    result = execute_optimize_dispatch(
        ["ORDER-001"],
        ["VEHICLE-001"],
        DispatchConstraints(
            priority=Priority.NORMAL,
            departure_time=datetime(2026, 9, 10, 20, 0, tzinfo=timezone.utc),
        ),
        context,
    )

    assert result.status.value == "success"
    assert result.routes[0].stops[0].destination_id == "STORE-001"
    assert result.routes[0].distance_meters == 19423
    assert calls[0]["startTime"] == "0500"


def test_execute_optimize_dispatch_retries_transient_poll_only(monkeypatch) -> None:
    import importlib

    module = importlib.import_module("badaro.tools.optimize_dispatch")
    context = _context_with_delivery_geocode(
        {
            "서울시 중구 세종대로 1": GeocodeResult(
                status=GeocodeStatus.OK,
                input_address="서울시 중구 세종대로 1",
                candidates=[GeocodeCandidate(matched_address="주소", lat=37.5, lon=126.9)],
            )
        }
    )
    responses = iter([
        (200, {"resultCode": "200", "mappingKey": "map-1"}),
        (503, {}),
        (200, {"resultCode": "200", "vehicleList": []}),
    ])

    def fake_get(*args, **kwargs):
        status, payload = next(responses)
        return type("Response", (), {"status_code": status, "json": lambda self: payload})()

    monkeypatch.setenv("TMAP_APP_KEY", "test-key")
    monkeypatch.setenv("TMS_POLL_INTERVAL_SECONDS", "0")
    monkeypatch.setenv("TMS_POLL_MAX_ATTEMPTS", "2")
    monkeypatch.setattr(module.httpx, "get", fake_get)
    result = execute_optimize_dispatch(
        ["ORDER-001"],
        ["VEHICLE-001"],
        DispatchConstraints(priority=Priority.NORMAL, departure_time=datetime(2026, 9, 11, 5)),
        context,
    )

    assert result.status.value == "failed"


def test_dispatch_rejects_vehicle_route_when_total_weight_exceeds_capacity() -> None:
    from badaro.tools.optimize_dispatch import _parse_dispatch_result

    context = _context_with_delivery_geocode({})
    context.orders["ORDER-002"] = context.orders["ORDER-001"].model_copy(
        update={"order_id": "ORDER-002", "weight_kg": 1000}
    )
    context.vehicles["VEHICLE-001"] = context.vehicles["VEHICLE-001"].model_copy(
        update={"capacity_weight_kg": 1000}
    )

    result = _parse_dispatch_result(
        {
            "resultCode": "200",
            "vehicleList": [{
                "vehicleId": "VEHICLE-001",
                "orderList": [{"orderId": "ORDER-001"}, {"orderId": "ORDER-002"}],
            }],
        },
        ["ORDER-001", "ORDER-002"],
        context,
    )

    assert result.status.value == "failed"
    assert result.routes == []
    assert {item.reason_code for item in result.unassigned_orders} == {"capacity_exceeded"}
