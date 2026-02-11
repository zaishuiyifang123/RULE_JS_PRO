# 教务驾驶舱系统 DEV_PLAN（同步版）

最后同步时间：2026-02-11  
同步依据：当前仓库源码（后端 `app/`、前端 `frontend/src/`、脚本 `scripts/`）

## 状态说明

- `计划中`：尚未开始或仅有方案
- `开发中`：部分完成，仍有功能缺口
- `完成`：代码已落地并可在当前项目中运行
- `暂缓`：明确不进入当前主链路

---

## 版本 1.0（MVP）

### TASK001 管理员认证与基础框架
- 状态：完成
- 结果对齐：
  - FastAPI 主应用、路由注册、统一异常响应已实现
  - JWT 登录鉴权链路已实现（`/api/auth/login`、`get_current_admin`）

### TASK002 数据库初始化与基础表
- 状态：完成
- 结果对齐：
  - SQLAlchemy 会话层与模型层已完成
  - 核心基础表已落地（admin/college/major/class/student/teacher/course）

### TASK003 基础 CRUD 接口
- 状态：完成
- 结果对齐：
  - `/api/data/{table}` 通用 CRUD 已实现
  - 支持分页、字段过滤、关键词模糊搜索、排序、软删除

### TASK004 批量导入功能
- 状态：完成
- 结果对齐：
  - `/api/import/{table}` 已实现 CSV/XLSX 导入
  - 当前导入白名单：student/teacher/course
  - 导入日志 `import_log` 已落库

### TASK005 前端基础界面
- 状态：完成
- 结果对齐：
  - 登录页、路由守卫、基础布局已实现
  - 页面入口：`/login`、`/cockpit`、`/data`、`/chat`

### TASK006 最小驾驶舱视图
- 状态：完成
- 结果对齐：
  - `/api/cockpit/overview` 已提供指标、趋势、分布、榜单、风险清单
  - 前端驾驶舱页面已展示并可联动筛选

### TASK007 数据库全量落地与模拟数据
- 状态：完成
- 结果对齐：
  - `scripts/init_db.py` 已创建全量模型对应表
  - `scripts/generate_mock_data.py` 已生成大规模模拟数据
  - 数据规模逻辑：教师 1100、学生 20000、专业 64、每专业 6 班

### TASK008 核心表数据管理（切换 + 搜索筛选 + 分页 + CRUD）
- 状态：完成
- 结果对齐：
  - 数据表切换、筛选、分页、弹窗 CRUD 已完成
  - 学生“成绩明细”弹窗与后端接口已实现

### TASK009 驾驶舱增强（筛选 + 对比 + 导出 + 风险榜单）
- 状态：完成
- 结果对齐：
  - 学期/学院/专业/年级筛选已实现并联动
  - 风险清单导出 `/api/cockpit/risk/export` 已实现
  - 支持下钻跳转到数据管理页并携带筛选

---

## 版本 2.0（智能流程）

### TASK010 LangGraph-意图识别节点
- 状态：完成
- 结果对齐：
  - 意图限定 `chat` / `business_query`
  - 读取最近 4 条 user 历史消息参与识别
  - confidence 阈值控制保留（低于阈值降级 chat）

### TASK011 LangGraph-任务解析节点
- 状态：完成
- 结果对齐：
  - 输出结构化任务：entities/dimensions/metrics/filters/time_range/operation/confidence
  - `filters.field` 严格按知识库字段白名单过滤

### TASK012 LangGraph-混合检索节点（暂缓）
- 状态：暂缓
- 结果对齐：
  - 当前主链路未包含该节点

### TASK013 LangGraph-LLM 重排节点（TOP5，暂缓）
- 状态：暂缓
- 结果对齐：
  - 当前主链路未包含该节点

### TASK014 LangGraph-隐藏上下文探索节点
- 状态：完成
- 结果对齐：
  - `hidden_context` 节点已实现
  - SQL 失败/空结果/零指标时触发只读探测并回跳 SQL 生成
  - 最大重试次数 2

### TASK015 LangGraph-SQL 生成节点
- 状态：完成
- 结果对齐：
  - SQL 生成强约束：CTE-only、字段白名单、实体映射完整性校验
  - 输出 `sql/entity_mappings/sql_fields`

### TASK016 LangGraph-SQL 验证与失败回跳节点
- 状态：完成
- 结果对齐：
  - SQL 真执行校验，仅允许 `SELECT/WITH`
  - 输出 `sql_validate_result`（含 `empty_result`/`zero_metric_result`）
  - 失败分支已与 `hidden_context` 回跳闭环联通

### TASK017 LangGraph-结果返回节点
- 状态：完成
- 结果对齐：
  - `result_return` 节点已实现
  - 输出统一结构：`final_status/reason_code/summary/assistant_reply/download_url`
  - 大结果自动导出 CSV，并提供下载地址

---

## 版本 3.0（可视化与知识资产）

### TASK018 工作流可视化
- 状态：计划中
- 当前差距：
  - 尚无独立工作流可视化页面（节点级回放未实现）

### TASK019 历史记录与知识资产
- 状态：开发中
- 已有基础：
  - chat_history/workflow_log/sql_log 已落库
  - 会话列表、会话消息查询、会话删除/清空 API 已实现
- 未完成项：
  - 查询模板抽取与模板库管理尚未落地

### TASK020 安全与审计增强
- 状态：计划中
- 当前差距：
  - 登录失败限制、限流、敏感操作二次确认未完成
  - audit 相关查询与治理能力未形成闭环

---

## 本次同步更新记录

- [2026-02-11]
  - 已修改：`README.md`、`DEV_PLAN.md`
  - 更改：按当前源码重建文档口径，修正任务状态并补充实际接口/工作流行为
  - 原因：用户要求“读取整个项目代码，同步更新 README 及 DEV_PLAN”
  - 阻碍因素：无
  - 状态：成功
