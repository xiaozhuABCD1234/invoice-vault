import { describe, expect, it } from 'vitest'

import { formatDate, formatDateTime } from '../date'

describe('formatDate', () => {
  it('formats date-only strings as YYYY-MM-DD', () => {
    expect(formatDate('2026-07-12')).toBe('2026-07-12')
    expect(formatDate(new Date(2026, 0, 5))).toBe('2026-01-05')
  })

  it('formats ISO timestamps by date', () => {
    expect(formatDate('2026-07-12T08:30:00')).toBe('2026-07-12')
  })

  it('shows an em dash for empty or invalid input', () => {
    expect(formatDate(null)).toBe('—')
    expect(formatDate(undefined)).toBe('—')
    expect(formatDate('')).toBe('—')
    expect(formatDate('not-a-date')).toBe('—')
  })
})

describe('formatDateTime', () => {
  it('formats timestamps as YYYY-MM-DD HH:mm', () => {
    expect(formatDateTime('2026-07-12T08:30:00')).toBe('2026-07-12 08:30')
    expect(formatDateTime(new Date(2026, 6, 12, 18, 5))).toBe('2026-07-12 18:05')
  })

  it('shows an em dash for empty or invalid input', () => {
    expect(formatDateTime(null)).toBe('—')
    expect(formatDateTime('')).toBe('—')
    expect(formatDateTime('2026-13-01T00:00:00')).toBe('—')
  })
})
