import inspect

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
    [get_delivery_orders, get_available_vehicles],
)
def test_b03_tools_are_stubs(tool) -> None:
    with pytest.raises(NotImplementedError):
        tool(*([None] * len(inspect.signature(tool).parameters)))


def test_optimize_dispatch_does_not_expose_runtime_context() -> None:
    with pytest.raises(NotImplementedError):
        optimize_dispatch([], [], None)


def test_geocode_address_parses_tmap_response_and_caches(monkeypatch) -> None:
    from importlib import import_module

    geocode_module = import_module("badaro.tools.geocode_address")

    geocode_module.clear_geocode_cache()
    monkeypatch.setenv("TMAP_APP_KEY", "test-key")
    calls = []

    def fake_get(url, *, params, timeout):
        calls.append((url, params, timeout))
        return type(
            "Response",
            (),
            {
                "status_code": 200,
                "json": lambda self: {
                    "coordinateInfo": {
                        "totalCount": "1",
                        "coordinate": [
                                {
                                    "city_do": "서울",
                                    "gu_gun": "중구",
                                    "newMatchFlag": "N51",
                                    "newLat": "37.5",
                                "newLon": "126.9",
                            }
                        ],
                    }
                },
            },
        )()

    monkeypatch.setattr(geocode_module.httpx, "get", fake_get)
    first = geocode_address(" 서울시 중구 ")
    second = geocode_address("서울시 중구")

    assert first.status is GeocodeStatus.OK
    assert first.candidates[0].lat == 37.5
    assert second == first
    assert len(calls) == 1


def test_geocode_address_returns_not_found(monkeypatch) -> None:
    from importlib import import_module

    geocode_module = import_module("badaro.tools.geocode_address")

    geocode_module.clear_geocode_cache()
    monkeypatch.setenv("TMAP_APP_KEY", "test-key")
    monkeypatch.setattr(
        geocode_module.httpx,
        "get",
        lambda *args, **kwargs: type(
            "Response",
            (),
            {"status_code": 200, "json": lambda self: {"coordinateInfo": {"totalCount": "0"}}},
        )(),
    )

    result = geocode_address("가나다라 물류센터")

    assert result.status is GeocodeStatus.NOT_FOUND
    assert result.candidates == []


def test_geocode_address_keeps_approximate_match_ambiguous(monkeypatch) -> None:
    from importlib import import_module

    geocode_module = import_module("badaro.tools.geocode_address")
    geocode_module.clear_geocode_cache()
    monkeypatch.setenv("TMAP_APP_KEY", "test-key")
    monkeypatch.setattr(
        geocode_module.httpx,
        "get",
        lambda *args, **kwargs: type(
            "Response",
            (),
            {
                "status_code": 200,
                "json": lambda self: {
                    "coordinateInfo": {
                        "totalCount": "1",
                        "coordinate": [
                            {"newMatchFlag": "N55", "newLat": "37.5", "newLon": "126.9"}
                        ],
                    }
                },
            },
        )(),
    )

    result = geocode_module.geocode_address("서울시 중구")

    assert result.status is GeocodeStatus.AMBIGUOUS


def test_geocode_address_ok_keeps_only_exact_candidate(monkeypatch) -> None:
    from importlib import import_module

    geocode_module = import_module("badaro.tools.geocode_address")
    geocode_module.clear_geocode_cache()
    monkeypatch.setenv("TMAP_APP_KEY", "test-key")
    monkeypatch.setattr(
        geocode_module.httpx,
        "get",
        lambda *args, **kwargs: type(
            "Response",
            (),
            {
                "status_code": 200,
                "json": lambda self: {
                    "coordinateInfo": {
                        "totalCount": "2",
                        "coordinate": [
                            {"newMatchFlag": "N51", "newLat": "37.5", "newLon": "126.9"},
                            {"newMatchFlag": "N55", "newLat": "37.6", "newLon": "127.0"},
                        ],
                    }
                },
            },
        )(),
    )

    result = geocode_module.geocode_address("서울시 중구 세종대로 1")

    assert result.status is GeocodeStatus.OK
    assert len(result.candidates) == 1
    assert result.candidates[0].lat == 37.5


@pytest.mark.parametrize(
    "payload",
    [{}, {"coordinateInfo": []}, {"coordinateInfo": {"coordinate": {}}}],
)
def test_geocode_address_rejects_malformed_response(monkeypatch, payload) -> None:
    from importlib import import_module

    geocode_module = import_module("badaro.tools.geocode_address")
    geocode_module.clear_geocode_cache()
    monkeypatch.setenv("TMAP_APP_KEY", "test-key")
    monkeypatch.setattr(
        geocode_module.httpx,
        "get",
        lambda *args, **kwargs: type(
            "Response", (), {"status_code": 200, "json": lambda self: payload}
        )(),
    )

    with pytest.raises(ToolErrorException) as exc_info:
        geocode_module.geocode_address("서울시 중구")

    assert exc_info.value.error.code is ToolErrorCode.UPSTREAM_ERROR


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


@pytest.mark.parametrize("match_flag", ["M11", "M21"])
def test_geocode_lot_exact_uses_lot_coordinates(match_flag) -> None:
    from importlib import import_module

    module = import_module("badaro.tools.geocode_address")
    result = module._parse_response("서울 중구 명동 1", {
        "coordinateInfo": {"totalCount": "1", "coordinate": [{
            "matchFlag": match_flag, "lat": "37.5", "lon": "126.9",
            "newMatchFlag": "N55", "newLat": "37.6", "newLon": "127.0",
            "city_do": "서울", "gu_gun": "중구", "legalDong": "명동", "bunji": "1",
        }]},
    })
    assert result.status is GeocodeStatus.OK
    assert result.candidates[0].lat == 37.5
    assert result.candidates[0].lon == 126.9
    assert result.candidates[0].matched_address == "서울 중구 명동 1"


@pytest.mark.parametrize("lat,lon", [("91", "126.9"), ("37.5", "181"), ("nan", "127")])
def test_geocode_invalid_coordinate_uses_common_error(lat, lon) -> None:
    from importlib import import_module

    module = import_module("badaro.tools.geocode_address")
    with pytest.raises(ToolErrorException) as exc_info:
        module._parse_response("검증용 주소", {
            "coordinateInfo": {"totalCount": "1", "coordinate": [{
                "newMatchFlag": "N51", "newLat": lat, "newLon": lon,
            }]},
        })
    assert exc_info.value.error.code is ToolErrorCode.UPSTREAM_ERROR
    assert exc_info.value.error.retryable is False


@pytest.mark.parametrize("status,code,retryable", [
    (401, ToolErrorCode.UNAUTHORIZED, False),
    (429, ToolErrorCode.RATE_LIMITED, True),
    (503, ToolErrorCode.UPSTREAM_ERROR, True),
])
def test_geocode_http_error_calls_once(monkeypatch, status, code, retryable) -> None:
    from importlib import import_module
    from unittest.mock import Mock

    module = import_module("badaro.tools.geocode_address")
    get = Mock(return_value=type("Response", (), {"status_code": status})())
    monkeypatch.setattr(module.httpx, "get", get)
    with pytest.raises(ToolErrorException) as exc_info:
        module._request_once({"appKey": "test-placeholder"})
    assert get.call_count == 1
    assert exc_info.value.error.code is code
    assert exc_info.value.error.retryable is retryable
