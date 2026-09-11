from pathlib import Path

import httpx
import pytest

from badaro.schemas import (
    DispatchConstraints,
    DispatchRuntimeContext,
    GeocodeCandidate,
    Order,
    ToolErrorCode,
    ToolErrorException,
    Vehicle,
)
from badaro.tools import _http, geocode_address
from badaro.tools.geocode_address import clear_geocode_cache
from badaro.tools.optimize_dispatch import execute_optimize_dispatch

ADDRESS = "서울특별시 중구 을지로 65"


@pytest.fixture(autouse=True)
def offline_mock(monkeypatch):
    monkeypatch.setenv("USE_MOCK", "1")
    monkeypatch.setenv("TMAP_APP_KEY", "")
    monkeypatch.setattr(httpx, "get", lambda *a, **kw: pytest.fail("외부 HTTP 호출 발생"))
    clear_geocode_cache()
    yield
    clear_geocode_cache()


def test_recorded_geocode_and_dispatch_without_key_or_network():
    geo = geocode_address(ADDRESS)
    assert geo.candidates[0].lat == 37.56649
    context = DispatchRuntimeContext(
        depot_id="badaro-b02-center",
        origin=GeocodeCandidate(matched_address="테스트 출발지", lat=37.5, lon=127),
        orders={"badaro-b02-order": Order(
            order_id="badaro-b02-order", destination_id="badaro-b02-order", address=ADDRESS,
            items=[], weight_kg=100, storage_type="ambient", priority="normal", service_seconds=600,
        )},
        vehicles={"badaro-b02-vehicle": Vehicle(
            vehicle_id="badaro-b02-vehicle", capacity_weight_kg=1000,
            supported_storage_types=["ambient"], available=True,
            shift_start="2026-09-11T05:00:00+09:00", shift_end="2026-09-11T18:00:00+09:00",
        )}, geocodes={ADDRESS: geo},
    )
    result = execute_optimize_dispatch(
        list(context.orders), list(context.vehicles),
        DispatchConstraints(priority="normal", departure_time="2026-09-11T11:00:00+09:00"),
        context,
    )
    assert result.status == "success"
    assert result.routes[0].stops[0].order_id == "badaro-b02-order"
    assert result.routes[0].stops[0].eta.hour == 11
    assert result.routes[0].stops[0].eta.minute == 39


@pytest.mark.parametrize("url,params", [
    ("https://example.invalid/unknown", {}),
    ("https://example.invalid/tmap/geo/fullAddrGeo", {}),
    (f"{_http._BASE}/tms/allocation", {"orderIdList": "unrecorded"}),
    (f"{_http._BASE}/tms/allocationData", {"mappingKey": "unknown", "routeYn": "N"}),
])
def test_unrecorded_requests_never_fall_back_to_http(url, params):
    with pytest.raises(ToolErrorException) as caught:
        _http.get(url, params=params, timeout=1)
    assert caught.value.error.code is ToolErrorCode.INVALID_INPUT
    assert not caught.value.error.retryable


def test_unrecorded_address_is_not_confirmed():
    with pytest.raises(ToolErrorException) as caught:
        geocode_address("존재하지 않는 가짜 주소 999999")
    assert caught.value.error.code is ToolErrorCode.INVALID_INPUT


def test_switching_to_live_mode_does_not_reuse_mock_coordinates(monkeypatch):
    geocode_address(ADDRESS)
    monkeypatch.setenv("USE_MOCK", "0")
    with pytest.raises(ToolErrorException) as caught:
        geocode_address(ADDRESS)
    assert caught.value.error.code is ToolErrorCode.UNAUTHORIZED


def test_live_adapter_forwards_request(monkeypatch):
    monkeypatch.setenv("USE_MOCK", "0")
    calls = []
    response = httpx.Response(200, json={"test": True})

    def fake_get(url, **kwargs):
        calls.append((url, kwargs))
        return response

    monkeypatch.setattr(httpx, "get", fake_get)
    assert _http.get("https://example.invalid", params={"test": "1"}, timeout=2) is response
    assert calls == [("https://example.invalid", {"params": {"test": "1"}, "timeout": 2})]


@pytest.mark.parametrize("content", [None, "not-json", "[]"])
def test_missing_or_invalid_fixture_returns_safe_error(monkeypatch, tmp_path, content):
    directory = tmp_path / "mock_responses"
    directory.mkdir()
    if content is not None:
        (directory / "tmap-geocode-response.json").write_text(content)
    monkeypatch.setattr(_http, "files", lambda _: tmp_path)
    with pytest.raises(ToolErrorException) as caught:
        geocode_address(ADDRESS)
    assert caught.value.error.code is ToolErrorCode.INTERNAL_ERROR
    assert str(tmp_path) not in caught.value.error.message


def test_invalid_mode_does_not_enable_live_http(monkeypatch):
    monkeypatch.setenv("USE_MOCK", "typo")
    with pytest.raises(ToolErrorException):
        geocode_address(ADDRESS)


def test_packaged_responses_match_recorded_api_examples():
    root = Path(__file__).resolve().parents[2]
    for name, _ in _http._FIXTURES.values():
        assert (root / "docs/api" / name).read_bytes() == (
            root / "agent/badaro/tools/mock_responses" / name
        ).read_bytes()
