<script setup lang="ts">
import { Eye } from '@lucide/vue'

import type { AuditLog } from '@/api/types'
import DataTable from '@/components/common/DataTable.vue'
import DateText from '@/components/common/DateText.vue'
import type { DataTableColumn } from '@/components/common/data-table'
import Button from '@/components/ui/Button.vue'
import Pagination from '@/components/ui/Pagination.vue'
import { emptyText } from '@/lib/format'
import { auditActorLabel, auditEntityLabel } from './audit-format'

withDefaults(
  defineProps<{
    rows: AuditLog[]
    loading?: boolean
    error?: string | null
    page: number
    pageSize: number
    total: number
  }>(),
  {
    loading: false,
    error: null,
  },
)

const emit = defineEmits<{
  (event: 'detail', log: AuditLog): void
  (event: 'retry'): void
  (event: 'update:page', page: number): void
  (event: 'update:pageSize', pageSize: number): void
}>()

const columns: DataTableColumn[] = [
  { key: 'created_at', label: '时间', width: 150, nowrap: true },
  { key: 'actor', label: '操作人', width: 140 },
  { key: 'action', label: '动作', width: 190 },
  { key: 'entity', label: '实体类型 / ID', width: 180 },
  { key: 'ip', label: 'IP', width: 130, nowrap: true },
  { key: 'detail', label: '详情', width: 90, align: 'right', fixed: 'right' },
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
      empty="暂无审计日志"
      empty-description="调整筛选条件后重试，或等待新的操作记录。"
      @retry="emit('retry')"
    >
      <template #cell-created_at="{ value }">
        <DateText :value="String(value)" mode="datetime" />
      </template>

      <template #cell-actor="{ row }">
        <span class="block truncate">{{ auditActorLabel(row) }}</span>
      </template>

      <template #cell-action="{ value }">
        <span class="font-mono text-table">{{ value }}</span>
      </template>

      <template #cell-entity="{ row }">
        <span class="font-mono text-table">{{ auditEntityLabel(row) }}</span>
      </template>

      <template #cell-ip="{ value }">
        <span class="font-mono text-table text-text-secondary">
          {{ emptyText(value) }}
        </span>
      </template>

      <template #cell-detail="{ row }">
        <div class="flex justify-end">
          <Button
            variant="secondary"
            size="sm"
            :aria-label="`查看审计详情 ${row.action}`"
            @click="emit('detail', row)"
          >
            <template #icon>
              <Eye :size="16" :stroke-width="1.75" aria-hidden="true" />
            </template>
            详情
          </Button>
        </div>
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
