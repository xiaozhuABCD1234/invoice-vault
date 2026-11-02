# 发票管理系统设计

> 依据：README.md、12-7月发票整理汇总.xlsx、4 个样例发票目录。
> 本文把已确认的规则收敛成可实现的设计；本版明确不做的范围见第 13 节。
> xlsx 只作为测试语料和对照基准，不作为生产数据迁移来源；表内可能存在人工录入错误。

## 1. 从手工表读到的事实

对 12-7月发票整理汇总.xlsx 的实际统计（仅用于测试对照）：

- 10 个采购类别：标准件、板材件、机加工、官方器件、硬件、铝方管、大采购、快递、打车、周边。
- 145 张发票，145 个发票号码，未发现重复号码。
- 发票总额 50,349.94 元，与总表 D2:D11 合计一致。
- 118 张有付款截图，27 张是老师代付、付款记录为 "/"，只有"申请老师代付时间"。
- 一张发票可以对应多条商品明细；一条明细也可能跨多张发票。
- 明细合计与发票金额不一致的有 9 张，部分是合并单元格、重复填写总价造成，不能直接做硬校验。
- 发票日期不在表里，但存在"按开票时间汇总"页，说明日期需要从票面抽取。
- 表内存在"蒋烨阳/蒋烨洋"、"机加工/机加工件"这类人工录入错误，不能把 xlsx 的每个单元格都当成正确标签，需要别名字典和人工修正。
- 发票图片和付款截图是 WPS 的 DISPIMG 嵌入图，不是普通图片链接；做测试语料时需要从 xl/cellimages.xml 和 xl/media 里导出。

样例目录里的命名规则是：

    金额-人员-商户或路线-费用类型-文档类型.扩展名

例如：

    124.00-杨泽,朱建诚-上海站-无锡站-高铁-支付凭证.jpg
    668.00元-杨洋,杨泽,朱建诚-滨湖区锦瑞酒店-酒店-水单.pdf
    1200元-杨洋,杨泽,朱建诚-中国计算机设计大赛报名费-发票(老师自己的报名费已转账).pdf

实际写法不统一：有无"元"、小数位、全角/半角横线、支付截图/支付凭证/水单混用。系统不能照抄，必须定义规范名。

## 2. 付款与发票是多对多

已确认：付款记录和发票不是一一对应，而是多对多。一笔付款可以覆盖多张发票，一张发票也可以由多笔付款覆盖。

截图证据：

- 124.00：2026-08-13 中铁网络一笔支付，对应 2 张 62.00 元高铁票。
- 198.00：2026-08-18 一笔转账，对应 3 张 66.00 元高铁票。

因此去掉 payment_batch 和 payments.invoice_id，改为：

- payments：一笔真实付款/转账，金额是交易总额；
- payment_allocations：把付款金额分配到发票，记录 payment_id、invoice_id、amount_cents。

对账目标不再是"一条付款对一条发票"，而是：

- 每张发票的已分配付款合计 = 发票金额，才算已付款；
- 每笔付款的已分配金额合计 = 付款金额，才算已核销；
- 未达到就是"缺付款"或"缺发票"，中间状态是部分付款/部分分配。

这样 124 就是一条 payment + 两条 allocation（62 + 62），198 就是一条 payment + 三条 allocation（66 + 66 + 66），不需要拆付款记录。

老师代付也生成 payment（method=teacher_advance），可以一张发票一条，也可以一笔老师转账分配多张；不要求凭证。

本版只实现正常付款和部分付款：部分付款就是发票未分配满。超额付款、退款、红冲、发票验真、作废处理暂不做，只在表结构里保留 status 字段，后续再加。

## 3. 范围与不变量

部署：单机、单实例、用户量不大；SQLite + 本地文件存储；不按部门/项目隔离。

核心不变量：

- 发票号码全局唯一；重复上传不新建发票，提示已存在。
- 发票必须经过人工审核才能变成 active。
- 发票与付款通过 payment_allocations 多对多关联，不直接挂 invoice_id。
- 每张发票的 active 分配合计不得超过发票金额；每笔付款的 active 分配合计不得超过付款金额。
- 每张发票分配满才算 paid；每笔付款分配满才算 fully_allocated。
- 发票金额、付款金额以"分"为整数存储；禁止浮点金额。
- 文件永远不覆盖，只新增版本；普通用户只能在线查看最新版，不能下载。
- 所有修改、审核、预览、下载、导出写审计日志。

## 4. 角色与权限

只有两种角色：admin、user；不开放注册。

