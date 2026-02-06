# DIRECTORY

本文件描述当前仓库结构（截至 2026-02-06）。

```
RULE_JS_PRO/
├─ .codex/                  Codex 代理指令与本地文档
│  ├─ AGENTS.md
│  └─ RIPER-5-CN.md
├─ .git/                    Git 元数据
├─ .idea/                   JetBrains IDE 配置
├─ .vscode/                 VS Code 配置
├─ app/                     FastAPI 应用包
│  ├─ core/                 应用配置与安全工具
│  │  ├─ config.py
│  │  └─ security.py
│  ├─ db/                   SQLAlchemy 基础与会话配置
│  │  ├─ base.py
│  │  └─ session.py
│  ├─ models/               ORM 模型
│  │  ├─ admin.py
│  │  ├─ alert_event.py
│  │  ├─ alert_rule.py
│  │  ├─ attendance.py
│  │  ├─ audit_log.py
│  │  ├─ chat_history.py
│  │  ├─ class_model.py
│  │  ├─ classroom.py
│  │  ├─ college.py
│  │  ├─ course.py
│  │  ├─ course_class.py
│  │  ├─ enroll.py
│  │  ├─ import_log.py
│  │  ├─ major.py
│  │  ├─ metric_def.py
│  │  ├─ metric_snapshot.py
│  │  ├─ mixins.py
│  │  ├─ query_template.py
│  │  ├─ score.py
│  │  ├─ sql_log.py
│  │  ├─ strategy_policy.py
│  │  ├─ student.py
│  │  ├─ system_config.py
│  │  ├─ teacher.py
│  │  ├─ workflow_log.py
│  │  └─ __init__.py
│  ├─ routers/              API 路由模块
│  │  ├─ admin.py
│  │  ├─ auth.py
│  │  ├─ cockpit.py
│  │  ├─ data.py
│  │  ├─ importer.py
│  │  ├─ metric.py
│  │  └─ __init__.py
│  ├─ schemas/              Pydantic 请求/响应结构
│  │  ├─ admin.py
│  │  ├─ auth.py
│  │  ├─ class_schema.py
│  │  ├─ cockpit.py
│  │  ├─ college.py
│  │  ├─ course.py
│  │  ├─ importer.py
│  │  ├─ major.py
│  │  ├─ metric_def.py
│  │  ├─ metric_snapshot.py
│  │  ├─ response.py
│  │  ├─ student.py
│  │  ├─ teacher.py
│  │  └─ __init__.py
│  ├─ services/             业务服务层逻辑
│  │  ├─ auth_service.py
│  │  ├─ cockpit_service.py
│  │  └─ import_service.py
│  ├─ knowledge/            Schema 知识库资产（供 Agent 检索，含 TASK010 工作流元数据）
│  │  └─ schema_kb_core.json
│  ├─ deps.py               依赖注入辅助函数
│  ├─ main.py               FastAPI 工厂与路由注册
│  └─ __init__.py
├─ scripts/                 辅助脚本
│  ├─ build_schema_kb.py    从 ORM 模型构建可检索 schema 知识库（含 intent/检索/工作流配置）
│  ├─ fill_recent_attendance.py
│  ├─ init_admin.py
│  ├─ init_db.py
│  └─ generate_mock_data.py
├─ frontend/                Vue3 + Vite 前端
│  ├─ src/
│  │  ├─ api/                Axios 客户端与拦截器
│  │  │  ├─ chat.ts
│  │  │  └─ client.ts
│  │  ├─ components/         前端通用组件（弹窗、分页等）
│  │  │  ├─ DataFormModal.vue
│  │  │  ├─ PaginationBar.vue
│  │  │  └─ ScoreListModal.vue
│  │  ├─ layouts/            页面布局组件
│  │  ├─ router/             路由与守卫
│  │  ├─ stores/             Pinia 登录态
│  │  ├─ styles/             全局样式
│  │  ├─ views/              页面视图
│  │  │  ├─ ChatView.vue
│  │  │  ├─ CockpitView.vue
│  │  │  ├─ DataView.vue
│  │  │  └─ LoginView.vue
│  │  ├─ App.vue
│  │  ├─ env.d.ts
│  │  └─ main.ts
│  ├─ index.html
│  ├─ package.json
│  ├─ package-lock.json
│  ├─ tsconfig.json
│  └─ vite.config.ts
├─ .env                     本地环境变量
├─ DEV_PLAN.md              开发计划与任务清单
├─ DIRECTORY.md             目录结构说明（本文件）
├─ main.py                  暴露 FastAPI 应用的入口
├─ README.md                项目蓝图与需求说明
├─ requirements.txt         Python 依赖列表
└─ _cn_test.txt             小型测试文件
```

说明：
- 已存在的 Python __pycache__ 目录在此处省略。
