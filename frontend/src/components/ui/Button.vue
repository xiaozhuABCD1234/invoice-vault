<script setup lang="ts">
import { computed, useAttrs } from 'vue'
import type { ClassValue } from 'clsx'
import { Loader2 } from '@lucide/vue'

import { cn } from '@/lib/cn'

defineOptions({ inheritAttrs: false })

type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'danger'
type ButtonSize = 'sm' | 'md' | 'lg'

const props = withDefaults(
  defineProps<{
    variant?: ButtonVariant
    size?: ButtonSize
    type?: 'button' | 'submit' | 'reset'
    disabled?: boolean
    loading?: boolean
  }>(),
  {
    variant: 'primary',
    size: 'md',
    type: 'button',
    disabled: false,
    loading: false,
  },
)

const attrs = useAttrs()

const variantClasses: Record<ButtonVariant, string> = {
  primary:
    'border-primary bg-primary text-surface hover:border-primary-hover hover:bg-primary-hover',
  secondary:
    'border-border-strong bg-surface text-text hover:bg-surface-muted',
  ghost:
    'border-transparent bg-transparent text-text-secondary hover:bg-surface-muted hover:text-text',
  danger:
    'border-danger bg-danger text-surface hover:bg-danger/90',
}

const sizeClasses: Record<ButtonSize, string> = {
  sm: 'h-8 px-3',
  md: 'h-9 px-4',
  lg: 'h-10 px-5',
}

const iconSize = computed(() => (props.size === 'sm' ? 16 : 18))

const classes = computed(() =>
  cn(
    'relative inline-flex min-h-11 select-none items-center justify-center gap-2 whitespace-nowrap rounded-control border text-body font-medium transition-colors duration-150 ease-out disabled:pointer-events-none disabled:opacity-50 md:min-h-0',
    variantClasses[props.variant],
    sizeClasses[props.size],
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
  <button
    v-bind="restAttrs"
    :type="type"
    :class="classes"
    :disabled="disabled || loading"
    :aria-busy="loading || undefined"
  >
    <span
      class="inline-flex items-center justify-center gap-2"
      :class="loading ? 'opacity-0' : ''"
    >
      <slot name="icon" />
      <slot />
    </span>
    <span
      v-if="loading"
      class="absolute inset-0 flex items-center justify-center"
      aria-hidden="true"
    >
      <Loader2
        class="animate-spin"
        :size="iconSize"
        :stroke-width="1.75"
      />
    </span>
  </button>
</template>
