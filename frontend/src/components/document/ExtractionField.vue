<script setup lang="ts">
import { computed } from 'vue'

import FormField from '@/components/ui/FormField.vue'

import ConfidenceText from './ConfidenceText.vue'

const props = withDefaults(
  defineProps<{
    id: string
    label: string
    required?: boolean
    error?: string
    hint?: string
    confidence?: number | null
  }>(),
  {
    required: false,
    error: '',
    hint: '',
    confidence: null,
  },
)

defineSlots<{
  default?: (slotProps: {
    id: string
    invalid: boolean
    describedBy: string | undefined
  }) => unknown
}>()

const hasConfidence = computed(
  () =>
    typeof props.confidence === 'number' &&
    Number.isFinite(props.confidence),
)
const confidenceId = computed(() =>
  hasConfidence.value ? `${props.id}-confidence` : undefined,
)

function combineDescribedBy(describedBy: string | undefined): string | undefined {
  const ids = [describedBy, confidenceId.value].filter(
    (value): value is string => Boolean(value),
  )
  return ids.length > 0 ? ids.join(' ') : undefined
}
</script>

<template>
  <FormField
    :id="id"
    :label="label"
    :required="required"
    :error="error"
    :hint="hint"
  >
    <template #default="{ id: fieldId, invalid, describedBy }">
      <slot
        v-bind="{
          id: fieldId,
          invalid,
          describedBy: combineDescribedBy(describedBy),
        }"
      />
      <p
        v-if="hasConfidence && confidenceId"
        :id="confidenceId"
        class="mt-1 flex flex-wrap items-center gap-1 text-meta text-text-muted"
      >
        <span>字段置信度</span>
        <ConfidenceText
          :value="confidence"
          show-low-label
        />
      </p>
    </template>
  </FormField>
</template>
