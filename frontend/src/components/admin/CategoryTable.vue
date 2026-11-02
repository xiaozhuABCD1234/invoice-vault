<script setup lang="ts">
import { Pencil, Plus } from '@lucide/vue'

import type { Category } from '@/api/types'
import DataTable from '@/components/common/DataTable.vue'
import StatusBadge from '@/components/common/StatusBadge.vue'
import type { DataTableColumn } from '@/components/common/data-table'
import Button from '@/components/ui/Button.vue'
import { activeStatusLabel, categoryKindLabel } from './admin-labels'

withDefaults(
  defineProps<{
    rows: Category[]
    loading?: boolean
    error?: string | null
  }>(),
  {
    loading: false,
    error: null,
  },
)

const emit = defineEmits<{
  (event: 'edit', category: Category): void
  (event: 'create'): void
  (event: 'retry'): void
}>()

const columns: DataTableColumn[] = [
  { key: 'name', label: '名称', width: 220 },
  { key: 'kind', label: '类型', width: 110 },
  { key: 'sort_order', label: '排序', width: 90, align: 'right', nowrap: true },
  { key: 'is_active', label: '启用', width: 100, align: 'center' },
  { key: 'actions', label: '操作', width: 90, align: 'right', fixed: 'right' },
]
</script>

<template>
  <DataTable
    :rows="rows"
    :columns="columns"
    row-key="id"
    :loading="loading"
    :error="error"
    empty="暂无类别"
    empty-description="新建类别后可用于发票分类。"
    @retry="emit('retry')"
  >
    <template #cell-name="{ value }">
      <span class="font-medium">{{ value }}</span>
    </template>

    <template #cell-kind="{ value }">
      <span class="text-text-secondary">{{ categoryKindLabel(String(value)) }}</span>
    </template>

    <template #cell-sort_order="{ value }">
      <span class="tabular-nums">{{ value }}</span>
    </template>

    <template #cell-is_active="{ row }">
      <StatusBadge
        :tone="row.is_active ? 'success' : 'neutral'"
        :label="activeStatusLabel(row.is_active)"
      />
    </template>

    <template #cell-actions="{ row }">
      <div class="flex justify-end">
        <Button
          variant="secondary"
          size="sm"
          :aria-label="`编辑类别 ${row.name}`"
          @click="emit('edit', row)"
        >
          <template #icon>
            <Pencil :size="16" :stroke-width="1.75" aria-hidden="true" />
          </template>
          编辑
        </Button>
      </div>
    </template>

    <template #empty-action>
      <Button variant="secondary" size="sm" @click="emit('create')">
        <template #icon>
          <Plus :size="16" :stroke-width="1.75" aria-hidden="true" />
        </template>
        新建类别
      </Button>
    </template>
  </DataTable>
</template>
