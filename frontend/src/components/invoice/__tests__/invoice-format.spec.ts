import { describe, expect, it } from 'vitest'

import {
  formatTaxRateBp,
  formatUnitPrice,
  millisToYuanInput,
  parseYuanToMillis,
} from '../invoice-format'

describe('formatUnitPrice', () => {
  it('formats thousandths as yuan with grouping', () => {
    expect(formatUnitPrice(1000)).toBe('¥1.00')
    expect(formatUnitPrice(1234567)).toBe('¥1,234.567')
  })

  it('drops trailing precision only when possible', () => {
    expect(formatUnitPrice(1050)).toBe('¥1.05')
    expect(formatUnitPrice(1005)).toBe('¥1.005')
  })

  it('handles negative and empty values', () => {
    expect(formatUnitPrice(-1500)).toBe('-¥1.50')
    expect(formatUnitPrice(null)).toBe('—')
    expect(formatUnitPrice(Number.NaN)).toBe('—')
  })
})

describe('parseYuanToMillis', () => {
  it('accepts currency symbol, commas and up to 3 decimals', () => {
    expect(parseYuanToMillis('¥1,234.567')).toBe(1234567)
    expect(parseYuanToMillis('1.5')).toBe(1500)
    expect(parseYuanToMillis('0')).toBe(0)
  })

  it('rejects invalid input', () => {
    expect(parseYuanToMillis('1.2345')).toBeNull()
    expect(parseYuanToMillis('abc')).toBeNull()
    expect(parseYuanToMillis('')).toBeNull()
    expect(parseYuanToMillis(null)).toBeNull()
  })
})

describe('millisToYuanInput', () => {
  it('renders editable yuan strings', () => {
    expect(millisToYuanInput(1500)).toBe('1.5')
    expect(millisToYuanInput(1005)).toBe('1.005')
    expect(millisToYuanInput(2000)).toBe('2')
  })

  it('handles empty values', () => {
    expect(millisToYuanInput(null)).toBe('')
    expect(millisToYuanInput(Number.NaN)).toBe('')
  })
})

describe('formatTaxRateBp', () => {
  it('converts basis points to percent', () => {
    expect(formatTaxRateBp(1300)).toBe('13%')
    expect(formatTaxRateBp(650)).toBe('6.5%')
  })

  it('handles empty values', () => {
    expect(formatTaxRateBp(null)).toBe('—')
  })
})
