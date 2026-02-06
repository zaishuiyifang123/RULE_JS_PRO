import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from app.db.base import Base
import app.models  # noqa: F401


CORE_TABLES = [
    "college",
    "major",
    "class",
    "student",
    "teacher",
    "course",
    "course_class",
    "enroll",
    "score",
    "attendance",
]

TABLE_TITLE_CN = {
    "college": "学院信息",
    "major": "专业信息",
    "class": "班级信息",
    "student": "学生信息",
    "teacher": "教师信息",
    "course": "课程信息",
    "course_class": "教学班信息",
    "enroll": "选课记录",
    "score": "成绩记录",
    "attendance": "考勤记录",
}

TABLE_INFO_TAGS = {
    "college": ["学院", "学院名称", "学院编码", "学院说明"],
    "major": ["专业", "专业名称", "学院", "学位类型"],
    "class": ["班级", "班级编码", "年级", "班主任"],
    "student": ["学生", "学号", "姓名", "班级", "年级", "学院"],
    "teacher": ["教师", "工号", "姓名", "职称", "学院"],
    "course": ["课程", "课程编码", "学分", "课时", "学院"],
    "course_class": ["教学班", "课程", "班级", "教师", "学期"],
    "enroll": ["选课", "学生", "教学班", "状态", "选课时间"],
    "score": ["成绩", "学生", "课程", "学期", "分数"],
    "attendance": ["考勤", "学生", "教学班", "日期", "状态"],
}

TABLE_ALIASES = {
    "college": ["学院", "学院信息", "院系"],
    "major": ["专业", "专业信息", "学科"],
    "class": ["班级", "行政班", "班"],
    "student": ["学生", "学籍", "学生信息"],
    "teacher": ["教师", "老师", "教职工"],
    "course": ["课程", "课", "课程信息"],
    "course_class": ["教学班", "开课", "授课班"],
    "enroll": ["选课", "选课记录", "选课状态"],
    "score": ["成绩", "分数", "考试成绩"],
    "attendance": ["考勤", "出勤", "缺勤"],
}

TABLE_RELATED = {
    "college": [("major", "专业"), ("student", "学生"), ("teacher", "教师"), ("course", "课程")],
    "major": [("college", "学院"), ("class", "班级"), ("student", "学生")],
    "class": [("major", "专业"), ("student", "学生"), ("course_class", "教学班")],
    "student": [("enroll", "选课"), ("score", "成绩"), ("attendance", "考勤")],
    "teacher": [("course_class", "教学班"), ("course", "课程"), ("class", "班级")],
    "course": [("course_class", "教学班"), ("score", "成绩"), ("college", "学院")],
    "course_class": [("course", "课程"), ("class", "班级"), ("teacher", "教师"), ("enroll", "选课"), ("attendance", "考勤")],
    "enroll": [("student", "学生"), ("course_class", "教学班"), ("course", "课程")],
    "score": [("student", "学生"), ("course", "课程"), ("course_class", "教学班")],
    "attendance": [("student", "学生"), ("course_class", "教学班")],
}

TABLE_BUSINESS_KEYS = {
    "student": "student_no",
    "teacher": "teacher_no",
    "course": "course_code",
    "class": "class_code",
    "major": "major_code",
    "college": "college_code",
}

FILTER_MAPPINGS = {
    "student_name": {"table": "student", "column": "real_name", "operator": "like", "description": "按学生姓名检索"},
    "student_no": {"table": "student", "column": "student_no", "operator": "=", "description": "按学号精确过滤"},
    "teacher_name": {"table": "teacher", "column": "real_name", "operator": "like", "description": "按教师姓名检索"},
    "course_name": {"table": "course", "column": "course_name", "operator": "like", "description": "按课程名称检索"},
    "term": {"table": "score", "column": "term", "operator": "=", "description": "按学期过滤"},
    "grade_year": {"table": "student", "column": "enroll_year", "operator": "=", "description": "按入学年份过滤"},
    "college_id": {"table": "student", "column": "college_id", "operator": "=", "description": "按学院过滤"},
    "major_id": {"table": "student", "column": "major_id", "operator": "=", "description": "按专业过滤"},
    "class_id": {"table": "student", "column": "class_id", "operator": "=", "description": "按班级过滤"},
}

