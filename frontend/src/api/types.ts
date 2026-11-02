/**
 * API 类型定义，严格对齐 docs/API_CONTRACT.md。
 * 字段名使用后端 snake_case；所有金额均为整数分（*_cents）。
 */

export type JsonValue =
  | string
  | number
  | boolean
  | null
  | JsonValue[]
  | { [key: string]: JsonValue }

export type JsonObject = { [key: string]: JsonValue }

export type SortOrder = 'asc' | 'desc'

// ---------------------------------------------------------------------------
// 通用
// ---------------------------------------------------------------------------

export interface Page<T> {
  items: T[]
  total: number
  page: number
  page_size: number
}

export interface PageQuery {
  page?: number
  page_size?: number
  q?: string
}

export interface ItemsResponse<T> {
  items: T[]
}

// ---------------------------------------------------------------------------
// 认证与用户
// ---------------------------------------------------------------------------

export type Role = 'admin' | 'user'

export interface User {
  id: number
  username: string
  display_name: string
  role: Role
  is_active: boolean
  created_at: string
  last_login_at: string | null
}

/** 下拉选择用的轻量用户信息，登录用户即可读取。 */
export interface UserOption {
  id: number
  display_name: string
  role: Role
  is_active: boolean
}

export interface LoginRequest {
  username: string
  password: string
}

export interface TokenResponse {
  access_token: string
  token_type: 'bearer'
  expires_in: number
  user: User
}

/** refresh 契约只保证 token 部分；user 为可选补齐字段。 */
export interface RefreshResponse {
  access_token: string
  token_type: 'bearer'
  expires_in: number
  user?: User
}

export interface UserListQuery extends PageQuery {
  role?: Role
  is_active?: boolean
}

export interface UserCreate {
  username: string
  display_name: string
  password: string
  role: Role
}

export interface UserUpdate {
  display_name?: string
  role?: Role
  is_active?: boolean
  password?: string
}

// ---------------------------------------------------------------------------
// 类别
// ---------------------------------------------------------------------------

export type CategoryKind = 'purchase' | 'expense'

export interface Category {
  id: number
  name: string
  kind: CategoryKind
  sort_order: number
  is_active: boolean
}

export interface CategoryListQuery {
  kind?: CategoryKind
  include_inactive?: boolean
}

export interface CategoryCreate {
  name: string
  kind: CategoryKind
  sort_order?: number
}

export interface CategoryUpdate {
  name?: string
  sort_order?: number
  is_active?: boolean
}

// ---------------------------------------------------------------------------
// 文档与文件
// ---------------------------------------------------------------------------

export type DocumentType = 'invoice' | 'payment_evidence' | 'receipt' | 'other'

export interface DocumentVersion {
  id: number
  version_no: number
  original_name: string
  display_name: string
  mime_type: string
  size_bytes: number
  sha256: string
  created_at: string
  is_latest: boolean
}

export interface Document {
  id: number
  doc_type: DocumentType
  title: string
  owner_user_id: number
  /** 后端补充的展示字段，旧响应可能缺省。 */
  owner_name?: string | null
  current_version: DocumentVersion
  created_at: string
  deleted_at: string | null
}

export interface DocumentListQuery extends PageQuery {
  doc_type?: DocumentType
}

export interface DocumentUploadInput {
  file: File
  doc_type: DocumentType
  title?: string
}

export interface DocumentUploadResponse {
  document: Document
  extraction_job: ExtractionJob | null
  /** 同一 sha256 已存在时为 true，此时不会新建版本。 */
  reused?: boolean
}

export interface DocumentDetail {
  document: Document
  version_count: number
  extraction_jobs: ExtractionJob[]
}

/** 预览：latest 或 admin 可用的版本 id。 */
export type DocumentPreviewVersion = 'latest' | number

// ---------------------------------------------------------------------------
// 抽取任务
// ---------------------------------------------------------------------------

export type ExtractionStatus =
  | 'queued'
  | 'running'
  | 'review_pending'
  | 'approved'
  | 'rejected'
  | 'failed'

export type ExtractionProvider =
  | 'pdf_text'
  | 'paddleocr_local'
  | 'multimodal_llm'
  | 'mock'

