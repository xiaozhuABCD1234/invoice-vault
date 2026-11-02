<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { Eye, RotateCw } from '@lucide/vue'

import DataTable from '@/components/common/DataTable.vue'
import DateText from '@/components/common/DateText.vue'
import StatusBadge from '@/components/common/StatusBadge.vue'
import type { DataTableColumn } from '@/components/common/data-table'
import Button from '@/components/ui/Button.vue'
import type { ExtractionJob } from '@/api/types'
import { EMPTY_TEXT } from '@/lib/format'

import ConfidenceText from './ConfidenceText.vue'
import {
  canRetryExtraction,
  documentTypeLabel,
  providerLabel,
  retryLimitReached,
} from './document-utils'
import { useMediaQuery } from '@/composables/useMediaQuery'

withDefaults(
  defineProps<{
    rows: ExtractionJob[]
    loading?: boolean
    error?: string
    retryingId?: number | null
  }>(),
  {
    loading: false,
    error: '',
    retryingId: null,
  },
)

const emit = defineEmits<{
  (event: 'retry', job: ExtractionJob): void
  (event: 'reload'): void
}>()

const router = useRouter()

const stickyColumns = useMediaQuery('(min-width: 768px)')

const columns = computed<DataTableColumn[]>(() => [
  {
    key: 'document',
    label: '文档名',
    width: 220,
    fixed: stickyColumns.value ? 'left' : undefined,
  },
  { key: 'doc_type', label: '类型', width: 100, nowrap: true },
  { key: 'provider', label: '识别器 / 模型', width: 170 },
  { key: 'confidence', label: '置信度', width: 110, align: 'right', nowrap: true },
  { key: 'status', label: '状态', width: 110, align: 'center', nowrap: true },
  { key: 'attempts', label: '尝试次数', width: 90, align: 'right', nowrap: true },
  { key: 'times', label: '入队 / 完成时间', width: 170, nowrap: true },
  {
    key: 'actions',
    label: '操作',
    width: 150,
    align: 'right',
    fixed: stickyColumns.value ? 'right' : undefined,
  },
])

function documentName(job: ExtractionJob): string {
  return job.document_name?.trim() || `文档 #${job.document_id}`
}

function openDetail(job: ExtractionJob): void {
  void router.push({
    name: 'review-detail',
    params: { jobId: job.id },
  })
}

</script>

<template>
  <DataTable
    :rows="rows"
    :columns="columns"
    row-key="id"
    :loading="loading"
    :error="error"
    empty="暂无审核任务"
    empty-description="上传发票后会自动创建识别任务，识别完成后进入审核队列。"
    @retry="emit('reload')"
  >
    <template #cell-document="{ row }">
      <button
        type="button"
        class="inline-flex min-h-11 min-w-48 items-center break-words text-left font-medium text-primary hover:underline md:min-h-0"
        @click="openDetail(row)"
      >
        {{ documentName(row) }}
      </button>
    </template>

    <template #cell-doc_type="{ row }">
      {{ documentTypeLabel(row.document_doc_type) }}
    </template>

    <template #cell-provider="{ row }">
      <div class="min-w-36 space-y-0.5">
        <p>{{ providerLabel(row.provider) }}</p>
        <p class="break-words font-mono text-meta text-text-muted">
          {{ row.model || EMPTY_TEXT }}
        </p>
      </div>
    </template>

    <template #cell-confidence="{ row }">
      <ConfidenceText :value="row.confidence" />
    </template>

    <template #cell-status="{ row }">
      <StatusBadge kind="job_status" :status="row.status" />
    </template>

    <template #cell-attempts="{ row }">
      <span class="tabular-nums">{{ row.attempts }}</span>
    </template>

    <template #cell-times="{ row }">
      <div class="min-w-40 space-y-0.5 text-meta">
        <div class="flex items-center gap-1">
          <span class="text-text-muted">入队</span>
          <DateText :value="row.queued_at" mode="datetime" />
        </div>
        <div class="flex items-center gap-1">
          <span class="text-text-muted">完成</span>
          <DateText :value="row.finished_at" mode="datetime" />
        </div>
      </div>
    </template>

    <template #cell-actions="{ row }">
      <div class="flex flex-wrap items-center justify-end gap-1">
        <Button variant="ghost" size="sm" @click="openDetail(row)">
          <template #icon>
            <Eye :size="16" :stroke-width="1.75" aria-hidden="true" />
          </template>
          查看
        </Button>

        <Button
          v-if="canRetryExtraction(row)"
          variant="ghost"
          size="sm"
          :loading="retryingId === row.id"
          :disabled="retryLimitReached(row)"
          :title="retryLimitReached(row) ? '重试次数已达上限（3 次）' : undefined"
          @click="emit('retry', row)"
        >
          <template #icon>
            <RotateCw :size="16" :stroke-width="1.75" aria-hidden="true" />
          </template>
          重试
        </Button>
      </div>
    </template>

    <template #empty-action>
      <slot name="empty-action" />
    </template>
  </DataTable>
</template>
