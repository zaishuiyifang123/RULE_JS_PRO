from pydantic import BaseModel


class AdminProfile(BaseModel):
    id: int
    username: str
    real_name: str | None = None
    phone: str | None = None
    email: str | None = None
    status: str

    class Config:
        from_attributes = True
