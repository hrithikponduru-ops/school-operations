"""Nearest-neighbor baseline: the route a dispatcher draws by hand.

Start at the school, always drive to the closest unvisited stop that still
fits on the bus. When nothing fits, return to school and start the next bus.
Feasible (respects capacity) but greedy, so it is the "before" figure.
"""

from stage3_bus_routing.model import RoutingData

def nearest_neighbor(d: RoutingData) -> tuple[tuple[int, ...], ...]:
    unvisited = frozenset(i for i in d.stops.index if i != 0)
    routes: tuple[tuple[int, ...], ...] = ()
    while unvisited:
        route, load, cur = (), 0, 0
        while True:
            fits = [j for j in unvisited if load + d.stops.students[j] <= d.capacity]
            if not fits:
                break
            cur = min(fits, key=lambda j: d.dist[cur, j])
            route, load = (*route, cur), load + d.stops.students[cur]
            unvisited = unvisited - {cur}
        routes = (*routes, route)
    return routes