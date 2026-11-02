import type {
  ExtractionJob,
  InvoiceCreate,
  InvoiceForm,
  InvoiceItemInput,
  JsonObject,
  JsonValue,
} from '@/api/types'
import { formatDate } from '@/lib/date'
import { EMPTY_TEXT } from '@/lib/format'
import { centsToYuanInput, formatCents, parseYuanToCents } from '@/lib/money'

export interface InvoiceItemDraft {
  name: string
  quantity: string
  unitPrice: string
  amount: string
  note: string
}

export interface InvoiceDraft {
  invoiceNumber: string
  invoiceCode: string
  invoiceType: string
  issueDate: string
  sellerName: string
  sellerTaxId: string
  buyerName: string
  buyerTaxId: string
  amountExTax: string
  tax: string
  total: string
  taxRate: string
  categoryId: string
  requesterId: string
  ownerId: string
  invoiceForm: InvoiceForm
  note: string
  productUrl: string
  items: InvoiceItemDraft[]
}

export type InvoiceDraftErrors = Record<string, string>

export interface InvoiceDraftValidation {
  errors: InvoiceDraftErrors
  payload: InvoiceCreate | null
  amountMismatch: string | null
}

export const INVOICE_FIELD_IDS: Record<string, string> = {
  invoiceNumber: 'review-invoice-number',
  invoiceCode: 'review-invoice-code',
  invoiceType: 'review-invoice-type',
  issueDate: 'review-issue-date',
  sellerName: 'review-seller-name',
  sellerTaxId: 'review-seller-tax-id',
  buyerName: 'review-buyer-name',
  buyerTaxId: 'review-buyer-tax-id',
  amountExTax: 'review-amount-ex-tax',
  tax: 'review-tax',
  total: 'review-total',
  taxRate: 'review-tax-rate',
  categoryId: 'review-category',
  requesterId: 'review-requester',
  ownerId: 'review-owner',
  invoiceForm: 'review-invoice-form',
  note: 'review-note',
  productUrl: 'review-product-url',
  items: 'review-items',
}

const ITEM_FIELD_IDS: Record<string, string> = {
  name: 'name',
  quantity: 'quantity',
  unitPrice: 'unit-price',
  amount: 'amount',
}

export const EXTRACTION_FIELD_LABELS: Record<string, string> = {
  invoice_number: '发票号码',
  invoiceNumber: '发票号码',
  invoice_code: '发票代码',
  invoiceCode: '发票代码',
  invoice_type: '发票类型',
  invoiceType: '发票类型',
  issue_date: '开票日期',
  issueDate: '开票日期',
  seller_name: '销方名称',
  sellerName: '销方名称',
  seller_tax_id: '销方税号',
  sellerTaxId: '销方税号',
  buyer_name: '购方名称',
  buyerName: '购方名称',
  buyer_tax_id: '购方税号',
  buyerTaxId: '购方税号',
  amount_ex_tax_cents: '不含税金额',
  amountExTaxCents: '不含税金额',
  amount_ex_tax: '不含税金额',
  amountExTax: '不含税金额',
  tax_cents: '税额',
  taxCents: '税额',
  tax: '税额',
  total_cents: '价税合计',
  totalCents: '价税合计',
  total: '价税合计',
  tax_rate_bp: '税率',
  taxRateBp: '税率',
  tax_rate: '税率',
  taxRate: '税率',
  category_id: '类别',
  categoryId: '类别',
  requester_id: '申购人',
  requesterId: '申购人',
  owner_id: '负责人',
  ownerId: '负责人',
  invoice_form: '发票形式',
  invoiceForm: '发票形式',
  note: '备注',
  product_url: '商品链接',
  productUrl: '商品链接',
  items: '发票明细',
}

