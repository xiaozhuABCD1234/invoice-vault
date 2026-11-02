# API 契约 v1

> 本文件是前后端并行开发的唯一接口契约。实现与本文不一致时，先改本文再改代码。
> 所有金额均为整数**分**（`*_cents`），单价允许千分位整数（`unit_price_millis` = 1/1000 元）。
> 时间戳为 UTC ISO 8601；日期为 `YYYY-MM-DD`。
> 基础路径：`/api/v1`。健康检查在根路径：`/healthz`、`/readyz`。

## 0. 通用约定

### 0.1 认证
- access token 放 `Authorization: Bearer <token>`，只存前端内存。
- refresh token 为 HttpOnly Cookie，名 `refresh_token`，Path=`/api/v1/auth`，SameSite=Lax，Secure 由配置决定。
- access 15 分钟；refresh 7 天，轮换并在服务端存哈希；登出/改密/禁用递增 `token_version`。
- 除 `POST /auth/login`、`POST /auth/refresh` 外全部需要登录。

### 0.2 分页
列表统一返回：
```json
{ "items": [], "total": 0, "page": 1, "page_size": 20 }
```
query：`page`（默认 1）、`page_size`（默认 20，最大 100）、`q`（模糊搜索，按各接口说明）。
支持排序的列表统一用 `sort="字段:asc|desc"` 单值格式，例如 `sort=issue_date:desc`；字段白名单与默认值见各接口说明。

### 0.3 错误
```json
{ "code": "invoice_duplicate", "message": "发票号码已存在", "details": {"invoice_number": "..."}, "trace_id": "..." }
```
HTTP 状态：400 校验/业务参数错误，401 未认证，403 无权限，404 不存在，409 冲突/重复，422 请求体校验失败，500 未预期错误。

### 0.4 枚举
- role: `admin` | `user`
- category.kind: `purchase` | `expense`
- document.doc_type: `invoice` | `payment_evidence` | `receipt` | `other`
- extraction status: `queued` | `running` | `review_pending` | `approved` | `rejected` | `failed`
- extraction provider: `pdf_text` | `paddleocr_local` | `multimodal_llm` | `mock`
- invoice.status: `review_pending` | `active` | `void` | `duplicate`
- invoice.payment_status: `unpaid` | `partial` | `paid`
- invoice.invoice_form: `electronic` | `paper`
- payment.status: `unallocated` | `partially_allocated` | `fully_allocated` | `void`
- payment.method: `personal_advance` | `teacher_advance` | `bank_transfer` | `alipay` | `wechat` | `card` | `cash` | `other`
- allocation.status: `active` | `reversed`
- export.status: `queued` | `running` | `succeeded` | `failed`
- review_decision: `approved` | `rejected`

## 1. 认证与用户

### POST /auth/login
body: `{ "username": "string", "password": "string" }`
200: `{ "access_token": "...", "token_type": "bearer", "expires_in": 900, "user": User }`，同时 Set-Cookie refresh_token。
401：用户名或密码错误；423：连续失败锁定。

### POST /auth/refresh
无 body，读 Cookie。
200: 同 login 的 token 部分（轮换 Cookie）。
401：refresh 失效。

### POST /auth/logout
204，清除 Cookie，吊销当前 refresh token。

### GET /me
200: User。

User: `{ id, username, display_name, role, is_active, created_at, last_login_at }`

### GET /users/options
所有登录用户可用（表单选择申购人/负责人）：返回 `{ items: [{ id, display_name, role, is_active }] }`，只含展示必需字段。

### 用户管理（admin）
- `GET /users?page&page_size&q&role&is_active` → 分页 User
- `POST /users` body `{ username, display_name, password, role }` → 201 User
- `PATCH /users/{id}` body `{ display_name?, role?, is_active?, password? }` → User
  - 改密或禁用时递增 token_version；不能禁用最后一个 admin，不能禁用自己。

## 2. 类别

Category: `{ id, name, kind, sort_order, is_active }`

- `GET /categories?kind&include_inactive=false` → `{ items: Category[] }`（不分页）
- `POST /categories`（admin）body `{ name, kind, sort_order? }` → 201 Category
- `PATCH /categories/{id}`（admin）body `{ name?, sort_order?, is_active? }` → Category

