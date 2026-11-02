<script setup lang="ts">
import { computed } from 'vue'
import { Download, Eye, Trash2 } from '@lucide/vue'

import DataTable from '@/components/common/DataTable.vue'
import DateText from '@/components/common/DateText.vue'
import type { DataTableColumn } from '@/components/common/data-table'
import Button from '@/components/ui/Button.vue'
import { EMPTY_TEXT, fileSize } from '@/lib/format'
import type { Document, ExtractionJob } from '@/api/types'

import {
  documentFileName,
  documentTypeLabel,
} from './document-utils'
import JobStatusPill from './JobStatusPill.vue'
import { useMediaQuery } from '@/composables/useMediaQuery'

withDefaults(
  defineProps<{
    rows: Document[]
    latestJobs: Record<number, ExtractionJob | null>
    loading?: boolean
    error?: string
    isAdmin?: boolean
    downloadingId?: number | null
  }>(),
  {
    loading: false,
    error: '',
    isAdmin: false,
    downloadingId: null,
  },
)

const emit = defineEmits<{
  (event: 'preview', document: Document): void
  (event: 'download', document: Document): void
  (event: 'delete', document: Document): void
  (event: 'retry'): void
}>()

const stickyColumns = useMediaQuery('(min-width: 768px)')

const columns = computed<DataTableColumn[]>(() => [
  {
    key: 'file',
    label: '文件名',
    width: 240,
    fixed: stickyColumns.value ? 'left' : undefined,
  },
  { key: 'doc_type', label: '类型', width: 110, nowrap: true },
  { key: 'owner', label: '归属人', width: 110, nowrap: true },
  { key: 'size', label: '大小', width: 100, align: 'right', nowrap: true },
  { key: 'created_at', label: '上传时间', width: 150, nowrap: true },
  { key: 'job', label: '状态 / 最新任务', width: 140, nowrap: true },
  {
    key: 'actions',
    label: '操作',
    width: 230,
    align: 'right',
    fixed: stickyColumns.value ? 'right' : undefined,
  },
])

function versionName(document: Document): string {
  return document.current_version?.original_name ?? ''
}

function ownerName(document: Document): string {
  return document.owner_name?.trim() || EMPTY_TEXT
}

function jobEmptyText(document: Document): string {
  return document.doc_type === 'invoice' ? EMPTY_TEXT : '无需识别'
}
</script>

<template>
  <DataTable
    :rows="rows"
    :columns="columns"
    row-key="id"
    :loading="loading"
    :error="error"
    empty="暂无文档"
    empty-description="上传发票或付款凭证后，文件会显示在这里。"
    @retry="emit('retry')"
  >
    <template #cell-file="{ row }">
      <div class="min-w-52 space-y-0.5">
        <p class="break-words font-medium text-text">
          {{ documentFileName(row) }}
        </p>
        <p
          v-if="versionName(row) && versionName(row) !== documentFileName(row)"
          class="break-words text-meta text-text-muted"
        >
          {{ versionName(row) }}
        </p>
      </div>
    </template>

    <template #cell-doc_type="{ row }">
      {{ documentTypeLabel(row.doc_type) }}
    </template>

    <template #cell-owner="{ row }">
      <span class="inline-block min-w-24">{{ ownerName(row) }}</span>
    </template>

    <template #cell-size="{ row }">
      <span class="tabular-nums">
        {{ fileSize(row.current_version?.size_bytes) }}
      </span>
    </template>

    <template #cell-created_at="{ row }">
      <DateText :value="row.created_at" mode="datetime" />
    </template>

    <template #cell-job="{ row }">
      <div class="min-w-28">
        <JobStatusPill
          :status="latestJobs[row.id]?.status ?? null"
          :empty-text="jobEmptyText(row)"
        />
      </div>
    </template>

    <template #cell-actions="{ row }">
      <div class="flex flex-wrap items-center justify-end gap-1">
        <Button
          variant="ghost"
          size="sm"
          @click="emit('preview', row)"
        >
          <template #icon>
            <Eye :size="16" :stroke-width="1.75" aria-hidden="true" />
          </template>
          预览
        </Button>

        <Button
          v-if="isAdmin"
          variant="ghost"
          size="sm"
          :loading="downloadingId === row.id"
          @click="emit('download', row)"
        >
          <template #icon>
            <Download :size="16" :stroke-width="1.75" aria-hidden="true" />
          </template>
          下载
        </Button>

        <Button
          v-if="isAdmin"
          variant="ghost"
          size="sm"
          class="text-danger hover:bg-danger-soft hover:text-danger"
          @click="emit('delete', row)"
        >
          <template #icon>
            <Trash2 :size="16" :stroke-width="1.75" aria-hidden="true" />
          </template>
          删除
        </Button>
      </div>
    </template>

    <template #empty-action>
      <slot name="empty-action" />
    </template>
  </DataTable>
</template>
