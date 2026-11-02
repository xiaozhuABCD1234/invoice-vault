import { describe, expect, it } from 'vitest'

import { normalizeDiff } from '../extraction-diff'

describe('normalizeDiff', () => {
  it('returns empty entries for null or empty diff', () => {
    expect(normalizeDiff(null)).toEqual([])
    expect(normalizeDiff({})).toEqual([])
  })

  it('supports old/new, before/after and from/to shapes', () => {
    expect(
      normalizeDiff({
        seller_name: { old: 'A 公司', new: 'B 公司' },
        total_cents: { before: 100, after: 200 },
        issue_date: { from: '2026-01-01', to: '2026-01-02' },
      }),
    ).toEqual([
      {
        key: 'seller_name',
        label: '销方名称',
        previous: 'A 公司',
        next: 'B 公司',
      },
      {
        key: 'total_cents',
        label: '价税合计',
        previous: '100',
        next: '200',
      },
      {
        key: 'issue_date',
        label: '开票日期',
        previous: '2026-01-01',
        next: '2026-01-02',
      },
    ])
  })

  it('supports [old, new] tuples and scalar values', () => {
    expect(
      normalizeDiff({
        total_cents: [100, 200],
        note: '新备注',
      }),
    ).toEqual([
      {
        key: 'total_cents',
        label: '价税合计',
        previous: '100',
        next: '200',
      },
      {
        key: 'note',
        label: '备注',
        previous: '—',
        next: '新备注',
      },
    ])
  })

  it('unwraps a fields wrapper', () => {
    expect(
      normalizeDiff({
        fields: {
          invoice_number: { old: '1', new: '2' },
        },
      }),
    ).toEqual([
      {
        key: 'invoice_number',
        label: '发票号码',
        previous: '1',
        next: '2',
      },
    ])
  })
})
