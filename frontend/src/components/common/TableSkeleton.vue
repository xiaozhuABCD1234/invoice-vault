<script setup lang="ts">
import Skeleton from '@/components/ui/Skeleton.vue'

withDefaults(
  defineProps<{
    rows?: number
    columns?: number
  }>(),
  {
    rows: 6,
    columns: 5,
  },
)

const widthClasses = [
  'w-1/4',
  'w-1/3',
  'w-1/2',
  'w-2/3',
  'w-3/4',
  'w-full',
]

function widthClass(index: number): string {
  return widthClasses[index % widthClasses.length] ?? 'w-full'
}
</script>

<template>
  <div
    class="overflow-hidden rounded-card border border-border bg-surface"
    role="status"
    aria-live="polite"
  >
    <span class="sr-only">正在加载数据</span>

    <div class="flex items-center gap-4 border-b border-border bg-surface-muted px-4 py-3">
      <Skeleton
        v-for="columnIndex in columns"
        :key="`header-${columnIndex}`"
        class="h-3"
        :class="widthClass(columnIndex)"
      />
    </div>

    <div
      v-for="rowIndex in rows"
      :key="`row-${rowIndex}`"
      class="flex items-center gap-4 border-b border-border px-4 py-3 last:border-b-0"
    >
      <Skeleton
        v-for="columnIndex in columns"
        :key="`cell-${rowIndex}-${columnIndex}`"
        class="h-4"
        :class="widthClass(columnIndex + rowIndex)"
      />
    </div>
  </div>
</template>