| 能力 | user | admin |
|---|---|---|
| 查看全部发票/付款记录 | 是 | 是 |
| 在线查看全部最新版文件 | 是 | 是 |
| 下载原文件 | 否 | 是 |
| 上传发票、付款凭证 | 是 | 是 |
| 审核自己上传的抽取结果 | 是 | 是 |
| 审核他人上传的抽取结果 | 否 | 是 |
| 查看历史版本、已删除文件 | 否 | 是 |
| 导出 xlsx | 是 | 是 |
| 用户管理、类别管理 | 否 | 是 |
| 审计日志 | 否 | 是 |

说明：普通用户只能在线预览，不能下载；管理员可以下载全部文件（含历史版本、已删除文件）。预览走鉴权接口，前端不提供下载入口，后端也不向 user 暴露下载 API；静态目录绝对不能直接暴露。浏览器仍可通过截图、打印或另存页面等方式留存内容，这是"只能查看"的实际边界，需要接受。

### 登录

- POST /auth/login，用户名 + 密码，返回 15 分钟 access token 和 7 天 refresh token。
- refresh token 放 HttpOnly、Secure、SameSite=Lax Cookie；access token 放内存，不放 localStorage。
- refresh token 哈希后存库，支持轮换和吊销；登出、改密、禁用用户时吊销。
- 密码用 Argon2id；登录限流；连续失败锁定。
- 不提供注册接口；首个管理员由启动参数或 CLI 创建；后续用户由管理员创建、重置密码、禁用。
- JWT 里带 token_version；禁用用户或改密后递增，旧 token 立即失效。

## 5. 领域模型

金额字段统一用整数分：amount_cents、total_cents。单价允许三位小数，用 unit_price_millis（1/1000 元）。日期用 date，时间戳用 UTC。

### users

id、username（唯一）、display_name、password_hash、role（admin/user）、is_active、token_version、created_at、last_login_at。

另设 person_aliases(alias, user_id)，处理"蒋烨阳/蒋烨洋"这类别名。

### categories

id、name、kind（purchase/expense）、sort_order、is_active。

采购类别：标准件、板材件、机加工、官方器件、硬件、铝方管、大采购、快递、打车、周边。

费用类型：报名费、高铁、住宿、货拉拉、打车、快递、采购、周边。

注意：样例目录的"高铁/酒店/报名费"和手工表的"标准件/板材件"不是同一层概念，不能共用一个字段硬塞。用 kind 区分，发票上只挂一个主类别，后续可扩展多标签。

### documents / document_versions

documents：id、doc_type（invoice/payment_evidence/receipt/other）、title、owner_user_id、current_version_id、created_by、created_at、deleted_at。

document_versions：id、document_id、version_no、storage_key、original_name、display_name、mime_type、size_bytes、sha256、created_by、created_at、is_latest。

- 文件按 sha256 去重；同一逻辑文件重复上传不新增版本。
- 存储路径：data/uploads/yyyy/mm/{sha256前两位}/{sha256}.{ext}；数据库只存相对 key。
- 原文件名只作展示，绝不参与路径拼接。

### extraction_jobs

id、document_id、provider（pdf_text/paddleocr_local/multimodal_llm）、model、prompt_version、status、attempts、raw_text、raw_response_json、parsed_json、confidence、error_code、error_message、queued_at、started_at、finished_at、reviewed_by、reviewed_at、review_decision、review_note。

状态：queued → running → review_pending → approved/rejected；失败为 failed。任何结果都必须人工审核后才能写发票主表。

### invoices

id、invoice_number（唯一）、invoice_code（可空）、invoice_type、issue_date、seller_name、seller_tax_id、buyer_name、buyer_tax_id、amount_ex_tax_cents、tax_cents、total_cents、tax_rate_bp、currency（默认 CNY）、category_id、requester_id、owner_id、invoice_form（电子/纸质）、status（review_pending/active/void/duplicate）、paid_cents（缓存）、payment_status（unpaid/partial/paid）、source_document_id、extraction_job_id、note、product_url、created_by、confirmed_by、confirmed_at、created_at、updated_at、deleted_at。

索引：invoice_number 唯一；issue_date、category_id、requester_id、status 建索引。

### invoice_items

id、invoice_id、name、quantity、unit_price_millis、amount_cents、note、sort_order。

明细合计与发票总额不一致时只告警，不阻断；审核人必须填写差异原因或修正。

### payments

id、amount_cents（真实付款总额）、paid_at、payer_user_id（可空）、payer_name、method（personal_advance/teacher_advance/bank_transfer/alipay/wechat/card/cash/other）、external_txn_ref、evidence_document_id（可空）、status（unallocated/partially_allocated/fully_allocated/void）、requested_at、confirmed_by、confirmed_at、note、created_by、created_at。

