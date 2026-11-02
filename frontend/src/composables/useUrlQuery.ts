import { useRoute, useRouter } from 'vue-router'

export const PAGE_SIZE_OPTIONS = [20, 50, 100] as const

export function normalizePageSize(value: number): number {
  return PAGE_SIZE_OPTIONS.includes(
    value as (typeof PAGE_SIZE_OPTIONS)[number],
  )
    ? value
    : PAGE_SIZE_OPTIONS[0]
}

type QueryPatch = Record<
  string,
  string | number | boolean | null | undefined
>

/**
 * 列表筛选 / 分页与 URL query 双向同步的轻量封装。
 * 读取只在进入页面时使用；写入统一走 replace，避免筛选产生大量历史记录。
 */
export function useUrlQuery() {
  const route = useRoute()
  const router = useRouter()

  function firstValue(value: unknown): string | null {
    if (Array.isArray(value)) {
      return firstValue(value[0])
    }
    return typeof value === 'string' ? value : null
  }

  function readString(key: string, fallback = ''): string {
    return firstValue(route.query[key]) ?? fallback
  }

  function readInt(
    key: string,
    fallback: number,
    min = Number.MIN_SAFE_INTEGER,
    max = Number.MAX_SAFE_INTEGER,
  ): number {
    const raw = firstValue(route.query[key])
    if (raw === null || raw.trim() === '') return fallback

    const parsed = Number(raw)
    if (!Number.isInteger(parsed)) return fallback
    return Math.min(Math.max(parsed, min), max)
  }

  function snapshot(): Record<string, string> {
    const result: Record<string, string> = {}
    for (const [key, value] of Object.entries(route.query)) {
      const first = firstValue(value)
      if (first !== null && first !== '') result[key] = first
    }
    return result
  }

  function update(patch: QueryPatch): void {
    const next = snapshot()
    for (const [key, value] of Object.entries(patch)) {
      if (value === null || value === undefined || value === '') {
        delete next[key]
      } else {
        next[key] = String(value)
      }
    }

    if (JSON.stringify(next) === JSON.stringify(snapshot())) return

    void router
      .replace({ query: next, hash: route.hash })
      .catch(() => undefined)
  }

  return { readString, readInt, update }
}
