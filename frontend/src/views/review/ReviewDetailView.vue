<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import { TriangleAlert } from '@lucide/vue'

import EmptyState from '@/components/common/EmptyState.vue'
import ErrorState from '@/components/common/ErrorState.vue'
import PageHeader from '@/components/common/PageHeader.vue'
import TableSkeleton from '@/components/common/TableSkeleton.vue'
import Button from '@/components/ui/Button.vue'
import ExtractionConfidencePanel from '@/components/document/ExtractionConfidencePanel.vue'
import ExtractionDiffPanel from '@/components/document/ExtractionDiffPanel.vue'
import ExtractionValidationPanel from '@/components/document/ExtractionValidationPanel.vue'
import RejectExtractionDialog from '@/components/document/RejectExtractionDialog.vue'
import ReviewDocumentPanel from '@/components/document/ReviewDocumentPanel.vue'
import ReviewFieldsCard from '@/components/document/ReviewFieldsCard.vue'
import ReviewPageHeader from '@/components/document/ReviewPageHeader.vue'
import ReviewStatusNotice from '@/components/document/ReviewStatusNotice.vue'
import { documentFileName } from '@/components/document/document-utils'
import { EMPTY_TEXT } from '@/lib/format'
import { useExtractionReview } from '@/composables/useExtractionReview'

const route = useRoute()

const jobId = computed<number | null>(() => {
  const raw = route.params.jobId
  const value = Array.isArray(raw) ? raw[0] : raw
  if (!value) return null
  const parsed = Number(value)
  return Number.isSafeInteger(parsed) && parsed > 0 ? parsed : null
})

const {
  detail,
  loading,
  error,
  actionError,
  pollError,
  draft,
  errors,
  fieldConfidence,
  validationErrors,
  validationWarnings,
  diff,
  isReviewable,
  canRetry,
  retryDisabled,
  approving,
  rejecting,
  retrying,
  rejectOpen,
  rejectError,
  categories,
  users,
  optionsLoading,
  optionsError,
  load,
  loadOptions,
  approve,
  openReject,
  confirmReject,
  retry,
} = useExtractionReview(jobId)

const fullDocumentName = computed(() =>
  detail.value ? documentFileName(detail.value.document) : '',
)

const pageTitle = computed(() => {
  const name = fullDocumentName.value
  if (name === '') return '审核详情'
  return name.length > 64 ? `${name.slice(0, 64)}…` : name
})

const pageDescription = computed(() => {
  if (!detail.value) return '核对识别结果、字段置信度与文件内容后完成审核。'
  const candidate = draft.value.invoiceNumber.trim()
  return `发票号候选：${candidate || EMPTY_TEXT}`
})
</script>

<template>
  <div>
    <ReviewPageHeader
      v-if="detail"
      class="break-words"
      :title="pageTitle"
      :description="pageDescription"
      :job="detail.job"
      :is-reviewable="isReviewable"
      :approving="approving"
      :rejecting="rejecting"
      :retrying="retrying"
      :can-retry="canRetry"
      :retry-disabled="retryDisabled"
      @approve="approve"
      @reject="openReject"
      @retry="retry"
    />
    <PageHeader
      v-else
      class="break-words"
      title="审核详情"
      description="核对识别结果、字段置信度与文件内容后完成审核。"
      back-to="/review"
    />

    <TableSkeleton v-if="loading" :rows="8" :columns="2" />

    <div
      v-else-if="error"
      class="rounded-card border border-border bg-surface"
    >
      <ErrorState
        title="审核任务加载失败"
        :message="error"
        @retry="load()"
      />
    </div>

    <div
      v-else-if="detail"
      class="grid gap-6 lg:grid-cols-11"
    >
      <aside class="min-w-0 lg:col-span-6">
        <ReviewDocumentPanel :document="detail.document" />
      </aside>

      <div class="min-w-0 space-y-4 lg:col-span-5">
        <ReviewStatusNotice :job="detail.job" />

        <div
          v-if="pollError"
          class="flex flex-wrap items-center gap-2 break-words rounded-card border border-warning/40 bg-warning-soft px-4 py-3 text-body text-warning"
          role="status"
        >
          <TriangleAlert :size="18" :stroke-width="1.75" aria-hidden="true" />
          <span>自动刷新已暂停：{{ pollError }}</span>
          <Button variant="secondary" size="sm" @click="load(false)">
            立即刷新
          </Button>
        </div>

        <div
          v-if="optionsError"
          class="flex flex-wrap items-center gap-2 break-words rounded-card border border-danger/30 bg-danger-soft px-4 py-3 text-body text-danger"
          role="alert"
        >
          <TriangleAlert :size="18" :stroke-width="1.75" aria-hidden="true" />
          <span>{{ optionsError }}</span>
          <Button variant="secondary" size="sm" @click="loadOptions">
            重新加载选项
          </Button>
        </div>

        <ExtractionConfidencePanel
          :confidence="detail.job.confidence"
          :field-confidence="fieldConfidence"
        />

        <ExtractionValidationPanel
          :errors="validationErrors"
          :warnings="validationWarnings"
        />

        <ExtractionDiffPanel :diff="diff" />

        <ReviewFieldsCard
          v-model="draft"
          :errors="errors"
          :field-confidence="fieldConfidence"
          :categories="categories"
          :users="users"
          :disabled="!isReviewable || approving || rejecting || retrying"
          :options-loading="optionsLoading"
          :is-reviewable="isReviewable"
          :action-error="actionError"
          :approving="approving"
          :rejecting="rejecting"
          :retrying="retrying"
          @approve="approve"
          @reject="openReject"
        />
      </div>
    </div>

    <div v-else class="rounded-card border border-border bg-surface">
      <EmptyState
        title="未找到审核任务"
        description="该任务可能已被删除，请返回审核队列重新进入。"
      >
        <template #action>
          <RouterLink
            to="/review"
            class="inline-flex min-h-11 items-center rounded-control border border-border-strong bg-surface px-4 text-body font-medium text-text hover:bg-surface-muted md:min-h-0"
          >
            返回审核队列
          </RouterLink>
        </template>
      </EmptyState>
    </div>

    <RejectExtractionDialog
      v-model:open="rejectOpen"
      :loading="rejecting"
      :error="rejectError"
      :document-name="pageTitle"
      @confirm="confirmReject"
    />
  </div>
</template>
