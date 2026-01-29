from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.deps import get_current_admin, get_db
from app.models import Course, Student, Teacher
from app.schemas.cockpit import AlertItem, CockpitOverview, MetricCard, TrendPoint
from app.schemas.response import OkResponse

router = APIRouter()


def _build_placeholder_trends(days: int = 7) -> list[TrendPoint]:
    today = datetime.utcnow().date()
    points: list[TrendPoint] = []
    for idx in range(days):
        day = today - timedelta(days=days - 1 - idx)
        points.append(
            TrendPoint(
                date=day.isoformat(),
                attendance_rate=0.0,
                fail_rate=0.0,
            )
        )
    return points


@router.get("/api/cockpit/overview", response_model=OkResponse)
def get_overview(
    db: Session = Depends(get_db),
    current_admin=Depends(get_current_admin),
):
    student_total = db.query(Student).filter(Student.is_deleted == False).count()
    teacher_total = db.query(Teacher).filter(Teacher.is_deleted == False).count()
    course_total = db.query(Course).filter(Course.is_deleted == False).count()

    cards = [
        MetricCard(code="student_total", name="学生总数", value=float(student_total)),
        MetricCard(code="teacher_total", name="教师总数", value=float(teacher_total)),
        MetricCard(code="course_total", name="课程总数", value=float(course_total)),
    ]

    trends = _build_placeholder_trends()
    alerts: list[AlertItem] = []

    payload = CockpitOverview(cards=cards, trends=trends, alerts=alerts)
    return OkResponse(data=payload.model_dump())