export type ReviewDecision = 'approved' | 'rejected'

export interface ExtractionValidation {
  errors: string[]
  warnings: string[]
  field_confidence: Record<string, number>
}

export interface ExtractionJob {
  id: number
  document_id: number
  provider: ExtractionProvider
  model: string | null
  prompt_version: string | null
  status: ExtractionStatus
  attempts: number
  confidence: number | null
  /** 规范化后的候选字段；字段集合随 provider 变化。 */
  parsed: JsonObject | null
  validation: ExtractionValidation | null
  error_code: string | null
  error_message: string | null
  queued_at: string
  started_at: string | null
  finished_at: string | null
  reviewed_by: number | null
  reviewed_at: string | null
  review_decision: ReviewDecision | null
  review_note: string | null
  /** 后端补充的展示字段。 */
  document_name?: string | null
  document_doc_type?: DocumentType | null
}

export interface ExtractionJobListQuery {
  page?: number
  page_size?: number
  status?: ExtractionStatus
  provider?: ExtractionProvider
}

export interface ExtractionJobDetail {
  job: ExtractionJob
  document: Document
  /** 与上一次审核 / 抽取结果的字段差异。 */
  diff: JsonObject | null
}

export interface ExtractionRejectRequest {
  note: string
}

export interface ExtractionApproveResponse {
  invoice: Invoice
  job: ExtractionJob
}

// ---------------------------------------------------------------------------
// 发票
// ---------------------------------------------------------------------------

export type InvoiceStatus = 'review_pending' | 'active' | 'void' | 'duplicate'
export type InvoicePaymentStatus = 'unpaid' | 'partial' | 'paid'
export type InvoiceForm = 'electronic' | 'paper'

export interface InvoiceItem {
  id: number
  name: string
  quantity: number
  /** 单价，整数 1/1000 元。 */
  unit_price_millis: number
  amount_cents: number
  note: string | null
  sort_order: number
}

export interface InvoiceAllocation {
  id: number
  payment_id: number
  amount_cents: number
  status: AllocationStatus
}

export interface Invoice {
  id: number
  invoice_number: string
  invoice_code: string | null
  invoice_type: string | null
  issue_date: string
  seller_name: string
  seller_tax_id: string | null
  buyer_name: string | null
  buyer_tax_id: string | null
  amount_ex_tax_cents: number
  tax_cents: number
  total_cents: number
  tax_rate_bp: number | null
  currency: string
  category_id: number
  requester_id: number | null
  owner_id: number | null
  invoice_form: InvoiceForm
  status: InvoiceStatus
  paid_cents: number
  payment_status: InvoicePaymentStatus
  source_document_id: number | null
  extraction_job_id: number | null
  note: string | null
  product_url: string | null
  created_by: number
  confirmed_by: number | null
  confirmed_at: string | null
  created_at: string
  updated_at: string
  deleted_at: string | null
  /** 后端补充的展示字段。 */
  category_name?: string | null
  requester_name?: string | null
  owner_name?: string | null
  items: InvoiceItem[]
  allocations: InvoiceAllocation[]
}

export interface InvoiceItemInput {
  name: string
  quantity: number
  unit_price_millis: number
  amount_cents: number
  note?: string | null
  sort_order?: number
}

export interface InvoiceCreate {
  invoice_number: string
  invoice_code?: string | null
  invoice_type?: string | null
  issue_date: string
  seller_name: string
  seller_tax_id?: string | null
  buyer_name?: string | null
  buyer_tax_id?: string | null
  amount_ex_tax_cents: number
  tax_cents: number
  total_cents: number
  tax_rate_bp?: number | null
  category_id: number
  requester_id?: number | null
  owner_id?: number | null
  invoice_form?: InvoiceForm
  status?: InvoiceStatus
  source_document_id?: number | null
  note?: string | null
  product_url?: string | null
  items: InvoiceItemInput[]
}

