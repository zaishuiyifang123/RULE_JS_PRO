import argparse
import os
import random
import sys
from datetime import date, datetime, timedelta

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from sqlalchemy import text

from app.db.session import SessionLocal, engine
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


COLLEGES = [
    "信息工程学院",
    "智能制造学院",
    "管理学院",
    "人文学院",
    "经济与贸易学院",
    "外国语学院",
    "理学院",
    "艺术与设计学院",
]

MAJOR_POOL = [
    "计算机科学与技术",
    "软件工程",
    "人工智能",
    "数据科学与大数据技术",
    "网络工程",
    "信息安全",
    "自动化",
    "机械设计制造及其自动化",
    "电气工程及其自动化",
    "土木工程",
    "财务管理",
    "市场营销",
    "人力资源管理",
    "工商管理",
    "会计学",
    "汉语言文学",
    "新闻传播学",
    "英语",
    "日语",
    "数学与应用数学",
    "物理学",
    "化学",
    "数字媒体艺术",
    "视觉传达设计",
]

SURNAMES = list("赵钱孙李周吴郑王冯陈褚卫蒋沈韩杨朱秦尤许何吕施张孔曹严华金魏陶姜")
GIVEN_MALE = list("伟强磊军洋勇杰峰超斌凯涛博鑫浩宇航鹏昊晨皓")
GIVEN_FEMALE = list("芳娜敏静丽艳萍燕洁琳婷雪颖慧丹媛倩欣雅琪")

FOREIGN_NAMES = [
    "Liam", "Noah", "Emma", "Olivia", "Ava", "Mia", "Ethan", "Lucas", "Sophia", "Isabella"
]

PHONE_PREFIX = ["130", "131", "132", "133", "135", "136", "137", "138", "139", "150", "151", "152", "157", "158", "159", "170", "171", "173", "175", "176", "177", "178", "180", "181", "182", "183", "185", "186", "187", "188", "189", "190", "191", "195", "199"]

AREA_CODES = ["110101", "120101", "310101", "420102", "420106", "420107", "440103", "440106", "510104"]


def truncate_all() -> None:
    tables = [
        "attendance",
        "score",
        "enroll",
        "course_class",
        "student",
        "class",
        "major",
        "college",
        "teacher",
        "course",
        "classroom",
        "metric_snapshot",
        "metric_def",
        "alert_event",
        "alert_rule",
        "chat_history",
        "workflow_log",
        "sql_log",
        "strategy_policy",
        "query_template",
        "audit_log",
        "system_config",
        "import_log",
    ]
    with engine.begin() as conn:
        conn.execute(text("SET FOREIGN_KEY_CHECKS = 0"))
        for table in tables:
            conn.execute(text(f"TRUNCATE TABLE {table}"))
        conn.execute(text("SET FOREIGN_KEY_CHECKS = 1"))


def random_phone() -> str:
    return random.choice(PHONE_PREFIX) + "".join(random.choice("0123456789") for _ in range(8))


def random_chinese_name(gender: str) -> str:
    surname = random.choice(SURNAMES)
    pool = GIVEN_MALE if gender == "男" else GIVEN_FEMALE
    given = random.choice(pool)
    if random.random() < 0.3:
        given += random.choice(pool)
    return surname + given


def random_foreign_name() -> str:
    return random.choice(FOREIGN_NAMES)


def generate_id_card(birth: date) -> str:
    base = random.choice(AREA_CODES)
    birth_str = birth.strftime("%Y%m%d")
    seq = f"{random.randint(100, 999)}"
    body = base + birth_str + seq
    weights = [7, 9, 10, 5, 8, 4, 2, 1, 6, 3, 7, 9, 10, 5, 8, 4, 2]
    check_map = ["1", "0", "X", "9", "8", "7", "6", "5", "4", "3", "2"]
    total = sum(int(n) * w for n, w in zip(body, weights))
    return body + check_map[total % 11]


def score_level(score_value: float) -> str:
    if score_value >= 90:
        return "A"
    if score_value >= 80:
        return "B"
    if score_value >= 70:
        return "C"
    if score_value >= 60:
        return "D"
    return "F"


