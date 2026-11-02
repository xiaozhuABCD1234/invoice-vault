<script setup lang="ts">
import { computed } from 'vue'

import { cn } from '@/lib/cn'
import { formatDate, formatDateTime, type DateInput } from '@/lib/date'
import { EMPTY_TEXT } from '@/lib/format'

type DateMode = 'date' | 'datetime'
type DateAlign = 'left' | 'center' | 'right'

const props = withDefaults(
  defineProps<{
    value: DateInput
    mode?: DateMode
    align?: DateAlign
  }>(),
  {
    mode: 'date',
    align: 'left',
  },
)

const alignClasses: Record<DateAlign, string> = {
  left: 'text-left',
  center: 'text-center',
  right: 'text-right',
}

const display = computed(() =>
  props.mode === 'datetime'
    ? formatDateTime(props.value)
    : formatDate(props.value),
)

const isEmpty = computed(() => display.value === EMPTY_TEXT)
</script>

<template>
  <span
    :class="
      cn(
        'block whitespace-nowrap tabular-nums',
        alignClasses[align],
        isEmpty ? 'text-text-muted' : '',
      )
    "
  >
    {{ display }}
  </span>
</template>
