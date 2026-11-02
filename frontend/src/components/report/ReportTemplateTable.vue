<script setup lang="ts">
import { Pencil, Plus, Trash2 } from '@lucide/vue'

import type { ReportTemplate } from '@/api/types'
import DataTable from '@/components/common/DataTable.vue'
import type { DataTableColumn } from '@/components/common/data-table'
import Badge from '@/components/ui/Badge.vue'
import Button from '@/components/ui/Button.vue'

withDefaults(
  defineProps<{
    templates: ReportTemplate[]
    loading?: boolean
    error?: string | null
    deletingId?: number | null
  }>(),
  {
    loading: false,
    error: null,
    deletingId: null,
  },
)

const emit = defineEmits<{
  (event: 'create'): void
  (event: 'edit', template: ReportTemplate): void
  (event: 'delete', template: ReportTemplate): void
  (event: 'retry'): void
}>()

const columns: DataTableColumn[] = [
  { key: 'name', label: '模板名称', width: 220 },
  { key: 'column_count', label: '列数', width: 80, align: 'center' },
  { key: 'is_shared', label: '共享', width: 90, align: 'center' },
  { key: 'created_by', label: '创建者', width: 100 },
  { key: 'actions', label: '操作', width: 190, align: 'right', fixed: 'right' },
]
</script>

<template>
  <DataTable
    :rows="templates"
    :columns="columns"
    row-key="id"
    :loading="loading"
    :error="error"
    empty="暂无报表模板"
    empty-description="新建模板后可复用列顺序与筛选条件。"
    @retry="emit('retry')"
  >
    <template #cell-name="{ row, value }">
      <div class="flex min-w-0 items-center gap-2">
        <span class="truncate font-medium">{{ value }}</span>
        <Badge v-if="row.id === 0" tone="neutral" :dot="false">内置</Badge>
      </div>
    </template>

    <template #cell-column_count="{ row }">
      <span class="tabular-nums">{{ row.columns.length }}</span>
    </template>

    <template #cell-is_shared="{ row }">
      <Badge :tone="row.is_shared ? 'info' : 'neutral'" :dot="false">
        {{ row.is_shared ? '共享' : '私有' }}
      </Badge>
    </template>

    <template #cell-created_by="{ row }">
      <span class="whitespace-nowrap text-text-secondary">
        用户 #{{ row.created_by }}
      </span>
    </template>

    <template #cell-actions="{ row }">
      <div class="flex justify-end gap-1">
        <span
          v-if="row.id === 0"
          class="inline-flex min-h-8 items-center text-meta text-text-muted"
        >
          内置模板不可修改
        </span>
        <template v-else>
          <Button
            variant="secondary"
            size="sm"
            :aria-label="`编辑模板 ${row.name}`"
            @click="emit('edit', row)"
          >
            <template #icon>
              <Pencil :size="16" :stroke-width="1.75" aria-hidden="true" />
            </template>
            编辑
          </Button>
          <Button
            variant="ghost"
            size="sm"
            class="text-danger hover:bg-danger-soft hover:text-danger"
            :disabled="deletingId === row.id"
            :aria-label="`删除模板 ${row.name}`"
            @click="emit('delete', row)"
          >
            <template #icon>
              <Trash2 :size="16" :stroke-width="1.75" aria-hidden="true" />
            </template>
            删除
          </Button>
        </template>
      </div>
    </template>

    <template #empty-action>
      <Button variant="secondary" size="sm" @click="emit('create')">
        <template #icon>
          <Plus :size="16" :stroke-width="1.75" aria-hidden="true" />
        </template>
        新建模板
      </Button>
    </template>
  </DataTable>
</template>
