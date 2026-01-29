from pydantic import BaseModel


class MetricCard(BaseModel):
    code: str
    name: str
    value: float


class TrendPoint(BaseModel):
    date: str
    attendance_rate: float
    fail_rate: float


class AlertItem(BaseModel):
    level: str
    title: str
    message: str


class CockpitOverview(BaseModel):
    cards: list[MetricCard]
    trends: list[TrendPoint]
    alerts: list[AlertItem]