export interface InvoiceUpdate {
  invoice_number?: string
  invoice_code?: string | null
  invoice_type?: string | null
  issue_date?: string
  seller_name?: string
  seller_tax_id?: string | null
  buyer_name?: string | null
  buyer_tax_id?: string | null
  amount_ex_tax_cents?: number
  tax_cents?: number
  total_cents?: number
  tax_rate_bp?: number | null
  category_id?: number
  requester_id?: number | null
  owner_id?: number | null
  invoice_form?: InvoiceForm
  status?: InvoiceStatus
  source_document_id?: number | null
  note?: string | null
  product_url?: string | null
  items?: InvoiceItemInput[]
}

export interface InvoiceListQuery extends PageQuery {
  status?: InvoiceStatus
  payment_status?: InvoicePaymentStatus
  category_id?: number
  requester_id?: number
  owner_id?: number
  date_from?: string
  date_to?: string
  sort?: string
}

/** GET /invoices/{id}/payments 中附带的付款摘要。 */
export interface InvoicePaymentSummary {
  id: number
  amount_cents: number
  paid_at: string
  payer_name: string
  method: PaymentMethod
  status: PaymentStatus
}

export interface InvoicePaymentAllocation extends Allocation {
  payment?: InvoicePaymentSummary
}

export interface InvoicePaymentsResponse {
  items: InvoicePaymentAllocation[]
}

// ---------------------------------------------------------------------------
// 付款与分配
// ---------------------------------------------------------------------------

export type PaymentMethod =
  | 'personal_advance'
  | 'teacher_advance'
  | 'bank_transfer'
  | 'alipay'
  | 'wechat'
  | 'card'
  | 'cash'
  | 'other'

export type PaymentStatus =
  | 'unallocated'
  | 'partially_allocated'
  | 'fully_allocated'
  | 'void'

export type AllocationStatus = 'active' | 'reversed'

export interface Allocation {
  id: number
  payment_id: number
  invoice_id: number
  amount_cents: number
  status: AllocationStatus
  note: string | null
  created_by: number
  created_at: string
  updated_at: string
  /** 付款详情响应可选内联的发票摘要；缺省时前端按 invoice_id 补取。 */
  invoice_number?: string | null
  invoice_seller_name?: string | null
}

export interface Payment {
  id: number
  amount_cents: number
  paid_at: string
  payer_user_id: number | null
  payer_name: string
  method: PaymentMethod
  external_txn_ref: string | null
  evidence_document_id: number | null
  status: PaymentStatus
  requested_at: string | null
  confirmed_by: number | null
  confirmed_at: string | null
  note: string | null
  created_by: number
  created_at: string
  allocated_cents: number
  allocations: Allocation[]
}

export interface PaymentListQuery extends PageQuery {
  status?: PaymentStatus
  method?: PaymentMethod
  date_from?: string
  date_to?: string
  /** 服务端排序，格式 "字段:顺序"（如 paid_at:desc）。 */
  sort?: string
}

export interface PaymentCreate {
  amount_cents: number
  paid_at: string
  payer_user_id?: number | null
  payer_name?: string | null
  method: PaymentMethod
  external_txn_ref?: string | null
  evidence_document_id?: number | null
  requested_at?: string | null
  note?: string | null
}

export interface PaymentUpdate {
  amount_cents?: number
  paid_at?: string
  payer_name?: string | null
  method?: PaymentMethod
  external_txn_ref?: string | null
  evidence_document_id?: number | null
  requested_at?: string | null
  note?: string | null
}

export interface AllocationCreate {
  invoice_id: number
  amount_cents: number
  note?: string | null
}

export interface AllocationUpdate {
  amount_cents?: number
  note?: string | null
}

// ---------------------------------------------------------------------------
// 对账
// ---------------------------------------------------------------------------

export type ReconciliationIssueType =
  | 'invoice_unpaid'
  | 'invoice_partial'
  | 'payment_unallocated'
  | 'payment_partial'
  | 'missing_evidence'
  | 'duplicate_invoice'
  | 'item_mismatch'
  | 'amount_anomaly'
  | 'date_anomaly'

export type ReconciliationSeverity = 'error' | 'warning'
export type ReconciliationEntityType = 'invoice' | 'payment' | 'allocation'

