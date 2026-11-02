<script setup lang="ts">
import { computed, type Component } from 'vue'
import {
  Ban,
  Check,
  CircleDashed,
  Clock,
  Copy,
  Loader2,
  TriangleAlert,
  X,
} from '@lucide/vue'

import Badge from '@/components/ui/Badge.vue'
import {
  getStatusDescriptor,
  type StatusDescriptor,
  type StatusIcon,
  type StatusKind,
  type StatusTone,
} from '@/lib/status'

const props = defineProps<{
  kind?: StatusKind
  status?: string
  /** 直接指定 tone + label 的简写模式。 */
  tone?: StatusTone
  label?: string
}>()

const statusIcons: Partial<Record<StatusIcon, Component>> = {
  clock: Clock,
  spinner: Loader2,
  check: Check,
  x: X,
  alert: TriangleAlert,
  ban: Ban,
  copy: Copy,
  'circle-dashed': CircleDashed,
}

const descriptor = computed<StatusDescriptor>(() => {
  if (props.kind && props.status) {
    return getStatusDescriptor(props.kind, props.status)
  }
  if (props.tone && props.label) {
    return { label: props.label, tone: props.tone, icon: 'dot' }
  }
  return {
    label: props.label ?? props.status ?? '未知状态',
    tone: props.tone ?? 'neutral',
    icon: 'dot',
  }
})

const icon = computed<Component | undefined>(
  () => statusIcons[descriptor.value.icon],
)

const iconClass = computed(() =>
  descriptor.value.icon === 'spinner' ? 'animate-spin' : undefined,
)
</script>

<template>
  <Badge :tone="descriptor.tone" :icon="icon" :icon-class="iconClass">
    {{ descriptor.label }}
  </Badge>
</template>
