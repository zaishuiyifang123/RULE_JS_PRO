from app.db.base import Base
from app.db.session import engine
from app.models import (
    Admin,
    AlertEvent,
    AlertRule,
    Attendance,
    AuditLog,
    ChatHistory,
    ClassModel,
    Classroom,
    College,
    Course,
    CourseClass,
    Enroll,
    ImportLog,
    Major,
    MetricDef,
    MetricSnapshot,
    QueryTemplate,
    Score,
    SqlLog,
    StrategyPolicy,
    Student,
    SystemConfig,
    Teacher,
    WorkflowLog,
)


def main() -> None:
    Base.metadata.create_all(bind=engine)
    print("Database tables created.")


if __name__ == "__main__":
    main()
