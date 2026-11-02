import { describe, expect, it } from 'vitest'

import { emptyText, fileSize, percent } from '../format'

describe('fileSize', () => {
  it('formats bytes, KB and MB with one decimal', () => {
    expect(fileSize(0)).toBe('0 B')
    expect(fileSize(512)).toBe('512 B')
    expect(fileSize(1536)).toBe('1.5 KB')
    expect(fileSize(1048576)).toBe('1.0 MB')
  })

  it('handles invalid input', () => {
    expect(fileSize(null)).toBe('—')
    expect(fileSize(-1)).toBe('—')
  })
})

describe('percent', () => {
  it('formats a 0-1 ratio with one decimal', () => {
    expect(percent(0.1234)).toBe('12.3%')
    expect(percent(1)).toBe('100.0%')
    expect(percent(null)).toBe('—')
  })
})

describe('emptyText', () => {
  it('uses an em dash only for empty values', () => {
    expect(emptyText(null)).toBe('—')
    expect(emptyText('  ')).toBe('—')
    expect(emptyText(0)).toBe('0')
    expect(emptyText('发票')).toBe('发票')
  })
})