INTENT_MAPPINGS = {
    "chat": {
        "description": "闲聊或非教务业务查询",
        "route": "direct_reply",
        "history_scope": "仅使用最近4条user消息判断是否追问",
        "output_fields": ["intent", "is_followup", "merged_query", "rewritten_query", "confidence"],
    },
    "business_query": {
        "description": "教务业务查询（成绩、考勤、选课、学籍、课程、教师等）",
        "route": "task_parse",
        "history_scope": "仅使用最近4条user消息判断是否追问",
        "output_fields": ["intent", "is_followup", "merged_query", "rewritten_query", "confidence"],
        "tables": CORE_TABLES,
    },
}

TASK010_WORKFLOW = {
    "name": "langgraph_task010",
    "description": "教务问答工作流（分节点编排，失败回跳）",
    "history_window": {"role": "user", "size": 4},
    "nodes": [
        {"name": "intent_recognition", "order": 1, "description": "识别意图并判断追问，输出业务化问题"},
        {"name": "task_parse", "order": 2, "description": "解析实体/指标/维度/过滤条件"},
        {"name": "hybrid_retrieval", "order": 3, "description": "BM25+Embedding 混合检索召回候选表"},
        {"name": "llm_rerank_top5", "order": 4, "description": "LLM 重排候选表并返回 TOP5"},
        {"name": "hidden_context_discovery", "order": 5, "description": "探索库内真实值（term/status/名称映射）"},
        {"name": "sql_generate", "order": 6, "description": "基于任务+TOP5表+隐藏上下文生成 SQL（仅 CTE 分解）"},
        {"name": "sql_validate", "order": 7, "description": "执行验证 SQL 可执行性"},
        {"name": "result_return", "order": 8, "description": "返回结果数据与简要业务解释"},
    ],
    "edges": [
        {"from": "intent_recognition", "to": "task_parse", "when": "intent=business_query"},
        {"from": "task_parse", "to": "hybrid_retrieval", "when": "always"},
        {"from": "hybrid_retrieval", "to": "llm_rerank_top5", "when": "always"},
        {"from": "llm_rerank_top5", "to": "hidden_context_discovery", "when": "always"},
        {"from": "hidden_context_discovery", "to": "sql_generate", "when": "always"},
        {"from": "sql_generate", "to": "sql_validate", "when": "always"},
        {"from": "sql_validate", "to": "hidden_context_discovery", "when": "validate_failed"},
        {"from": "sql_validate", "to": "result_return", "when": "validate_success"},
    ],
    "retry_policy": {"from_node": "sql_validate", "to_node": "hidden_context_discovery", "max_retry": 2},
}

RETRIEVAL_POLICY = {
    "strategy": "bm25_embedding_hybrid",
    "steps": ["bm25_recall", "embedding_recall", "merge", "llm_rerank_top5"],
    "top_k": 5,
    "output_fields": ["tables", "columns", "joins", "score", "source"],
}

SQL_GENERATION_POLICY = {
    "mode": "cte_only",
    "description": "SQL 生成阶段必须使用 CTE 分解（WITH ... AS ...），不允许直接简单查询。",
    "forbidden_patterns": ["simple_select_no_cte"],
}

