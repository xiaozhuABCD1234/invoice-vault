<script setup lang="ts">
import type { Category, UserOption } from '@/api/types'

import ExtractionFieldForm from './ExtractionFieldForm.vue'
import ReviewActionButtons from './ReviewActionButtons.vue'
import type {
  InvoiceDraft,
  InvoiceDraftErrors,
} from './extraction-fields'

withDefaults(
  defineProps<{
    errors?: InvoiceDraftErrors
    fieldConfidence?: Record<string, number> | null
    categories?: Category[]
    users?: UserOption[]
    disabled?: boolean
    optionsLoading?: boolean
    isReviewable: boolean
    actionError?: string
    approving?: boolean
    rejecting?: boolean
    retrying?: boolean
  }>(),
  {
    errors: () => ({}),
    fieldConfidence: null,
    categories: () => [],
    users: () => [],
    disabled: false,
    optionsLoading: false,
    actionError: '',
    approving: false,
    rejecting: false,
    retrying: false,
  },
)

const draft = defineModel<InvoiceDraft>({ required: true })

const emit = defineEmits<{
  (event: 'approve'): void
  (event: 'reject'): void
}>()
</script>

<template>
  <section
    class="rounded-card border border-border bg-surface"
    aria-labelledby="review-fields-title"
  >
    <header class="border-b border-border px-4 py-3">
      <h2 id="review-fields-title" class="text-heading font-semibold text-text">
        审核字段
      </h2>
      <p class="mt-1 text-body text-text-secondary">
        低置信度字段会以警告色标识，请对照左侧文件核对后修改。
      </p>
    </header>

    <div class="p-4">
      <ExtractionFieldForm
        v-model="draft"
        :errors="errors"
        :field-confidence="fieldConfidence"
        :categories="categories"
        :users="users"
        :disabled="disabled"
        :options-loading="optionsLoading"
      />
    </div>

    <footer class="space-y-3 border-t border-border px-4 py-4">
      <p
        v-if="actionError"
        class="rounded-control border border-danger/30 bg-danger-soft px-3 py-2 text-body text-danger break-words"
        role="alert"
      >
        {{ actionError }}
      </p>

      <p v-if="!isReviewable" class="text-meta text-text-muted">
        当前任务不是待审核状态，通过和驳回操作不可用。
      </p>

      <div class="flex justify-end">
        <ReviewActionButtons
          layout="footer"
          :is-reviewable="isReviewable"
          :approving="approving"
          :rejecting="rejecting"
          :retrying="retrying"
          @approve="emit('approve')"
          @reject="emit('reject')"
        />
      </div>
    </footer>
  </section>
</template>
