"""Stage 2 tests: the hard rules must hold, and the IP must beat the greedy plan.

Optimality itself is NOT asserted here. Proving it takes about a minute, so
tests use a short time limit and check feasibility plus improvement. Run
`python -m stage2_timetable_ip.run` for the proven-optimal figure.
"""

from collections import Counter

import pytest

from stage2_timetable_ip.baseline import greedy_schedule
from stage2_timetable_ip.model import count_conflicts, load_data, solve

TEST_TIME_LIMIT_S = 30


@pytest.fixture(scope="module")
def data():
    return load_data()


@pytest.fixture(scope="module")
def result():
    return solve(time_limit_s=TEST_TIME_LIMIT_S)


def test_every_course_scheduled_exactly_once(result, data):
    """Constraint (1): a course left out of the timetable is not a schedule at all."""
    assert set(result.assignment) == set(data.courses.index)


def test_no_room_double_booked(result):
    """Constraint (2): two classes cannot share a room in the same period."""
    slots = Counter(result.assignment.values())
    assert max(slots.values()) == 1

def test_no_teacher_double_booked(result, data):
    """Constraint (3): the objective would happily clone teachers to reduce student conflicts."""
    teacher_periods = Counter((data.courses.loc[c, "teacher"], p) for c, (p, _) in result.assignment.items())
    assert max(teacher_periods.values()) == 1

def test_every_class_fits_its_room(result, data):
    """Constraint (4): enforced by not creating the variable, so verify it survived."""
    for c, (_, r) in result.assignment.items():
        assert data.courses.loc[c, "enroll"] <= data.rooms[r]

def test_objective_matches_independent_conflict_count(result, data):
    """The solver's objective must mean what the write-up says it means."""
    assert result.conflicts == count_conflicts(result.assignment, data.students)

def test_ip_has_no_more_conflicts_than_greedy(result, data):
    """The entire point of the model. Greedy respects (1)-(4) too, so it is a feasible
    solution, and an optimizer must never return something worse than a feasible plan."""
    greedy = count_conflicts(greedy_schedule(data), data.students)
    assert result.conflicts <= greedy
    assert result.conflicts < greedy, "IP found no improvement over greedy; check the model"

def test_greedy_baseline_is_itself_feasible(data):
    """If the baseline broke hard rules, the before/after comparison would be unfair."""
    greedy = greedy_schedule(data)
    assert set(greedy) == set(data.courses.index)
    assert max(Counter(greedy.values()).values()) == 1