import dayjs from 'dayjs'

import { EMPTY_TEXT } from './format'

export type DateInput = string | number | Date | null | undefined

const ISO_DATE_PREFIX = /^(\d{4})-(\d{2})-(\d{2})(?:[T\s].*)?$/

/**
 * dayjs 默认会把 2026-13-01 滚动成 2027-01-01，
 * 这里先校验 ISO 日期前缀，避免展示错误日期。
 */
function hasValidDatePrefix(value: string): boolean {
  const match = ISO_DATE_PREFIX.exec(value.trim())
  if (!match) return true

  const year = Number(match[1])
  const month = Number(match[2])
  const day = Number(match[3])
  const date = new Date(0)
  date.setUTCHours(0, 0, 0, 0)
  date.setUTCFullYear(year, month - 1, day)

  return (
    date.getUTCFullYear() === year &&
    date.getUTCMonth() === month - 1 &&
    date.getUTCDate() === day
  )
}

function parseDate(value: DateInput): dayjs.Dayjs | null {
  if (value === null || value === undefined) return null
  if (typeof value === 'string') {
    const trimmed = value.trim()
    if (trimmed === '' || !hasValidDatePrefix(trimmed)) return null
  }

  const parsed = dayjs(value)
  return parsed.isValid() ? parsed : null
}

/** 日期统一 YYYY-MM-DD；空值 / 非法日期 → —。 */
export function formatDate(value: DateInput): string {
  const parsed = parseDate(value)
  return parsed ? parsed.format('YYYY-MM-DD') : EMPTY_TEXT
}

/** 时间统一 YYYY-MM-DD HH:mm；空值 / 非法日期 → —。 */
export function formatDateTime(value: DateInput): string {
  const parsed = parseDate(value)
  return parsed ? parsed.format('YYYY-MM-DD HH:mm') : EMPTY_TEXT
}
