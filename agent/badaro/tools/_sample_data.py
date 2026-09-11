"""B-04 CSV 샘플을 B-03 Python 모델로 변환하는 조회 계층."""

import csv
from datetime import date, datetime, time, timedelta, timezone
from functools import wraps
from pathlib import Path

from badaro.schemas import (
    Order,
    OrderItem,
    Priority,
    StorageType,
    ToolError,
    ToolErrorCode,
    ToolErrorException,
    Vehicle,
)

_DATA_DIR = Path(__file__).resolve().parents[2] / "data"
_SEOUL = timezone(timedelta(hours=9))
_STORAGE_TYPES = {
    "활어": StorageType.LIVE,
    "냉장": StorageType.REFRIGERATED,
    "냉동": StorageType.FROZEN,
    "일반": StorageType.AMBIENT,
}


def _data_errors(function):
    """CSV 읽기와 모델 변환 실패를 공통 Tool 오류로 전달한다."""
    @wraps(function)
    def wrapped(*args, **kwargs):
        try:
            return function(*args, **kwargs)
        except (OSError, UnicodeError, csv.Error, KeyError, ValueError, TypeError) as exc:
            raise ToolErrorException(ToolError(
                code=ToolErrorCode.INTERNAL_ERROR,
                message="샘플 데이터의 파일과 필드 형식을 확인해 주세요",
                retryable=False,
            )) from exc
    return wrapped


def _rows(filename: str) -> list[dict[str, str]]:
    try:
        with (_DATA_DIR / filename).open(encoding="utf-8-sig", newline="") as stream:
            return list(csv.DictReader(stream))
    except FileNotFoundError as exc:
        raise ToolErrorException(
            ToolError(
                code=ToolErrorCode.INTERNAL_ERROR,
                message="샘플 데이터 파일을 찾을 수 없습니다",
                retryable=False,
            )
        ) from exc


def _date(value: str) -> date:
    return date.fromisoformat(value)


def _time(value: str) -> time:
    return datetime.strptime(value.zfill(4), "%H%M").time()


def _at_seoul(day: date, clock: time) -> datetime:
    return datetime.combine(day, clock, tzinfo=_SEOUL)


def _storage(value: str) -> StorageType:
    try:
        return _STORAGE_TYPES[value.strip()]
    except KeyError as exc:
        raise ValueError(f"지원하지 않는 품목 유형입니다: {value}") from exc


@_data_errors
def load_orders(
    depot_id: str,
    delivery_date: date,
    destination_ids: list[str] | None,
    product_names: list[str] | None,
) -> list[Order]:
    """센터·배송일·지점·품목 조건으로 샘플 주문을 조회한다."""
    if destination_ids == []:
        return []
    requested_destinations = set(destination_ids or [])
    requested_products = {name.casefold() for name in (product_names or [])}
    result: list[Order] = []
    for row in _rows("delivery_orders.csv"):
        if row["centerId"] != depot_id or _date(row["deliveryDate"]) != delivery_date:
            continue
        if requested_destinations and row["branchId"] not in requested_destinations:
            continue
        if requested_products and not any(
            name in row["itemName"].casefold() or name in row["orderName"].casefold()
            for name in requested_products
        ):
            continue
        storage_type = _storage(row["itemType"])
        result.append(
            Order(
                order_id=row["orderId"],
                destination_id=row["branchId"],
                address=row["address"],
                items=[
                    OrderItem(
                        product_name=row["itemName"],
                        weight_kg=float(row["deliveryWeight"]),
                    )
                ],
                weight_kg=float(row["deliveryWeight"]),
                volume_m3=float(row["deliveryVolume"]),
                storage_type=storage_type,
                priority=Priority(row.get("priority") or "normal"),
                deadline=_at_seoul(delivery_date, _time(row["closeTime"])),
                service_seconds=int(row["serviceTime"]) * 60,
            )
        )
    return result


@_data_errors
def load_vehicles(
    depot_id: str,
    delivery_date: date,
    vehicle_count: int | None,
    excluded_vehicle_ids: list[str],
) -> list[Vehicle]:
    """센터와 근무일에 투입할 수 있는 차량을 조회한다."""
    excluded = set(excluded_vehicle_ids)
    result: list[Vehicle] = []
    for row in _rows("vehicles.csv"):
        if row["centerId"] != depot_id or row["vehicleId"] in excluded:
            continue
        shift_start = datetime.fromisoformat(row["shift_start"])
        shift_end = datetime.fromisoformat(row["shift_end"])
        if shift_start.date() != delivery_date or row["inputYn"] != "1":
            continue
        supported = [
            _storage(item)
            for item in row["supportedItemTypes"].replace("·", ",").replace("|", ",").split(",")
            if item.strip()
        ]
        result.append(
            Vehicle(
                vehicle_id=row["vehicleId"],
                capacity_weight_kg=float(row["maxLoadKg"]),
                capacity_volume_m3=float(row["volume"]),
                supported_storage_types=supported,
                available=True,
                shift_start=shift_start,
                shift_end=shift_end,
            )
        )
    return result[:vehicle_count] if vehicle_count is not None else result
