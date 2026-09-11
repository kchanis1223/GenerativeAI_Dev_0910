"""CSV·저장된 주소 근거의 정상/손상 입력 및 Python 매핑 회귀 검증."""

import csv
import os
import runpy
import shutil
from pathlib import Path

import pytest

DATA = Path(__file__).parents[1] / "data"
helpers = runpy.run_path(str(DATA / "validate_samples.py"))
validate = helpers["validate"]


def test_sample_data():
    assert validate() == {"branches": 20, "centers": 1, "orders": 40, "vehicles": 5,
                          "weight_kg": 3125, "geocoding_exact": 21, "rejected": 4}


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


def test_b03_models():
    models = os.environ.get("BADARO_SCHEMA_FILE")
    if not models:
        pytest.skip("B-03 모델은 main 미병합: BADARO_SCHEMA_FILE로 고정 models.py를 지정하세요")
    report = validate(models=Path(models))
    assert report["Order"] == {"raw_rejected": 40, "mapped_passed": 40}
    assert report["Vehicle"] == {"raw_rejected": 5, "mapped_passed": 5}
