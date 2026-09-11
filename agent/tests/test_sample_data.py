"""CSV·저장된 주소 근거의 정상/손상 입력 및 Python 매핑 회귀 검증."""

import csv
import runpy
import shutil
from datetime import date
from pathlib import Path

import pytest

DATA = Path(__file__).parents[1] / "data"
helpers = runpy.run_path(str(DATA / "validate_samples.py"))
validate = helpers["validate"]


def test_sample_data():
    assert validate() == {"branches": 20, "centers": 1, "orders": 40, "vehicles": 5,
                          "weight_kg": 3125, "geocoding_exact": 21, "rejected": 4,
                          "Order": {"raw_rejected": 40, "mapped_passed": 40},
                          "Vehicle": {"raw_rejected": 5, "mapped_passed": 5}}


def test_units_and_deadline_are_preserved():
    row = helpers["rows"](DATA, "delivery_orders.csv")[0]
    order = helpers["order_payload"](row)
    assert order["storage_type"] == "live"
    assert order["service_seconds"] == 600
    assert order["weight_kg"] == sum(item["weight_kg"] for item in order["items"]) == 80
    assert order["deadline"].isoformat() == "2026-09-11T10:30:00+09:00"
    vehicle = helpers["vehicle_payload"](helpers["rows"](DATA, "vehicles.csv")[0])
    assert vehicle["capacity_weight_kg"] == 2000
    assert vehicle["supported_storage_types"] == ["live"]


def test_separate_demo_data_preserves_source_and_does_not_fall_back(tmp_path, monkeypatch):
    from badaro.schemas import ToolErrorException
    from badaro.tools._sample_data import load_orders

    source = DATA / "delivery_orders.csv"
    before = source.read_bytes()
    row = helpers["rows"](DATA, source.name)[5]
    row.update(orderId="ORD-20260912-006", deliveryDate="2026-09-12")
    target = tmp_path / source.name
    with target.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(row))
        writer.writeheader()
        writer.writerow(row)
    monkeypatch.setenv("BADARO_DATA_DIR", str(tmp_path))
    orders = load_orders("CENTER-NR", date(2026, 9, 12), ["S03"], ["건미역"])
    assert [o.order_id for o in orders] == ["ORD-20260912-006"]
    assert orders[0].volume_m3 == 0.12
    assert orders[0].deadline.date() == date(2026, 9, 12)
    assert source.read_bytes() == before
    target.unlink()
    with pytest.raises(ToolErrorException):
        load_orders("CENTER-NR", date(2026, 9, 12), None, None)


@pytest.mark.parametrize("filename,field,value", [
    ("delivery_orders.csv", "deliveryWeight", "-1"),
    ("delivery_orders.csv", "branchId", "missing"),
    ("delivery_orders.csv", "closeTime", "0800"),
    ("vehicles.csv", "maxLoadKg", "2"),
    ("vehicles.csv", "inputYn", "yes"),
    ("vehicles.csv", "shift_end", "2026-09-11T05:00:00+09:00"),
    ("geocoding_results.csv", "latitude", "0"),
    ("geocoding_results.csv", "httpStatus", "500"),
])
def test_invalid_data_is_rejected(tmp_path, filename, field, value):
    for source in DATA.glob("*.csv"):
        shutil.copyfile(source, tmp_path / source.name)
    records = helpers["rows"](tmp_path, filename)
    records[0][field] = value
    with (tmp_path / filename).open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)
    with pytest.raises(ValueError):
        validate(tmp_path)


@pytest.mark.parametrize("category,passes", [("냉동", False), ("활어", True)])
def test_only_available_vehicles_supply_capacity(tmp_path, category, passes):
    for source in DATA.glob("*.csv"):
        shutil.copyfile(source, tmp_path / source.name)
    records = helpers["rows"](tmp_path, "vehicles.csv")
    vehicle = next(row for row in records if category in row["supportedItemTypes"].split("|"))
    vehicle["inputYn"] = "0"
    with (tmp_path / "vehicles.csv").open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)
    if passes:
        assert validate(tmp_path)["Vehicle"]["mapped_passed"] == 5
    else:
        with pytest.raises(ValueError, match="품목별 적재량"):
            validate(tmp_path)


def test_changed_checkout_model_fails_validation(tmp_path):
    shutil.copytree(DATA, tmp_path / "data")
    models = tmp_path / "badaro" / "schemas" / "models.py"
    models.parent.mkdir(parents=True)
    models.write_text(helpers["MODELS"].read_text() +
                      '\nclass Order(Order):\n    newly_required_field: str\n', encoding="utf-8")
    from pydantic import ValidationError
    with pytest.raises(ValidationError, match="newly_required_field"):
        runpy.run_path(str(tmp_path / "data" / "validate_samples.py"))["validate"]()
