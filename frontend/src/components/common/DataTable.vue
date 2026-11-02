<script setup lang="ts" generic="T extends object">
import { computed, type Component } from 'vue'
import {
  ArrowUpDown,
  ChevronDown,
  ChevronUp,
} from '@lucide/vue'

import EmptyState from './EmptyState.vue'
import ErrorState from './ErrorState.vue'
import TableSkeleton from './TableSkeleton.vue'
import type {
  DataTableAlign,
  DataTableColumn,
  DataTableSort,
} from './data-table'
import { cn } from '@/lib/cn'
import { EMPTY_TEXT } from '@/lib/format'

const props = withDefaults(
  defineProps<{
    rows: T[]
    columns: DataTableColumn[]
    rowKey: keyof T | ((row: T) => string | number)
    loading?: boolean
    error?: string | null
    sort?: DataTableSort | null
    empty?: string
    emptyDescription?: string
    selectedKey?: string | number | null
  }>(),
  {
    loading: false,
    error: null,
    sort: null,
    empty: '暂无数据',
    emptyDescription: '',
    selectedKey: null,
  },
)

const emit = defineEmits<{
  (event: 'update:sort', value: DataTableSort): void
  (event: 'retry'): void
}>()

const alignClasses: Record<DataTableAlign, string> = {
  left: 'text-left',
  center: 'text-center',
  right: 'text-right',
}

function cellValue(row: T, key: string): unknown {
  return (row as unknown as Record<string, unknown>)[key]
}

function formatCell(value: unknown): string {
  if (value === null || value === undefined || value === '') return EMPTY_TEXT
  if (typeof value === 'string' || typeof value === 'number') {
    return String(value)
  }
  return ''
}

function resolveRowKey(row: T): string | number {
  if (typeof props.rowKey === 'function') return props.rowKey(row)
  const value = cellValue(row, String(props.rowKey))
  if (typeof value === 'string' || typeof value === 'number') return value
  return String(value)
}

function isSelected(row: T): boolean {
  if (props.selectedKey === null || props.selectedKey === undefined) {
    return false
  }
  return String(resolveRowKey(row)) === String(props.selectedKey)
}

function headerFixedClass(column: DataTableColumn): string {
  if (column.fixed === 'left') return 'sticky left-0 z-20 bg-surface-muted'
  if (column.fixed === 'right') return 'sticky right-0 z-20 bg-surface-muted'
  return ''
}

function cellFixedClass(column: DataTableColumn): string {
  if (column.fixed === 'left') return 'sticky left-0 z-10 bg-inherit'
  if (column.fixed === 'right') return 'sticky right-0 z-10 bg-inherit'
  return ''
}

function ariaSort(
  column: DataTableColumn,
): 'ascending' | 'descending' | 'none' | undefined {
  if (!column.sortable) return undefined
  if (props.sort?.key !== column.key) return 'none'
  return props.sort.order === 'asc' ? 'ascending' : 'descending'
}

function isSorted(column: DataTableColumn): boolean {
  return props.sort?.key === column.key
}

function sortIcon(column: DataTableColumn): Component {
  if (props.sort?.key !== column.key) return ArrowUpDown
  return props.sort.order === 'asc' ? ChevronUp : ChevronDown
}

function toggleSort(column: DataTableColumn): void {
  if (!column.sortable) return
  const next: DataTableSort =
    props.sort?.key === column.key && props.sort.order === 'asc'
      ? { key: column.key, order: 'desc' }
      : { key: column.key, order: 'asc' }
  emit('update:sort', next)
}

const columnCount = computed(() => props.columns.length)
</script>

<template>
  <TableSkeleton
    v-if="loading"
    :rows="6"
    :columns="columnCount"
  />

  <div
    v-else-if="error"
    class="rounded-card border border-border bg-surface"
  >
    <ErrorState
      title="数据加载失败"
      :message="error"
      @retry="emit('retry')"
    />
  </div>

  <div
    v-else-if="rows.length === 0"
    class="rounded-card border border-border bg-surface"
  >
    <EmptyState :title="empty" :description="emptyDescription">
      <template v-if="$slots['empty-action']" #action>
        <slot name="empty-action" />
      </template>
    </EmptyState>
  </div>

  <div
    v-else
    class="w-full overflow-x-auto rounded-card border border-border bg-surface"
  >
    <table class="w-full border-collapse text-table text-text">
      <thead>
        <tr>
          <th
            v-for="column in columns"
            :key="column.key"
            scope="col"
            :aria-sort="ariaSort(column)"
            :style="column.width ? { width: `${column.width}px` } : undefined"
            :class="
              cn(
                'sticky top-0 z-10 h-10 whitespace-nowrap border-b border-border bg-surface-muted px-4 font-medium text-text-secondary',
                alignClasses[column.align ?? 'left'],
                headerFixedClass(column),
              )
            "
          >
            <button
              v-if="column.sortable"
              type="button"
              class="inline-flex min-h-8 items-center gap-1 rounded-tag hover:text-text"
              :aria-label="`按${column.label}排序`"
              @click="toggleSort(column)"
            >
              {{ column.label }}
              <component
                :is="sortIcon(column)"
                :size="16"
                :stroke-width="1.75"
                :class="isSorted(column) ? 'text-text' : 'text-text-muted'"
                aria-hidden="true"
              />
            </button>
            <template v-else>{{ column.label }}</template>
          </th>
        </tr>
      </thead>

      <tbody>
        <tr
          v-for="row in rows"
          :key="resolveRowKey(row)"
          :class="
            cn(
              'border-b border-border bg-surface transition-colors duration-150 last:border-b-0',
              isSelected(row)
                ? 'bg-primary-soft hover:bg-primary-soft'
                : 'hover:bg-surface-muted',
            )
          "
        >
          <td
            v-for="column in columns"
            :key="column.key"
            :class="
              cn(
                'px-4 py-3 align-middle',
                alignClasses[column.align ?? 'left'],
                column.nowrap && 'whitespace-nowrap',
                cellFixedClass(column),
              )
            "
          >
            <slot
              :name="`cell-${column.key}`"
              :row="row"
              :value="cellValue(row, column.key)"
              :column="column"
            >
              <slot
                name="cell"
                :row="row"
                :value="cellValue(row, column.key)"
                :column="column"
              >
                {{ formatCell(cellValue(row, column.key)) }}
              </slot>
            </slot>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