### payment_allocations

id、payment_id、invoice_id、amount_cents、status（active/reversed）、note、created_by、created_at、updated_at。

约束：

- 同一 payment + invoice 只允许一条 active allocation（SQLite 部分唯一索引）。
- SUM(active allocation.amount_cents) <= payments.amount_cents。
- SUM(active allocation.amount_cents) <= invoices.total_cents。
- 分配或撤销后，重算 payment.status 和 invoice.payment_status。
- payments.status 的 void、payment_allocations.status 的 reversed 只是预留，本版不提供超额付款、退款、红冲入口。

### audit_logs

id、actor_id、action、entity_type、entity_id、before_json、after_json、ip、user_agent、created_at。

### report_templates / export_jobs

report_templates：id、name、columns_json、filters_json、sort_json、created_by、is_shared、created_at。

export_jobs：id、template_id、filters_json、status、file_document_id、created_by、created_at、expires_at、error_message。

## 6. 文件命名与下载

存储名：

    金额-人员-商户或路线-类别-文档类型-时间戳.扩展名

管理员下载名：

    金额-人员-商户或路线-类别-文档类型.扩展名

规则：

- 金额统一两位小数，不带"元"；例如 124.00。
- 人员用英文逗号分隔，使用 users.display_name 的规范名。
- 商户或路线：交通用"出发站-到达站"，住宿/采购用商户名。
- 类别用 categories.name；文档类型用 发票/支付截图/支付凭证/水单/收据。
- 时间戳 yyyyMMddHHmmss，追加在扩展名前；这是存储名的一部分。
- 展示名不带时间戳；管理员下载时文件名必须带扩展名，例如 "124.00-杨泽,朱建诚-上海站-无锡站-高铁-支付凭证.jpg"。
- 下载响应使用正确 Content-Type（application/pdf、image/jpeg 等）和 attachment，文件名带当前版本扩展名，确保下载后能直接打开。
- 普通用户没有下载权限；只能通过预览接口查看最新版，预览用 inline，不提供 attachment。
- 扩展名以当前版本的实际文件类型为准（pdf/jpg/png），不能从展示名猜。
- 文件名做 NFKC 规范化，去掉 / \ : * ? " < > | 和控制字符，总长度限制 150 字符。
- 抽取完成前可用 "待识别-时间戳.ext"；审核通过后生成规范展示名，旧版本保留但不对普通用户展示。

## 7. 识别引擎

支持三种 provider，统一接口：

    extract(document) -> ExtractionResult

- pdf_text：优先读 PDF 文本层、嵌入 XML/OFD；数电票能直接解析就不 OCR。
- paddleocr_local：调用本地 PaddleOCR HTTP 服务，返回文本块、坐标、置信度。
- multimodal_llm：把页面图片和 JSON Schema 发给多模态 LLM，要求返回严格 JSON；校验失败重试一次。

流程：

1. 上传校验：大小、MIME、magic bytes，拒绝 SVG/HTML/脚本；PDF 渲染成 200-300 DPI 图片。
2. 按配置选择 provider；auto 模式先 pdf_text，再 PaddleOCR，失败再 LLM。
3. 结果做规范化：金额、日期、发票号码、税号、购方/销方。
4. 规则校验：发票号码格式、金额关系、日期范围、发票号码是否重复。
5. 无论置信度高低，都进入人工审核；低置信度/校验失败高亮。
6. 审核通过后才创建/更新 invoice、invoice_items，并生成 payment 草稿。

每个 job 必须记录 provider、model、prompt_version，保证可复现。云端 LLM 会把发票图片发到外部，默认关闭，需显式开启并在页面提示；本地 PaddleOCR 是默认引擎。

### 人工审核

- 待审核列表：按上传时间、状态、置信度排序。
- 详情页：左侧原文件预览，右侧字段表单；字段级置信度、校验错误、与上一次结果的 diff。
- 操作：保存草稿、通过、驳回、换引擎重跑、标记重复。
- 通过前必须填必填字段：发票号码、开票日期、金额、类别、申购人、负责人。
- 审核记录写 audit_logs，保留修改前后值。

### 异步任务

单机不引入 Redis。用 SQLite 的 extraction_jobs 表做队列，独立 worker 进程轮询：

- worker 启动时把超时的 running 任务改回 queued。
- 一次只处理 1 个任务（可配置到 2），避免 SQLite 写锁。
- 失败重试 3 次，指数退避；超过后标记 failed 并通知管理员。
- 前端轮询 job 状态即可，单机用户量不需要 WebSocket。

