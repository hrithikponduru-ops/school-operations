"""Generate a reproducible student enrollment file (data/students.csv).

Each student takes one course from each band (math, science, english,
history, elective), like a real school. About one in six students also
adds a second course from a random band, which is what makes a perfect
zero-conflict timetable hard rather than trivial.

Run once: python -m stage2_timetable_ip.make_data
"""

import random
from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).parent / "data"
N_STUDENTS = 45
EXTRA_COURSE_RATE = 1 / 6
SEED = 2026

def generate(courses: pd.DataFrame, rng: random.Random) -> pd.DataFrame:
    by_band = courses.groupby("band")["course_id"].apply(list).to_dict()
    rows = []
    for s in range(1, N_STUDENTS + 1):
        picks = [rng.choice(options) for options in by_band.values()]
        if rng.random() < EXTRA_COURSE_RATE:
            band = rng.choice(list(by_band))
            extra = [c for c in by_band[band] if c not in picks]
            if extra:
                picks = picks + [rng.choice(extra)]
        rows.extend({"student_id": f"S{s:02d}", "course_id": c} for c in picks)
    return pd.DataFrame(rows)

def main() -> None:
    courses = pd.read_csv(DATA_DIR / "courses.csv")
    students = generate(courses, random.Random(SEED))
    students.to_csv(DATA_DIR / "students.csv", index=False)
    print(f"Wrote {len(students)} enrollments for {students.student_id.nunique()} students")

if __name__ == "__main__":
    main()