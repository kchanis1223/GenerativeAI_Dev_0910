from datetime import date

from badaro.runtime.backend import Backend
from badaro.runtime.contracts import Settings
from badaro.runtime.data import depot_profile
from badaro.schemas import DispatchConstraints, DispatchRuntimeContext


def test_demo_uses_existing_orders_and_validates_saved_routes():
    backend = Backend(Settings())
    orders = backend.orders("CENTER-NR", date(2026, 9, 11), ["S01", "S02", "S03"], None)
    vehicles = backend.vehicles("CENTER-NR", date(2026, 9, 11), None, [])
    context = DispatchRuntimeContext(
        depot_id="CENTER-NR",
        origin=depot_profile("CENTER-NR").origin,
        orders={o.order_id: o for o in orders},
        vehicles={v.vehicle_id: v for v in vehicles},
        geocodes={o.address: backend.geocode(o.address) for o in orders},
    )
    result = backend.dispatch(
        list(context.orders),
        list(context.vehicles),
        DispatchConstraints(
            priority="normal",
            departure_time="2026-09-11T06:00:00+09:00",
        ),
        context,
    )
    assert result.status == "success"
    assert sum(len(r.stops) for r in result.routes) == 6
    assert all(s.eta is None for r in result.routes for s in r.stops)
