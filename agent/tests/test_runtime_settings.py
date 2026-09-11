from pathlib import Path

import pytest

from badaro.runtime.contracts import Settings


@pytest.mark.parametrize(
    "values",
    [
        {"max_model_calls": 7},
        {"max_model_calls": 0},
        {"model_mode": "unknown"},
        {"model_mode": "openai"},
        {"use_mock": False},
    ],
)
def test_invalid_settings_do_not_start_model_or_tools(values):
    with pytest.raises(ValueError):
        Settings(**values)


def test_invalid_env_mode_is_rejected(monkeypatch):
    monkeypatch.setenv("USE_MOCK", "typo")
    with pytest.raises(ValueError):
        Settings.from_env()


def test_packaged_csv_files_match_sources():
    agent = Path(__file__).resolve().parents[1]
    for name in ["centers.csv", "branches.csv", "delivery_orders.csv", "vehicles.csv"]:
        assert (agent / "data" / name).read_bytes() == (agent / "badaro/data" / name).read_bytes()
