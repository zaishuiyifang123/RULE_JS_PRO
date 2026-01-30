from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.deps import get_current_admin, get_db
from app.schemas.cockpit import CockpitDashboard
from app.schemas.response import OkResponse
from app.services.cockpit_service import build_dashboard, build_risk_csv

router = APIRouter()


@router.get("/api/cockpit/overview", response_model=OkResponse)
def get_overview(
    term: str | None = None,
    college_id: int | None = Query(None),
    major_id: int | None = Query(None),
    grade_year: int | None = Query(None),
    db: Session = Depends(get_db),
    current_admin=Depends(get_current_admin),
):
    dashboard: CockpitDashboard = build_dashboard(
        db=db, term=term, college_id=college_id, major_id=major_id, grade_year=grade_year
    )
    return OkResponse(data=dashboard.model_dump())


@router.get("/api/cockpit/risk/export")
def export_risk(
    term: str | None = None,
    college_id: int | None = Query(None),
    major_id: int | None = Query(None),
    grade_year: int | None = Query(None),
    db: Session = Depends(get_db),
    current_admin=Depends(get_current_admin),
):
    csv_text = build_risk_csv(
        db=db, term=term, college_id=college_id, major_id=major_id, grade_year=grade_year
    )
    filename = "risk_list.csv"
    headers = {"Content-Disposition": f"attachment; filename={filename}"}
    return StreamingResponse(iter([csv_text]), media_type="text/csv", headers=headers)
