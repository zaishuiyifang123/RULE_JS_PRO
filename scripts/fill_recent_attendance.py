import argparse
import os
import random
import sys
from datetime import date, timedelta

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from app.db.session import SessionLocal
from app.models.attendance import Attendance
from app.models.course_class import CourseClass
from app.models.student import Student


def month_starts(anchor: date, count: int) -> list[date]:
    # 生成从最早到最新的月份起始日期
    months: list[date] = []
    y, m = anchor.year, anchor.month
    for i in range(count - 1, -1, -1):
        mm = m - i
        yy = y
        while mm <= 0:
            mm += 12
            yy -= 1
        months.append(date(yy, mm, 1))
    return months


def next_month_start(d: date) -> date:
    if d.month == 12:
        return date(d.year + 1, 1, 1)
    return date(d.year, d.month + 1, 1)


def main() -> None:
    parser = argparse.ArgumentParser(description="Fill recent attendance data")
    parser.add_argument("--per-month", type=int, default=2000, help="records per month")
    parser.add_argument("--seed", type=int, default=42, help="random seed")
    parser.add_argument("--wipe", action="store_true", help="wipe recent 6 months attendance")
    args = parser.parse_args()

    random.seed(args.seed)

    db = SessionLocal()
    try:
        student_ids = [row[0] for row in db.query(Student.id).filter(Student.is_deleted == False).all()]
        class_ids = [row[0] for row in db.query(CourseClass.id).filter(CourseClass.is_deleted == False).all()]
        if not student_ids:
            raise RuntimeError("no students found")
        if not class_ids:
            raise RuntimeError("no course_class found")

        anchor = date.today().replace(day=1)
        months = month_starts(anchor, 6)
        start_date = months[0]

        if args.wipe:
            db.query(Attendance).filter(Attendance.attend_date >= start_date).delete(
                synchronize_session=False
            )
            db.commit()

        present_choices = ["出勤", "迟到", "早退"]
        absent_choices = ["缺勤"]

        for month_start in months:
            month_end = next_month_start(month_start)
            days = (month_end - month_start).days
            target_rate = random.uniform(0.70, 0.95)
            present_count = int(round(args.per_month * target_rate))
            absent_count = max(args.per_month - present_count, 0)
            records: list[Attendance] = []
            status_pool: list[str] = []
            status_pool.extend(random.choices(present_choices, k=present_count))
            status_pool.extend(random.choices(absent_choices, k=absent_count))
            random.shuffle(status_pool)
            for status in status_pool:
                attend_day = month_start + timedelta(days=random.randrange(days))
                records.append(
                    Attendance(
                        student_id=random.choice(student_ids),
                        course_class_id=random.choice(class_ids),
                        attend_date=attend_day,
                        status=status,
                        created_by=1,
                        updated_by=1,
                        is_deleted=False,
                    )
                )
            db.bulk_save_objects(records)
            db.commit()
            actual_rate = present_count / args.per_month if args.per_month else 0
            print(f"{month_start.strftime('%Y-%m')} inserted {len(records)} rate={actual_rate:.2%}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
