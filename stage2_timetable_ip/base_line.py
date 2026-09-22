"""Greedy baseline: what a person with a spreadsheet would do.

Take courses in file order. Put each in the first period and room where the
room is free, the teacher is free, and the class fits. Ignore students.
This respects the hard constraints (1)-(4) but not (5), so the number of
student conflicts it produces is the "before" figure the IP is judged against.
"""

from stage2_timetable_ip.model import TimetableData

def greedy_schedule(d: TimetableData) -> dict[str, tuple[int, str]]:
    assignment: dict[str, tuple[int, str]] = {}
    for c, row in d.courses.iterrows():
        slot = next(
            (p, r)
            for p in d.periods
            for r in d.rooms
            if row.enroll <= d.rooms[r]
            and not any(a == (p, r) for a in assignment.values())
            and not any(
                a[0] == p and d.courses.loc[other, "teacher"] == row.teacher
                for other, a in assignment.items()
            )
        )
        assignment = {**assignment, c: slot}
    return assignment