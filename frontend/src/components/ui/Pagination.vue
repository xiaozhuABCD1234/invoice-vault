<script setup lang="ts">
import { computed } from 'vue'
import { ChevronLeft, ChevronRight } from '@lucide/vue'

import Button from './Button.vue'
import Select from './Select.vue'

type PageEntry = number | 'ellipsis-start' | 'ellipsis-end'

const props = withDefaults(
  defineProps<{
    page: number
    pageSize: number
    total: number
    pageSizes?: number[]
  }>(),
  {
    pageSizes: () => [20, 50, 100],
  },
)

const emit = defineEmits<{
  (event: 'update:page', value: number): void
  (event: 'update:pageSize', value: number): void
}>()

const pageCount = computed(() =>
  Math.max(1, Math.ceil(props.total / props.pageSize)),
)

const safePage = computed(() =>
  Math.min(Math.max(1, props.page), pageCount.value),
)

const pages = computed<PageEntry[]>(() => {
  const count = pageCount.value
  if (count <= 7) {
    return Array.from({ length: count }, (_, index) => index + 1)
  }

  const current = safePage.value
  const entries: PageEntry[] = []

  if (current <= 4) {
    const end = Math.min(count - 1, 5)
    for (let page = 1; page <= end; page += 1) entries.push(page)
    if (end < count - 1) entries.push('ellipsis-end')
    entries.push(count)
    return entries
  }

  if (current >= count - 3) {
    entries.push(1, 'ellipsis-start')
    for (let page = count - 4; page <= count; page += 1) entries.push(page)
    return entries
  }

  entries.push(1, 'ellipsis-start')
  for (let page = current - 1; page <= current + 1; page += 1) {
    entries.push(page)
  }
  entries.push('ellipsis-end', count)

  return entries
})

const pageSizeModel = computed({
  get: () => String(props.pageSize),
  set: (value: string) => {
    const next = Number(value)
    if (!Number.isFinite(next) || next <= 0) return
    emit('update:pageSize', next)
    emit('update:page', 1)
  },
})

const pageSizeOptions = computed(() =>
  props.pageSizes.map((size) => ({
    value: String(size),
    label: `${size} 条/页`,
  })),
)

function goToPage(value: number): void {
  const next = Math.min(Math.max(1, value), pageCount.value)
  if (next !== props.page) emit('update:page', next)
}
</script>

<template>
  <div
    class="flex flex-col gap-3 border-t border-border px-4 py-3 sm:flex-row sm:items-center sm:justify-between"
  >
    <p class="text-table text-text-secondary">
      共
      <span class="tabular-nums text-text">{{ total }}</span>
      条
    </p>

    <div class="flex flex-wrap items-center gap-2">
      <Button
        variant="ghost"
        size="sm"
        :disabled="safePage <= 1"
        aria-label="上一页"
        @click="goToPage(safePage - 1)"
      >
        <ChevronLeft :size="16" :stroke-width="1.75" aria-hidden="true" />
        上一页
      </Button>

      <nav aria-label="分页">
        <ul class="flex items-center gap-1">
          <li v-for="entry in pages" :key="entry">
            <span
              v-if="typeof entry !== 'number'"
              class="inline-flex h-8 items-center px-1 text-text-muted"
              aria-hidden="true"
            >
              …
            </span>
            <span
              v-else-if="entry === safePage"
              class="inline-flex h-11 min-w-11 items-center justify-center rounded-tag bg-primary-soft px-2 text-body font-medium tabular-nums text-primary sm:h-8 sm:min-w-8"
              aria-current="page"
            >
              {{ entry }}
            </span>
            <Button
              v-else
              variant="ghost"
              size="sm"
              class="min-w-11 px-2 tabular-nums sm:min-w-8"
              :aria-label="`第 ${entry} 页`"
              @click="goToPage(entry)"
            >
              {{ entry }}
            </Button>
          </li>
        </ul>
      </nav>

      <Button
        variant="ghost"
        size="sm"
        :disabled="safePage >= pageCount"
        aria-label="下一页"
        @click="goToPage(safePage + 1)"
      >
        下一页
        <ChevronRight :size="16" :stroke-width="1.75" aria-hidden="true" />
      </Button>

      <div class="w-32">
        <Select
          v-model="pageSizeModel"
          :options="pageSizeOptions"
          aria-label="每页条数"
        />
      </div>
    </div>
  </div>
</template>
