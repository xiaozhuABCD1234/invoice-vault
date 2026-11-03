# 发票管理系统

内部财务/票据工作台：上传发票与付款凭证、自动识别、人工审核、付款分配、对账缺口、报表导出和审计。

- 后端：FastAPI + SQLite + SQLAlchemy 2 + Alembic + Pydantic v2
- 前端：Vue 3 + TypeScript + Vite + Tailwind CSS v4 + Reka UI / shadcn-vue + ECharts
- 设计：见 [DESIGN.md](./DESIGN.md)；UI 规范见 [UI_STYLE.md](./UI_STYLE.md)；接口契约见 [docs/API_CONTRACT.md](./docs/API_CONTRACT.md)

## 功能

- 角色与权限：admin / user；JWT access token（内存）+ HttpOnly refresh cookie 轮换；登录限流与锁定；首个管理员由 CLI 创建，不开放注册。
- 文档：发票、付款凭证、收据上传；sha256 去重；版本只增不改；用户在线预览最新版，管理员可下载原文件与历史版本。
- 识别：pdf_text（pypdf 文本层）、PaddleOCR HTTP、OpenAI 兼容多模态 LLM、mock；独立 worker 轮询 SQLite 队列，失败重试与退避。
- 审核：抽取结果必须人工审核；左右分栏对照原文件，字段置信度、校验错误、与上次结果 diff；通过后生成规范文件展示名。
- 发票与付款：发票/明细 CRUD；付款与发票通过 payment_allocations 多对多分配；部分付款、老师代付；进入/撤销分配时重算两端状态。
- 对账：按分配口径输出有票无付款、有付款未分配、缺凭证、明细差异、金额异常、日期异常等缺口，支持忽略与备注。
- 报表：模板保存列顺序/筛选/排序；异步生成 xlsx（冻结表头、合计行、防公式注入）；默认复刻 16 列手工表。
- 仪表盘：开票总额、付款、已付/未付、按类别/月份/付款人聚合、缺口数量。
- 审计：登录、文件预览/下载、创建/修改/审核/分配/忽略/导出等操作写审计日志。

## 快速开始

### 后端（端口 8000）

```bash
cd backend
uv sync

# 可选：复制并按需修改配置（数据库、上传目录、JWT 密钥等）
cp .env.example .env

# 初始化数据库（二选一；create_app 也会按模型补齐表）
uv run alembic upgrade head

# 创建首个管理员（重复执行会重置该账号）
uv run python -m backend.cli create-admin --username admin --password 'admin-pass-123' --display-name 管理员

uv run uvicorn backend.main:app --reload --port 8000
```

识别 worker 单独进程运行（web 进程不会自动识别）：

```bash
cd backend
uv run python -m backend.worker            # 常驻轮询
uv run python -m backend.worker --once     # 处理一轮，适合调试
```

本地演示可用 mock 识别器，不依赖 OCR/LLM：

```bash
IV_EXTRACTION_PROVIDER=mock uv run python -m backend.worker --once
```

识别引擎也可以在管理端「识别设置」（`/admin/settings`）里改：provider、自动链路、PaddleOCR / 大模型地址与密钥、超时与重试参数。保存后写入数据库并优先于 `.env` 与进程环境变量，对下一个任务立即生效（worker 每轮重新读取），每次变更都有审计与版本记录，可一键回滚。

### 前端（端口 5173）

```bash
cd frontend
pnpm install
pnpm dev
```

Vite 将 `/api` 代理到 `http://127.0.0.1:8000`。登录页使用上面创建的管理员账号。

### 测试与构建

```bash
cd backend && uv run pytest -q          # 238 个测试
cd frontend && pnpm test && pnpm build  # 69 个测试 + 类型检查 + 生产构建
```

## 目录

```text
backend/
  src/backend/
    shared/        # 配置、数据库、鉴权、错误、分页、审计、存储
    models/        # SQLAlchemy 模型（按领域拆分）
    schemas/       # Pydantic 契约
    auth/ users/ categories/
    documents/     # 上传、版本、预览/下载、规范命名
    extraction/    # provider、规范化、任务处理
    app_settings/  # 识别设置覆盖层、版本历史与回滚
    invoices/      # 发票、明细、审核通过
    payments/      # 付款、分配、状态重算
    reconciliation/# 对账口径、缺口
    reports/       # 模板、xlsx 导出
    dashboard/     # 汇总指标
    audit/
    worker.py      # 独立识别 worker
  alembic/         # 迁移（已含初始 schema）
  tests/
frontend/
  src/
    api/           # fetch 客户端、类型、按领域请求函数
    components/    # ui 基础组件 / common 领域通用组件 / layout
    composables/   # 页面级取数与轮询
    lib/           # 金额、日期、状态、格式化
    stores/        # 登录态、UI 偏好
    views/         # 页面（登录、上传、审核、发票、付款、对账、导出、仪表盘、管理）
    styles/        # Tailwind v4 主题 token
docs/API_CONTRACT.md
```

## 关键口径

- 金额传输与存储一律整数分（`*_cents`）；单价用 1/1000 元（`unit_price_millis`）。
- 发票号码全局唯一；重复上传只提示，不新建发票。
- 每张发票 active 分配合计 ≤ 发票金额；每笔付款 active 分配合计 ≤ 付款金额。
- 发票已付金额 = active allocation 合计；发票付满为 `paid`，付款分满为 `fully_allocated`。
- 普通用户只能在线预览最新版文件；管理员可下载原文件与历史版本。
- 老师代付（`teacher_advance`）不要求支付凭证。

## 生产注意事项

- 设置足够长的 `IV_JWT_SECRET`（≥32 字符），并开启 `IV_COOKIE_SECURE=true`，通过 HTTPS 反向代理访问。
- SQLite 使用 WAL 与 `foreign_keys=ON`；上线前执行 `uv run alembic upgrade head`，不要依赖开发期自动建表。
- web 与 worker 共用同一个数据库文件和 uploads 目录；worker 保持单实例（一次处理 1 个任务）。
- 每天做 SQLite 在线备份 + uploads 增量备份，并定期演练恢复。
- 云端 LLM 会把发票图片发送到外部，默认关闭；默认使用本地 PaddleOCR/pdf_text。
- 管理端保存的 LLM API Key 以明文存入 SQLite（接口与审计只返回掩码）；请限制数据库、备份文件权限，优先使用环境变量或密钥管理服务。

## 范围边界

本版不做：超额付款/退款、发票验真、红冲/作废重开、外币与汇率、多标签分类、暗色主题。数据库保留 `void` / `reversed` 状态位，后续再开放流程。

## 版本管理

仓库使用单一 git 仓库主干开发：

- `main` 保持可运行、测试通过；
- 功能按领域在 `feat/*` 分支开发，完成后合并回 `main`（合并提交保留上下文）；
- 提交信息采用 `feat/fix/docs/test/chore(scope): 说明`；
- 初始迁移在 `backend/alembic/versions/`，模型变更必须同时提交迁移。
