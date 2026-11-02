<script setup lang="ts">
import { computed } from 'vue'
import { ArrowDown, ArrowUp, X } from '@lucide/vue'

import type { ReportColumn } from '@/api/types'
import Button from '@/components/ui/Button.vue'
import Input from '@/components/ui/Input.vue'
import {
  REPORT_FIELD_CATALOG,
  createReportColumn,
  formatReportFormat,
  type ReportFieldDefinition,
  type ReportFieldGroup,
} from './report-fields'

const props = defineProps<{
  error?: string
}>()

const columns = defineModel<ReportColumn[]>({ required: true })

const selectedKeys = computed(
  () => new Set(columns.value.map((column) => column.key)),
)

const groups = computed(() => {
  const result: Array<{
    group: ReportFieldGroup
    fields: ReportFieldDefinition[]
  }> = []

  for (const field of REPORT_FIELD_CATALOG) {
    const existing = result.find((item) => item.group === field.group)
    if (existing) {
      existing.fields.push(field)
    } else {
      result.push({ group: field.group, fields: [field] })
    }
  }

  return result
})

function toggleField(field: ReportFieldDefinition): void {
  if (selectedKeys.value.has(field.key)) {
    columns.value = columns.value.filter(
      (column) => column.key !== field.key,
    )
    return
  }

  const column = createReportColumn(field.key)
  if (column) columns.value = [...columns.value, column]
}

function moveColumn(index: number, delta: number): void {
  const target = index + delta
  if (target < 0 || target >= columns.value.length) return

  const next = [...columns.value]
  const [item] = next.splice(index, 1)
  if (!item) return
  next.splice(target, 0, item)
  columns.value = next
}

function removeColumn(index: number): void {
  columns.value.splice(index, 1)
}
</script>

<template>
  <section>
    <div class="flex flex-wrap items-center justify-between gap-2">
      <h3 class="text-heading font-semibold text-text">列选择与排序</h3>
      <p class="text-meta text-text-muted">
        已选
        <span class="tabular-nums text-text">{{ columns.length }}</span>
        列
      </p>
    </div>
    <p v-if="props.error" class="mt-1 text-meta text-danger" aria-live="polite">
      {{ props.error }}
    </p>

    <div class="mt-3 grid gap-4 lg:grid-cols-2">
      <div class="min-w-0 rounded-control border border-border">
        <div
          class="border-b border-border bg-surface-muted px-3 py-2 text-meta font-medium text-text-secondary"
        >
          可选字段
        </div>
        <div class="max-h-96 overflow-y-auto p-2">
          <div
            v-for="group in groups"
            :key="group.group"
            class="mb-3 last:mb-0"
          >
            <p class="px-1 pb-1 text-meta font-medium text-text-muted">
              {{ group.group }}
            </p>
            <label
              v-for="field in group.fields"
              :key="field.key"
              :for="`field-${field.key}`"
              class="flex min-h-11 cursor-pointer items-center gap-2 rounded-tag px-1 py-1.5 text-body text-text hover:bg-surface-muted"
            >
              <input
                :id="`field-${field.key}`"
                type="checkbox"
                class="size-4 shrink-0 accent-primary"
                :checked="selectedKeys.has(field.key)"
                @change="toggleField(field)"
              />
              <span class="min-w-0 flex-1 truncate">{{ field.label }}</span>
              <span class="text-meta text-text-muted">
                {{ formatReportFormat(field.format) }}
              </span>
            </label>
          </div>
        </div>
      </div>

      <div class="min-w-0 rounded-control border border-border">
        <div
          class="border-b border-border bg-surface-muted px-3 py-2 text-meta font-medium text-text-secondary"
        >
          已选列（按顺序）
        </div>
        <div class="max-h-96 overflow-y-auto p-2">
          <p
            v-if="columns.length === 0"
            class="px-2 py-6 text-center text-body text-text-muted"
          >
            尚未选择列
          </p>

          <div
            v-for="(column, index) in columns"
            :key="column.key"
            class="flex items-start gap-2 rounded-tag px-1 py-1.5 hover:bg-surface-muted"
          >
            <div class="min-w-0 flex-1">
              <Input
                v-model="column.label"
                :aria-label="`第 ${index + 1} 列名称`"
              />
              <p class="mt-1 text-meta text-text-muted">
                {{ column.key }} · 宽度
                <span class="tabular-nums">{{ column.width }}</span>
                · {{ formatReportFormat(column.format) }}
              </p>
            </div>

            <div class="flex shrink-0 items-center gap-1">
              <Button
                variant="ghost"
                size="sm"
                class="size-11 px-0 md:size-8"
                :disabled="index === 0"
                :aria-label="`上移第 ${index + 1} 列`"
                @click="moveColumn(index, -1)"
              >
                <template #icon>
                  <ArrowUp :size="16" :stroke-width="1.75" aria-hidden="true" />
                </template>
              </Button>
              <Button
                variant="ghost"
                size="sm"
                class="size-11 px-0 md:size-8"
                :disabled="index === columns.length - 1"
                :aria-label="`下移第 ${index + 1} 列`"
                @click="moveColumn(index, 1)"
              >
                <template #icon>
                  <ArrowDown :size="16" :stroke-width="1.75" aria-hidden="true" />
                </template>
              </Button>
              <Button
                variant="ghost"
                size="sm"
                class="size-11 px-0 text-danger hover:bg-danger-soft hover:text-danger md:size-8"
                :aria-label="`移除第 ${index + 1} 列`"
                @click="removeColumn(index)"
              >
                <template #icon>
                  <X :size="16" :stroke-width="1.75" aria-hidden="true" />
                </template>
              </Button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>
