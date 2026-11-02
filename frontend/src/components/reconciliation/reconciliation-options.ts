import type { ReconciliationIssueType } from '@/api/types'
import { UNSET_SELECT_VALUE } from '@/composables/selectValue'
import { EMPTY_TEXT } from '@/lib/format'

export const ISSUE_TYPE_LABELS: Record<ReconciliationIssueType, string> = {
  invoice_unpaid: '未付款发票',
  invoice_partial: '部分付款发票',
  payment_unallocated: '未分配付款',
  payment_partial: '部分分配付款',
  missing_evidence: '缺少凭证',
  duplicate_invoice: '重复发票',
  item_mismatch: '明细金额不一致',
  amount_anomaly: '金额异常',
  date_anomaly: '日期异常',
}

export const ISSUE_TYPE_VALUES = Object.keys(
  ISSUE_TYPE_LABELS,
) as ReconciliationIssueType[]

export const ISSUE_TYPE_OPTIONS = [
  { value: UNSET_SELECT_VALUE, label: '全部类型' },
  ...ISSUE_TYPE_VALUES.map((value) => ({
    value,
    label: ISSUE_TYPE_LABELS[value],
  })),
]

export function issueTypeLabel(type: string | null | undefined): string {
  if (!type) return EMPTY_TEXT
  return ISSUE_TYPE_LABELS[type as ReconciliationIssueType] ?? EMPTY_TEXT
}
