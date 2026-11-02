export type StatusKind =
  | 'invoice_status'
  | 'payment_status'
  | 'job_status'
  | 'export_status'
  | 'allocation_status'

export type StatusTone = 'neutral' | 'success' | 'warning' | 'danger' | 'info'

export type StatusIcon =
  | 'dot'
  | 'clock'
  | 'spinner'
  | 'check'
  | 'x'
  | 'alert'
  | 'ban'
  | 'copy'
  | 'circle-dashed'

export interface StatusDescriptor {
  label: string
  tone: StatusTone
  icon: StatusIcon
}

type StatusMap = Record<string, StatusDescriptor>

const invoiceStatusMap: StatusMap = {
  review_pending: { label: '待审核', tone: 'warning', icon: 'clock' },
  active: { label: '已生效', tone: 'success', icon: 'check' },
  void: { label: '已作废', tone: 'neutral', icon: 'ban' },
  duplicate: { label: '重复', tone: 'danger', icon: 'copy' },
}

const paymentStatusMap: StatusMap = {
  unpaid: { label: '未付款', tone: 'warning', icon: 'clock' },
  partial: { label: '部分付款', tone: 'info', icon: 'circle-dashed' },
  paid: { label: '已付款', tone: 'success', icon: 'check' },
  unallocated: { label: '未分配', tone: 'warning', icon: 'clock' },
  partially_allocated: { label: '部分分配', tone: 'info', icon: 'circle-dashed' },
  fully_allocated: { label: '已核销', tone: 'success', icon: 'check' },
  void: { label: '已作废', tone: 'neutral', icon: 'ban' },
}

const jobStatusMap: StatusMap = {
  queued: { label: '排队中', tone: 'neutral', icon: 'clock' },
  running: { label: '识别中', tone: 'info', icon: 'spinner' },
  review_pending: { label: '待审核', tone: 'warning', icon: 'clock' },
  approved: { label: '已通过', tone: 'success', icon: 'check' },
  rejected: { label: '已驳回', tone: 'danger', icon: 'x' },
  failed: { label: '失败', tone: 'danger', icon: 'alert' },
}

const exportStatusMap: StatusMap = {
  queued: { label: '排队中', tone: 'neutral', icon: 'clock' },
  running: { label: '导出中', tone: 'info', icon: 'spinner' },
  succeeded: { label: '已成功', tone: 'success', icon: 'check' },
  failed: { label: '失败', tone: 'danger', icon: 'alert' },
}

const allocationStatusMap: StatusMap = {
  active: { label: '已生效', tone: 'success', icon: 'check' },
  reversed: { label: '已撤销', tone: 'neutral', icon: 'ban' },
}

const statusMaps: Record<StatusKind, StatusMap> = {
  invoice_status: invoiceStatusMap,
  payment_status: paymentStatusMap,
  job_status: jobStatusMap,
  export_status: exportStatusMap,
  allocation_status: allocationStatusMap,
}

const UNKNOWN_STATUS: StatusDescriptor = {
  label: '未知状态',
  tone: 'neutral',
  icon: 'dot',
}

/** 业务状态 → 固定中文文案、语义色与图标；未知状态降级为中性。 */
export function getStatusDescriptor(
  kind: StatusKind,
  status: string | null | undefined,
): StatusDescriptor {
  if (!status) return UNKNOWN_STATUS
  return statusMaps[kind][status] ?? UNKNOWN_STATUS
}
