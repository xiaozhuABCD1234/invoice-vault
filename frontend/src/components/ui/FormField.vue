<script setup lang="ts">
import { computed } from 'vue'
import { CircleAlert } from '@lucide/vue'

import Label from './Label.vue'

const props = withDefaults(
  defineProps<{
    id: string
    label: string
    required?: boolean
    error?: string
    hint?: string
  }>(),
  {
    required: false,
    error: '',
    hint: '',
  },
)

defineSlots<{
  default?: (props: {
    id: string
    invalid: boolean
    describedBy: string | undefined
  }) => unknown
  /** 标签右侧的补充信息（如配置来源标记）。 */
  'label-extra'?: () => unknown
}>()

const hintId = computed(() => `${props.id}-hint`)
const errorId = computed(() => `${props.id}-error`)

const describedBy = computed(() => {
  const ids: string[] = []
  if (props.hint) ids.push(hintId.value)
  if (props.error) ids.push(errorId.value)
  return ids.length > 0 ? ids.join(' ') : undefined
})
</script>

<template>
  <div class="space-y-1">
    <div class="flex items-center justify-between gap-2">
      <Label :for="id" :required="required">{{ label }}</Label>
      <slot name="label-extra" />
    </div>
    <slot
      :id="id"
      :invalid="Boolean(error)"
      :describedBy="describedBy"
    />
    <p v-if="hint" :id="hintId" class="text-meta text-text-muted">
      {{ hint }}
    </p>
    <p
      v-if="error"
      :id="errorId"
      class="flex items-start gap-1 text-meta text-danger"
      aria-live="polite"
    >
      <CircleAlert
        class="mt-1 shrink-0"
        :size="16"
        :stroke-width="1.75"
        aria-hidden="true"
      />
      <span>{{ error }}</span>
    </p>
  </div>
</template>
