<script setup lang="ts">
import { computed } from 'vue'

import { cn } from '@/lib/cn'
import { EMPTY_TEXT } from '@/lib/format'
import { formatCents } from '@/lib/money'

type MoneyAlign = 'left' | 'center' | 'right'

const props = withDefaults(
  defineProps<{
    cents: number | null | undefined
    strong?: boolean
    align?: MoneyAlign
  }>(),
  {
    strong: false,
    align: 'right',
  },
)

const alignClasses: Record<MoneyAlign, string> = {
  left: 'text-left',
  center: 'text-center',
  right: 'text-right',
}

const display = computed(() => formatCents(props.cents))
const isEmpty = computed(() => display.value === EMPTY_TEXT)
</script>

<template>
  <span
    :class="
      cn(
        'block whitespace-nowrap tabular-nums',
        alignClasses[align],
        strong && 'font-semibold',
        isEmpty ? 'text-text-muted' : '',
      )
    "
  >
    {{ display }}
  </span>
</template>
