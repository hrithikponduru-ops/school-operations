"""Stage 3 tests: every student picked up, no bus overloaded, shorter than the hand method."""

from collections import Counter

import pytest

from stage3_bus_routing.baseline import nearest_neighbor
from stage3_bus_routing.model import load_data, route_length, solve


@pytest.fixture(scope="module")
def data():
    return load_data()


@pytest.fixture(scope="module")
def result():
    return solve()


def test_every_stop_visited_exactly_once(result, data):
    """Constraints (1)+(2): a shorter plan that skips a stop leaves students on the curb."""
    visited = Counter(stop for route in result.routes for stop in route)
    assert set(visited) == set(data.stops.index) - {0}
    assert max(visited.values()) == 1

def test_no_bus_exceeds_capacity(result, data):
    """Constraint (4)+(5): the MTZ load variables are the only thing enforcing seats."""
    for route in result.routes:
        assert sum(data.stops.students[i] for i in route) <= data.capacity

def test_no_more_buses_than_available(result, data):
    """Constraint (3): the objective would prefer one bus per stop if it could."""
    assert len(result.routes) <= data.buses

def test_no_subtours(result):
    """MTZ must have killed loops that never return to school. extract_routes would
    hang or drop stops if a subtour existed, so route reconstruction is the check."""
    assert all(len(r) > 0 for r in result.routes)

def test_objective_equals_sum_of_route_lengths(result, data):
    """The solver's number must be the number the write-up reports."""
    recomputed = sum(route_length(r, data.dist) for r in result.routes)
    assert result.total_km == pytest.approx(recomputed, abs=1e-3)

def test_optimizer_beats_nearest_neighbor(result, data):
    """Nearest-neighbor is feasible, so the optimum can never be longer than it."""
    baseline_km = sum(route_length(r, data.dist) for r in nearest_neighbor(data))
    assert result.total_km <= baseline_km + 1e-6