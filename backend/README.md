# 后端（FastAPI + SQLite + SQLAlchemy 2）

## 环境要求

- Python >= 3.14
- uv >= 0.12（本仓库使用 uv 管理虚拟环境与锁文件）

## 安装

```bash
cd backend
uv sync
```

首次启动会自动创建 data/ 与 data/uploads/，并调用 create_all 建表（开发/测试便利）。
生产环境使用 Alembic 迁移。

## 配置

复制示例文件并按需修改：

```bash
cp .env.example .env
```

所有配置项使用 IV_ 前缀，默认读取 backend/.env。关键项：

- IV_DATABASE_URL：默认 sqlite:///./data/app.db
- IV_UPLOAD_DIR：默认 data/uploads
- IV_JWT_SECRET：生产必须替换
- IV_ACCESS_TOKEN_MINUTES=15、IV_REFRESH_TOKEN_DAYS=7
- IV_COOKIE_SECURE：HTTPS 部署时设为 true
- IV_CORS_ORIGINS：JSON 数组或逗号分隔

## 初始化管理员与类别

```bash
uv run python -m backend.cli create-admin --username admin --display-name 管理员
uv run python -m backend.cli seed-categories
```

create-admin 在不传 --password 时交互输入；重复执行会重置该账号密码并提升为管理员。

## 运行

```bash
uv run uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

- 健康检查：GET /healthz、GET /readyz
- OpenAPI：GET /openapi.json、/docs
- API 基础路径：/api/v1

## 测试

```bash
uv run pytest -q
```

测试使用临时 SQLite 文件与临时上传目录，不污染开发数据库；每个测试独立建库。
fixtures 位于 tests/conftest.py，可直接复用：app、client、admin_client、user_client、
db_session、admin_user、normal_user。

## Alembic

已配置 alembic.ini 与 alembic/env.py：读取 backend.shared.config 的连接串、导入完整
Base.metadata、SQLite 使用 render_as_batch=True。本阶段不生成 revision，集成阶段统一生成初始迁移。

```bash
uv run alembic revision --autogenerate -m "initial schema"
uv run alembic upgrade head
```

## 目录说明

- src/backend/shared：配置、数据库、安全、错误、分页、审计、存储、枚举
- src/backend/models：全部 ORM 模型（后续领域只读）
- src/backend/schemas：Pydantic v2 契约（后续领域复用）
- src/backend/auth、users、categories、audit：本阶段完整实现
- src/backend/documents、extraction、invoices、payments、reconciliation、reports、dashboard：
  占位 router，由后续并行智能体接管

## 共享层接口（并行智能体直接复用）

- paginate(db, stmt, page=1, page_size=20) -> {items, total, page, page_size}；page_size 自动限制到 100。
- record_audit(db, actor_id, action, entity_type, entity_id=None, before=None, after=None, request=None)，调用方负责 commit。
- save_bytes(data, ext, created_at=None, *, settings=None) -> {storage_key, sha256, size_bytes}；
  resolve_path(storage_key, *, settings=None) -> Path；sanitize_filename(name) -> str。
- 依赖别名：DbSession / CurrentUser / AdminUser / AppSettings / RequestCtx。
- 模型、schema 分别从 backend.models、backend.schemas 导入；金额全部为整数分。

## 并行开发约定

- 只从 backend.models 导入 ORM 模型；模型字段本阶段已固定。
- 只从 backend.schemas 导入请求/响应 schema；金额全部为整数分。
- 依赖注入使用 shared.deps 的 DbSession / CurrentUser / AdminUser / AppSettings / RequestCtx。
- 审计写 shared.audit.record_audit，调用方负责 commit。
- 文件存储用 shared.storage.save_bytes / resolve_path，数据库只存相对 storage_key。
- 占位 router 文件会被整体替换；api/router.py 不再需要改动。
- 测试账号密码见 tests/conftest.py 中 ADMIN_PASSWORD、NORMAL_PASSWORD。
