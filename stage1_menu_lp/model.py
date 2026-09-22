"""Stage 1: the school-lunch diet problem as a linear program.

Decision variable x_i = servings of food i (continuous, 0 <= x_i <= u_i)
Objective         min sum_i c_i * x_i          (total cost)
Constraints       L_n <= sum_i a_{n,i} * x_i <= U_n   for each nutrient n

Every symbol above maps to one line of code below. See README.md for the
derivation and the sensitivity (shadow price) discussion.
"""

from dataclasses import dataclass
from pathlib import Path

import pandas as pd
import pulp

DATA_DIR = Path(__file__).parent / "data"

@dataclass(frozen=True)
class MenuResult:
    status: str
    total_cost: float
    servings: dict[str, float]        # food -> servings chosen
    nutrients: dict[str, float]       # nutrient -> amount delivered
    shadow_prices: dict[str, float]   # constraint name -> dual value ($ per unit)

def load_data(data_dir: Path = DATA_DIR) -> tuple[pd.DataFrame, pd.DataFrame]:
    foods = pd.read_csv(data_dir / "foods.csv").set_index("food")
    targets = pd.read_csv(data_dir / "targets.csv").set_index("nutrient")
    return foods, targets

def build_model(foods: pd.DataFrame, targets: pd.DataFrame) -> tuple[pulp.LpProblem, dict]:
    prob = pulp.LpProblem("school_lunch", pulp.LpMinimize)

    # x_i: servings of each food, bounded by the max a student would eat.
    x = {
        food: pulp.LpVariable(f"x_{i}", lowBound=0, upBound=row.max_servings)
        for i, (food, row) in enumerate(foods.iterrows())
    }

    # Objective: total cost = sum of (cost per serving) * (servings).
    prob += pulp.lpSum(foods.loc[f, "cost_per_serving"] * x[f] for f in x), "total_cost"

    # One constraint per nutrient bound. Blank cells in targets.csv mean "no bound".
    for nutrient, row in targets.iterrows():
        delivered = pulp.lpSum(foods.loc[f, nutrient] * x[f] for f in x)
        if pd.notna(row["min"]):
            prob += delivered >= row["min"], f"{nutrient}_min"
        if pd.notna(row["max"]):
            prob += delivered <= row["max"], f"{nutrient}_max"

    return prob, x

def solve(data_dir: Path = DATA_DIR) -> MenuResult:
    foods, targets = load_data(data_dir)
    prob, x = build_model(foods, targets)
    prob.solve(pulp.PULP_CBC_CMD(msg=False))

    servings = {f: round(v.value() or 0.0, 4) for f, v in x.items()}
    nutrients = {
        n: round(sum(foods.loc[f, n] * servings[f] for f in servings), 2)
        for n in targets.index
    }
    # .pi is the dual value: how much the optimal cost changes per unit change
    # in that constraint's right-hand side. Zero means the constraint is slack.
    shadow_prices = {name: round(c.pi or 0.0, 4) for name, c in prob.constraints.items()}

    return MenuResult(
        status=pulp.LpStatus[prob.status],
        total_cost=round(pulp.value(prob.objective), 4),
        servings=servings,
        nutrients=nutrients,
        shadow_prices=shadow_prices,
    )