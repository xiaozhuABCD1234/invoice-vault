import { describe, expect, it } from 'vitest'

import { getStatusDescriptor } from '../status'

describe('getStatusDescriptor', () => {
  it('maps invoice statuses to the fixed Chinese labels and tones', () => {
    expect(getStatusDescriptor('invoice_status', 'review_pending')).toMatchObject({
      label: '待审核',
      tone: 'warning',
    })
    expect(getStatusDescriptor('invoice_status', 'active')).toMatchObject({
      label: '已生效',
      tone: 'success',
    })
    expect(getStatusDescriptor('invoice_status', 'void')).toMatchObject({
      label: '已作废',
      tone: 'neutral',
    })
    expect(getStatusDescriptor('invoice_status', 'duplicate')).toMatchObject({
      label: '重复',
      tone: 'danger',
    })
  })

  it('maps payment and allocation statuses', () => {
    expect(getStatusDescriptor('payment_status', 'unpaid').tone).toBe('warning')
    expect(getStatusDescriptor('payment_status', 'partially_allocated').label).toBe(
      '部分分配',
    )
    expect(getStatusDescriptor('payment_status', 'fully_allocated').label).toBe(
      '已核销',
    )
    expect(getStatusDescriptor('allocation_status', 'reversed').label).toBe(
      '已撤销',
    )
  })

  it('maps job and export statuses', () => {
    expect(getStatusDescriptor('job_status', 'running')).toMatchObject({
      label: '识别中',
      tone: 'info',
      icon: 'spinner',
    })
    expect(getStatusDescriptor('export_status', 'succeeded')).toMatchObject({
      label: '已成功',
      tone: 'success',
    })
    expect(getStatusDescriptor('export_status', 'failed').tone).toBe('danger')
  })

  it('falls back to a neutral descriptor for unknown statuses', () => {
    expect(getStatusDescriptor('invoice_status', 'unknown')).toEqual({
      label: '未知状态',
      tone: 'neutral',
      icon: 'dot',
    })
    expect(getStatusDescriptor('invoice_status', null)).toMatchObject({
      label: '未知状态',
      tone: 'neutral',
    })
  })
})
