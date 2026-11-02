import type { InvoiceForm, InvoicePaymentStatus, InvoiceStatus } from '@/api/types'
import { getStatusDescriptor } from '@/lib/status'
import { EMPTY_TEXT } from '@/lib/format'

export interface Option {
  value: string
  label: string
}

export const INVOICE_STATUS_VALUES: InvoiceStatus[] = [
  'review_pending',
  'active',
  'void',
  'duplicate',
]

export const INVOICE_STATUS_OPTIONS: Option[] = INVOICE_STATUS_VALUES.map(
  (value) => ({
    value,
    label: getStatusDescriptor('invoice_status', value).label,
  }),
)

export const INVOICE_PAYMENT_STATUS_VALUES: InvoicePaymentStatus[] = [
  'unpaid',
  'partial',
  'paid',
]

export const INVOICE_PAYMENT_STATUS_OPTIONS: Option[] =
  INVOICE_PAYMENT_STATUS_VALUES.map((value) => ({
    value,
    label: getStatusDescriptor('payment_status', value).label,
  }))

export const INVOICE_FORM_OPTIONS: Option[] = [
  { value: 'electronic', label: '电子发票' },
  { value: 'paper', label: '纸质发票' },
]

export function invoiceFormLabel(form: InvoiceForm | null | undefined): string {
  if (!form) return EMPTY_TEXT
  return (
    INVOICE_FORM_OPTIONS.find((option) => option.value === form)?.label ??
    EMPTY_TEXT
  )
}