默认种子：采购 `标准件, 板材件, 机加工, 官方器件, 硬件, 铝方管, 大采购, 快递, 打车, 周边`；费用 `报名费, 高铁, 住宿, 货拉拉, 打车, 快递, 采购, 周边`。

## 3. 文档与文件

Document: `{ id, doc_type, title, owner_user_id, owner_name, current_version: DocumentVersion, created_at, deleted_at }`
DocumentVersion: `{ id, version_no, original_name, display_name, mime_type, size_bytes, sha256, created_at, is_latest }`

- `POST /documents`（multipart：`file`、`doc_type`、`title?`）→ 201
  `{ "document": Document, "extraction_job": Job | null }`
  - doc_type=invoice 时自动入队抽取任务；其余为 null。
  - 同 sha256 已存在：返回 200 同结构，`reused=true`，不新建版本。
  - 限制：pdf/jpg/jpeg/png/webp；单文件 ≤ 20MB；校验 magic bytes；文件名只作展示。
- `GET /documents?page&page_size&doc_type&q` → 分页 Document
- `GET /documents/{id}` → `{ document, version_count, extraction_jobs: Job[] }`
- `GET /documents/{id}/preview?version=latest` → 二进制，`Content-Disposition: inline`，正确 Content-Type。user/admin 均可，仅最新版；admin 可传 version_id。
- `GET /documents/{id}/download?version=latest`（admin）→ `attachment; filename*=UTF-8''...`，文件名带扩展名。
- `POST /documents/{id}/versions`（multipart file）→ 新建 201、sha256 已存在 200 复用，均返回 Document；不新增版本。
- `DELETE /documents/{id}`（admin，软删）→ 204；文件不物理删除。

写审计：document.create / document.upload_version / document.preview / document.download / document.delete。

## 4. 抽取任务

Job: `{ id, document_id, document_name, document_doc_type, provider, model, prompt_version, status, attempts, confidence, parsed, validation, error_code, error_message, queued_at, started_at, finished_at, reviewed_by, reviewed_at, review_decision, review_note }`
`parsed`：规范化后的候选字段（见第 5 节 InvoiceCreate 结构的大驼峰 camelCase 版本，金额仍为分）。
`validation`：`{ "errors": string[], "warnings": string[], "field_confidence": { "field": 0.0 } }`

- `GET /extraction-jobs?page&page_size&status&provider` → 分页 Job
- `GET /extraction-jobs/{id}` → `{ job, document, diff: object | null }`（diff = 与上一次审核/抽取结果的字段差异）
- `POST /extraction-jobs/{id}/retry` → 202 Job（queued，attempts 保留；超过 3 次 409）
- `POST /extraction-jobs/{id}/approve` body = InvoiceCreate（见 5.1，必须含 items）→ 201 `{ invoice, job }`
  - 仅 status=review_pending 可 approve；发票号码重复 409；审核人 user 只能审自己上传的文档。
  - 审核通过：创建 invoice + items（active），job=approved，回填 reviewed_by/at/decision；同时把源文档当前版本 display_name 更新为规范名（金额-人员-商户-类别-文档类型.扩展名）。
- `POST /extraction-jobs/{id}/reject` body `{ "note": "string" }` → 200 Job（rejected）。

## 5. 发票

Invoice（响应）：
```json
{
  "id": 1, "invoice_number": "2532...", "invoice_code": null, "invoice_type": "电子发票",
  "issue_date": "2026-07-12", "seller_name": "店铺", "seller_tax_id": null,
  "buyer_name": null, "buyer_tax_id": null,
  "amount_ex_tax_cents": 10000, "tax_cents": 1300, "total_cents": 11300, "tax_rate_bp": 1300,
  "currency": "CNY", "category_id": 1, "category_name": "标准件",
  "requester_id": 2, "requester_name": "杨泽", "owner_id": 2, "owner_name": "杨泽",
  "invoice_form": "electronic", "status": "active",
  "paid_cents": 0, "payment_status": "unpaid",
  "source_document_id": 3, "extraction_job_id": 4,
  "note": null, "product_url": null, "created_by": 2, "confirmed_by": 1, "confirmed_at": "...",
  "created_at": "...", "updated_at": "...", "deleted_at": null,
  "items": [ { "id": 1, "name": "螺栓", "quantity": 10, "unit_price_millis": 1000, "amount_cents": 10000, "note": null, "sort_order": 1 } ],
  "allocations": [ { "id": 1, "payment_id": 2, "amount_cents": 5000, "status": "active" } ]
}
```

