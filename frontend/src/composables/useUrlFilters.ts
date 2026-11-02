import { reactive, watch } from 'vue'
import {
  useRoute,
  useRouter,
  type LocationQuery,
  type LocationQueryValue,
} from 'vue-router'

export type UrlFilterValue = string | number

export function queryString(
  value: LocationQueryValue | LocationQueryValue[] | undefined,
): string {
  if (Array.isArray(value)) {
    const first = value.find((item) => item !== null && item !== '')
    return first ?? ''
  }
  return value ?? ''
}

export function queryPositiveInt(
  value: LocationQueryValue | LocationQueryValue[] | undefined,
  fallback: number,
): number {
  const parsed = Number(queryString(value))
  return Number.isSafeInteger(parsed) && parsed > 0 ? parsed : fallback
}

function canonical(values: Record<string, unknown>): string {
  const entries: Array<[string, string]> = []

  for (const [key, value] of Object.entries(values)) {
    if (value === undefined || value === null || value === '') continue
    if (Array.isArray(value)) {
      for (const item of value) {
        if (item !== null && item !== '') entries.push([key, String(item)])
      }
      continue
    }
    entries.push([key, String(value)])
  }

  return entries
    .sort(([left], [right]) => left.localeCompare(right))
    .map(([key, value]) => `${key}=${value}`)
    .join('&')
}

/**
 * 列表筛选条件与 URL query 双向同步。
 * onChange 只在 URL 条件真正变化时触发；页面首次进入需自行 load。
 */
export function useUrlFilters<T extends object>(
  parse: (query: LocationQuery) => T,
  serialize: (state: T) => Record<string, string>,
  onChange: () => void,
): { filters: T; commit: () => void } {
  const route = useRoute()
  const router = useRouter()

  const filters = reactive(parse(route.query)) as unknown as T
  let lastKey = canonical(route.query)

  function commit(): void {
    const next = serialize(filters)
    const nextKey = canonical(next)
    if (nextKey === canonical(route.query)) {
      lastKey = nextKey
      return
    }

    lastKey = nextKey
    void router.replace({ query: next })
    onChange()
  }

  watch(
    () => route.query,
    () => {
      const routeKey = canonical(route.query)
      if (routeKey === lastKey) return

      Object.assign(filters, parse(route.query))
      lastKey = routeKey
      onChange()
    },
  )

  return { filters, commit }
}