def build_schedule(building: str, room: str) -> str:
    weekday = random.choice(["周一", "周二", "周三", "周四", "周五"])
    slot = random.choice(["1-2节", "3-4节", "5-6节", "7-8节"])
    return f"{weekday} {slot} {building}{room}"


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate mock data for Edu Cockpit")
    parser.add_argument("--seed", type=int, default=42, help="random seed")
    parser.add_argument("--truncate", action="store_true", help="truncate tables before insert")
    args = parser.parse_args()

    random.seed(args.seed)

    if args.truncate:
        truncate_all()

    db = SessionLocal()
    try:
        admin = db.query(Admin).filter(Admin.is_deleted == False).first()
        admin_id = admin.id if admin else None

        colleges = []
        for idx, name in enumerate(COLLEGES, start=1):
            colleges.append(
                College(
                    college_name=f"三峡科技MOCK大学{name}",
                    college_code=f"C{idx:02d}",
                    description=f"{name}（三峡科技MOCK大学）",
                    created_by=admin_id,
                    updated_by=admin_id,
                    is_deleted=False,
                )
            )
        db.add_all(colleges)
        db.commit()
        for item in colleges:
            db.refresh(item)

        majors = []
        major_total = 64
        for idx in range(major_total):
            college = colleges[idx % len(colleges)]
            major_name = MAJOR_POOL[idx % len(MAJOR_POOL)]
            if idx >= len(MAJOR_POOL):
                major_name = f"{major_name}{idx // len(MAJOR_POOL) + 1}"
            majors.append(
                Major(
                    major_name=major_name,
                    major_code=f"M{idx+1:03d}",
                    college_id=college.id,
                    degree_type="本科",
                    description=f"{major_name}（三峡科技MOCK大学）",
                    created_by=admin_id,
                    updated_by=admin_id,
                    is_deleted=False,
                )
            )
        db.add_all(majors)
        db.commit()
        for item in majors:
            db.refresh(item)
        major_by_id = {item.id: item for item in majors}

        classes = []
        class_sizes = []
        total_students = 20000
        class_count = len(majors) * 6
        base_size = total_students // class_count
        extra = total_students % class_count
        for i in range(class_count):
            class_sizes.append(base_size + (1 if i < extra else 0))

        class_index = 0
        for major in majors:
            for cls_idx in range(1, 7):
                grade_year = random.choice([2022, 2023, 2024, 2025])
                classes.append(
                    ClassModel(
                        class_name=f"{grade_year}级{major.major_name}{cls_idx}班",
                        class_code=f"CL{major.major_code}{cls_idx}",
                        major_id=major.id,
                        grade_year=grade_year,
                        head_teacher_id=None,
                        student_count=class_sizes[class_index],
                        created_by=admin_id,
                        updated_by=admin_id,
                        is_deleted=False,
                    )
                )
                class_index += 1
        db.add_all(classes)
        db.commit()
        for item in classes:
            db.refresh(item)

        classrooms = []
        for idx in range(1, 81):
            building = random.choice(["A", "B", "C", "D"])
            room_no = f"{building}{random.randint(101, 599)}"
            classrooms.append(
                Classroom(
                    building=f"教学楼{building}",
                    room_no=room_no,
                    capacity=random.randint(50, 90),
                    status="available",
                    created_by=admin_id,
                    updated_by=admin_id,
                    is_deleted=False,
                )
            )
        db.add_all(classrooms)
        db.commit()
        for item in classrooms:
            db.refresh(item)

        teachers = []
        titles = ["讲师", "副教授", "教授", "助教"]
        for idx in range(1, 1101):
            college = random.choice(colleges)
            gender = random.choice(["男", "女"])
            name = random_chinese_name(gender)
            teachers.append(
                Teacher(
                    teacher_no=f"T{idx:05d}",
                    real_name=name,
                    gender=gender,
                    id_card=None,
                    birth_date=date(1975, 1, 1) + timedelta(days=random.randint(0, 12000)),
                    phone=random_phone(),
                    email=f"t{idx:05d}@mock.edu.cn",
                    title=random.choice(titles),
                    college_id=college.id,
                    status="在职",
                    created_by=admin_id,
                    updated_by=admin_id,
                    is_deleted=False,
                )
            )
        db.add_all(teachers)
        db.commit()
        for item in teachers:
            db.refresh(item)

        courses = []
        course_total = 300
        for idx in range(1, course_total + 1):
            college = random.choice(colleges)
            courses.append(
                Course(
                    course_name=f"{college.college_name[-4:]}课程{idx}",
                    course_code=f"K{idx:04d}",
                    credit=random.choice([2.0, 3.0, 4.0]),
                    hours=random.choice([32, 48, 64]),
                    course_type=random.choice(["必修", "选修"]),
                    college_id=college.id,
                    description=f"{college.college_name}课程{idx}",
                    created_by=admin_id,
                    updated_by=admin_id,
                    is_deleted=False,
                )
            )
        db.add_all(courses)
        db.commit()
        for item in courses:
            db.refresh(item)

        # assign head teachers
        for cls in classes:
            major = major_by_id.get(cls.major_id)
            if not major:
                continue
            related_teachers = [t for t in teachers if t.college_id == major.college_id]
            if related_teachers:
                cls.head_teacher_id = random.choice(related_teachers).id
        db.add_all(classes)
        db.commit()

        # build course classes
        course_classes_by_class = {}
        term = "2025-2026-1"
        for cls in classes:
            major = major_by_id.get(cls.major_id)
            if not major:
                continue
            college_courses = [c for c in courses if c.college_id == major.college_id]
            selected = random.sample(college_courses, k=6)
            course_classes = []
            for course in selected:
                teacher = random.choice([t for t in teachers if t.college_id == major.college_id])
                room = random.choice(classrooms)
                course_classes.append(
                    CourseClass(
                        course_id=course.id,
                        class_id=cls.id,
                        teacher_id=teacher.id,
                        term=term,
                        schedule_info=build_schedule(room.building, room.room_no),
                        max_students=cls.student_count,
                        created_by=admin_id,
                        updated_by=admin_id,
                        is_deleted=False,
                    )
                )
            db.add_all(course_classes)
            db.commit()
            for item in course_classes:
                db.refresh(item)
            course_classes_by_class[cls.id] = course_classes

        # students
        student_seq = 1
        students_by_class = {}
        for idx, cls in enumerate(classes):
            size = class_sizes[idx]
            students = []
            major = major_by_id.get(cls.major_id)
            if not major:
                continue
            for _ in range(size):
                gender = random.choice(["男", "女"])
                if random.random() < 0.9:
                    name = random_chinese_name(gender)
                else:
                    name = random_foreign_name()
                enroll_year = cls.grade_year or random.choice([2022, 2023, 2024, 2025])
                birth = date(enroll_year - 18, 1, 1) + timedelta(days=random.randint(0, 600))
                students.append(
                    Student(
                        student_no=f"S{student_seq:05d}",
                        real_name=name,
                        gender=gender,
                        id_card=generate_id_card(birth),
                        birth_date=birth,
                        phone=random_phone(),
                        email=f"s{student_seq:05d}@student.mock.edu.cn",
                        address="湖北省宜昌市西陵区三峡科技MOCK大学",
                        class_id=cls.id,
                        major_id=major.id,
                        college_id=major.college_id,
                        enroll_year=enroll_year,
                        status="在读",
                        created_by=admin_id,
                        updated_by=admin_id,
                        is_deleted=False,
                    )
                )
                student_seq += 1
            db.add_all(students)
            db.commit()
            for item in students:
                db.refresh(item)
            students_by_class[cls.id] = students

        # enrollments, scores, attendance
        attendance_status = ["出勤", "出勤", "出勤", "迟到", "缺勤", "早退"]
        for cls in classes:
            course_classes = course_classes_by_class.get(cls.id, [])
            students = students_by_class.get(cls.id, [])
            if not course_classes or not students:
                continue
            enrollments = []
            scores = []
            attends = []
            for student in students:
                for course_class in course_classes:
                    enrollments.append(
                        Enroll(
                            student_id=student.id,
                            course_class_id=course_class.id,
                            enroll_time=datetime.utcnow(),
                            status="enrolled",
                            created_by=admin_id,
                            updated_by=admin_id,
                            is_deleted=False,
                        )
                    )
                    score_value = round(random.uniform(50, 100), 1)
                    scores.append(
                        Score(
                            student_id=student.id,
                            course_id=course_class.course_id,
                            course_class_id=course_class.id,
                            term=term,
                            score_value=score_value,
                            score_level=score_level(score_value),
                            created_by=admin_id,
                            updated_by=admin_id,
                            is_deleted=False,
                        )
                    )
                    for offset in range(3):
                        attends.append(
                            Attendance(
                                student_id=student.id,
                                course_class_id=course_class.id,
                                attend_date=date(2025, 9, 1) + timedelta(days=offset * 7),
                                status=random.choice(attendance_status),
                                created_by=admin_id,
                                updated_by=admin_id,
                                is_deleted=False,
                            )
                        )
            db.bulk_save_objects(enrollments)
            db.bulk_save_objects(scores)
            db.bulk_save_objects(attends)
            db.commit()

        # seed metrics and config
        metric_defs = [
            MetricDef(
                metric_code="student_total",
                metric_name="学生总数",
                metric_category="规模",
                calc_rule="student 表记录数",
                refresh_cycle="manual",
                description="全量学生规模",
                created_by=admin_id,
                updated_by=admin_id,
                is_deleted=False,
            ),
            MetricDef(
                metric_code="teacher_total",
                metric_name="教师总数",
                metric_category="规模",
                calc_rule="teacher 表记录数",
                refresh_cycle="manual",
                description="全量教师规模",
                created_by=admin_id,
                updated_by=admin_id,
                is_deleted=False,
            ),
            MetricDef(
                metric_code="course_total",
                metric_name="课程总数",
                metric_category="规模",
                calc_rule="course 表记录数",
                refresh_cycle="manual",
                description="全量课程规模",
                created_by=admin_id,
                updated_by=admin_id,
                is_deleted=False,
            ),
        ]
        db.add_all(metric_defs)
        db.commit()

        policies = [
            StrategyPolicy(
                policy_name="高风险更新确认",
                policy_type="风险",
                policy_rule={"require_confirm": True},
                status="active",
                description="高风险操作需二次确认",
                created_by=admin_id,
                updated_by=admin_id,
                is_deleted=False,
            )
        ]
        db.add_all(policies)

        configs = [
            SystemConfig(
                config_key="school_name",
                config_value="三峡科技MOCK大学",
                description="学校名称",
                created_by=admin_id,
                updated_by=admin_id,
                is_deleted=False,
            )
        ]
        db.add_all(configs)
        db.commit()

        print("mock data generated.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
