from datetime import datetime
from pydantic import BaseModel


class MetricSnapshotOut(BaseModel):
    id: int
    metric_id: int
    metric_value: float
    stat_time: datetime
    dimension_json: dict | None = None
    is_deleted: bool

    class Config:
        from_attributes = True
