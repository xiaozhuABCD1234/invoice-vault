<script setup lang="ts">
import { computed } from 'vue'
import { Check, TriangleAlert } from '@lucide/vue'

import ConfidenceText from './ConfidenceText.vue'
import { extractionFieldLabel } from './extraction-fields'

const props = withDefaults(
  defineProps<{
    confidence?: number | null
    fieldConfidence?: Record<string, number> | null
  }>(),
  {
    confidence: null,
    fieldConfidence: null,
  },
)

const fieldCount = computed(
  () => Object.keys(props.fieldConfidence ?? {}).length,
)

const lowFields = computed(() => {
  const grouped = new Map<string, number>()
  for (const [key, value] of Object.entries(props.fieldConfidence ?? {})) {
    if (typeof value !== 'number' || !Number.isFinite(value) || value >= 0.8) {
      continue
    }
    const label = extractionFieldLabel(key)
    const previous = grouped.get(label)
    if (previous === undefined || value < previous) {
      grouped.set(label, value)
    }
  }

  return [...grouped.entries()]
    .map(([label, value]) => ({ label, value }))
    .sort((left, right) => left.value - right.value)
})
</script>

<template>
  <section
    class="rounded-card border border-border bg-surface p-4"
    aria-labelledby="review-confidence-title"
  >
    <h3 id="review-confidence-title" class="text-heading font-semibold text-text">
      置信度
    </h3>

    <div class="mt-2 flex flex-wrap items-center justify-between gap-2">
      <span class="text-body text-text-secondary">整体置信度</span>
      <ConfidenceText :value="confidence" show-low-label />
    </div>

    <p v-if="fieldCount === 0" class="mt-2 text-body text-text-muted">
      暂无字段置信度数据，请逐项人工核对。
    </p>

    <template v-else>
      <p class="mt-2 text-meta text-text-muted">
        共 {{ fieldCount }} 个字段包含置信度数据。
      </p>

      <div
        v-if="lowFields.length === 0"
        class="mt-2 flex items-start gap-2 text-body text-text-secondary"
      >
        <Check
          class="mt-1 shrink-0 text-success"
          :size="18"
          :stroke-width="1.75"
          aria-hidden="true"
        />
        <span>字段置信度均不低于 80%。</span>
      </div>

      <div v-else class="mt-2" role="status">
        <p class="flex items-center gap-1 text-body font-medium text-warning">
          <TriangleAlert :size="18" :stroke-width="1.75" aria-hidden="true" />
          低置信度字段（{{ lowFields.length }}）
        </p>
        <ul class="mt-1 space-y-1">
          <li
            v-for="field in lowFields"
            :key="field.label"
            class="flex flex-wrap items-center justify-between gap-2 text-body"
          >
            <span class="break-words text-text-secondary">{{ field.label }}</span>
            <ConfidenceText :value="field.value" show-low-label />
          </li>
        </ul>
      </div>
    </template>
  </section>
</template>
