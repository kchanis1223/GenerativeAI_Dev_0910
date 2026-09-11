from datetime import date

import pytest

from badaro.runtime.contracts import RequestDraft
from badaro.runtime.models import OfflineExtractor
from badaro.schemas import ToolErrorException


def test_demo_extractor_preserves_request_when_date_is_supplied():
    result = OfflineExtractor().extract(
        "2026-09-11",
        RequestDraft(
            destination_ids=["S01", "S02", "S03"],
            vehicle_count=5,
        ),
        {},
    )
    assert result.delivery_date == date(2026, 9, 11)
    assert result.destination_ids == ["S01", "S02", "S03"]
    assert result.vehicle_count == 5


def test_demo_does_not_silently_ignore_unsupported_time():
    with pytest.raises(ToolErrorException):
        OfflineExtractor().extract("2026-09-11 마포 8시 출발", RequestDraft(), {})


def test_openai_output_schema_requires_nullable_fields_without_defaults():
    from badaro.runtime.models import strict_schema

    schema = strict_schema(RequestDraft.model_json_schema())
    assert set(schema["required"]) == set(RequestDraft.model_fields)
    assert schema["additionalProperties"] is False
    assert {"type": "null"} in schema["properties"]["delivery_date"]["anyOf"]
    assert "default" not in schema["properties"]["all_destinations"]
    correction = schema["$defs"]["AddressCorrection"]
    assert correction["required"] == ["original", "replacement"]
    assert correction["additionalProperties"] is False
