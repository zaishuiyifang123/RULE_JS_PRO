from pydantic import BaseModel


class OptionItem(BaseModel):
    value: int | str
    label: str


class FilterOptions(BaseModel):
    terms: list[str]
    colleges: list[OptionItem]
    majors: list[OptionItem]
    grades: list[int]


class MetricCard(BaseModel):
    code: str
    name: str
    value: float
    unit: str | None = None
    delta: float | None = None


class TrendPoint(BaseModel):
    date: str
    attendance_rate: float
    fail_rate: float
    avg_score: float | None = None


class DistributionItem(BaseModel):
    name: str
    value: float


class RankingItem(BaseModel):
    name: str
    value: float
    extra: str | None = None


class RiskItem(BaseModel):
    level: str
    title: str
    message: str


class CockpitDashboard(BaseModel):
    filters: FilterOptions
    cards: list[MetricCard]
    trends: list[TrendPoint]
    distributions: dict[str, list[DistributionItem]]
    rankings: dict[str, list[RankingItem]]
    risks: list[RiskItem]