SQL_TEMPLATES = [
    {
        "id": "tpl_query_score_by_student_course_term",
        "intent": "business_query",
        "scenario": "query_score",
        "name": "按学生+课程+学期查询成绩",
        "description": "使用 CTE 分解查询某学生在某学期某课程的成绩明细。",
        "tables": ["student", "score", "course"],
        "params": [":student_name", ":course_name", ":term"],
        "generation_mode": "cte_only",
        "sql": (
            "WITH target_student AS (\n"
            "    SELECT id, student_no, real_name\n"
            "    FROM student\n"
            "    WHERE real_name = :student_name\n"
            "),\n"
            "target_course AS (\n"
            "    SELECT id, course_name\n"
            "    FROM course\n"
            "    WHERE course_name = :course_name\n"
            "),\n"
            "target_scores AS (\n"
            "    SELECT sc.student_id, sc.course_id, sc.term, sc.score_value\n"
            "    FROM score sc\n"
            "    JOIN target_student ts ON sc.student_id = ts.id\n"
            "    JOIN target_course tc ON sc.course_id = tc.id\n"
            "    WHERE sc.term = :term\n"
            ")\n"
            "SELECT ts.student_no, ts.real_name, tc.course_name, tsc.term, tsc.score_value\n"
            "FROM target_scores tsc\n"
            "JOIN target_student ts ON tsc.student_id = ts.id\n"
            "JOIN target_course tc ON tsc.course_id = tc.id;"
        ),
    },
    {
        "id": "tpl_query_score_avg_by_course_term",
        "intent": "business_query",
        "scenario": "query_score",
        "name": "按课程与学期统计平均分",
        "description": "使用 CTE 分解统计课程在指定学期的平均分。",
        "tables": ["score", "course"],
        "params": [":course_name", ":term"],
        "generation_mode": "cte_only",
        "sql": (
            "WITH target_course AS (\n"
            "    SELECT id, course_name\n"
            "    FROM course\n"
            "    WHERE course_name = :course_name\n"
            "),\n"
            "term_scores AS (\n"
            "    SELECT sc.course_id, sc.term, sc.score_value\n"
            "    FROM score sc\n"
            "    JOIN target_course tc ON sc.course_id = tc.id\n"
            "    WHERE sc.term = :term\n"
            ")\n"
            "SELECT tc.course_name, ts.term, AVG(ts.score_value) AS avg_score\n"
            "FROM term_scores ts\n"
            "JOIN target_course tc ON ts.course_id = tc.id\n"
            "GROUP BY tc.course_name, ts.term;"
        ),
    },
    {
        "id": "tpl_query_attendance_by_student_term",
        "intent": "business_query",
        "scenario": "query_attendance",
        "name": "按学生与时间范围查询考勤",
        "description": "使用 CTE 分解查询学生在时间范围内的考勤记录。",
        "tables": ["attendance", "student", "course_class", "course"],
        "params": [":student_name", ":start_date", ":end_date"],
        "generation_mode": "cte_only",
        "sql": (
            "WITH target_student AS (\n"
            "    SELECT id, student_no, real_name\n"
            "    FROM student\n"
            "    WHERE real_name = :student_name\n"
            "),\n"
            "attendance_scope AS (\n"
            "    SELECT a.student_id, a.course_class_id, a.attend_date, a.status\n"
            "    FROM attendance a\n"
            "    JOIN target_student ts ON a.student_id = ts.id\n"
            "    WHERE a.attend_date BETWEEN :start_date AND :end_date\n"
            "),\n"
            "class_course AS (\n"
            "    SELECT cc.id AS course_class_id, cc.term, c.course_name\n"
            "    FROM course_class cc\n"
            "    JOIN course c ON cc.course_id = c.id\n"
            ")\n"
            "SELECT ts.student_no, ts.real_name, cc.term, cc.course_name, a.attend_date, a.status\n"
            "FROM attendance_scope a\n"
            "JOIN target_student ts ON a.student_id = ts.id\n"
            "JOIN class_course cc ON a.course_class_id = cc.course_class_id;"
        ),
    },
    {
        "id": "tpl_query_enroll_by_class_term",
        "intent": "business_query",
        "scenario": "query_enroll",
        "name": "按班级与学期查询选课",
        "description": "使用 CTE 分解查询班级在指定学期的选课记录。",
        "tables": ["enroll", "student", "class", "course_class", "course"],
        "params": [":class_name", ":term"],
        "generation_mode": "cte_only",
        "sql": (
            "WITH target_class AS (\n"
            "    SELECT id, class_name\n"
            "    FROM class\n"
            "    WHERE class_name = :class_name\n"
            "),\n"
            "class_students AS (\n"
            "    SELECT s.id, s.student_no, s.real_name, s.class_id\n"
            "    FROM student s\n"
            "    JOIN target_class tc ON s.class_id = tc.id\n"
            "),\n"
            "term_course_class AS (\n"
            "    SELECT cc.id AS course_class_id, cc.term, c.course_name\n"
            "    FROM course_class cc\n"
            "    JOIN course c ON cc.course_id = c.id\n"
            "    WHERE cc.term = :term\n"
            "),\n"
            "enroll_scope AS (\n"
            "    SELECT e.student_id, e.course_class_id, e.status\n"
            "    FROM enroll e\n"
            ")\n"
            "SELECT tc.class_name, cs.student_no, cs.real_name, tcc.course_name, tcc.term, es.status\n"
            "FROM enroll_scope es\n"
            "JOIN class_students cs ON es.student_id = cs.id\n"
            "JOIN term_course_class tcc ON es.course_class_id = tcc.course_class_id\n"
            "JOIN target_class tc ON cs.class_id = tc.id;"
        ),
    },
]

