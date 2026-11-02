<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { ImageDown } from '@lucide/vue'
import VChart from 'vue-echarts'
import type { EChartsOption } from 'echarts'
import { toast } from 'vue-sonner'

import EmptyState from '@/components/common/EmptyState.vue'
import ErrorState from '@/components/common/ErrorState.vue'
import Button from '@/components/ui/Button.vue'
import Skeleton from '@/components/ui/Skeleton.vue'
import { readCssVar } from './dashboard-charts'

const props = withDefaults(
  defineProps<{
    title: string
    description?: string
    option: EChartsOption | null
    empty?: boolean
    loading?: boolean
    error?: string | null
    exportName: string
    heightClass?: string
  }>(),
  {
    description: '',
    empty: false,
    loading: false,
    error: null,
    heightClass: 'h-80',
  },
)

const emit = defineEmits<{
  (event: 'retry'): void
}>()

const chartRef = ref<InstanceType<typeof VChart> | null>(null)
const ready = ref(false)

const chartOption = computed<EChartsOption>(() => props.option ?? {})
const canExport = computed(
  () =>
    ready.value &&
    !props.loading &&
    !props.error &&
    !props.empty &&
    props.option !== null,
)

const skeletonHeights = [
  'h-1/4',
  'h-1/3',
  'h-1/2',
  'h-2/3',
  'h-3/4',
  'h-full',
]

watch(
  [() => props.option, () => props.loading, () => props.empty, () => props.error],
  () => {
    ready.value = false
  },
)

function exportImage(): void {
  const chart = chartRef.value
  if (!chart || !canExport.value) return

  try {
    const dataUrl = chart.getDataURL({
      type: 'png',
      pixelRatio: 2,
      backgroundColor: readCssVar('--color-surface'),
    })
    const link = document.createElement('a')
    link.href = dataUrl
    link.download = `仪表盘-${props.exportName}.png`
    document.body.appendChild(link)
    link.click()
    link.remove()
  } catch {
    toast.error('图片导出失败，请稍后重试')
  }
}
</script>

<template>
  <article class="flex min-w-0 flex-col rounded-card border border-border bg-surface">
    <header class="flex flex-wrap items-start justify-between gap-3 border-b border-border p-4">
      <div class="min-w-0">
        <h2 class="text-heading font-semibold text-text">{{ title }}</h2>
        <p v-if="description" class="mt-1 text-meta text-text-muted">
          {{ description }}
        </p>
      </div>

      <Button
        v-if="canExport"
        variant="secondary"
        size="sm"
        @click="exportImage"
      >
        <template #icon>
          <ImageDown :size="16" :stroke-width="1.75" aria-hidden="true" />
        </template>
        导出图片
      </Button>
    </header>

    <div class="min-w-0 flex-1 p-4">
      <div
        v-if="loading"
        :class="heightClass"
        class="flex items-end gap-2"
        role="status"
        aria-live="polite"
      >
        <span class="sr-only">正在加载图表</span>
        <Skeleton
          v-for="height in skeletonHeights"
          :key="height"
          class="flex-1"
          :class="height"
        />
      </div>

      <ErrorState
        v-else-if="error"
        title="图表加载失败"
        :message="error"
        @retry="emit('retry')"
      />

      <EmptyState
        v-else-if="empty"
        title="暂无图表数据"
        description="当前日期范围内没有可展示的数据。"
      />

      <div v-else :class="heightClass" class="w-full">
        <VChart
          ref="chartRef"
          :option="chartOption"
          :aria-label="title"
          autoresize
          class="h-full w-full"
          @rendered="ready = true"
        />
      </div>
    </div>
  </article>
</template>
