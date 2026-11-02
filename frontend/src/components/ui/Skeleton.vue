<script setup lang="ts">
import { computed, useAttrs } from 'vue'
import type { ClassValue } from 'clsx'

import { cn } from '@/lib/cn'

defineOptions({ inheritAttrs: false })

const attrs = useAttrs()

const classes = computed(() =>
  cn(
    'animate-pulse rounded-control bg-surface-muted',
    attrs.class as ClassValue,
  ),
)

const restAttrs = computed(() => {
  const copy: Record<string, unknown> = { ...attrs }
  delete copy.class
  return copy
})
</script>

<template>
  <div v-bind="restAttrs" :class="classes" aria-hidden="true" />
</template>