FIELD_LABELS = {
    "id": "主键ID",
    "student_no": "学号",
    "teacher_no": "工号",
    "real_name": "姓名",
    "gender": "性别",
    "id_card": "身份证号",
    "birth_date": "出生日期",
    "phone": "手机号",
    "email": "邮箱",
    "address": "家庭住址",
    "class_id": "班级ID",
    "major_id": "专业ID",
    "college_id": "学院ID",
    "enroll_year": "入学年份",
    "status": "状态",
    "class_name": "班级名称",
    "class_code": "班级编码",
    "grade_year": "年级",
    "head_teacher_id": "班主任教师ID",
    "student_count": "班级人数",
    "major_name": "专业名称",
    "major_code": "专业编码",
    "degree_type": "学位类型",
    "description": "说明",
    "college_name": "学院名称",
    "college_code": "学院编码",
    "title": "职称",
    "course_name": "课程名称",
    "course_code": "课程编码",
    "credit": "学分",
    "hours": "学时",
    "course_type": "课程类型",
    "course_id": "课程ID",
    "teacher_id": "教师ID",
    "term": "学期",
    "schedule_info": "排课信息",
    "max_students": "最大人数",
    "course_class_id": "教学班ID",
    "enroll_time": "选课时间",
    "score_value": "成绩值",
    "score_level": "成绩等级",
    "attend_date": "考勤日期",
    "building": "教学楼",
    "room_no": "教室编号",
    "capacity": "容量",
    "created_at": "创建时间",
    "updated_at": "更新时间",
    "created_by": "创建人",
    "updated_by": "更新人",
    "is_deleted": "逻辑删除标记",
}

