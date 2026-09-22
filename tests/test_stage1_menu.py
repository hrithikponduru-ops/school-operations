"""Stage 1 tests: a cheaper menu that breaks a nutrition rule is not a menu.

Each test names the modeling promise it protects, so if the model changes and
a test fails, the failure message says which promise was broken.
"""

import pandas as pd
import pytest

from stage1_menu_lp.model import DATA_DIR, load_data, solve

@pytest.fixture(scope="module")
def result():
    return solve()

@pytest.fixture(scope="module")
def data():
    return load_data()

def test_solver_reports_optimal(result):
    assert result.status == "Optimal"

def test_every_nutrient_bound_is_respected(result, data):
    """The objective only counts cost, so nutrition must be enforced by constraints."""
    _, targets = data
    for nutrient, row in targets.iterrows():
        delivered = result.nutrients[nutrient]
        if pd.notna(row["min"]):
            assert delivered >= row["min"] - 1e-6, f"{nutrient} below minimum"
        if pd.notna(row["max"]):
            assert delivered <= row["max"] + 1e-6, f"{nutrient} above maximum"

def test_servings_stay_within_realistic_limits(result, data):
    """Without the upper bound the LP would serve one food 10 times. The bound is the model's realism."""
    foods, _ = data
    for food, qty in result.servings.items():
        assert 0 <= qty <= foods.loc[food, "max_servings"] + 1e-6

def test_optimal_cost_beats_a_hand_built_feasible_menu(result):
    """Optimality means no feasible menu is cheaper. This menu is feasible by hand-check:
    1 chicken + 2 rice + 1 beans + 1 apple = 800 kcal, 48.5 g protein, 18.5 g fiber, 297 mg sodium."""
    hand_built_cost = 1.20 + 2 * 0.20 + 0.35 + 0.50
    assert result.total_cost <= hand_built_cost + 1e-6
    assert result.total_cost > 0

def test_shadow_prices_are_zero_on_slack_constraints(result, data):
    """A dual price only exists where a bound is binding. If a slack constraint showed a
    nonzero price the sensitivity section of the write-up would be wrong."""
    _, targets = data
    for name, pi in result.shadow_prices.items():
        nutrient, side = name.rsplit("_", 1)
        bound = targets.loc[nutrient, side]
        delivered = result.nutrients[nutrient]
        if abs(delivered - bound) > 1e-6:
            assert pi == pytest.approx(0.0, abs=1e-6), f"{name} is slack but priced"