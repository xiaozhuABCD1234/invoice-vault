import type { DataTableSort } from '@/components/common/data-table'

/** 列表页允许的分页大小，与 Pagination 组件保持一致。 */
export const PAGE_SIZES = [20, 50, 100] as const

export function parsePage(raw: string): number | undefined {
  const value = Number(raw)
  return Number.isInteger(value) && value >= 1 ? value : undefined
}

export function parsePageSize(raw: string): number | undefined {
  const value = Number(raw)
  return (PAGE_SIZES as readonly number[]).includes(value)
    ? value
    : undefined
}

export function parsePositiveInt(raw: string): number | undefined {
  const value = Number(raw)
  return Number.isInteger(value) && value >= 1 ? value : undefined
}

export function parseIsoDate(raw: string): string | undefined {
  return /^\d{4}-\d{2}-\d{2}$/.test(raw) ? raw : undefined
}

export function parseEnum<T extends string>(
  values: readonly T[],
  raw: string,
): T | undefined {
  return (values as readonly string[]).includes(raw) ? (raw as T) : undefined
}

export function parseBoolean(raw: string): boolean | undefined {
  if (raw === '1' || raw === 'true') return true
  if (raw === '0' || raw === 'false') return false
  return undefined
}

/** 校验 "field:order" 形式的排序参数，字段必须在允许列表内。 */
export function parseSort(
  raw: string,
  fields: readonly string[],
): string | undefined {
  const [key, order] = raw.split(':')
  if (!key || !fields.includes(key)) return undefined
  if (order !== 'asc' && order !== 'desc') return undefined
  return `${key}:${order}`
}

export function parseSortValue(value: string): DataTableSort | null {
  const [key, order] = value.split(':')
  if (!key) return null
  return { key, order: order === 'asc' ? 'asc' : 'desc' }
}

export function sortValue(sort: DataTableSort): string {
  return `${sort.key}:${sort.order}`
}
