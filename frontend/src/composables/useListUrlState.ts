import { reactive, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { parseBoolean } from './listQuery'

export type UrlStateValue = string | number | boolean
export type UrlState = Record<string, UrlStateValue>

export interface ListUrlStateOptions<T extends UrlState> {
  defaults: T
  /** 按字段校验 URL 值；返回 undefined 表示回退到默认值。 */
  parsers?: Partial<Record<keyof T, (raw: string) => UrlStateValue | undefined>>
}

export interface ListUrlStateHandle<T extends UrlState> {
  state: T
  reset: (keys?: Array<keyof T>) => void
}

function queryValue(
  query: Record<string, unknown>,
  key: string,
): string | null {
  const raw = query[key]
  const value = Array.isArray(raw) ? raw[0] : raw
  return typeof value === 'string' ? value : null
}

/**
 * 列表筛选 / 分页 / 排序与 URL query 双向同步。
 * 只写入与默认值不同的字段，非法值回退默认值并从 URL 中清理。
 */
export function useListUrlState<T extends UrlState>(
  options: ListUrlStateOptions<T>,
): ListUrlStateHandle<T> {
  const route = useRoute()
  const router = useRouter()
  const defaults = options.defaults
  const state = reactive({ ...defaults }) as T

  function decode(): T {
    const next: Record<string, UrlStateValue> = { ...defaults }
    for (const key of Object.keys(defaults)) {
      const raw = queryValue(route.query, key)
      if (raw === null || raw === '') continue

      const parser = options.parsers?.[key as keyof T]
      if (parser) {
        const parsed = parser(raw)
        if (parsed !== undefined) next[key] = parsed
        continue
      }

      const fallback = defaults[key as keyof T]
      if (typeof fallback === 'number') {
        const numeric = Number(raw)
        if (Number.isFinite(numeric)) next[key] = numeric
      } else if (typeof fallback === 'boolean') {
        const parsed = parseBoolean(raw)
        if (parsed !== undefined) next[key] = parsed
      } else {
        next[key] = raw
      }
    }
    return next as T
  }

  function encode(value: T): Record<string, string> {
    const query: Record<string, string> = {}
    for (const key of Object.keys(defaults)) {
      const current = value[key as keyof T]
      if (current === defaults[key as keyof T] || current === '') continue
      query[key] = String(current)
    }
    return query
  }

  function sameQuery(next: Record<string, string>): boolean {
    const currentKeys: string[] = []
    for (const [key, raw] of Object.entries(route.query)) {
      const value = Array.isArray(raw) ? raw[0] : raw
      if (typeof value === 'string' && value !== '') currentKeys.push(key)
    }
    if (currentKeys.length !== Object.keys(next).length) return false
    return currentKeys.every((key) => queryValue(route.query, key) === next[key])
  }

  function apply(next: T): void {
    Object.assign(state, next)
  }

  apply(decode())

  watch(
    () => route.query,
    () => {
      apply(decode())
    },
    { deep: true },
  )

  watch(
    state,
    () => {
      const query = encode(state)
      if (!sameQuery(query)) {
        void router.replace({ query, hash: route.hash })
      }
    },
    { deep: true },
  )

  function reset(keys?: Array<keyof T>): void {
    const target = keys ?? (Object.keys(defaults) as Array<keyof T>)
    const patch: Record<string, UrlStateValue> = {}
    for (const key of target) patch[String(key)] = defaults[key]
    Object.assign(state, patch)
  }

  return { state, reset }
}
