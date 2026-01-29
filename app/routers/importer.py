from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session

from app.deps import get_current_admin, get_db
from app.schemas.response import OkResponse
from app.services.import_service import import_data

router = APIRouter()


@router.post("/api/import/{table}", response_model=OkResponse)
async def import_file(
    table: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_admin=Depends(get_current_admin),
):
    content = await file.read()
    result = import_data(table, file.filename or "", content, db, current_admin.id)
    return OkResponse(data=result)
