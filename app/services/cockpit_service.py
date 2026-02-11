from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from sqlalchemy import case, desc, func
from sqlalchemy.orm import Session

from app.models import (
    Attendance,
    ClassModel,
    College,
    Course,
    Enroll,
    Major,
    Score,
    Student,
    Teacher,
)
from app.schemas.cockpit import (
    CockpitDashboard,
    DistributionItem,
    FilterOptions,
    MetricCard,
    OptionItem,
    RankingItem,
    RiskItem,
    TrendPoint,
)

# 计入出勤率的考勤状态（缺勤不计入）
PRESENT_STATUSES = {"出勤", "迟到", "早退"}


def build_dashboard(
    db: Session,
    term: str | None,
    college_id: int | None,
    major_id: int | None,
    grade_year: int | None,
) -> CockpitDashboard:
    """组装驾驶舱总览：筛选项、卡片、趋势、分布、榜单、风险。"""

    def _helper_apply_student_filters(query: Any) -> Any:
        if college_id:
            query = query.filter(Student.college_id == college_id)
        if major_id:
            query = query.filter(Student.major_id == major_id)
        if grade_year:
            query = query.filter(Student.enroll_year == grade_year)
        return query

    terms = [
        row[0]
        for row in db.query(Score.term)
        .filter(Score.is_deleted == False)
        .distinct()
        .order_by(Score.term.desc())
        .all()
    ]
    colleges = (
        db.query(College)
        .filter(College.is_deleted == False)
        .order_by(College.college_name.asc())
        .all()
    )
    majors = (
        db.query(Major)
        .filter(Major.is_deleted == False)
        .order_by(Major.major_name.asc())
        .all()
    )
    grades = [
        row[0]
        for row in db.query(Student.enroll_year)
        .filter(Student.enroll_year.isnot(None))
        .distinct()
        .order_by(Student.enroll_year.desc())
        .all()
    ]
    filter_options = FilterOptions(
        terms=terms,
        colleges=[OptionItem(value=item.id, label=item.college_name) for item in colleges],
        majors=[OptionItem(value=item.id, label=item.major_name) for item in majors],
        grades=[item for item in grades if item is not None],
    )

    student_query = db.query(Student).filter(Student.is_deleted == False)
    student_query = _helper_apply_student_filters(student_query)
    student_total = student_query.count()

    teacher_query = db.query(Teacher).filter(Teacher.is_deleted == False)
    if college_id:
        teacher_query = teacher_query.filter(Teacher.college_id == college_id)
    teacher_total = teacher_query.count()

    course_query = db.query(Course).filter(Course.is_deleted == False)
    if college_id:
        course_query = course_query.filter(Course.college_id == college_id)
    course_total = course_query.count()

    enroll_query = db.query(Enroll, Student).join(Student, Enroll.student_id == Student.id)
    enroll_query = enroll_query.filter(Enroll.is_deleted == False, Student.is_deleted == False)
    enroll_query = _helper_apply_student_filters(enroll_query)
    enroll_total = enroll_query.count()

    fail_case = case((Score.score_value < 60, 1), else_=0)
    score_query = db.query(Score, Student).join(Student, Score.student_id == Student.id)
    score_query = score_query.filter(Score.is_deleted == False, Student.is_deleted == False)
    score_query = _helper_apply_student_filters(score_query)
    if term:
        score_query = score_query.filter(Score.term == term)
    avg_score, fail_sum, score_total = score_query.with_entities(
        func.avg(Score.score_value), func.sum(fail_case), func.count(Score.id)
    ).one()
    score_total = score_total or 0
    fail_sum = fail_sum or 0
    avg_score = float(avg_score) if avg_score is not None else 0.0
    fail_rate = float(fail_sum / score_total) if score_total else 0.0

    present_case = case((Attendance.status.in_(PRESENT_STATUSES), 1), else_=0)
    attendance_query = db.query(Attendance, Student).join(Student, Attendance.student_id == Student.id)
    attendance_query = attendance_query.filter(Attendance.is_deleted == False, Student.is_deleted == False)
    attendance_query = _helper_apply_student_filters(attendance_query)
    present_sum, attendance_total = attendance_query.with_entities(
        func.sum(present_case), func.count(Attendance.id)
    ).one()
    attendance_total = attendance_total or 0
    present_sum = present_sum or 0
    attendance_rate = float(present_sum / attendance_total) if attendance_total else 0.0

    cards = [
        MetricCard(code="student_total", name="学生总数", value=float(student_total)),
        MetricCard(code="teacher_total", name="教师总数", value=float(teacher_total)),
        MetricCard(code="course_total", name="课程总数", value=float(course_total)),
        MetricCard(code="enroll_total", name="选课总数", value=float(enroll_total)),
        MetricCard(code="avg_score", name="平均成绩", value=float(avg_score), unit="分"),
        MetricCard(code="attendance_rate", name="出勤率", value=float(attendance_rate), unit="ratio"),
        MetricCard(code="fail_rate", name="挂科率", value=float(fail_rate), unit="ratio"),
    ]

    today = date.today()
    first_of_month = today.replace(day=1)
    months = []
    cursor = first_of_month
    for _ in range(6):
        months.append(cursor)
        cursor = (cursor - timedelta(days=1)).replace(day=1)
    months = list(reversed(months))

    trend_query = (
        db.query(
            func.date_format(Attendance.attend_date, "%Y-%m"),
            func.sum(present_case),
            func.count(Attendance.id),
        )
        .join(Student, Attendance.student_id == Student.id)
        .filter(Attendance.is_deleted == False, Student.is_deleted == False)
        .filter(Attendance.attend_date >= months[0])
    )
    trend_query = _helper_apply_student_filters(trend_query)
    trend_stats = {
        row[0]: (row[1] or 0, row[2] or 0)
        for row in trend_query.group_by(func.date_format(Attendance.attend_date, "%Y-%m")).all()
    }
    trends: list[TrendPoint] = []
    for month in months:
        key = month.strftime("%Y-%m")
        month_present_sum, month_total = trend_stats.get(key, (0, 0))
        month_rate = float(month_present_sum / month_total) if month_total else 0.0
        trends.append(TrendPoint(date=key, attendance_rate=month_rate))

    college_dist_query = (
        db.query(College.college_name, func.count(Student.id))
        .join(Student, Student.college_id == College.id)
        .filter(College.is_deleted == False, Student.is_deleted == False)
    )
    college_dist_query = _helper_apply_student_filters(college_dist_query)
    college_dist = [
        DistributionItem(name=row[0], value=float(row[1]))
        for row in college_dist_query.group_by(College.id)
        .order_by(desc(func.count(Student.id)))
        .limit(8)
        .all()
    ]

    # 统一成绩段分桶，便于前端结构分布图直接消费
    band_case = case(
        (Score.score_value < 60, "不及格"),
        (Score.score_value < 70, "60-69"),
        (Score.score_value < 80, "70-79"),
        (Score.score_value < 90, "80-89"),
        else_="90+",
    )
    score_band_query = db.query(band_case, func.count(Score.id)).join(
        Student, Score.student_id == Student.id
    )
    score_band_query = score_band_query.filter(Score.is_deleted == False, Student.is_deleted == False)
    score_band_query = _helper_apply_student_filters(score_band_query)
    if term:
        score_band_query = score_band_query.filter(Score.term == term)
    score_band = [
        DistributionItem(name=row[0], value=float(row[1]))
        for row in score_band_query.group_by(band_case).all()
    ]

    course_rank_query = (
        db.query(Course.course_name, func.sum(fail_case), func.count(Score.id))
        .join(Score, Score.course_id == Course.id)
        .join(Student, Score.student_id == Student.id)
        .filter(Course.is_deleted == False, Score.is_deleted == False, Student.is_deleted == False)
    )
    course_rank_query = _helper_apply_student_filters(course_rank_query)
    if term:
        course_rank_query = course_rank_query.filter(Score.term == term)
    course_rankings = []
    for name, course_fail_sum, course_total in (
        course_rank_query.group_by(Course.id)
        .order_by(desc(func.sum(fail_case)))
        .limit(6)
        .all()
    ):
        course_total = course_total or 1
        value = float((course_fail_sum or 0) / course_total)
        course_rankings.append(RankingItem(name=name, value=value))

    absent_case = case((Attendance.status == "缺勤", 1), else_=0)
    class_rank_query = (
        db.query(ClassModel.class_name, func.sum(absent_case), func.count(Attendance.id))
        .join(Student, Student.class_id == ClassModel.id)
        .join(Attendance, Attendance.student_id == Student.id)
        .filter(
            ClassModel.is_deleted == False,
            Student.is_deleted == False,
            Attendance.is_deleted == False,
        )
    )
    class_rank_query = _helper_apply_student_filters(class_rank_query)
    class_rankings = []
    for name, absent_sum, class_total in (
        class_rank_query.group_by(ClassModel.id)
        .order_by(desc(func.sum(absent_case)))
        .limit(6)
        .all()
    ):
        class_total = class_total or 1
        value = float((absent_sum or 0) / class_total)
        class_rankings.append(RankingItem(name=name, value=value))

    risk_query = (
        db.query(Student.real_name, Student.student_no, func.sum(fail_case))
        .join(Score, Score.student_id == Student.id)
        .filter(Student.is_deleted == False, Score.is_deleted == False)
    )
    risk_query = _helper_apply_student_filters(risk_query)
    if term:
        risk_query = risk_query.filter(Score.term == term)
    risks = []
    for name, student_no, risk_fail_sum in (
        risk_query.group_by(Student.id)
        .order_by(desc(func.sum(fail_case)))
        .limit(200)
        .all()
    ):
        count = int(risk_fail_sum or 0)
        if count >= 5:
            level = "high"
        elif count >= 2:
            level = "medium"
        else:
            level = "low"
        risks.append(
            RiskItem(
                level=level,
                title=f"{name}（{student_no}）",
                message=f"挂科 {count} 门",
            )
        )

    return CockpitDashboard(
        filters=filter_options,
        cards=cards,
        trends=trends,
        distributions={
            "college_students": college_dist,
            "score_band": score_band,
        },
        rankings={
            "course_fail_rate": course_rankings,
            "class_absent_rate": class_rankings,
        },
        risks=risks,
    )


