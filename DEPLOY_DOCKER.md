# Docker 部署与运维文档

当前状态：已完成部署并稳定运行。  
公网地址：http://47.97.122.195/

## 1. 部署架构

- `backend`：FastAPI 服务（`uvicorn`）
- `web`：Nginx 承载前端静态资源，并反向代理 `/api`
- 数据库：云服务器 MySQL（外部数据库，不在 Compose 内启动）

## 2. 已使用文件

- `Dockerfile.backend`
- `Dockerfile.web`
- `docker-compose.yml`
- `deploy/nginx/default.conf`
- `.env`（服务器环境变量）

建议在 `.env` 中显式配置：
- `LLM_MODEL_INTENT`（意图识别/任务解析/结果总结）
- `LLM_MODEL_SQL_GENERATION`（SQL 生成专用，默认 `qwen3-coder-plus`）

## 3. 启动命令（外部 MySQL）

```bash
docker compose up -d --build
```

## 4. 常用运维命令

### 4.1 查看状态

```bash
docker compose ps
docker compose logs -f backend
docker compose logs -f web
```

### 4.2 健康检查

```bash
curl http://127.0.0.1/healthz
```

### 4.3 更新发布

```bash
git pull
docker compose up -d --build
```

### 4.4 回滚方式（建议）

- 使用固定镜像版本标签
- 保留上一个稳定版本的镜像和配置
- 回滚时切回旧 tag 并重启 Compose

## 5. 数据库说明

- 当前生产库已存在完整结构与数据
- 不执行 `scripts/init_db.py`、`scripts/generate_mock_data.py`
- 仅在新增环境或空库场景下才执行初始化脚本

## 6. 网络与访问要求

- 云安全组开放：`22`、`80`（以及后续 `443`）
- 服务入口：`http://47.97.122.195/`
- 若启用域名与 HTTPS，可在 Nginx 层补充证书配置
