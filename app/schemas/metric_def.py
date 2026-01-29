from pydantic import BaseModel


class MetricDefOut(BaseModel):
    id: int
    metric_code: str
    metric_name: str
    metric_category: str
    calc_rule: str | None = None
    refresh_cycle: str | None = None
    description: str | None = None
    is_deleted: bool

    class Config:
        from_attributes = True
