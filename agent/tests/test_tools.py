import inspect

import pytest

from badaro.tools import (
    geocode_address,
    get_available_vehicles,
    get_delivery_orders,
    optimize_dispatch,
)


@pytest.mark.parametrize(
    ("tool", "parameters"),
    [
        (get_delivery_orders, ["depot_id", "delivery_date", "destination_ids", "product_names"]),
        (
            get_available_vehicles,
            ["depot_id", "delivery_date", "vehicle_count", "excluded_vehicle_ids"],
        ),
        (geocode_address, ["address"]),
        (optimize_dispatch, ["order_ids", "vehicle_ids", "constraints"]),
    ],
)
def test_b03_tool_signatures_are_importable(tool, parameters) -> None:
    assert list(inspect.signature(tool).parameters) == parameters


@pytest.mark.parametrize(
    "tool",
    [get_delivery_orders, get_available_vehicles, geocode_address, optimize_dispatch],
)
def test_b03_tools_are_stubs(tool) -> None:
    with pytest.raises(NotImplementedError):
        tool(*([None] * len(inspect.signature(tool).parameters)))
