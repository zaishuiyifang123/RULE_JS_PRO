from pydantic import BaseModel


class ImportErrorItem(BaseModel):
    row: int
    field: str
    message: str


class ImportSummary(BaseModel):
    table: str
    filename: str
    total: int
    success: int
    failed: int


class ImportResult(BaseModel):
    summary: ImportSummary
    errors: list[ImportErrorItem]
