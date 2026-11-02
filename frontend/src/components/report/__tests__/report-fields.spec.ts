import { describe, expect, it } from 'vitest'

import type { ExportJob, ReportTemplate } from '@/api/types'
import {
  REPORT_FIELD_CATALOG,
  createDefaultReportColumns,
  exportFileName,
  formatReportFormat,
  templateName,
} from '../report-fields'

const CONTRACT_KEYS = [
  'invoice_number',
  'issue_date',
  'seller_name',
  'total_cents',
  'amount_ex_tax_cents',
  'tax_cents',
  'category_name',
  'requester_name',
  'owner_name',
  'invoice_form',
  'status',
  'note',
  'product_url',
  'item_name',
  'quantity',
  'unit_price_millis',
  'amount_cents',
  'payer_name',
  'method',
  'paid_at',
  'source_file_name',
]

const BASE_JOB: ExportJob = {
  id: 7,
  template_id: null,
  status: 'succeeded',
  file_document_id: null,
  error_message: null,
  created_at: '2026-11-03T00:00:00Z',
  expires_at: '2026-11-04T00:00:00Z',
  download_url: null,
}

const TEMPLATE: ReportTemplate = {
  id: 2,
  name: '月度采购汇总',
  columns: [],
  filters: {},
  sort: [],
  created_by: 1,
  is_shared: true,
  created_at: '2026-11-03T00:00:00Z',
}

describe('report fields', () => {
  it('covers every field key from the API contract', () => {
    const keys = new Set(REPORT_FIELD_CATALOG.map((field) => field.key))
    for (const key of CONTRACT_KEYS) {
      expect(keys.has(key)).toBe(true)
    }
  })

  it('keeps the shared amount_cents key unique', () => {
    const amountFields = REPORT_FIELD_CATALOG.filter(
      (field) => field.key === 'amount_cents',
    )
    expect(amountFields).toHaveLength(1)
  })

  it('creates default columns from the catalog', () => {
    const columns = createDefaultReportColumns()
    expect(columns.length).toBeGreaterThan(0)
    for (const column of columns) {
      expect(
        REPORT_FIELD_CATALOG.some((field) => field.key === column.key),
      ).toBe(true)
    }
  })

  it('maps formats to readable labels', () => {
    expect(formatReportFormat('money')).toBe('金额')
    expect(formatReportFormat('date')).toBe('日期')
    expect(formatReportFormat('custom')).toBe('custom')
  })

  it('prefers file_name and falls back to the generated filename', () => {
    expect(exportFileName(BASE_JOB)).toBe('发票导出-7.xlsx')
    expect(exportFileName({ ...BASE_JOB, file_name: '  ' })).toBe(
      '发票导出-7.xlsx',
    )
    expect(exportFileName({ ...BASE_JOB, file_name: '发票.xlsx' })).toBe(
      '发票.xlsx',
    )
  })

  it('resolves template names with a fallback', () => {
    expect(templateName([TEMPLATE], 2)).toBe('月度采购汇总')
    expect(templateName([], 2)).toBe('模板 #2')
    expect(templateName([], null)).toBe('自定义列')
  })
})
