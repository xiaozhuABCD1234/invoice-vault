<script setup lang="ts">
import PageHeader from '@/components/common/PageHeader.vue'
import type { ExtractionJob } from '@/api/types'
import { EMPTY_TEXT } from '@/lib/format'

import ConfidenceText from './ConfidenceText.vue'
import JobStatusPill from './JobStatusPill.vue'
import ReviewActionButtons from './ReviewActionButtons.vue'
import { providerLabel } from './document-utils'

withDefaults(
  defineProps<{
    title: string
    description: string
    job: ExtractionJob
    isReviewable: boolean
    approving?: boolean
    rejecting?: boolean
    retrying?: boolean
    canRetry?: boolean
    retryDisabled?: boolean
  }>(),
  {
    approving: false,
    rejecting: false,
    retrying: false,
    canRetry: false,
    retryDisabled: false,
  },
)

const emit = defineEmits<{
  (event: 'approve'): void
  (event: 'reject'): void
  (event: 'retry'): void
}>()
</script>

<template>
  <PageHeader
    class="break-words"
    :title="title"
    :description="description"
    back-to="/review"
  >
    <template #meta>
      <div class="flex flex-wrap items-center gap-x-3 gap-y-1 break-words text-meta text-text-muted">
        <JobStatusPill :status="job.status" />
        <span>{{ providerLabel(job.provider) }}</span>
        <span>模型 {{ job.model || EMPTY_TEXT }}</span>
        <span>提示词 {{ job.prompt_version || EMPTY_TEXT }}</span>
        <span class="inline-flex items-center gap-1">
          整体置信度
          <ConfidenceText :value="job.confidence" />
        </span>
        <span>尝试 {{ job.attempts }} 次</span>
      </div>
    </template>

    <template #actions>
      <ReviewActionButtons
        layout="header"
        :is-reviewable="isReviewable"
        :approving="approving"
        :rejecting="rejecting"
        :retrying="retrying"
        :can-retry="canRetry"
        :retry-disabled="retryDisabled"
        @approve="emit('approve')"
        @reject="emit('reject')"
        @retry="emit('retry')"
      />
    </template>
  </PageHeader>
</template>
