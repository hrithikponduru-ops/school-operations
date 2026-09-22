"""Solve the bus CVRP, compare with nearest-neighbor, draw the route map."""

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from stage3_bus_routing.baseline import nearest_neighbor
from stage3_bus_routing.model import load_data, route_length, solve

FIGURES = Path(__file__).resolve().parents[1] / "figures"
COLORS = ["#4C72B0", "#DD8452", "#55A868", "#C44E52"]

def describe(label: str, routes, d) -> float:
    total = sum(route_length(r, d.dist) for r in routes)
    print(f"{label}: {total:.2f} km over {len(routes)} buses")
    for k, r in enumerate(routes, 1):
        names = " -> ".join(d.stops.name[i] for i in r)
        load = sum(d.stops.students[i] for i in r)
        print(f"  Bus {k} ({load}/{d.capacity} students, {route_length(r, d.dist):.2f} km): School -> {names} -> School")
    return total

def main() -> None:
    d = load_data()
    base_routes = nearest_neighbor(d)
    before = describe("Nearest-neighbor baseline", base_routes, d)

    result = solve()
    proof = "proven optimal" if result.proven_optimal else "NOT proven optimal (time limit)"
    print(f"\nStatus: {result.status} ({proof})")
    after = describe("Optimized", result.routes, d)
    print(f"\nSaved {100 * (before - after) / before:.1f}% of driving distance")

    FIGURES.mkdir(exist_ok=True)
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.5), sharex=True, sharey=True)
    for ax, routes, title, total in (
        (axes[0], base_routes, "Nearest-neighbor", before),
        (axes[1], result.routes, "Integer program", after),
    ):
        for k, r in enumerate(routes):
            path = (0, *r, 0)
            ax.plot(d.stops.x_km[list(path)], d.stops.y_km[list(path)], "-o", color=COLORS[k % 4], label=f"Bus {k + 1}")
        ax.plot(0, 0, "ks", markersize=10)
        for i, row in d.stops.iterrows():
            ax.annotate(str(i), (row.x_km, row.y_km), textcoords="offset points", xytext=(4, 4), fontsize=8)
        ax.set_title(f"{title}: {total:.1f} km")
        ax.set_aspect("equal")
        ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(FIGURES / "stage3_routes.png", dpi=150)
    print(f"Saved {FIGURES / 'stage3_routes.png'}")

if __name__ == "__main__":
    main()