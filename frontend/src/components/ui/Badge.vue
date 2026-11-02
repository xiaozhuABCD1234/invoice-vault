<script setup lang="ts">
import { computed, type Component } from 'vue'

import { cn } from '@/lib/cn'
import type { StatusTone } from '@/lib/status'

const props = withDefaults(
  defineProps<{
    tone?: StatusTone
    icon?: Component
    iconClass?: string
    dot?: boolean
  }>(),
  {
    tone: 'neutral',
    dot: true,
  },
)

const toneClasses: Record<StatusTone, string> = {
  neutral: 'bg-surface-muted text-text-secondary',
  success: 'bg-success-soft text-success',
  warning: 'bg-warning-soft text-warning',
  danger: 'bg-danger-soft text-danger',
  info: 'bg-info-soft text-info',
}

const showDot = computed(() => props.dot && !props.icon)
</script>

<template>
  <span
    :class="
      cn(
        'inline-flex items-center gap-1 whitespace-nowrap rounded-tag px-2 py-0.5 text-meta font-medium',
        toneClasses[tone],
      )
    "
  >
    <span
      v-if="showDot"
      class="size-2 shrink-0 rounded-pill bg-current"
      aria-hidden="true"
    />
    <component
      :is="icon"
      v-if="icon"
      :size="16"
      :stroke-width="1.75"
      :class="iconClass"
      aria-hidden="true"
    />
    <slot />
  </span>
</template>