### 5.1 创建 / 更新
`POST /invoices` body：
`{ invoice_number, invoice_code?, invoice_type?, issue_date, seller_name, seller_tax_id?, buyer_name?, buyer_tax_id?, amount_ex_tax_cents, tax_cents, total_cents, tax_rate_bp?, category_id, requester_id?, owner_id?, invoice_form?, status?, source_document_id?, note?, product_url?, items: InvoiceItemInput[] }`
- `amount_ex_tax_cents + tax_cents` 与 `total_cents` 不一致：422（差额超过 1 分）。
- items 合计与 total 不一致：接受但写 validation warning（审核页提示）。
- 默认 status=active（直接录入场景）；审核通过路径由 job approve 创建。
- invoice_number 全局唯一（含已删除/作废）：409。
InvoiceItemInput: `{ name, quantity, unit_price_millis, amount_cents, note?, sort_order? }`

- `GET /invoices` query：`page, page_size, q, status, payment_status, category_id, requester_id, owner_id, date_from, date_to, sort, include_deleted`
  `sort` 白名单：`issue_date`、`total_cents`、`created_at`、`id`；默认 `issue_date:desc`，非法值回退默认。默认排除软删；admin 可传 `include_deleted=true`。
- `GET /invoices/{id}`
- `PATCH /invoices/{id}`：InvoiceCreate 的可选字段 + `status?`；修改金额后重算 payment_status，并校验 active 分配合计 ≤ 新金额，否则 409。
- `DELETE /invoices/{id}`（admin）→ 204 软删；存在 active allocation 时 409。

## 6. 付款与分配

Payment 响应：
`{ id, amount_cents, paid_at, payer_user_id, payer_name, method, external_txn_ref, evidence_document_id, status, requested_at, confirmed_by, confirmed_at, note, created_by, created_at, allocated_cents, allocations: Allocation[] }`
说明：`allocated_cents` 为 active allocation 合计；列表不返回 allocations，详情返回。
Allocation: `{ id, payment_id, invoice_id, amount_cents, status, note, created_by, created_at, updated_at }`

- `GET /payments?page&page_size&q&status&method&date_from&date_to&sort`
  `sort` 白名单：`paid_at`、`amount_cents`、`created_at`、`id`；默认 `paid_at:desc`。
- `POST /payments` body `{ amount_cents, paid_at, payer_user_id?, payer_name?, method, external_txn_ref?, evidence_document_id?, requested_at?, note? }` → 201 Payment
  - `method != teacher_advance` 且无 evidence_document_id：允许，但对账产生"缺凭证"异常。
- `GET /payments/{id}`（含 allocations 与发票摘要）
- `PATCH /payments/{id}` 可改 `amount_cents, paid_at, payer_name, method, external_txn_ref, evidence_document_id, requested_at, note`；改小金额时校验已分配，否则 409。
- `POST /payments/{id}/allocations` body `{ invoice_id, amount_cents, note? }` → 201 Allocation
  - 同一 payment+invoice 已有 active allocation：409。
  - 超过发票/付款剩余额度：409。
  - 重算 payment.status 与 invoice.paid_cents/payment_status。
- `PATCH /allocations/{id}` body `{ amount_cents?, note? }` → Allocation（校验额度）
- `DELETE /allocations/{id}` → 204（status=reversed；重算两端）
- `GET /invoices/{id}/payments` → `{ items: (Allocation + payment 摘要)[] }`

## 7. 对账

### GET /reconciliation/summary
```json
{
  "invoice_total_cents": 0, "invoice_paid_cents": 0, "invoice_unpaid_cents": 0,
  "payment_total_cents": 0, "payment_allocated_cents": 0, "payment_unallocated_cents": 0,
  "invoice_count": 0, "payment_count": 0,
  "issue_counts": { "invoice_unpaid": 0, "invoice_partial": 0, "payment_unallocated": 0, "payment_partial": 0, "missing_evidence": 0, "duplicate_invoice": 0, "item_mismatch": 0, "amount_anomaly": 0, "date_anomaly": 0 }
}
```
口径：invoice_* 只统计 status=active 且未删除；payment_* 只统计 status!=void；已付/已分配只统计 allocation.status=active。

