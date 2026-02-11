# 教务驾驶舱系统（RULE_JS_PRO）

本项目是一个前后端分离的教务管理与智能查询系统，核心目标是：
- 管理员登录后，进行核心教务数据管理（学生/教师/学院/专业/班级/课程）
- 在驾驶舱查看指标、趋势、榜单与风险清单
- 在智能问答中通过多节点工作流完成“意图识别 -> 任务解析 -> SQL 生成与校验 -> 结果返回”

当前代码状态已包含可运行的后端 API、前端页面、数据库脚本与模拟数据脚本。

## 1. 技术栈

- 后端：FastAPI + SQLAlchemy + MySQL 8 + LangGraph
- 前端：Vue 3 + Vite + TypeScript + Pinia + Vue Router
- 模型调用：OpenAI SDK 兼容接口（由 `LLM_BASE_URL`/`LLM_API_KEY` 控制）

## 2. 当前已实现功能

### 2.1 认证与权限
- `POST /api/auth/login`：管理员登录，返回 JWT
- `POST /api/auth/logout`：登出（前端清 token）
- `GET /api/admin/profile`：管理员个人信息

### 2.2 数据管理
- 通用 CRUD：
  - `GET /api/data/{table}/list`
  - `GET /api/data/{table}/{id}`
  - `POST /api/data/{table}/create`
  - `PUT /api/data/{table}/{id}`
  - `DELETE /api/data/{table}/{id}`（软删除）
- 支持分页、关键词模糊搜索、字段过滤、排序、多表切换
- 学生成绩明细：
  - `GET /api/data/student/{student_id}/scores`

### 2.3 导入能力
- `POST /api/import/{table}`
- 支持 CSV/XLSX
- 当前允许导入表：`student`、`teacher`、`course`
- 校验失败不入库，并写入 `import_log`

### 2.4 驾驶舱
- `GET /api/cockpit/overview`
- `GET /api/cockpit/risk/export`（CSV 导出）
- 支持筛选维度：学期、学院、专业、年级
- 输出内容：
  - 指标卡（学生/教师/课程/选课/平均分/出勤率/挂科率）
  - 近 6 个月出勤率趋势
  - 学院规模分布、成绩分段分布
  - 课程挂科率榜单、班级缺勤率榜单
  - 高风险学生列表

### 2.5 智能问答（核心）
- `POST /api/chat`：同步返回完整工作流结果
- `POST /api/chat/stream`：SSE 流式事件（可切换为同步）
- 会话管理：
  - `GET /api/chat/sessions`
  - `GET /api/chat/sessions/{session_id}/messages`
  - `DELETE /api/chat/sessions/{session_id}`
  - `DELETE /api/chat/sessions`
  - `GET /api/chat/downloads/{file_name}`（下载大结果 CSV）

#### 工作流节点（`app/services/chat_graph.py`）
- `intent_recognition`
- `task_parse`（仅 `business_query` 进入）
- `sql_generation`（CTE-only + 字段白名单 + 实体映射校验）
- `sql_validate`（真实执行，只允许只读 SQL）
- `hidden_context`（失败/空结果/零指标触发，最多 2 次回跳）
- `result_return`（产出 `final_status/reason_code/summary/assistant_reply/download_url`）

#### 关键行为约束
- 必须配置 `LLM_API_KEY`，否则工作流直接报错
- 问答上下文统一从 `chat_history` 读取最近 4 条 user 消息
- 节点输入输出落盘到 `local_logs/node_io/<session_id>/<step_name>/`

## 3. 前端页面

- `/login` 登录页
- `/cockpit` 驾驶舱页
- `/data` 数据管理页
- `/chat` 智能问答页（历史会话、滚动加载、SSE 状态流）

## 4. 数据库与模型

已实现模型（含审计字段）覆盖：
- 基础主数据：`admin`、`college`、`major`、`class`、`student`、`teacher`、`course`
- 教学业务：`course_class`、`enroll`、`score`、`attendance`、`classroom`
- 指标与预警：`metric_def`、`metric_snapshot`、`alert_rule`、`alert_event`
- 聊天与流程：`chat_history`、`workflow_log`、`sql_log`
- 策略与配置：`query_template`、`strategy_policy`、`audit_log`、`system_config`、`import_log`

## 5. 目录结构（核心）

```text
app/
  core/         配置与安全
  db/           SQLAlchemy 会话与 Base
  models/       ORM 模型
  routers/      API 路由
  schemas/      请求/响应结构
  services/     业务逻辑（含 chat_graph）
  prompts/      LLM 提示词
  knowledge/    schema_kb_core.json
scripts/        初始化、知识库生成、模拟数据与考勤填充
frontend/src/   Vue 页面、路由、状态与 API 封装
```

## 6. 本地启动

### 6.1 后端

```bash
pip install -r requirements.txt
python scripts/init_db.py
python scripts/init_admin.py --username admin --password your_password
python scripts/generate_mock_data.py --truncate --seed 42
python main.py
```

默认后端地址：`http://127.0.0.1:8000`

### 6.2 前端

```bash
cd frontend
npm install
npm run dev
```

默认前端地址：`http://127.0.0.1:5173`（已代理 `/api` 到 `8000`）

## 7. 环境变量（示例）

请在 `.env` 中配置：
- `DB_HOST` / `DB_PORT` / `DB_USER` / `DB_PASSWORD` / `DB_NAME`
- `JWT_SECRET` / `JWT_ALGORITHM` / `ACCESS_TOKEN_EXPIRE_MINUTES`
- `LLM_API_KEY` / `LLM_BASE_URL` / `LLM_MODEL_INTENT`
- `INTENT_CONFIDENCE_THRESHOLD`
- `CHAT_STREAM_MODE=stream|sync`

## 8. 开发脚本

- `scripts/init_db.py`：建表
- `scripts/init_admin.py`：创建管理员
- `scripts/generate_mock_data.py`：生成全量模拟数据
- `scripts/fill_recent_attendance.py`：填充最近 6 个月考勤
- `scripts/build_schema_kb.py`：生成字段知识库 `schema_kb_core.json`

## 9. 当前未完成/待增强

- `alert_*`、`strategy_*`、`audit_*` 相关 API 尚未落地
- 查询模板沉淀与知识资产管理尚未形成闭环
- 工作流可视化回放页面尚未实现
