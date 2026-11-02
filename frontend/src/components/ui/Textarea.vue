<script setup lang="ts">
import { computed, useAttrs } from 'vue'
import type { ClassValue } from 'clsx'

import { cn } from '@/lib/cn'

defineOptions({ inheritAttrs: false })

const props = withDefaults(
  defineProps<{
    rows?: number
    invalid?: boolean
    disabled?: boolean
    readonly?: boolean
  }>(),
  {
    rows: 4,
    invalid: false,
    disabled: false,
    readonly: false,
  },
)

const model = defineModel<string>({ default: '' })
const attrs = useAttrs()

const classes = computed(() =>
  cn(
    'block w-full resize-y rounded-control border bg-surface px-3 py-2 text-input text-text transition-colors duration-150 placeholder:text-text-muted disabled:cursor-not-allowed disabled:bg-surface-muted disabled:text-text-muted',
    props.invalid
      ? 'border-danger hover:border-danger focus:border-danger'
      : 'border-border hover:border-border-strong focus:border-primary',
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
  <textarea
    v-bind="restAttrs"
    v-model="model"
    :rows="rows"
    :disabled="disabled"
    :readonly="readonly"
    :aria-invalid="invalid || undefined"
    :class="classes"
  />
</template>
