import { describe, expect, it } from 'vitest'

import { centsToYuanInput, formatCents, parseYuanToCents } from '../money'

describe('formatCents', () => {
  it('formats integer cents with currency, thousands separators and two decimals', () => {
    expect(formatCents(0)).toBe('¥0.00')
    expect(formatCents(5)).toBe('¥0.05')
    expect(formatCents(123456)).toBe('¥1,234.56')
    expect(formatCents(100000000)).toBe('¥1,000,000.00')
  })

  it('formats negative amounts with the minus sign before the currency symbol', () => {
    expect(formatCents(-123456)).toBe('-¥1,234.56')
    expect(formatCents(-1)).toBe('-¥0.01')
  })

  it('shows an em dash for empty or invalid values', () => {
    expect(formatCents(null)).toBe('—')
    expect(formatCents(undefined)).toBe('—')
    expect(formatCents(Number.NaN)).toBe('—')
    expect(formatCents(Number.POSITIVE_INFINITY)).toBe('—')
  })
})

describe('parseYuanToCents', () => {
  it('parses yuan strings into integer cents without floating point drift', () => {
    expect(parseYuanToCents('1234.56')).toBe(123456)
    expect(parseYuanToCents('0.10')).toBe(10)
    expect(parseYuanToCents('0.07')).toBe(7)
    expect(parseYuanToCents('19.99')).toBe(1999)
  })

  it('accepts currency symbols, thousands separators, whitespace and negatives', () => {
    expect(parseYuanToCents(' ¥1,234.56 ')).toBe(123456)
    expect(parseYuanToCents('-0.01')).toBe(-1)
    expect(parseYuanToCents('-1,000')).toBe(-100000)
  })

  it('returns null for empty or malformed input', () => {
    expect(parseYuanToCents('')).toBeNull()
    expect(parseYuanToCents(null)).toBeNull()
    expect(parseYuanToCents(undefined)).toBeNull()
    expect(parseYuanToCents('abc')).toBeNull()
    expect(parseYuanToCents('12.345')).toBeNull()
    expect(parseYuanToCents('1,2,3')).toBe(12300)
    expect(parseYuanToCents('12元')).toBeNull()
  })
})

describe('centsToYuanInput', () => {
  it('returns an editable value without separators or symbol', () => {
    expect(centsToYuanInput(123456)).toBe('1234.56')
    expect(centsToYuanInput(-1)).toBe('-0.01')
    expect(centsToYuanInput(null)).toBe('')
  })
})
