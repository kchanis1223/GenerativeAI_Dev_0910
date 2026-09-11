from datetime import date, datetime

import pytest
from pydantic import ValidationError

from badaro.schemas import (
    DispatchRequest,
    DispatchResult,
    DispatchRuntimeContext,
    DispatchStatus,
    GeocodeCandidate,
    GeocodeResult,
    GeocodeStatus,
    Priority,
    StorageType,
    UnassignedOrder,
    Vehicle,
)


def test_runtime_context_keeps_results_keyed_by_id() -> None:
    context = DispatchRuntimeContext()

    assert context.orders == {}
    assert context.vehicles == {}
    assert context.geocodes == {}


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


def test_dispatch_request_accepts_agreed_storage_and_priority_values() -> None:
    request = DispatchRequest(
        depot_id="DEPOT-001",
        destination_ids=["STORE-001"],
        delivery_date=date(2026, 9, 11),
        priority="urgent",
        storage_types=["refrigerated", StorageType.LIVE],
    )

    assert request.priority is Priority.URGENT
    assert request.storage_types == [StorageType.REFRIGERATED, StorageType.LIVE]
    assert DispatchRequest.model_fields["depot_id"].description == "출발 물류센터 ID"


def test_dispatch_request_rejects_unknown_storage_type() -> None:
    with pytest.raises(ValidationError):
        DispatchRequest(
            depot_id="DEPOT-001",
            delivery_date=date(2026, 9, 11),
            storage_types=["chilled"],
        )


def test_geocode_result_enforces_status_candidate_contract() -> None:
    candidate = GeocodeCandidate(matched_address="서울시 중구 세종대로 1", lat=37.566, lon=126.978)
    result = GeocodeResult(
        status=GeocodeStatus.OK,
        input_address="서울시 중구 세종대로 1",
        candidates=[candidate],
    )

    assert result.candidates == [candidate]

    with pytest.raises(ValidationError):
        GeocodeResult(
            status=GeocodeStatus.OK,
            input_address="서울시 중구 세종대로 1",
            candidates=[],
        )

    ambiguous = GeocodeResult(
        status=GeocodeStatus.AMBIGUOUS,
        input_address="서울시 중구 세종대로 1",
        candidates=[candidate],
    )
    assert ambiguous.status is GeocodeStatus.AMBIGUOUS

    with pytest.raises(ValidationError):
        GeocodeResult(
            status=GeocodeStatus.AMBIGUOUS,
            input_address="서울시 중구 세종대로 1",
            candidates=[],
        )


def test_vehicle_rejects_reversed_shift() -> None:
    with pytest.raises(ValidationError):
        Vehicle(
            vehicle_id="VEHICLE-001",
            capacity_weight_kg=1000,
            supported_storage_types=[StorageType.REFRIGERATED],
            available=True,
            shift_start=datetime(2026, 9, 11, 18),
            shift_end=datetime(2026, 9, 11, 5),
        )


def test_vehicle_rejects_mixed_timezone_shift_as_validation_error() -> None:
    with pytest.raises(ValidationError, match="both include a timezone"):
        Vehicle(
            vehicle_id="VEHICLE-001",
            capacity_weight_kg=1000,
            supported_storage_types=[StorageType.REFRIGERATED],
            available=True,
            shift_start="2026-09-11T05:00:00+09:00",
            shift_end="2026-09-11T18:00:00",
        )


def test_dispatch_result_allows_missing_tms_optional_values() -> None:
    result = DispatchResult(
        status=DispatchStatus.PARTIAL,
        routes=[],
        unassigned_orders=[UnassignedOrder(order_id="ORDER-001")],
    )

    assert result.unassigned_orders[0].reason_code is None
