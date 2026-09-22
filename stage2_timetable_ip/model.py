"""Stage 2: course timetabling as an integer program.

Sets    C courses, P periods, R rooms, T teachers, S students
Data    enroll_c  students in course c
        cap_r     seats in room r
        C_t       courses taught by teacher t
        C_s       courses taken by student s

Variables
        x[c,p,r] in {0,1}   course c meets in period p, room r
        y[c,p]   in {0,1}   course c meets in period p   (y = sum_r x, a helper)
        v[s,p]   >= 0 int   number of extra courses student s has in period p
                            beyond the one they can attend (a "conflict")

Objective   min  sum_{s,p} v[s,p]

Constraints
  (1) each course scheduled once      sum_{p,r} x[c,p,r] = 1        for all c
  (2) room holds one course           sum_c x[c,p,r] <= 1           for all p,r
  (3) teacher in one place            sum_{c in C_t} y[c,p] <= 1    for all t,p
  (4) room must fit the class         x[c,p,r] = 0 if enroll_c > cap_r (domain reduction)
  (5) count conflicts                 sum_{c in C_s} y[c,p] - 1 <= v[s,p]   for all s,p

(1)-(4) are hard rules a school cannot break. (5) is soft: we count violations
and minimize them, so the model always has a feasible answer and reports the
best achievable number of conflicts.

Symmetry breaking (does not change the optimum, only removes duplicate
solutions the solver would otherwise explore):
  (S1) periods are interchangeable, so fix the first course into period 1.
  (S2) rooms with identical capacity are interchangeable, so a period may
       use the second identical room only if it also uses the first.
"""

import json
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
import pulp

DATA_DIR = Path(__file__).parent / "data"

@dataclass(frozen=True)
class TimetableData:
    courses: pd.DataFrame          # index course_id, columns name, band, teacher, enroll
    students: dict[str, list[str]] # student_id -> course_ids
    periods: list[int]
    rooms: dict[str, int]          # room -> capacity

@dataclass(frozen=True)
class TimetableResult:
    status: str
    proven_optimal: bool           # False if the solver hit the time limit
    conflicts: int
    assignment: dict[str, tuple[int, str]] # course_id -> (period, room)

def load_data(data_dir: Path = DATA_DIR) -> TimetableData:
    config = json.loads((data_dir / "config.json").read_text())
    courses = pd.read_csv(data_dir / "courses.csv").set_index("course_id")
    enrollments = pd.read_csv(data_dir / "students.csv")
    courses = courses.assign(enroll=enrollments.course_id.value_counts()).fillna({"enroll": 0})
    students = enrollments.groupby("student_id")["course_id"].apply(list).to_dict()
    return TimetableData(
        courses=courses,
        students=students,
        periods=list(range(1, config["periods"] + 1)),
        rooms=config["rooms"],
    )

def build_model(d: TimetableData) -> tuple[pulp.LpProblem, dict, dict]:
    prob = pulp.LpProblem("timetable", pulp.LpMinimize)
    C, P, R = list(d.courses.index), d.periods, list(d.rooms)

    # (4) Domain reduction: only create x[c,p,r] when the room can hold the class.
    x = {
        (c, p, r): pulp.LpVariable(f"x_{c}_{p}_{r}", cat="Binary")
        for c in C for p in P for r in R
        if d.courses.loc[c, "enroll"] <= d.rooms[r]
    }
    y = {(c, p): pulp.lpSum(x[c, p, r] for r in R if (c, p, r) in x) for c in C for p in P}
    v = {
        (s, p): pulp.LpVariable(f"v_{s}_{p}", lowBound=0, cat="Integer")
        for s in d.students for p in P
    }

    prob += pulp.lpSum(v.values()), "total_conflicts"

    for c in C:
        prob += pulp.lpSum(y[c, p] for p in P) == 1, f"once_{c}"                 # (1)
    for p in P:
        for r in R:
            prob += pulp.lpSum(x[c, p, r] for c in C if (c, p, r) in x) <= 1, f"room_{r}_{p}"      # (2)
        for t, taught in d.courses.groupby("teacher").groups.items():        # (3)
            prob += pulp.lpSum(y[c, p] for c in taught) <= 1, f"teacher_{t.replace(' ', '')}_{p}"
        for s, taken in d.students.items():                                  # (5)
            prob += pulp.lpSum(y[c, p] for c in taken) - 1 <= v[s, p], f"conflict_{s}_{p}"

    prob += y[C[0], P[0]] == 1, "sym_first_course_period1"           # (S1)
    for p in P:                                                      # (S2)
        for r_first, r_second in _identical_room_pairs(d.rooms):
            used_first = pulp.lpSum(x[c, p, r_first] for c in C if (c, p, r_first) in x)
            used_second = pulp.lpSum(x[c, p, r_second] for c in C if (c, p, r_second) in x)
            prob += used_second <= used_first, f"sym_rooms_{r_first}_{r_second}_{p}"

    return prob, x, v

def _identical_room_pairs(rooms: dict[str, int]) -> list[tuple[str, str]]:
    """Consecutive pairs of rooms sharing a capacity, in file order."""
    by_cap: dict[int, list[str]] = {}
    for r, cap in rooms.items():
        by_cap = {**by_cap, cap: by_cap.get(cap, []) + [r]}
    return [(names[i], names[i + 1]) for names in by_cap.values() for i in range(len(names) - 1)]

def solve(data_dir: Path = DATA_DIR, time_limit_s: int = 120) -> TimetableResult:
    d = load_data(data_dir)
    prob, x, _ = build_model(d)
    prob.solve(pulp.PULP_CBC_CMD(msg=False, timeLimit=time_limit_s))
    assignment = {c: (p, r) for (c, p, r), var in x.items() if (var.value() or 0) > 0.5}
    return TimetableResult(
        status=pulp.LpStatus[prob.status],
        proven_optimal=prob.sol_status == pulp.LpSolutionOptimal,
        conflicts=int(round(pulp.value(prob.objective))),
        assignment=assignment,
    )

def count_conflicts(assignment: dict[str, tuple[int, str]], students: dict[str, list[str]]) -> int:
    """Independent check: for each student and period, extra courses beyond one."""
    total = 0
    for taken in students.values():
        periods = [assignment[c][0] for c in taken]
        total += sum(max(periods.count(p) - 1, 0) for p in set(periods))
    return total