### GET /reconciliation/issues?type&page&page_size
Issue: `{ id: "type:entity_id", type, severity: "error"|"warning", entity_type: "invoice"|"payment"|"allocation", entity_id, title, detail, amount_cents, ignored, note }`
type 取值：`invoice_unpaid, invoice_partial, payment_unallocated, payment_partial, missing_evidence, duplicate_invoice, item_mismatch, amount_anomaly, date_anomaly`
- `POST /reconciliation/issues/{issue_key}/ignore` body `{ note }` → 200 Issue（忽略记录写库 + 审计）
- `DELETE /reconciliation/issues/{issue_key}/ignore` → 200 Issue（取消忽略）

## 8. 报表模板与导出

ReportTemplate: `{ id, name, columns, filters, sort, created_by, is_shared, created_at }`
`columns`: `[{ "key": "invoice_number", "label": "发票号码", "width": 18, "format": "text" }]`
`filters`: 与 `GET /invoices` query 同名字段组成的对象；`sort`: `[{ "key": "issue_date", "order": "desc" }]`
字段目录（key）：发票 invoice_number/issue_date/seller_name/total_cents/amount_ex_tax_cents/tax_cents/category_name/requester_name/owner_name/invoice_form/status/note/product_url；明细 item_name/quantity/unit_price_millis/amount_cents；付款 payer_name/method/paid_at/amount_cents；文件 source_file_name。

- `GET /report-templates` → `{ items: ReportTemplate[] }`（含内置默认模板，id=0，名称"默认导出"）
- `POST /report-templates` body `{ name, columns, filters?, sort?, is_shared? }` → 201
- `PATCH /report-templates/{id}` / `DELETE /report-templates/{id}`（创建者或 admin）
- `POST /exports` body `{ template_id?, columns?, filters?, sort? }` → 202 `{ export: ExportJob }`
- `GET /exports?page&page_size` → 分页 ExportJob
- `GET /exports/{id}` → ExportJob
- `GET /exports/{id}/download` → xlsx 附件（创建者或 admin；过期 24h 后 410）

ExportJob: `{ id, template_id, status, file_document_id, file_name, error_message, created_at, expires_at, download_url }`
本版导出为同步生成：`POST /exports` 返回 202 时 status 已为 `succeeded` 或 `failed`。
xlsx 要求：金额写数字、日期写日期格式、冻结表头、合计行；文本防公式注入；默认模板 16 列见 DESIGN §10。

## 9. 仪表盘

### GET /dashboard/summary?date_from&date_to
```json
{
  "totals": { "invoice_count": 0, "invoice_total_cents": 0, "payment_total_cents": 0, "paid_cents": 0, "unpaid_cents": 0, "missing_evidence_count": 0 },
  "by_category": [ { "category_id": 1, "name": "标准件", "invoice_count": 0, "total_cents": 0 } ],
  "by_month": [ { "month": "2026-01", "invoice_count": 0, "total_cents": 0 } ],
  "by_payer": [ { "payer_name": "杨泽", "payment_count": 0, "total_cents": 0 } ],
  "gaps": { "invoice_unpaid": 0, "payment_unallocated": 0, "missing_evidence": 0 }
}
```

## 10. 审计日志（admin）

AuditLog: `{ id, actor_id, actor_name, action, entity_type, entity_id, before, after, ip, user_agent, created_at }`
`entity_id` 为字符串（兼容数字 ID 与对账 issue_key）。
- `GET /audit-logs?page&page_size&action&entity_type&entity_id&actor_id&date_from&date_to`

## 11. 前端路由 ↔ 接口对应

| 路由 | 接口 |
|---|---|
| /login | auth/login |
| /uploads | documents（POST）、extraction-jobs、documents/{id}/preview |
| /review、/review/:jobId | extraction-jobs、approve/reject、documents preview |
| /invoices、/invoices/:id | invoices、documents preview |
| /payments、/payments/:id | payments、allocations、invoices 选择器 |
| /reconciliation | reconciliation/summary、issues |
| /exports | report-templates、exports |
| /dashboard | dashboard/summary |
| /admin/users | users、categories |
| /admin/audit | audit-logs |
