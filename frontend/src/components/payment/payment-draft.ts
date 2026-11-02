import type { Payment } from '@/api/types'
import { centsToYuanInput } from '@/lib/money'
import { nowDateTimeLocal, toDateTimeLocal } from './payment-datetime'

export interface PaymentFormDraft {
  amount: string
  paidAt: string
  method: string
  txnRef: string
  note: string
  requestedAt: string
}

export function emptyPaymentDraft(): PaymentFormDraft {
  return {
    amount: '',
    paidAt: nowDateTimeLocal(),
    method: '',
    txnRef: '',
    note: '',
    requestedAt: '',
  }
}

export function paymentToDraft(payment: Payment): PaymentFormDraft {
  return {
    amount: centsToYuanInput(payment.amount_cents),
    paidAt: toDateTimeLocal(payment.paid_at),
    method: payment.method,
    txnRef: payment.external_txn_ref ?? '',
    note: payment.note ?? '',
    requestedAt: toDateTimeLocal(payment.requested_at),
  }
}