## 8. 对账与"缺什么"

对账口径按 allocation 汇总：

- 发票已付金额 = SUM(active allocation.amount_cents)。
- 付款已分配金额 = SUM(active allocation.amount_cents)。

对账页面分四类：

1. 有发票无付款/部分付款：发票已付金额 < 发票金额。
2. 有付款无发票/部分未分配：付款已分配金额 < 付款金额。
3. 金额异常：分配导致发票或付款超额、四舍五入差超过 0.01 元。
4. 凭证缺失：method != teacher_advance 且 evidence_document_id 为空。老师代付不要求凭证。

补充检查：

- 发票号码重复。
- 发票明细合计与总额不一致。
- 付款日期早于开票日期（预付款，仅提示）。
- allocation 挂到 void/duplicate 发票。
- 同一 payment + invoice 出现多条 active allocation。

老师代付在验收语料中按已付款处理：27 张各生成一条 payment 并全额分配，不产生"缺付款"或"缺凭证"告警。每条异常支持"忽略/备注/人工关联"，处理后写审计日志。对账结果不直接改数据，必须走确认动作。

## 9. API 草图

    POST   /api/v1/auth/login
    POST   /api/v1/auth/refresh
    POST   /api/v1/auth/logout
    GET    /api/v1/me

    GET    /api/v1/users                  admin
    POST   /api/v1/users                  admin
    PATCH  /api/v1/users/{id}             admin

    POST   /api/v1/documents              上传，返回 document + job
    GET    /api/v1/documents/{id}
    GET    /api/v1/documents/{id}/preview?version=latest   user/admin，inline
    GET    /api/v1/documents/{id}/download?version=latest  admin only，带扩展名
    POST   /api/v1/documents/{id}/versions

    GET    /api/v1/extraction-jobs
    GET    /api/v1/extraction-jobs/{id}
    POST   /api/v1/extraction-jobs/{id}/retry
    POST   /api/v1/extraction-jobs/{id}/approve
    POST   /api/v1/extraction-jobs/{id}/reject

    GET    /api/v1/invoices
    POST   /api/v1/invoices
    GET    /api/v1/invoices/{id}
    PATCH  /api/v1/invoices/{id}

    GET    /api/v1/payments
    POST   /api/v1/payments
    GET    /api/v1/payments/{id}
    PATCH  /api/v1/payments/{id}
    POST   /api/v1/payments/{id}/allocations
    PATCH  /api/v1/allocations/{id}
    DELETE /api/v1/allocations/{id}
    GET    /api/v1/invoices/{id}/payments

    GET    /api/v1/reconciliation/summary
    GET    /api/v1/reconciliation/issues

    GET    /api/v1/report-templates
    POST   /api/v1/report-templates
    POST   /api/v1/exports
    GET    /api/v1/exports/{id}/download

    GET    /api/v1/dashboard/summary
    GET    /api/v1/audit-logs             admin

统一错误结构：{code, message, details, trace_id}。列表用 page/page_size，默认 20，最大 100。

## 10. 导出与图表

"按用户要求整理表头"落成模板，不做自然语言生成：

- 字段目录：发票、明细、付款、人员、类别、文件等可选列。
- 模板保存列顺序、列名、宽度、格式、筛选、排序、汇总行。
- 预览后异步生成 xlsx；生成完给下载链接，过期时间 24 小时。
- 导出的 xlsx 是系统生成文件，保留 .xlsx 扩展名；所有下载都必须带扩展名。
- 大数量用 openpyxl write_only；金额写数字、日期写日期格式；冻结表头；加合计行。
- 文本单元格防公式注入：以 = + - @ 开头的值前加单引号。
- 默认模板复刻手工表的 16 列：序号、名称、购买数量、单价、总价、单张发票金额、店铺、申购人、负责人、发票号码、发票图片、付款记录、发票形式、备注、申请老师代付时间、链接。
- 按付款人汇总用 payments.amount_cents；按发票归属/成本用 payment_allocations.amount_cents，两者不能混用。

图表：

- 指标口径先定：开票总额、付款总额、按类别、按付款人、按月、缺口数量。
- 前端 ECharts 渲染；导出图片用 getDataURL 生成 PNG。
- 需要服务端出图时用 Playwright，服务器必须安装中文字体。

## 11. 架构与部署

模块化单体，按限界上下文分目录：

    auth / users / documents / extraction / invoices / payments /
    reconciliation / reports / audit / shared

依赖方向：api → application → domain ← infrastructure。ORM 模型不直接进 API，统一用 Pydantic schema。