FIELD_EXAMPLES = {
    "id": "1",
    "student_no": "S00001",
    "teacher_no": "T00001",
    "real_name": "张三",
    "gender": "男",
    "id_card": "42010620040816725X",
    "birth_date": "2004-08-16",
    "phone": "13800138000",
    "email": "zhangsan@student.mock.edu.cn",
    "address": "湖北省宜昌市西陵区三峡科技MOCK大学",
    "class_id": "1",
    "major_id": "1",
    "college_id": "1",
    "enroll_year": "2024",
    "class_name": "2024级计算机科学与技术1班",
    "class_code": "CLS2024CS01",
    "grade_year": "2024",
    "head_teacher_id": "1",
    "student_count": "45",
    "major_name": "计算机科学与技术",
    "major_code": "CS001",
    "degree_type": "本科",
    "description": "示例说明",
    "college_name": "三峡科技MOCK大学信息工程学院",
    "college_code": "COL001",
    "title": "副教授",
    "course_name": "高等数学A",
    "course_code": "MATH101",
    "credit": "4.0",
    "hours": "64",
    "course_type": "必修",
    "course_id": "1",
    "teacher_id": "1",
    "term": "2025-2026-1",
    "schedule_info": "周一1-2节/教一101",
    "max_students": "120",
    "course_class_id": "1",
    "enroll_time": "2026-02-01 09:00:00",
    "score_value": "86.5",
    "score_level": "良好",
    "attend_date": "2026-02-06",
    "building": "教一楼",
    "room_no": "101",
    "capacity": "120",
    "created_at": "2026-02-06 10:00:00",
    "updated_at": "2026-02-06 10:00:00",
    "created_by": "1",
    "updated_by": "1",
    "is_deleted": "false",
}

STATUS_EXAMPLES = {
    "student": "在读",
    "teacher": "active",
    "enroll": "selected",
    "attendance": "出勤",
    "course_class": "active",
    "class": "active",
    "course": "active",
    "major": "active",
    "college": "active",
}


def base_column_description(column_name: str, raw_comment: str | None) -> str:
    """优先使用模型注释，缺失时用中文字段词典兜底。"""
    if raw_comment and raw_comment.strip():
        return raw_comment.strip()
    if column_name in FIELD_LABELS:
        return FIELD_LABELS[column_name]
    return f"{column_name} 字段"


def column_example_value(table_name: str, column_name: str, col_type: str) -> str:
    if column_name == "status":
        return STATUS_EXAMPLES.get(table_name, "active")
    if column_name in FIELD_EXAMPLES:
        return FIELD_EXAMPLES[column_name]
    lower = col_type.lower()
    if "int" in lower:
        return "1"
    if "float" in lower or "double" in lower or "decimal" in lower:
        return "1.0"
    if "date" in lower and "time" in lower:
        return "2026-02-06 10:00:00"
    if "date" in lower:
        return "2026-02-06"
    if "bool" in lower:
        return "false"
    return "示例值"


def column_description(table_name: str, column_name: str, raw_comment: str | None, col_type: str) -> str:
    desc = base_column_description(column_name, raw_comment)
    example = column_example_value(table_name, column_name, col_type)
    return f"{desc}（示例值：{example}）"


def is_indexed(table, column_name: str) -> bool:
    for idx in table.indexes:
        if any(col.name == column_name for col in idx.columns):
            return True
    col = table.columns[column_name]
    return bool(getattr(col, "index", False))


def is_unique(table, column_name: str) -> bool:
    col = table.columns[column_name]
    if getattr(col, "unique", False):
        return True
    for constraint in table.constraints:
        if constraint.__class__.__name__ == "UniqueConstraint":
            names = [c.name for c in constraint.columns]
            if len(names) == 1 and names[0] == column_name:
                return True
    return False


def table_description(table_name: str, table) -> str:
    """按指定风格输出单行描述：表+信息范围+主键+相关表。"""
    title = TABLE_TITLE_CN.get(table_name, "业务信息")
    tags = TABLE_INFO_TAGS.get(table_name, [title])
    pk_cols = [col for col in table.columns if col.primary_key]
    if pk_cols:
        pk_col = pk_cols[0]
        pk_desc = column_description(table_name, pk_col.name, pk_col.comment, str(pk_col.type))
        pk_text = f"主键 {pk_col.name}({pk_desc})"
    else:
        pk_text = "主键 无"

    business_key_text = ""
    business_key = TABLE_BUSINESS_KEYS.get(table_name)
    if business_key and business_key in table.columns:
        col = table.columns[business_key]
        business_key_text = f"；业务键 {business_key}({column_description(table_name, col.name, col.comment, str(col.type))})"

    related_items = TABLE_RELATED.get(table_name, [])
    if related_items:
        related = ", ".join([f"{tb}({cn})" for tb, cn in related_items])
        related_text = f"相关: {related}"
    else:
        related_text = "相关: 无"

    return f"表 {table_name} {title}; {'/'.join(tags)}; {pk_text}{business_key_text}; {related_text}"


