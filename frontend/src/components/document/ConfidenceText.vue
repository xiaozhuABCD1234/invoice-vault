<script setup lang="ts">
import { computed } from 'vue'
import { TriangleAlert } from '@lucide/vue'

import { cn } from '@/lib/cn'
import { EMPTY_TEXT, percent } from '@/lib/format'

const props = withDefaults(
  defineProps<{
    value: number | null | undefined
    threshold?: number
    showLowLabel?: boolean
  }>(),
  {
    threshold: 0.8,
    showLowLabel: false,
  },
)

const display = computed(() => percent(props.value))
const isEmpty = computed(() => display.value === EMPTY_TEXT)
const isLow = computed(
  () =>
    typeof props.value === 'number' &&
    Number.isFinite(props.value) &&
    props.value < props.threshold,
)
</script>

<template>
  <span
    :class="
      cn(
        'inline-flex items-center gap-1 whitespace-nowrap tabular-nums',
        isEmpty && 'text-text-muted',
        isLow && 'text-warning',
      )
    "
    :title="isLow ? '低置信度，请重点核对' : undefined"
  >
    <TriangleAlert
      v-if="isLow"
      :size="16"
      :stroke-width="1.75"
      aria-hidden="true"
    />
    <span>{{ display }}</span>
    <span
      v-if="isLow && showLowLabel"
      class="text-meta font-medium"
    >
      低置信度
    </span>
  </span>
</template>
