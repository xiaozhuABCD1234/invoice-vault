import { describe, expect, it } from 'vitest'

import {
  parseBoolean,
  parseEnum,
  parseIsoDate,
  parsePage,
  parsePageSize,
  parsePositiveInt,
  parseSort,
  parseSortValue,
  sortValue,
} from '../listQuery'

describe('list query parsers', () => {
  it('parses pagination safely', () => {
    expect(parsePage('3')).toBe(3)
    expect(parsePage('0')).toBeUndefined()
    expect(parsePage('abc')).toBeUndefined()
    expect(parsePageSize('50')).toBe(50)
    expect(parsePageSize('30')).toBeUndefined()
  })

  it('parses ids, dates and enums', () => {
    expect(parsePositiveInt('12')).toBe(12)
    expect(parsePositiveInt('1.5')).toBeUndefined()
    expect(parseIsoDate('2026-11-03')).toBe('2026-11-03')
    expect(parseIsoDate('2026-13-03')).toBe('2026-13-03')
    expect(parseIsoDate('20261103')).toBeUndefined()
    expect(parseEnum(['a', 'b'] as const, 'b')).toBe('b')
    expect(parseEnum(['a', 'b'] as const, 'c')).toBeUndefined()
    expect(parseBoolean('true')).toBe(true)
    expect(parseBoolean('0')).toBe(false)
    expect(parseBoolean('yes')).toBeUndefined()
  })

  it('validates sort fields and order', () => {
    expect(parseSort('issue_date:desc', ['issue_date'])).toBe('issue_date:desc')
    expect(parseSort('issue_date:sideways', ['issue_date'])).toBeUndefined()
    expect(parseSort('unknown:asc', ['issue_date'])).toBeUndefined()
  })

  it('round-trips DataTableSort', () => {
    expect(parseSortValue('total_cents:asc')).toEqual({
      key: 'total_cents',
      order: 'asc',
    })
    expect(parseSortValue('total_cents:other')).toEqual({
      key: 'total_cents',
      order: 'desc',
    })
    expect(sortValue({ key: 'paid_at', order: 'desc' })).toBe('paid_at:desc')
  })
})
