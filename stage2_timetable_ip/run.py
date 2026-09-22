"""Solve the timetable IP, compare against the greedy baseline, save a chart."""

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from stage2_timetable_ip.base_line import greedy_schedule
from stage2_timetable_ip.model import count_conflicts, load_data, solve

FIGURES = Path(__file__).resolve().parents[1] / "figures"

def main() -> None:
    d = load_data()
    baseline = greedy_schedule(d)
    before = count_conflicts(baseline, d.students)

    result = solve()
    after = count_conflicts(result.assignment, d.students)
    assert after == result.conflicts, "solver objective and independent count disagree"

    proof = "proven optimal" if result.proven_optimal else "best found within time limit, NOT proven optimal"
    print(f"Status: {result.status} ({proof})")
    print(f"Student conflicts: greedy baseline {before} -> optimized {after}\n")
    print(f"{'Course':<10}{'Teacher':<12}{'Size':>5}   Period  Room")
    for c, (p, r) in sorted(result.assignment.items(), key=lambda kv: kv[1]):
        row = d.courses.loc[c]
        print(f"{c:<10}{row.teacher:<12}{int(row.enroll):>5}   {p}       {r}")

    FIGURES.mkdir(exist_ok=True)
    fig, ax = plt.subplots(figsize=(5, 3.5))
    ax.bar(["Greedy baseline", "Integer program"], [before, after], color=["#C44E52", "#4C72B0"])
    ax.set_ylabel("Student schedule conflicts")
    ax.set_title(f"{len(d.courses)} courses, {len(d.students)} students, {len(d.periods)} periods")
    for i, val in enumerate([before, after]):
        ax.text(i, val + 0.3, str(val), ha="center")
    fig.tight_layout()
    fig.savefig(FIGURES / "stage2_conflicts.png", dpi=150)
    print(f"\nSaved {FIGURES / 'stage2_conflicts.png'}")

if __name__ == "__main__":
    main()