from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.deps import get_current_admin, get_db
from app.models import MetricDef, MetricSnapshot, Student, Teacher, Course
from app.schemas.metric_def import MetricDefOut
from app.schemas.metric_snapshot import MetricSnapshotOut
from app.schemas.response import OkResponse

router = APIRouter()


def _ensure_metric_defs(db: Session) -> list[MetricDef]:
    defaults = [
        {
            "metric_code": "student_total",
            "metric_name": "学生总数",
            "metric_category": "规模",
            "calc_rule": "student 表记录数",
            "refresh_cycle": "manual",
            "description": "全量学生规模",
        },
        {
            "metric_code": "teacher_total",
            "metric_name": "教师总数",
            "metric_category": "规模",
            "calc_rule": "teacher 表记录数",
            "refresh_cycle": "manual",
            "description": "全量教师规模",
        },
        {
            "metric_code": "course_total",
            "metric_name": "课程总数",
            "metric_category": "规模",
            "calc_rule": "course 表记录数",
            "refresh_cycle": "manual",
            "description": "全量课程规模",
        },
    ]
    items: list[MetricDef] = []
    for default in defaults:
        item = (
            db.query(MetricDef)
            .filter(MetricDef.metric_code == default["metric_code"], MetricDef.is_deleted == False)
            .first()
        )
        if not item:
            item = MetricDef(**default)
            db.add(item)
            db.commit()
            db.refresh(item)
        items.append(item)
    return items


@router.get("/api/metric/def", response_model=OkResponse)
def list_metric_defs(
    db: Session = Depends(get_db),
    current_admin=Depends(get_current_admin),
):
    items = db.query(MetricDef).filter(MetricDef.is_deleted == False).all()
    data = [MetricDefOut.from_orm(item).model_dump() for item in items]
    return OkResponse(data=data)


@router.get("/api/metric/snapshot", response_model=OkResponse)
def list_metric_snapshots(
    metric_code: str | None = None,
    start_time: str | None = Query(default=None, alias="from"),
    end_time: str | None = Query(default=None, alias="to"),
    db: Session = Depends(get_db),
    current_admin=Depends(get_current_admin),
):
    query = db.query(MetricSnapshot).filter(MetricSnapshot.is_deleted == False)

    if metric_code:
        metric = (
            db.query(MetricDef)
            .filter(MetricDef.metric_code == metric_code, MetricDef.is_deleted == False)
            .first()
        )
        if not metric:
            return OkResponse(data=[])
        query = query.filter(MetricSnapshot.metric_id == metric.id)

    if start_time:
        try:
            start_dt = datetime.fromisoformat(start_time)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid from timestamp")
        query = query.filter(MetricSnapshot.stat_time >= start_dt)

    if end_time:
        try:
            end_dt = datetime.fromisoformat(end_time)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid to timestamp")
        query = query.filter(MetricSnapshot.stat_time <= end_dt)

    items = query.order_by(MetricSnapshot.stat_time.desc()).all()
    data = [MetricSnapshotOut.from_orm(item).model_dump() for item in items]
    return OkResponse(data=data)


@router.post("/api/metric/refresh", response_model=OkResponse)
def refresh_metrics(
    db: Session = Depends(get_db),
    current_admin=Depends(get_current_admin),
):
    defs = _ensure_metric_defs(db)
    counts = {
        "student_total": db.query(Student).filter(Student.is_deleted == False).count(),
        "teacher_total": db.query(Teacher).filter(Teacher.is_deleted == False).count(),
        "course_total": db.query(Course).filter(Course.is_deleted == False).count(),
    }

    now = datetime.utcnow()
    snapshots: list[MetricSnapshot] = []
    for metric in defs:
        value = float(counts.get(metric.metric_code, 0))
        snapshot = MetricSnapshot(
            metric_id=metric.id,
            metric_value=value,
            stat_time=now,
            dimension_json=None,
            created_by=current_admin.id,
            updated_by=current_admin.id,
            is_deleted=False,
        )
        snapshots.append(snapshot)
    db.add_all(snapshots)
    db.commit()
    data = [MetricSnapshotOut.from_orm(item).model_dump() for item in snapshots]
    return OkResponse(data=data)
