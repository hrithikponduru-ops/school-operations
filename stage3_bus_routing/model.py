"""Stage 3: school bus routing as a capacitated vehicle routing problem (CVRP).

Sets    N = stops {1..n}, V = N + {0} where 0 is the school (depot)
Data    d_ij  straight-line distance between i and j
        q_j   students waiting at stop j
        K     buses available, Q  seats per bus

Variables
  x[i,j] in {0,1}  a bus drives directly from i to j
  u[j]  >= 0       students on board after picking up stop j

Objective   min sum_{i != j} d_ij * x[i,j]

Constraints
  (1) arrive at every stop once       sum_i x[i,j] = 1        for j in N
  (2) leave every stop once           sum_j x[i,j] = 1        for i in N
  (3) at most K buses leave school    sum_j x[0,j] <= K
  (4) load propagates along a route   u[j] >= u[i] + q_j - Q(1 - x[i,j])  i,j in N
  (5) load bounds                     q_j <= u[j] <= Q        for j in N

(4) is the Miller-Tucker-Zemlin trick. When x[i,j] = 1 it forces u[j] >= u[i] + q_j,
so the load strictly increases along a route. A cycle that never touches the
school would need u to increase forever around the loop, which is impossible.
So (4) kills sub-tours AND enforces capacity in a single constraint family.
"""

import json
import math
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
import pulp

DATA_DIR = Path(__file__).parent / "data"

@dataclass(frozen=True)
class RoutingData:
    stops: pd.DataFrame       # index stop_id, columns name, x_km, y_km, students
    dist: dict[tuple[int, int], float]
    buses: int
    capacity: int

@dataclass(frozen=True)
class RoutingResult:
    status: str
    proven_optimal: bool
    total_km: float
    routes: tuple[tuple[int, ...], ...]  # each route: stop ids in visit order, no depot

def load_data(data_dir: Path = DATA_DIR) -> RoutingData:
    config = json.loads((data_dir / "config.json").read_text())
    stops = pd.read_csv(data_dir / "stops.csv").set_index("stop_id")
    dist = {
        (i, j): math.hypot(stops.x_km[i] - stops.x_km[j], stops.y_km[i] - stops.y_km[j])
        for i in stops.index for j in stops.index if i != j
    }
    return RoutingData(stops=stops, dist=dist, buses=config["buses"], capacity=config["capacity"])

def build_model(d: RoutingData) -> tuple[pulp.LpProblem, dict, dict]:
    prob = pulp.LpProblem("bus_routes", pulp.LpMinimize)
    V = list(d.stops.index)
    N = [i for i in V if i != 0]
    q, Q, K = d.stops.students, d.capacity, d.buses

    x = {(i, j): pulp.LpVariable(f"x_{i}_{j}", cat="Binary") for i in V for j in V if i != j}
    u = {j: pulp.LpVariable(f"u_{j}", lowBound=q[j], upBound=Q) for j in N}   # (5)

    prob += pulp.lpSum(d.dist[a] * x[a] for a in x), "total_distance"

    for j in N:
        prob += pulp.lpSum(x[i, j] for i in V if i != j) == 1, f"arrive_{j}"    # (1)
        prob += pulp.lpSum(x[j, i] for i in V if i != j) == 1, f"leave_{j}"     # (2)
    prob += pulp.lpSum(x[0, j] for j in N) <= K, "buses_out"                    # (3)
    for i in N:
        for j in N:
            if i != j:
                prob += u[j] >= u[i] + q[j] - Q * (1 - x[i, j]), f"load_{i}_{j}" # (4)

    return prob, x, u

def extract_routes(x_values: dict[tuple[int, int], int]) -> tuple[tuple[int, ...], ...]:
    """Follow chosen arcs from the depot until each route returns to it."""
    nxt = {i: j for (i, j), val in x_values.items() if val}
    starts = [j for (i, j), val in x_values.items() if val and i == 0]
    routes = []
    for first in starts:
        route, cur = [], first
        while cur != 0:
            route.append(cur)
            cur = nxt[cur]
        routes.append(tuple(route))
    return tuple(routes)

def solve(data_dir: Path = DATA_DIR, time_limit_s: int = 120) -> RoutingResult:
    d = load_data(data_dir)
    prob, x, _ = build_model(d)
    prob.solve(pulp.PULP_CBC_CMD(msg=False, timeLimit=time_limit_s))
    x_values = {a: int(round(var.value() or 0)) for a, var in x.items()}
    return RoutingResult(
        status=pulp.LpStatus[prob.status],
        proven_optimal=prob.sol_status == pulp.LpSolutionOptimal,
        total_km=round(pulp.value(prob.objective), 3),
        routes=extract_routes(x_values),
    )

def route_length(route: tuple[int, ...], dist: dict[tuple[int, int], float]) -> float:
    """Depot -> stops in order -> depot."""
    path = (0, *route, 0)
    return sum(dist[a, b] for a, b in zip(path, path[1:]))