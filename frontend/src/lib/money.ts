import { EMPTY_TEXT } from './format'

const CURRENCY_SYMBOL = '¥'

function isFiniteNumber(value: number | null | undefined): value is number {
  return typeof value === 'number' && Number.isFinite(value)
}

function groupThousands(value: number): string {
  return Math.trunc(value)
    .toString()
    .replace(/\B(?=(\d{3})+(?!\d))/g, ',')
}

/**
 * 整数分 → ¥1,234.56 / -¥1,234.56；空值或非有限数字 → —。
 * 金额只允许在展示层格式化，禁止浮点累加。
 */
export function formatCents(cents: number | null | undefined): string {
  if (!isFiniteNumber(cents)) return EMPTY_TEXT

  const rounded = Math.round(cents)
  const negative = rounded < 0
  const absolute = Math.abs(rounded)
  const yuan = Math.floor(absolute / 100)
  const fen = absolute % 100

  return `${negative ? '-' : ''}${CURRENCY_SYMBOL}${groupThousands(yuan)}.${String(fen).padStart(2, '0')}`
}

/**
 * 元字符串 → 整数分，全程使用整数运算，避免 0.1 + 0.2 这类浮点误差。
 * 支持 ¥ / ￥、千分位逗号与首尾空白；非法输入返回 null。
 */
export function parseYuanToCents(input: string | null | undefined): number | null {
  if (typeof input !== 'string') return null

  const normalized = input.trim().replace(/[¥￥,\s]/g, '')
  const match = /^(-?)(\d+)(?:\.(\d{1,2}))?$/.exec(normalized)
  if (!match) return null

  const sign = match[1] === '-' ? -1 : 1
  const integerPart = match[2] ?? ''
  const fractionPart = match[3] ?? ''
  const centsText = `${integerPart}${fractionPart.padEnd(2, '0')}`
  const cents = Number(centsText)

  if (!Number.isSafeInteger(cents)) return null
  const result = sign * cents
  return result === 0 ? 0 : result
}

/** 整数分 → 可编辑的元字符串（无货币符号、无千分位，保留 2 位小数）。 */
export function centsToYuanInput(cents: number | null | undefined): string {
  if (!isFiniteNumber(cents)) return ''

  const rounded = Math.round(cents)
  const negative = rounded < 0
  const absolute = Math.abs(rounded)
  const yuan = Math.floor(absolute / 100)
  const fen = absolute % 100

  return `${negative ? '-' : ''}${yuan}.${String(fen).padStart(2, '0')}`
}
