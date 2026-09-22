"""Solve the lunch LP, print the menu and shadow prices, save a chart."""

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from stage1_menu_lp.model import solve

FIGURES = Path(__file__).resolve().parents[1] / "figures"

def main() -> None:
    result = solve()
    print(f"Status: {result.status}")
    print(f"Minimum cost: ${result.total_cost:.2f}\n")

    print("Menu (servings):")
    for food, qty in result.servings.items():
        if qty > 1e-6:
            print(f"  {food:<20} {qty:.2f}")

    print("\nNutrients delivered:")
    for n, amount in result.nutrients.items():
        print(f"  {n:<12} {amount:.1f}")

    print("\nShadow prices ($ change in cost per unit of nutrient bound):")
    for name, pi in result.shadow_prices.items():
        print(f"  {name:<14} {pi:+.4f}")

    FIGURES.mkdir(exist_ok=True)
    chosen = {f: q for f, q in result.servings.items() if q > 1e-6}
    fig, ax = plt.subplots(figsize=(7, 3.5))
    ax.barh(list(chosen), list(chosen.values()), color="#4C72B0")
    ax.set_xlabel("Servings")
    ax.set_title(f"Cheapest lunch meeting all nutrient targets: ${result.total_cost:.2f}")
    fig.tight_layout()
    fig.savefig(FIGURES / "stage1_menu.png", dpi=150)
    print(f"\nSaved {FIGURES / 'stage1_menu.png'}")

if __name__ == "__main__":
    main()