def build_tables(meta_tables: dict[str, Any]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for table_name in CORE_TABLES:
        table = meta_tables[table_name]
        cols: list[dict[str, Any]] = []
        for col in table.columns:
            fk_refs = []
            for fk in col.foreign_keys:
                target_col = fk.column
                fk_refs.append(
                    {
                        "table": target_col.table.name,
                        "column": target_col.name,
                    }
                )
            cols.append(
                {
                    "name": col.name,
                    "type": str(col.type),
                    "nullable": bool(col.nullable),
                    "is_pk": bool(col.primary_key),
                    "is_indexed": is_indexed(table, col.name),
                    "is_unique": is_unique(table, col.name),
                    "description": column_description(table_name, col.name, col.comment, str(col.type)),
                    "fk_refs": fk_refs,
                }
            )

        items.append(
            {
                "name": table_name,
                "description": table_description(table_name, table),
                "aliases": TABLE_ALIASES.get(table_name, []),
                "columns": cols,
            }
        )
    return items


def build_joins(meta_tables: dict[str, Any]) -> list[dict[str, Any]]:
    joins: list[dict[str, Any]] = []
    seen = set()
    for table_name in CORE_TABLES:
        table = meta_tables[table_name]
        for col in table.columns:
            for fk in col.foreign_keys:
                target_col = fk.column
                right_table = target_col.table.name
                if right_table not in CORE_TABLES:
                    continue
                key = (table_name, col.name, right_table, target_col.name)
                if key in seen:
                    continue
                seen.add(key)
                joins.append(
                    {
                        "left_table": table_name,
                        "left_column": col.name,
                        "right_table": right_table,
                        "right_column": target_col.name,
                        "expression": f"{table_name}.{col.name} = {right_table}.{target_col.name}",
                    }
                )
    return joins


def build_kb() -> dict[str, Any]:
    meta_tables = Base.metadata.tables
    missing = [name for name in CORE_TABLES if name not in meta_tables]
    if missing:
        raise RuntimeError(f"核心表缺失：{missing}")

    return {
        "meta": {
            "name": "edu_schema_kb_core",
            "version": "1.1.0",
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "source": ["app.models", "manual_templates"],
            "scope": "core_business_tables",
        },
        "tables": build_tables(meta_tables),
        "joins": build_joins(meta_tables),
        "filters": FILTER_MAPPINGS,
        "intents": INTENT_MAPPINGS,
        "workflow_task010": TASK010_WORKFLOW,
        "retrieval_policy": RETRIEVAL_POLICY,
        "sql_generation_policy": SQL_GENERATION_POLICY,
        "sql_templates": SQL_TEMPLATES,
    }


def validate_kb(kb: dict[str, Any]) -> None:
    for table in kb["tables"]:
        if not table.get("description"):
            raise RuntimeError(f"表描述为空：{table['name']}")
        for col in table["columns"]:
            if not col.get("description"):
                raise RuntimeError(f"列描述为空：{table['name']}.{col['name']}")


def main() -> None:
    parser = argparse.ArgumentParser(description="构建核心业务表 Schema 知识库")
    parser.add_argument(
        "--out",
        default="app/knowledge/schema_kb_core.json",
        help="输出文件路径（默认 app/knowledge/schema_kb_core.json）",
    )
    args = parser.parse_args()

    kb = build_kb()
    validate_kb(kb)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(kb, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Schema KB generated: {out_path}")
    print(f"tables={len(kb['tables'])} joins={len(kb['joins'])} templates={len(kb['sql_templates'])}")


if __name__ == "__main__":
    main()
