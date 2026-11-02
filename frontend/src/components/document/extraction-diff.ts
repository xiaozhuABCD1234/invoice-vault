import type { JsonObject, JsonValue } from '@/api/types'
import { EMPTY_TEXT } from '@/lib/format'

import { extractionFieldLabel } from './extraction-fields'

export interface DiffEntry {
  key: string
  label: string
  previous: string
  next: string
}

const OLD_KEYS = ['old', 'before', 'from', 'previous']
const NEW_KEYS = ['new', 'after', 'to', 'current']

function isRecord(value: JsonValue | undefined): value is JsonObject {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function pick(record: JsonObject, keys: string[]): JsonValue | undefined {
  for (const key of keys) {
    if (key in record) return record[key]
  }
  return undefined
}

function formatDiffValue(value: JsonValue | undefined): string {
  if (value === undefined || value === null) return EMPTY_TEXT
  if (typeof value === 'string') {
    return value.trim() === '' ? EMPTY_TEXT : value
  }
  if (typeof value === 'number') {
    return Number.isFinite(value) ? String(value) : EMPTY_TEXT
  }
  if (typeof value === 'boolean') return value ? '是' : '否'
  if (Array.isArray(value) || isRecord(value)) {
    return JSON.stringify(value)
  }
  return EMPTY_TEXT
}

/**
 * 契约只约定 diff 为对象，未约定结构。
 * 兼容 { old, new } / { before, after } / { from, to }，其余按「新值」展示。
 */
export function normalizeDiff(diff: JsonObject | null | undefined): DiffEntry[] {
  if (!diff) return []

  if (isRecord(diff.fields) && Object.keys(diff).length === 1) {
    return normalizeDiff(diff.fields)
  }

  const entries: DiffEntry[] = []
  for (const [key, value] of Object.entries(diff)) {
    if (isRecord(value)) {
      const previous = pick(value, OLD_KEYS)
      const next = pick(value, NEW_KEYS)
      if (previous !== undefined || next !== undefined) {
        entries.push({
          key,
          label: extractionFieldLabel(key),
          previous: formatDiffValue(previous),
          next: formatDiffValue(next),
        })
        continue
      }
    }

    if (Array.isArray(value) && value.length === 2) {
      entries.push({
        key,
        label: extractionFieldLabel(key),
        previous: formatDiffValue(value[0]),
        next: formatDiffValue(value[1]),
      })
      continue
    }

    entries.push({
      key,
      label: extractionFieldLabel(key),
      previous: EMPTY_TEXT,
      next: formatDiffValue(value),
    })
  }

  return entries
}