export interface ReconciliationIssueCounts {
  invoice_unpaid: number
  invoice_partial: number
  payment_unallocated: number
  payment_partial: number
  missing_evidence: number
  duplicate_invoice: number
  item_mismatch: number
  amount_anomaly: number
  date_anomaly: number
}

export interface ReconciliationSummary {
  invoice_total_cents: number
  invoice_paid_cents: number
  invoice_unpaid_cents: number
  payment_total_cents: number
  payment_allocated_cents: number
  payment_unallocated_cents: number
  invoice_count: number
  payment_count: number
  issue_counts: ReconciliationIssueCounts
}

export interface ReconciliationIssue {
  /** 形如 "invoice_unpaid:12"。 */
  id: string
  type: ReconciliationIssueType
  severity: ReconciliationSeverity
  entity_type: ReconciliationEntityType
  entity_id: number
  title: string
  detail: string
  amount_cents: number | null
  ignored: boolean
  note: string | null
}

export interface ReconciliationIssueListQuery {
  page?: number
  page_size?: number
  type?: ReconciliationIssueType
  include_ignored?: boolean
}

export interface IgnoreIssueRequest {
  note: string
}

// ---------------------------------------------------------------------------
// 报表模板与导出
// ---------------------------------------------------------------------------

export interface ReportColumn {
  key: string
  label: string
  width: number
  format: string
}

export type ReportFilters = Omit<InvoiceListQuery, 'page' | 'page_size' | 'sort'>

export interface ReportSort {
  key: string
  order: SortOrder
}

export interface ReportTemplate {
  id: number
  name: string
  columns: ReportColumn[]
  filters: ReportFilters
  sort: ReportSort[]
  created_by: number
  is_shared: boolean
  created_at: string
}

export interface ReportTemplateCreate {
  name: string
  columns: ReportColumn[]
  filters?: ReportFilters
  sort?: ReportSort[]
  is_shared?: boolean
}

export interface ReportTemplateUpdate {
  name?: string
  columns?: ReportColumn[]
  filters?: ReportFilters
  sort?: ReportSort[]
  is_shared?: boolean
}

export type ExportStatus = 'queued' | 'running' | 'succeeded' | 'failed'

export interface ExportJob {
  id: number
  template_id: number | null
  status: ExportStatus
  file_document_id: number | null
  error_message: string | null
  created_at: string
  expires_at: string
  download_url: string | null
}

export interface ExportCreate {
  template_id?: number
  columns?: ReportColumn[]
  filters?: ReportFilters
  sort?: ReportSort[]
}

export interface ExportCreateResponse {
  export: ExportJob
}

export interface ExportListQuery {
  page?: number
  page_size?: number
}

// ---------------------------------------------------------------------------
// 仪表盘
// ---------------------------------------------------------------------------

export interface DashboardTotals {
  invoice_count: number
  invoice_total_cents: number
  payment_total_cents: number
  paid_cents: number
  unpaid_cents: number
  missing_evidence_count: number
}

export interface DashboardCategorySummary {
  category_id: number
  name: string
  invoice_count: number
  total_cents: number
}

export interface DashboardMonthSummary {
  month: string
  invoice_count: number
  total_cents: number
}

export interface DashboardPayerSummary {
  payer_name: string
  payment_count: number
  total_cents: number
}

export interface DashboardGaps {
  invoice_unpaid: number
  payment_unallocated: number
  missing_evidence: number
}

export interface DashboardSummary {
  totals: DashboardTotals
  by_category: DashboardCategorySummary[]
  by_month: DashboardMonthSummary[]
  by_payer: DashboardPayerSummary[]
  gaps: DashboardGaps
}

export interface DashboardQuery {
  date_from?: string
  date_to?: string
}

// ---------------------------------------------------------------------------
// 审计日志
// ---------------------------------------------------------------------------

export interface AuditLog {
  id: number
  actor_id: number | null
  actor_name: string | null
  action: string
  entity_type: string
  entity_id: number | null
  before: JsonValue | null
  after: JsonValue | null
  ip: string | null
  user_agent: string | null
  created_at: string
}

export interface AuditLogListQuery {
  page?: number
  page_size?: number
  action?: string
  entity_type?: string
  entity_id?: number
  actor_id?: number
  date_from?: string
  date_to?: string
}
