<script setup lang="ts">
import { Download, Plus } from '@lucide/vue'

import type { ExportJob, ReportTemplate } from '@/api/types'
import DataTable from '@/components/common/DataTable.vue'
import DateText from '@/components/common/DateText.vue'
import StatusBadge from '@/components/common/StatusBadge.vue'
import type { DataTableColumn } from '@/components/common/data-table'
import Button from '@/components/ui/Button.vue'
import Pagination from '@/components/ui/Pagination.vue'
import Tooltip from '@/components/ui/Tooltip.vue'
import { exportFileName, templateName } from './report-fields'

withDefaults(
  defineProps<{
    rows: ExportJob[]
    templates: ReportTemplate[]
    loading?: boolean
    error?: string | null
    page: number
    pageSize: number
    total: number
    downloadingId?: number | null
  }>(),
  {
    loading: false,
    error: null,
    downloadingId: null,
  },
)

const emit = defineEmits<{
  (event: 'download', job: ExportJob): void
  (event: 'create'): void
  (event: 'retry'): void
  (event: 'update:page', page: number): void
  (event: 'update:pageSize', pageSize: number): void
}>()

const columns: DataTableColumn[] = [
  { key: 'id', label: '任务 ID', width: 90, nowrap: true },
  { key: 'template_id', label: '模板', width: 170 },
  { key: 'status', label: '状态', width: 100, align: 'center' },
  { key: 'created_at', label: '创建时间', width: 150, nowrap: true },
  { key: 'expires_at', label: '过期时间', width: 150, nowrap: true },
  { key: 'file_name', label: '文件名', width: 220 },
  { key: 'actions', label: '操作', width: 190, align: 'right', fixed: 'right' },
]
</script>

<template>
  <div class="min-w-0">
    <DataTable
      :rows="rows"
      :columns="columns"
      row-key="id"
      :loading="loading"
      :error="error"
      empty="暂无导出任务"
      empty-description="新建导出后，任务状态与下载入口会显示在这里。"
      @retry="emit('retry')"
    >
      <template #cell-id="{ value }">
        <span class="font-mono text-table text-text-secondary">#{{ value }}</span>
      </template>

      <template #cell-template_id="{ row }">
        <span class="truncate">
          {{ templateName(templates, row.template_id) }}
        </span>
      </template>

      <template #cell-status="{ value }">
        <StatusBadge kind="export_status" :status="String(value)" />
      </template>

      <template #cell-created_at="{ value }">
        <DateText :value="String(value)" mode="datetime" />
      </template>

      <template #cell-expires_at="{ value }">
        <DateText :value="String(value)" mode="datetime" />
      </template>

      <template #cell-file_name="{ row }">
        <Tooltip :content="exportFileName(row)">
          <span class="block max-w-48 truncate text-text-secondary">
            {{ exportFileName(row) }}
          </span>
        </Tooltip>
      </template>

      <template #cell-actions="{ row }">
        <div class="flex justify-end">
          <Button
            v-if="row.status === 'succeeded'"
            variant="secondary"
            size="sm"
            :loading="downloadingId === row.id"
            :aria-label="`下载导出文件 ${exportFileName(row)}`"
            @click="emit('download', row)"
          >
            <template #icon>
              <Download :size="16" :stroke-width="1.75" aria-hidden="true" />
            </template>
            下载
          </Button>

          <Tooltip
            v-else-if="row.status === 'failed'"
            :content="row.error_message || '导出失败'"
            :disabled="!row.error_message"
          >
            <span class="block max-w-48 truncate text-meta text-danger">
              {{ row.error_message || '导出失败' }}
            </span>
          </Tooltip>

          <span v-else class="text-meta text-text-muted">生成中…</span>
        </div>
      </template>

      <template #empty-action>
        <Button variant="secondary" size="sm" @click="emit('create')">
          <template #icon>
            <Plus :size="16" :stroke-width="1.75" aria-hidden="true" />
          </template>
          新建导出
        </Button>
      </template>
    </DataTable>

    <Pagination
      v-if="total > 0 && !error"
      class="mt-3 rounded-card border border-border bg-surface"
      :page="page"
      :page-size="pageSize"
      :total="total"
      @update:page="emit('update:page', $event)"
      @update:page-size="emit('update:pageSize', $event)"
    />
  </div>
</template>
