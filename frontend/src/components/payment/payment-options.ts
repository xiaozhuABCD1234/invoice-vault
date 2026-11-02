import type { PaymentMethod } from '@/api/types'
import { getStatusDescriptor } from '@/lib/status'
import { EMPTY_TEXT } from '@/lib/format'

export interface Option {
  value: string
  label: string
}

const METHOD_LABELS: Record<PaymentMethod, string> = {
  personal_advance: '个人垫付',
  teacher_advance: '老师代付',
  bank_transfer: '银行转账',
  alipay: '支付宝',
  wechat: '微信',
  card: '银行卡',
  cash: '现金',
  other: '其他',
}

export const PAYMENT_METHOD_VALUES = Object.keys(METHOD_LABELS) as PaymentMethod[]

export const PAYMENT_METHOD_OPTIONS: Option[] = PAYMENT_METHOD_VALUES.map(
  (value) => ({ value, label: METHOD_LABELS[value] }),
)

export const PAYMENT_STATUS_VALUES = [
  'unallocated',
  'partially_allocated',
  'fully_allocated',
  'void',
] as const

export const PAYMENT_STATUS_OPTIONS: Option[] = PAYMENT_STATUS_VALUES.map(
  (value) => ({
    value,
    label: getStatusDescriptor('payment_status', value).label,
  }),
)

export function paymentMethodLabel(
  method: PaymentMethod | null | undefined,
): string {
  if (!method) return EMPTY_TEXT
  return METHOD_LABELS[method] ?? EMPTY_TEXT
}
