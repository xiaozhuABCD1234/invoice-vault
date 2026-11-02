import type { ExportJob, ReportColumn, ReportTemplate } from '@/api/types'

export type ReportFieldFormat = 'text' | 'money' | 'date' | 'integer'
export type ReportFieldGroup = '发票' | '明细' | '付款' | '文件'

export interface ReportFieldDefinition {
  key: string
  label: string
  width: number
  format: ReportFieldFormat
  group: ReportFieldGroup
}

/**
 * 导出字段目录，key 与 docs/API_CONTRACT.md §8 对齐。
 * 明细金额与付款金额在契约中共用 amount_cents，因此这里只保留一个字段。
 */
export const REPORT_FIELD_CATALOG: readonly ReportFieldDefinition[] = [
  { key: 'invoice_number', label: '发票号码', width: 18, format: 'text', group: '发票' },
  { key: 'invoice_code', label: '发票代码', width: 18, format: 'text', group: '发票' },
  { key: 'invoice_type', label: '发票类型', width: 16, format: 'text', group: '发票' },
  { key: 'issue_date', label: '开票日期', width: 12, format: 'date', group: '发票' },
  { key: 'seller_name', label: '店铺', width: 24, format: 'text', group: '发票' },
  { key: 'total_cents', label: '发票金额', width: 14, format: 'money', group: '发票' },
  { key: 'amount_ex_tax_cents', label: '不含税金额', width: 14, format: 'money', group: '发票' },
  { key: 'tax_cents', label: '税额', width: 12, format: 'money', group: '发票' },
  { key: 'category_name', label: '类别', width: 12, format: 'text', group: '发票' },
  { key: 'requester_name', label: '申购人', width: 12, format: 'text', group: '发票' },
  { key: 'owner_name', label: '负责人', width: 12, format: 'text', group: '发票' },
  { key: 'invoice_form', label: '发票形式', width: 10, format: 'text', group: '发票' },
  { key: 'status', label: '发票状态', width: 10, format: 'text', group: '发票' },
  { key: 'note', label: '备注', width: 24, format: 'text', group: '发票' },
  { key: 'product_url', label: '链接', width: 28, format: 'text', group: '发票' },
  { key: 'item_name', label: '明细名称', width: 20, format: 'text', group: '明细' },
  { key: 'quantity', label: '数量', width: 10, format: 'integer', group: '明细' },
  { key: 'unit_price_millis', label: '单价', width: 12, format: 'money', group: '明细' },
  { key: 'amount_cents', label: '金额（明细/付款）', width: 14, format: 'money', group: '明细' },
  { key: 'payer_name', label: '付款人', width: 12, format: 'text', group: '付款' },
  { key: 'method', label: '付款方式', width: 12, format: 'text', group: '付款' },
  { key: 'paid_at', label: '付款日期', width: 12, format: 'date', group: '付款' },
  { key: 'source_file_name', label: '源文件名', width: 24, format: 'text', group: '文件' },
]

const DEFAULT_COLUMN_KEYS = [
  'invoice_number',
  'issue_date',
  'seller_name',
  'total_cents',
  'category_name',
  'requester_name',
  'owner_name',
  'note',
]

export function findReportField(key: string): ReportFieldDefinition | null {
  return REPORT_FIELD_CATALOG.find((field) => field.key === key) ?? null
}

export function createReportColumn(key: string): ReportColumn | null {
  const field = findReportField(key)
  if (!field) return null
  return {
    key: field.key,
    label: field.label,
    width: field.width,
    format: field.format,
  }
}

export function createDefaultReportColumns(): ReportColumn[] {
  return DEFAULT_COLUMN_KEYS.map((key) => createReportColumn(key)).filter(
    (column): column is ReportColumn => column !== null,
  )
}

const FORMAT_LABELS: Record<ReportFieldFormat, string> = {
  text: '文本',
  money: '金额',
  date: '日期',
  integer: '整数',
}

export function formatReportFormat(format: string): string {
  if (format === 'text' || format === 'money' || format === 'date' || format === 'integer') {
    return FORMAT_LABELS[format]
  }
  return format
}

/** 下载文件名优先使用后端返回的 file_name，其次生成稳定回退名。 */
export function exportFileName(job: ExportJob): string {
  const name = job.file_name?.trim()
  return name !== undefined && name !== '' ? name : `发票导出-${job.id}.xlsx`
}

export function templateName(
  templates: readonly ReportTemplate[],
  templateId: number | null,
): string {
  if (templateId === null) return '自定义列'
  return (
    templates.find((template) => template.id === templateId)?.name ??
    `模板 #${templateId}`
  )
}
