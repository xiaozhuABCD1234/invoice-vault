import { describe, expect, it } from 'vitest'

import {
  buildCategoryOption,
  buildPayerOption,
  estimateBarChartHeight,
} from '../dashboard-charts'

interface AxisLike {
  data?: unknown
  axisLabel?: Record<string, unknown>
}

function yAxis(option: unknown): AxisLike {
  const value = (option as { yAxis: AxisLike }).yAxis
  return value
}

describe('dashboard bar charts', () => {
  it('shows full payer names without auto-hiding labels', () => {
    const longName = '这是一个非常长的付款人名称'
    const option = buildPayerOption([
      { payer_name: longName, payment_count: 1, total_cents: 100 },
      { payer_name: '老师', payment_count: 2, total_cents: 200 },
    ])
    const axis = yAxis(option)

    expect(axis.data).toEqual(['老师', longName])
    expect(axis.axisLabel?.interval).toBe(0)
    expect(axis.axisLabel?.formatter).toBeUndefined()
  })

  it('shows full category names without truncation', () => {
    const longName = '办公用品及耗材采购与日常维护'
    const option = buildCategoryOption([
      { category_id: 1, name: longName, invoice_count: 1, total_cents: 100 },
    ])
    const axis = yAxis(option)

    expect(axis.data).toEqual([longName])
    expect(axis.axisLabel?.interval).toBe(0)
    expect(axis.axisLabel?.formatter).toBeUndefined()
  })

  it('grows the chart with the number of rows instead of hiding labels', () => {
    expect(estimateBarChartHeight(['老师'], 288)).toBe(288)
    const many = estimateBarChartHeight(
      Array.from({ length: 20 }, () => '老师'),
      288,
    )
    const few = estimateBarChartHeight(
      Array.from({ length: 10 }, () => '老师'),
      288,
    )
    expect(many).toBeGreaterThan(few)
  })
})
