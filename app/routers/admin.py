from fastapi import APIRouter, Depends

from app.deps import get_current_admin
from app.models.admin import Admin
from app.schemas.admin import AdminProfile

router = APIRouter()


@router.get("/profile", response_model=AdminProfile)
def get_profile(current_admin: Admin = Depends(get_current_admin)):
    return current_admin
