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

识别引擎配置由 extraction/config.py 直接读取（同样支持写入 backend/.env），完整变量见
.env.example，常用项：

- IV_EXTRACTION_PROVIDER：pdf_text（默认）/ paddleocr_local / multimodal_llm / mock / auto
- IV_EXTRACTION_AUTO_CHAIN：auto 模式的尝试顺序，逗号分隔；未配置的 provider 会被跳过
- IV_PADDLEOCR_ENDPOINT：本地 PaddleOCR HTTP 地址
- IV_LLM_ENABLED、IV_LLM_ENDPOINT、IV_LLM_API_KEY、IV_LLM_MODEL：多模态大模型，默认关闭
- IV_EXTRACTION_PROMPT_VERSION、IV_EXTRACTION_HTTP_TIMEOUT、IV_EXTRACTION_MAX_ATTEMPTS、
  IV_EXTRACTION_STALE_MINUTES、IV_EXTRACTION_BACKOFF_SECONDS

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

### worker

抽取任务由独立 worker 进程处理（SQLite 表即队列，不需要 Redis）：

```bash
uv run python -m backend.worker              # 常驻轮询，默认空闲间隔 5 秒
uv run python -m backend.worker --once       # 只处理一轮后退出（运维/演示用）
uv run python -m backend.worker --interval 2 # 自定义空闲轮询间隔
```

worker 启动时会把超时的 running 任务改回 queued；失败按指数退避重试，默认 3 次。
web 与 worker 必须共用同一个数据库和 uploads 目录。

### mock provider 本地演示

mock 返回固定的一张测试发票（发票号码 24512000000012345678、价税合计 113.00 元），
不需要 OCR/LLM 服务即可走通完整流程：

```bash
IV_EXTRACTION_PROVIDER=mock uv run python -m backend.worker --once
```

也可以把 IV_EXTRACTION_PROVIDER=mock 写进 backend/.env 后由 worker 读取。mock 只用于
本地演示和测试，生产请使用 pdf_text / paddleocr_local / multimodal_llm。

## 测试

```bash
uv run pytest -q
```

测试使用临时 SQLite 文件与临时上传目录，不污染开发数据库；每个测试独立建库。
fixtures 位于 tests/conftest.py，可直接复用：app、client、admin_client、user_client、
db_session、admin_user、normal_user。

tests/test_integration_flow.py 覆盖「上传 → mock 抽取 → 审核 → 付款分配 → 对账 →
导出 xlsx → 仪表盘」全链路，mock provider 直接注入，不访问外部网络。

## Alembic

已配置 alembic.ini 与 alembic/env.py：读取 backend.shared.config 的连接串、导入完整
Base.metadata、SQLite 使用 render_as_batch=True。仓库已包含初始迁移：

```bash
uv run alembic upgrade head
uv run alembic check   # 确认模型与迁移无漂移
```

模型本阶段已冻结；确需修改模型时再生成新 revision
（`uv run alembic revision --autogenerate -m "..."`），不要修改已提交的初始迁移。

## 目录说明

- src/backend/shared：配置、数据库、安全、错误、分页、审计、存储、枚举
- src/backend/models：全部 ORM 模型（后续领域只读）
- src/backend/schemas：Pydantic v2 契约（后续领域复用）
- src/backend/auth、users、categories、audit：认证、用户、类别与审计
- src/backend/documents、extraction、invoices、payments、reconciliation、reports、dashboard：
  文档、识别任务、发票、付款分配、对账、导出与仪表盘

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
- 新增领域路由挂载到 api/router.py。
- 测试账号密码见 tests/conftest.py 中 ADMIN_PASSWORD、NORMAL_PASSWORD。

## 生产部署注意

- 必须设置 IV_COOKIE_SECURE=true（HTTPS），并把 IV_JWT_SECRET 换成至少 32 字节的随机值；
  不要使用 .env.example 中的开发默认值。
- 启动前先执行 `uv run alembic upgrade head`，再分别启动 web 与 worker 两个进程；
  两者共用同一 SQLite 文件与 uploads 目录。
- uploads 目录不能由 Nginx 静态暴露；文件只能通过鉴权后的 preview/download 接口访问。
- 定期备份 SQLite（在线备份）与 uploads 增量，并做恢复演练。
- 反向代理需传递 X-Forwarded-For，审计日志依赖它记录来源 IP。
