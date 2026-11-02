export const EMPTY_TEXT = '—'

/** 统一空值展示：null / undefined / 空字符串 / 非有限数字 → —。 */
export function emptyText(value: unknown): string {
  if (value === null || value === undefined) return EMPTY_TEXT
  if (typeof value === 'string') {
    return value.trim() === '' ? EMPTY_TEXT : value
  }
  if (typeof value === 'number' && !Number.isFinite(value)) return EMPTY_TEXT
  return String(value)
}

/** 文件大小：B（整数）、KB / MB 保留 1 位小数。 */
export function fileSize(bytes: number | null | undefined): string {
  if (typeof bytes !== 'number' || !Number.isFinite(bytes) || bytes < 0) {
    return EMPTY_TEXT
  }
  if (bytes < 1024) return `${Math.round(bytes)} B`

  const kb = bytes / 1024
  if (kb < 1024) return `${kb.toFixed(1)} KB`

  return `${(kb / 1024).toFixed(1)} MB`
}

/** 比例（0–1）转百分比，保留 1 位小数。 */
export function percent(ratio: number | null | undefined): string {
  if (typeof ratio !== 'number' || !Number.isFinite(ratio)) return EMPTY_TEXT
  return `${(ratio * 100).toFixed(1)}%`
}
