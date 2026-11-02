import { ApiError } from '@/api/client'
import type {
  Document,
  DocumentType,
  ExtractionJob,
  ExtractionProvider,
  ExtractionStatus,
} from '@/api/types'
import { EMPTY_TEXT } from '@/lib/format'

/** 后端文档上传限制：单文件 20MB，只接受 PDF / JPG / JPEG / PNG / WEBP。 */
export const MAX_UPLOAD_BYTES = 20 * 1024 * 1024
export const UPLOAD_ACCEPT = '.pdf,.jpg,.jpeg,.png,.webp'
export const ACCEPTED_UPLOAD_EXTENSIONS = ['pdf', 'jpg', 'jpeg', 'png', 'webp']

export interface SelectOptionItem {
  value: string
  label: string
}

export const PAGE_SIZES = [20, 50, 100]
export const DEFAULT_PAGE_SIZE = PAGE_SIZES[0] ?? 20

export function isPageSize(value: number): boolean {
  return PAGE_SIZES.includes(value)
}

export const DOCUMENT_TYPE_LABELS: Record<DocumentType, string> = {
  invoice: '发票',
  payment_evidence: '付款凭证',
  receipt: '收据',
  other: '其他',
}

export const DOCUMENT_TYPE_OPTIONS: SelectOptionItem[] = [
  { value: 'invoice', label: DOCUMENT_TYPE_LABELS.invoice },
  { value: 'payment_evidence', label: DOCUMENT_TYPE_LABELS.payment_evidence },
  { value: 'receipt', label: DOCUMENT_TYPE_LABELS.receipt },
  { value: 'other', label: DOCUMENT_TYPE_LABELS.other },
]

export const DOCUMENT_TYPE_FILTER_OPTIONS: SelectOptionItem[] = [
  { value: 'all', label: '全部类型' },
  ...DOCUMENT_TYPE_OPTIONS,
]

export const PROVIDER_LABELS: Record<ExtractionProvider, string> = {
  pdf_text: 'PDF 文本',
  paddleocr_local: 'PaddleOCR 本地',
  multimodal_llm: '多模态大模型',
  mock: '模拟识别',
}

export const PROVIDER_FILTER_OPTIONS: SelectOptionItem[] = [
  { value: 'all', label: '全部识别器' },
  { value: 'pdf_text', label: PROVIDER_LABELS.pdf_text },
  { value: 'paddleocr_local', label: PROVIDER_LABELS.paddleocr_local },
  { value: 'multimodal_llm', label: PROVIDER_LABELS.multimodal_llm },
  { value: 'mock', label: PROVIDER_LABELS.mock },
]

export const JOB_STATUS_OPTIONS: SelectOptionItem[] = [
  { value: 'review_pending', label: '待审核' },
  { value: 'queued', label: '排队中' },
  { value: 'running', label: '识别中' },
  { value: 'approved', label: '已通过' },
  { value: 'rejected', label: '已驳回' },
  { value: 'failed', label: '失败' },
  { value: 'all', label: '全部状态' },
]

export function isDocumentType(value: unknown): value is DocumentType {
  return (
    value === 'invoice' ||
    value === 'payment_evidence' ||
    value === 'receipt' ||
    value === 'other'
  )
}

export function isExtractionProvider(value: unknown): value is ExtractionProvider {
  return (
    value === 'pdf_text' ||
    value === 'paddleocr_local' ||
    value === 'multimodal_llm' ||
    value === 'mock'
  )
}

export function apiErrorMessage(error: unknown, fallback: string): string {
  return error instanceof ApiError ? error.message : fallback
}

export function documentTypeLabel(
  value: DocumentType | null | undefined,
): string {
  return value ? DOCUMENT_TYPE_LABELS[value] : EMPTY_TEXT
}

export function providerLabel(
  value: ExtractionProvider | null | undefined,
): string {
  return value ? PROVIDER_LABELS[value] : EMPTY_TEXT
}

export function isActiveExtractionStatus(
  status: ExtractionStatus | null | undefined,
): boolean {
  return status === 'queued' || status === 'running'
}

/** 重试入口：仅失败 / 驳回 / 待审核可重试，后端限制最多 3 次尝试。 */
export function canRetryExtraction(job: ExtractionJob): boolean {
  return (
    job.status === 'failed' ||
    job.status === 'rejected' ||
    job.status === 'review_pending'
  )
}

export function retryLimitReached(job: ExtractionJob): boolean {
  return job.attempts >= 3
}

/** 文档展示名：display_name 优先，其次 original_name / 标题。 */
export function documentFileName(document: Document): string {
  const version = document.current_version
  return (
    version?.display_name?.trim() ||
    version?.original_name?.trim() ||
    document.title?.trim() ||
    EMPTY_TEXT
  )
}

function extensionOf(name: string | null | undefined): string {
  if (!name) return ''
  const match = /\.([A-Za-z0-9]{1,10})$/.exec(name.trim())
  return match?.[1] ?? ''
}

function hasExtension(name: string): boolean {
  return /\.([A-Za-z0-9]{1,10})$/.test(name)
}

function sanitizeFileName(name: string): string {
  return name.replace(/[\\/:*?"<>|]/g, '-').trim()
}

/** 下载文件名从 display_name 推导，缺扩展名时取 original_name 的扩展名。 */
export function documentDownloadFileName(document: Document): string {
  const version = document.current_version
  const display =
    version?.display_name?.trim() ||
    document.title?.trim() ||
    `document-${document.id}`
  const original = version?.original_name?.trim() ?? ''
  const extension = extensionOf(original)
  const withExtension =
    hasExtension(display) || extension === ''
      ? display
      : `${display}.${extension}`
  return sanitizeFileName(withExtension) || 'document'
}

export function validateUploadFile(file: File): string | null {
  const extension = extensionOf(file.name).toLowerCase()
  if (!ACCEPTED_UPLOAD_EXTENSIONS.includes(extension)) {
    return '仅支持 PDF、JPG、JPEG、PNG、WEBP 文件。'
  }
  if (file.size <= 0) {
    return '文件内容为空，请重新选择。'
  }
  if (file.size > MAX_UPLOAD_BYTES) {
    return '文件大小超过 20MB，请压缩后重新上传。'
  }
  return null
}

/** 同一文档可能有多个任务，取最新一条（按入队时间、id 倒序）。 */
export function latestExtractionJob(
  jobs: ExtractionJob[] | null | undefined,
): ExtractionJob | null {
  if (!jobs || jobs.length === 0) return null

  const sorted = [...jobs].sort((left, right) => {
    const byTime = left.queued_at.localeCompare(right.queued_at)
    return byTime !== 0 ? byTime : left.id - right.id
  })

  return sorted[sorted.length - 1] ?? null
}