- FastAPI + SQLAlchemy 2.0 + Alembic + Pydantic v2。
- SQLite：WAL、foreign_keys=ON、busy_timeout=5000、短事务；迁移用 Alembic。
- worker 独立进程，和 web 共用一个 SQLite 文件和 uploads 目录。
- 单机 Docker Compose 或 systemd 启动 web + worker；Nginx 做 HTTPS 和静态资源。
- 备份：每天 SQLite 在线备份 + uploads 增量备份；定期做恢复演练。
- 日志：结构化 JSON，带 request_id；健康检查 /healthz、/readyz。
- 测试：pytest + httpx + 临时 SQLite；前端 Vitest + Playwright；OCR 用 20-50 张金标准发票做字段准确率回归。

## 12. 与手工表对照（仅测试）

这份 xlsx 不导入生产库。它的用途是：

- 作为 145 张发票的测试索引；
- 提供发票图片、付款截图的来源；
- 抽取结果与人工表逐字段对照。

对照前必须先修正已知错误，例如"蒋烨阳/蒋烨洋"、类别写法不一致、合并单元格导致的重复总价。不能把 xlsx 的原始值直接当作准确率分母。

| 手工表列 | 系统字段 |
|---|---|
| 序号 | 不存；由 category + 序号生成展示编号，或直接用 id |
| 名称 | invoice_items.name |
| 购买数量 | invoice_items.quantity |
| 单价 | invoice_items.unit_price_millis |
| 总价 | invoice_items.amount_cents |
| 单张发票金额 | invoices.total_cents |
| 店铺 | invoices.seller_name |
| 申购人 | invoices.requester_id |
| 负责人 | invoices.owner_id |
| 发票号码 | invoices.invoice_number |
| 发票图片 | documents(doc_type=invoice) |
| 付款记录 | payments + payment_allocations；截图是 payment_evidence |
| 发票形式 | invoices.invoice_form |
| 备注 | invoices.note；"XX垫付"同时决定 payment.method/payer |
| 申请老师代付时间 | payments.requested_at + method=teacher_advance |
| 链接 | invoices.product_url |

### 12.1 测试语料怎么建

1. 从 xlsx 的 xl/cellimages.xml、xl/_rels/cellimages.xml.rels、xl/media 导出 DISPIMG 对应的发票图和付款截图。
2. 每张发票建一个 fixture 目录：tests/fixtures/invoices/{invoice_number}/，放 invoice.pdf 或 invoice.jpg、payment.jpg、expected.json。
3. expected.json 保存修正后的期望值：发票号码、开票日期、销方、价税合计、税额、明细、申购人、负责人、类别、发票形式、付款方式。另加 source_cell 和 corrections 字段，记录"xlsx 原值、修正值、修正原因"。
4. 直接覆盖全部 145 张：先跑通导出/对照脚本，再一次性生成 145 个 fixture，不抽样。
5. 对比脚本输出字段级准确率：发票号码、日期、金额、税额、销方、购方、明细行数。已知 xlsx 错误不计入错误率，单独列出。
6. 每次换 OCR/LLM 模型或 prompt，都跑同一套 fixture，结果存档，避免"感觉变好了"。

修正 xlsx 错误的责任人：管理员/最熟悉这批票据的人。修正后的 expected.json 才是测试基准。

## 13. 范围边界

已确认并纳入本版：

- 付款与发票是多对多，通过 payment_allocations 分配；124/198 用一笔 payment 分配 2/3 条 allocation；
- 管理员下载原文件必须带 .pdf/.jpg 等扩展名，下载后可直接打开；
- 普通用户不能下载，只能在线查看全部最新版文件；
- 老师代付不需要支付凭证，按有效付款处理；
- xlsx 只用于测试对照，不做生产数据迁移，且直接覆盖全部 145 张；
- xlsx 存在人工录入错误，测试基准要人工修正；
- 支持部分付款（发票未分配满），但不支持超额付款。

本版明确不做（先不管）：

- 超额付款/退款；
- 发票验真；
- 红冲、作废、重开；
- 外币、汇率、多币种结算。

数据库保留 void/reversed 等状态位，后续要做时再补流程，不在本版开放入口。

## 14. 建议里程碑

- M0：用户/JWT、类别、上传、文件版本、SQLite/Alembic。
- M1：PaddleOCR + LLM 适配器、任务队列、人工审核页。
- M2：发票/明细/付款、payment_allocations 多对多分配、对账缺口页。
- M3：模板导出 xlsx、仪表盘图表、审计日志。
- M4：测试语料与验收、备份、部署加固。
