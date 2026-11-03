<script setup lang="ts">
import { computed, useAttrs } from 'vue'
import type { ClassValue } from 'clsx'

import { cn } from '@/lib/cn'

defineOptions({ inheritAttrs: false })

const props = withDefaults(
  defineProps<{
    type?: string
    invalid?: boolean
    disabled?: boolean
    readonly?: boolean
  }>(),
  {
    type: 'text',
    invalid: false,
    disabled: false,
    readonly: false,
  },
)

const model = defineModel<string>({ default: '' })
const attrs = useAttrs()

// <input type="number"> 的原生 v-model 会把值转成 number；本组件对外契约是字符串，
// 这里统一归一化，避免调用方拿到意外的 number（如 .trim() 报错）。
const text = computed({
  get: () => model.value ?? '',
  set: (value: string) => {
    model.value = value === null || value === undefined ? '' : String(value)
  },
})

const classes = computed(() =>
  cn(
    'h-11 w-full rounded-control border bg-surface px-3 text-input text-text transition-colors duration-150 placeholder:text-text-muted disabled:cursor-not-allowed disabled:bg-surface-muted disabled:text-text-muted md:h-9',
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
  <input
    v-bind="restAttrs"
    v-model="text"
    :type="type"
    :disabled="disabled"
    :readonly="readonly"
    :aria-invalid="invalid || undefined"
    :class="classes"
  />
</template>