def build_risk_csv(
    db: Session, term: str | None, college_id: int | None, major_id: int | None, grade_year: int | None
) -> str:
    """导出风险榜单 CSV。"""

    fail_case = case((Score.score_value < 60, 1), else_=0)
    risk_query = (
        db.query(Student.real_name, Student.student_no, func.sum(fail_case))
        .join(Score, Score.student_id == Student.id)
        .filter(Student.is_deleted == False, Score.is_deleted == False)
    )
    if college_id:
        risk_query = risk_query.filter(Student.college_id == college_id)
    if major_id:
        risk_query = risk_query.filter(Student.major_id == major_id)
    if grade_year:
        risk_query = risk_query.filter(Student.enroll_year == grade_year)
    if term:
        risk_query = risk_query.filter(Score.term == term)

    lines = ["name,level,message"]
    for name, student_no, fail_sum in (
        risk_query.group_by(Student.id)
        .order_by(desc(func.sum(fail_case)))
        .all()
    ):
        count = int(fail_sum or 0)
        if count >= 5:
            level = "high"
        elif count >= 2:
            level = "medium"
        else:
            level = "low"
        title = f"{name}（{student_no}）".replace(",", " ")
        message = f"挂科 {count} 门".replace(",", " ")
        lines.append(f"{title},{level},{message}")
    return "\n".join(lines) + "\n"

