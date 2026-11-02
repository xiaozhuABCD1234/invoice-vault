import type { Invoice, InvoiceItem, InvoiceItemInput } from '@/api/types'
import { centsToYuanInput, parseYuanToCents } from '@/lib/money'
import { millisToYuanInput, parseYuanToMillis } from './invoice-format'

export interface InvoiceItemDraft {
  name: string
  quantity: string
  unitPrice: string
  amount: string
  note: string
}

export interface InvoiceFormDraft {
  invoice_number: string
  issue_date: string
  seller_name: string
  buyer_name: string
  category_id: string
  requester_id: string
  owner_id: string
  invoice_form: string
  status: string
  amount_ex_tax: string
  tax: string
  total: string
  note: string
  product_url: string
  items: InvoiceItemDraft[]
}

export function emptyItemDraft(item?: InvoiceItem): InvoiceItemDraft {
  if (!item) {
    return { name: '', quantity: '1', unitPrice: '', amount: '', note: '' }
  }
  return {
    name: item.name,
    quantity: String(item.quantity),
    unitPrice: millisToYuanInput(item.unit_price_millis),
    amount: centsToYuanInput(item.amount_cents),
    note: item.note ?? '',
  }
}

export function invoiceToDraft(invoice: Invoice): InvoiceFormDraft {
  return {
    invoice_number: invoice.invoice_number,
    issue_date: invoice.issue_date,
    seller_name: invoice.seller_name,
    buyer_name: invoice.buyer_name ?? '',
    category_id: String(invoice.category_id),
    requester_id: invoice.requester_id === null ? '' : String(invoice.requester_id),
    owner_id: invoice.owner_id === null ? '' : String(invoice.owner_id),
    invoice_form: invoice.invoice_form,
    status: invoice.status,
    amount_ex_tax: centsToYuanInput(invoice.amount_ex_tax_cents),
    tax: centsToYuanInput(invoice.tax_cents),
    total: centsToYuanInput(invoice.total_cents),
    note: invoice.note ?? '',
    product_url: invoice.product_url ?? '',
    items: invoice.items.map((item) => emptyItemDraft(item)),
  }
}

function isBlankItem(item: InvoiceItemDraft): boolean {
  return (
    item.name.trim() === '' &&
    item.quantity.trim() === '' &&
    item.unitPrice.trim() === '' &&
    item.amount.trim() === '' &&
    item.note.trim() === ''
  )
}

/**
 * 明细草稿 → 提交结构；非空行缺字段或数字非法时返回 null。
 * 金额与单价都做整数换算，避免浮点误差。
 */
export function parseItemDrafts(
  drafts: InvoiceItemDraft[],
): InvoiceItemInput[] | null {
  const items: InvoiceItemInput[] = []
  for (const draft of drafts) {
    if (isBlankItem(draft)) continue
    if (draft.name.trim() === '') return null

    const quantity = Number(draft.quantity)
    const unitPriceMillis = parseYuanToMillis(draft.unitPrice)
    const amountCents = parseYuanToCents(draft.amount)
    if (!Number.isFinite(quantity) || quantity < 0) return null
    if (unitPriceMillis === null || unitPriceMillis < 0) return null
    if (amountCents === null || amountCents < 0) return null

    items.push({
      name: draft.name.trim(),
      quantity,
      unit_price_millis: unitPriceMillis,
      amount_cents: amountCents,
      note: draft.note.trim() || null,
      sort_order: items.length + 1,
    })
  }
  return items
}