export function extractionFieldLabel(key: string): string {
  return EXTRACTION_FIELD_LABELS[key] ?? key
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function readValue(record: Record<string, unknown>, keys: string[]): unknown {
  for (const key of keys) {
    if (key in record) return record[key]
  }
  return undefined
}

function readString(record: Record<string, unknown>, keys: string[]): string {
  const value = readValue(record, keys)
  if (typeof value === 'string') return value
  if (typeof value === 'number' && Number.isFinite(value)) return String(value)
  return ''
}

function readNumber(
  record: Record<string, unknown>,
  keys: string[],
): number | null {
  const value = readValue(record, keys)
  if (typeof value === 'number' && Number.isFinite(value)) return value
  if (typeof value === 'string' && value.trim() !== '') {
    const parsed = Number(value)
    return Number.isFinite(parsed) ? parsed : null
  }
  return null
}

function readInvoiceForm(record: Record<string, unknown>): InvoiceForm {
  const value = readString(record, ['invoice_form', 'invoiceForm'])
  return value === 'paper' ? 'paper' : 'electronic'
}

function readItems(value: JsonValue | undefined): InvoiceItemDraft[] {
  if (!Array.isArray(value)) return []

  return value.map((entry) => {
    if (!isRecord(entry)) return createEmptyItemDraft()
    return {
      name: readString(entry, ['name']),
      quantity: readString(entry, ['quantity']),
      unitPrice: millisToYuanInput(
        readNumber(entry, ['unit_price_millis', 'unitPriceMillis']),
      ),
      amount: centsToYuanInput(
        readNumber(entry, ['amount_cents', 'amountCents']),
      ),
      note: readString(entry, ['note']),
    }
  })
}

export function createEmptyItemDraft(): InvoiceItemDraft {
  return { name: '', quantity: '1', unitPrice: '', amount: '', note: '' }
}

export function createEmptyInvoiceDraft(): InvoiceDraft {
  return {
    invoiceNumber: '',
    invoiceCode: '',
    invoiceType: '',
    issueDate: '',
    sellerName: '',
    sellerTaxId: '',
    buyerName: '',
    buyerTaxId: '',
    amountExTax: '',
    tax: '',
    total: '',
    taxRate: '',
    categoryId: '',
    requesterId: '',
    ownerId: '',
    invoiceForm: 'electronic',
    note: '',
    productUrl: '',
    items: [],
  }
}

function normalizeIssueDate(value: unknown): string {
  if (typeof value !== 'string' || value.trim() === '') return ''
  const formatted = formatDate(value)
  return formatted === EMPTY_TEXT ? '' : formatted
}

/** 从抽取任务的 parsed（camelCase，金额为分）生成可编辑草稿。 */
export function createInvoiceDraft(
  job: Pick<ExtractionJob, 'parsed'>,
): InvoiceDraft {
  const parsed: JsonObject | null = job.parsed
  if (!parsed) return createEmptyInvoiceDraft()

  const record: Record<string, unknown> = parsed
  const items = readItems(parsed.items)

  return {
    invoiceNumber: readString(record, ['invoice_number', 'invoiceNumber']),
    invoiceCode: readString(record, ['invoice_code', 'invoiceCode']),
    invoiceType: readString(record, ['invoice_type', 'invoiceType']),
    issueDate: normalizeIssueDate(
      readValue(record, ['issue_date', 'issueDate']),
    ),
    sellerName: readString(record, ['seller_name', 'sellerName']),
    sellerTaxId: readString(record, ['seller_tax_id', 'sellerTaxId']),
    buyerName: readString(record, ['buyer_name', 'buyerName']),
    buyerTaxId: readString(record, ['buyer_tax_id', 'buyerTaxId']),
    amountExTax: centsToYuanInput(
      readNumber(record, ['amount_ex_tax_cents', 'amountExTaxCents']),
    ),
    tax: centsToYuanInput(readNumber(record, ['tax_cents', 'taxCents'])),
    total: centsToYuanInput(readNumber(record, ['total_cents', 'totalCents'])),
    taxRate: bpToPercentInput(
      readNumber(record, ['tax_rate_bp', 'taxRateBp']),
    ),
    categoryId: readString(record, ['category_id', 'categoryId']),
    requesterId: readString(record, ['requester_id', 'requesterId']),
    ownerId: readString(record, ['owner_id', 'ownerId']),
    invoiceForm: readInvoiceForm(record),
    note: readString(record, ['note']),
    productUrl: readString(record, ['product_url', 'productUrl']),
    items,
  }
}

/** 元字符串 → 1/1000 元整数，最多 3 位小数，全程整数运算。 */
export function parseYuanToMillis(
  input: string | null | undefined,
): number | null {
  if (typeof input !== 'string') return null

  const normalized = input.trim().replace(/[¥￥,\s]/g, '')
  const match = /^(-?)(\d+)(?:\.(\d{1,3}))?$/.exec(normalized)
  if (!match) return null

  const sign = match[1] === '-' ? -1 : 1
  const integerPart = match[2] ?? ''
  const fractionPart = match[3] ?? ''
  const millis = Number(`${integerPart}${fractionPart.padEnd(3, '0')}`)
  if (!Number.isSafeInteger(millis)) return null

  const result = sign * millis
  return result === 0 ? 0 : result
}

export function millisToYuanInput(
  millis: number | null | undefined,
): string {
  if (typeof millis !== 'number' || !Number.isFinite(millis)) return ''

  const rounded = Math.round(millis)
  const negative = rounded < 0
  const absolute = Math.abs(rounded)
  const yuan = Math.floor(absolute / 1000)
  const remainder = absolute % 1000
  const fraction = String(remainder)
    .padStart(3, '0')
    .replace(/0+$/, '')

  return `${negative ? '-' : ''}${yuan}${fraction ? `.${fraction}` : ''}`
}

/** 百分比字符串（最多 2 位小数）→ 基点（1bp = 0.01%）。 */
export function parsePercentToBp(
  input: string | null | undefined,
): number | null {
  if (typeof input !== 'string') return null

  const normalized = input.trim().replace(/[%％,\s]/g, '')
  const match = /^(\d+)(?:\.(\d{1,2}))?$/.exec(normalized)
  if (!match) return null

  const integerPart = match[1] ?? ''
  const fractionPart = match[2] ?? ''
  const bp = Number(`${integerPart}${fractionPart.padEnd(2, '0')}`)
  return Number.isSafeInteger(bp) ? bp : null
}

export function bpToPercentInput(bp: number | null | undefined): string {
  if (typeof bp !== 'number' || !Number.isFinite(bp)) return ''

  const rounded = Math.round(bp)
  const integerPart = Math.floor(rounded / 100)
  const remainder = rounded % 100
  if (remainder === 0) return String(integerPart)

  const fraction = String(remainder).padStart(2, '0').replace(/0+$/, '')
  return `${integerPart}.${fraction}`
}

export function parseQuantityInput(
  input: string | null | undefined,
): number | null {
  if (typeof input !== 'string') return null
  const normalized = input.trim()
  if (!/^\d+(?:\.\d{1,4})?$/.test(normalized)) return null
  const value = Number(normalized)
  return Number.isFinite(value) ? value : null
}

export function sumItemAmountCents(items: InvoiceItemDraft[]): number {
  return items.reduce((total, item) => {
    const cents = parseYuanToCents(item.amount)
    return cents === null ? total : total + cents
  }, 0)
}

function blankToNull(value: string): string | null {
  const trimmed = value.trim()
  return trimmed === '' ? null : trimmed
}

function parsePositiveId(value: string): number | null {
  if (!/^\d+$/.test(value)) return null
  const parsed = Number(value)
  return Number.isSafeInteger(parsed) && parsed > 0 ? parsed : null
}

/**
 * 审核通过前的必填校验，并生成 InvoiceCreate。
 * 金额不一致、明细缺失会阻断提交；明细合计差异只做提示。
 */
export function validateInvoiceDraft(
  draft: InvoiceDraft,
  documentId: number,
): InvoiceDraftValidation {
  const errors: InvoiceDraftErrors = {}

  const invoiceNumber = draft.invoiceNumber.trim()
  if (invoiceNumber === '') errors.invoiceNumber = '请输入发票号码。'

  const sellerName = draft.sellerName.trim()
  if (sellerName === '') errors.sellerName = '请输入销方名称。'

  const issueDate = draft.issueDate.trim()
  if (issueDate === '') {
    errors.issueDate = '请选择开票日期。'
  } else if (formatDate(issueDate) !== issueDate) {
    errors.issueDate = '请输入有效的开票日期（YYYY-MM-DD）。'
  }

  const amountExTax = parseYuanToCents(draft.amountExTax)
  const tax = parseYuanToCents(draft.tax)
  const total = parseYuanToCents(draft.total)

  if (draft.amountExTax.trim() === '') {
    errors.amountExTax = '请输入不含税金额。'
  } else if (amountExTax === null) {
    errors.amountExTax = '金额格式有误，最多两位小数。'
  }

  if (draft.tax.trim() === '') {
    errors.tax = '请输入税额。'
  } else if (tax === null) {
    errors.tax = '金额格式有误，最多两位小数。'
  }

  if (draft.total.trim() === '') {
    errors.total = '请输入价税合计。'
  } else if (total === null) {
    errors.total = '金额格式有误，最多两位小数。'
  }

  let amountMismatch: string | null = null
  if (amountExTax !== null && tax !== null && total !== null) {
    const difference = amountExTax + tax - total
    if (Math.abs(difference) > 1) {
      amountMismatch = `价税合计与「不含税金额 + 税额」相差 ${formatCents(difference)}，请修正后再提交。`
      errors.total = amountMismatch
    }
  }

  let taxRateBp: number | null = null
  if (draft.taxRate.trim() !== '') {
    taxRateBp = parsePercentToBp(draft.taxRate)
    if (taxRateBp === null) {
      errors.taxRate = '税率格式有误，请填写百分比，例如 13 或 13.00。'
    } else if (taxRateBp > 10000) {
      errors.taxRate = '税率不能超过 100%。'
    }
  }

  const categoryId = parsePositiveId(draft.categoryId)
  if (categoryId === null) errors.categoryId = '请选择类别。'

  const requesterId = parsePositiveId(draft.requesterId)
  if (requesterId === null) errors.requesterId = '请选择申购人。'

  const ownerId = parsePositiveId(draft.ownerId)
  if (ownerId === null) errors.ownerId = '请选择负责人。'

  if (draft.invoiceForm !== 'electronic' && draft.invoiceForm !== 'paper') {
    errors.invoiceForm = '请选择发票形式。'
  }

  const parsedItems: InvoiceItemInput[] = []
  if (draft.items.length === 0) {
    errors.items = '至少添加一行发票明细后才能通过审核。'
  }

  draft.items.forEach((item, index) => {
    const prefix = `items.${index}.`
    const name = item.name.trim()
    if (name === '') {
      errors[`${prefix}name`] = '请输入商品名称。'
    }

    const quantity = parseQuantityInput(item.quantity)
    if (quantity === null || quantity <= 0) {
      errors[`${prefix}quantity`] = '数量须大于 0。'
    }

    const unitPriceMillis = parseYuanToMillis(item.unitPrice)
    if (unitPriceMillis === null || unitPriceMillis < 0) {
      errors[`${prefix}unitPrice`] = '单价格式有误。'
    }

    const amountCents = parseYuanToCents(item.amount)
    if (amountCents === null || amountCents < 0) {
      errors[`${prefix}amount`] = '金额格式有误。'
    }

    if (
      name !== '' &&
      quantity !== null &&
      quantity > 0 &&
      unitPriceMillis !== null &&
      unitPriceMillis >= 0 &&
      amountCents !== null &&
      amountCents >= 0
    ) {
      parsedItems.push({
        name,
        quantity,
        unit_price_millis: unitPriceMillis,
        amount_cents: amountCents,
        note: blankToNull(item.note),
        sort_order: index + 1,
      })
    }
  })

  if (
    Object.keys(errors).length > 0 ||
    amountExTax === null ||
    tax === null ||
    total === null ||
    categoryId === null ||
    requesterId === null ||
    ownerId === null
  ) {
    return { errors, payload: null, amountMismatch }
  }

  const payload: InvoiceCreate = {
    invoice_number: invoiceNumber,
    invoice_code: blankToNull(draft.invoiceCode),
    invoice_type: blankToNull(draft.invoiceType),
    issue_date: issueDate,
    seller_name: sellerName,
    seller_tax_id: blankToNull(draft.sellerTaxId),
    buyer_name: blankToNull(draft.buyerName),
    buyer_tax_id: blankToNull(draft.buyerTaxId),
    amount_ex_tax_cents: amountExTax,
    tax_cents: tax,
    total_cents: total,
    tax_rate_bp: taxRateBp,
    category_id: categoryId,
    requester_id: requesterId,
    owner_id: ownerId,
    invoice_form: draft.invoiceForm,
    source_document_id: documentId,
    note: blankToNull(draft.note),
    product_url: blankToNull(draft.productUrl),
    items: parsedItems,
  }

  return { errors, payload, amountMismatch }
}

export function firstErrorElementId(
  errors: InvoiceDraftErrors,
): string | null {
  const key = Object.keys(errors)[0]
  if (!key) return null

  if (key === 'items') return INVOICE_FIELD_IDS.items ?? null

  const itemMatch = /^items\.(\d+)\.(name|quantity|unitPrice|amount)$/.exec(key)
  if (itemMatch) {
    const index = itemMatch[1] ?? ''
    const field = ITEM_FIELD_IDS[itemMatch[2] ?? ''] ?? ''
    return field === '' ? null : `review-item-${index}-${field}`
  }

  return INVOICE_FIELD_IDS[key] ?? null
}

/** field_confidence 的键在 camelCase / snake_case 间不稳定，按别名兜底。 */
export function getFieldConfidence(
  fieldConfidence: Record<string, number> | null | undefined,
  keys: string[],
): number | null {
  if (!fieldConfidence) return null
  for (const key of keys) {
    const value = fieldConfidence[key]
    if (typeof value === 'number' && Number.isFinite(value)) return value
  }
  return null
}

export function itemFieldError(
  errors: InvoiceDraftErrors,
  index: number,
  field: keyof typeof ITEM_FIELD_IDS,
): string {
  return errors[`items.${index}.${field}`] ?? ''
}
