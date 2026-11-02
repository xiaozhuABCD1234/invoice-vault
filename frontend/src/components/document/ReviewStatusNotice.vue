<script setup lang="ts">
import { computed } from 'vue'
import {
  Check,
  CircleAlert,
  Loader2,
  TriangleAlert,
  X,
} from '@lucide/vue'

import DateText from '@/components/common/DateText.vue'
import type { ExtractionJob } from '@/api/types'
import { getStatusDescriptor } from '@/lib/status'

const props = defineProps<{
  job: ExtractionJob
}>()

const statusLabel = computed(
  () => getStatusDescriptor('job_status', props.job.status).label,
)

const showNotice = computed(() => props.job.status !== 'review_pending')
</script>

<template>
  <section v-if="showNotice" aria-live="polite">
    <div
      v-if="job.status === 'queued' || job.status === 'running'"
      class="flex items-start gap-2 rounded-card border border-info/30 bg-info-soft px-4 py-3 text-body text-info"
      role="status"
    >
      <Loader2
        class="mt-1 shrink-0 animate-spin"
        :size="18"
        :stroke-width="1.75"
        aria-hidden="true"
      />
      <div class="space-y-1">
        <p class="font-medium">
          {{ job.status === 'queued' ? '任务排队中' : '正在识别文档' }}
        </p>
        <p>页面每 3 秒自动刷新，识别完成后进入人工审核。</p>
      </div>
    </div>

    <div
      v-else-if="job.status === 'approved'"
      class="flex items-start gap-2 rounded-card border border-success/30 bg-success-soft px-4 py-3 text-body text-success"
      role="status"
    >
      <Check
        class="mt-1 shrink-0"
        :size="18"
        :stroke-width="1.75"
        aria-hidden="true"
      />
      <div class="space-y-1">
        <p class="font-medium">该任务已通过审核</p>
        <p>
          审核时间：
          <DateText
            :value="job.reviewed_at"
            mode="datetime"
            class="inline-block"
          />
        </p>
        <p>已通过的任务不能重复提交审核。</p>
      </div>
    </div>

    <div
      v-else-if="job.status === 'rejected'"
      class="flex items-start gap-2 rounded-card border border-danger/30 bg-danger-soft px-4 py-3 text-body text-danger"
      role="status"
    >
      <X
        class="mt-1 shrink-0"
        :size="18"
        :stroke-width="1.75"
        aria-hidden="true"
      />
      <div class="space-y-1">
        <p class="font-medium">该任务已驳回</p>
        <p class="break-words">
          驳回原因：{{ job.review_note?.trim() || '—' }}
        </p>
        <p>
          驳回时间：
          <DateText
            :value="job.reviewed_at"
            mode="datetime"
            class="inline-block"
          />
        </p>
        <p>如识别结果可修复，可点击「重试」重新排队识别。</p>
      </div>
    </div>

    <div
      v-else-if="job.status === 'failed'"
      class="flex items-start gap-2 rounded-card border border-danger/30 bg-danger-soft px-4 py-3 text-body text-danger"
      role="alert"
    >
      <CircleAlert
        class="mt-1 shrink-0"
        :size="18"
        :stroke-width="1.75"
        aria-hidden="true"
      />
      <div class="space-y-1">
        <p class="font-medium">识别失败</p>
        <p class="break-words">
          {{ job.error_message?.trim() || '识别服务未返回具体原因。' }}
        </p>
        <p v-if="job.error_code" class="text-meta">
          错误码：{{ job.error_code }}
        </p>
        <p>可点击「重试」重新排队识别。</p>
      </div>
    </div>

    <div
      v-else
      class="flex items-start gap-2 rounded-card border border-border bg-surface-muted px-4 py-3 text-body text-text-secondary"
      role="status"
    >
      <TriangleAlert
        class="mt-1 shrink-0 text-text-muted"
        :size="18"
        :stroke-width="1.75"
        aria-hidden="true"
      />
      <span>
        当前状态为「{{ statusLabel }}」，通过和驳回操作不可用。
      </span>
    </div>
  </section>
</template>
