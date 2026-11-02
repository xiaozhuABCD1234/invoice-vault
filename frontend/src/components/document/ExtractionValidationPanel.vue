<script setup lang="ts">
import { Check, CircleAlert, TriangleAlert } from '@lucide/vue'

withDefaults(
  defineProps<{
    errors?: string[]
    warnings?: string[]
  }>(),
  {
    errors: () => [],
    warnings: () => [],
  },
)
</script>

<template>
  <section
    class="rounded-card border border-border bg-surface p-4"
    aria-labelledby="review-validation-title"
  >
    <h3 id="review-validation-title" class="text-heading font-semibold text-text">
      自动校验
    </h3>

    <div
      v-if="errors.length === 0 && warnings.length === 0"
      class="mt-2 flex items-start gap-2 text-body text-text-secondary"
    >
      <Check
        class="mt-1 shrink-0 text-success"
        :size="18"
        :stroke-width="1.75"
        aria-hidden="true"
      />
      <span>自动校验未发现错误或提醒。</span>
    </div>

    <div v-if="errors.length > 0" class="mt-3" role="alert">
      <p class="flex items-center gap-1 text-body font-medium text-danger">
        <CircleAlert :size="18" :stroke-width="1.75" aria-hidden="true" />
        校验错误（{{ errors.length }}）
      </p>
      <ul class="mt-1 list-disc space-y-1 break-words pl-5 text-body text-danger">
        <li v-for="(item, index) in errors" :key="`error-${index}`">
          {{ item }}
        </li>
      </ul>
    </div>

    <div v-if="warnings.length > 0" class="mt-3">
      <p class="flex items-center gap-1 text-body font-medium text-warning">
        <TriangleAlert :size="18" :stroke-width="1.75" aria-hidden="true" />
        校验提醒（{{ warnings.length }}）
      </p>
      <ul class="mt-1 list-disc space-y-1 break-words pl-5 text-body text-warning">
        <li v-for="(item, index) in warnings" :key="`warning-${index}`">
          {{ item }}
        </li>
      </ul>
    </div>
  </section>
</template>
