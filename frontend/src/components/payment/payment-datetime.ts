import dayjs from 'dayjs'

/** 本地时间 → datetime-local 输入值（YYYY-MM-DDTHH:mm）。 */
export function toDateTimeLocal(value: string | null | undefined): string {
  if (!value) return ''
  const parsed = dayjs(value)
  return parsed.isValid() ? parsed.format('YYYY-MM-DDTHH:mm') : ''
}

export function nowDateTimeLocal(): string {
  return dayjs().format('YYYY-MM-DDTHH:mm')
}

/** datetime-local 输入值（本地时区）→ UTC ISO 时间戳。 */
export function toIsoTimestamp(value: string): string | null {
  if (value.trim() === '') return null
  const parsed = dayjs(value)
  return parsed.isValid() ? parsed.toISOString() : null
}
