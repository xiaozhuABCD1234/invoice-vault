<script setup lang="ts">
import { Eye, EyeOff, RotateCcw } from '@lucide/vue'

import Button from '@/components/ui/Button.vue'
import DataTable from '@/components/common/DataTable.vue'
import MoneyText from '@/components/common/MoneyText.vue'
import StatusBadge from '@/components/common/StatusBadge.vue'
import Tooltip from '@/components/ui/Tooltip.vue'
import type { DataTableColumn } from '@/components/common/data-table'
import type { ReconciliationIssue } from '@/api/types'
import { issueTypeLabel } from './reconciliation-options'

defineProps<{
  rows: ReconciliationIssue[]
  loading: boolean
  error: string | null
  isAdmin: boolean
}>()

const emit = defineEmits<{
  (event: 'view', issue: ReconciliationIssue): void
  (event: 'ignore', issue: ReconciliationIssue): void
  (event: 'unignore', issue: ReconciliationIssue): void
  (event: 'retry'): void
}>()

const columns: DataTableColumn[] = [
  { key: 'type', label: '类型', width: 112, nowrap: true },
  { key: 'title', label: '标题', width: 168 },
  { key: 'detail', label: '详情', width: 220 },
  { key: 'amount_cents', label: '金额', width: 112, align: 'right', nowrap: true },
  { key: 'severity', label: '严重程度', width: 92, align: 'center' },
  { key: 'ignored', label: '忽略状态', width: 88, align: 'center' },
  { key: 'note', label: '备注', width: 128 },
  { key: 'actions', label: '操作', width: 200, align: 'center', fixed: 'right' },
]

function canView(issue: ReconciliationIssue): boolean {
  return issue.entity_type === 'invoice' || issue.entity_type === 'payment'
}


</script>

<template>
  <DataTable
    :rows="rows"
    :columns="columns"
    :loading="loading"
    :error="error"
    row-key="id"
    empty="暂无对账问题"
    empty-description="调整筛选条件，或忽略已处理的问题后查看。"
    @retry="emit('retry')"
  >
    <template #cell-type="{ value }">
      {{ issueTypeLabel(value ? String(value) : null) }}
    </template>

    <template #cell-title="{ value }">
      <span class="block break-words">{{ value ?? '—' }}</span>
    </template>

    <template #cell-detail="{ value }">
      <Tooltip
        v-if="value && String(value).length > 28"
        :content="String(value)"
      >
        <span class="line-clamp-2 block break-words">{{ value }}</span>
      </Tooltip>
      <span v-else class="block break-words">{{ value ?? '—' }}</span>
    </template>

    <template #cell-amount_cents="{ value }">
      <MoneyText
        :cents="typeof value === 'number' ? value : null"
      />
    </template>

    <template #cell-severity="{ value }">
      <StatusBadge
        :tone="value === 'error' ? 'danger' : 'warning'"
        :label="value === 'error' ? '错误' : '警告'"
      />
    </template>

    <template #cell-ignored="{ value }">
      <StatusBadge
        :tone="value ? 'neutral' : 'warning'"
        :label="value ? '已忽略' : '未忽略'"
      />
    </template>

    <template #cell-note="{ value }">
      <span class="block break-words">{{ value ?? '—' }}</span>
    </template>

    <template #cell-actions="{ row }">
      <div class="flex flex-nowrap items-center justify-center gap-1">
        <Button
          v-if="canView(row)"
          variant="ghost"
          size="sm"
          :aria-label="'查看问题 ' + row.title"
          @click="emit('view', row)"
        >
          <template #icon>
            <Eye :size="16" :stroke-width="1.75" aria-hidden="true" />
          </template>
          查看
        </Button>

        <Button
          v-if="isAdmin && !row.ignored"
          variant="ghost"
          size="sm"
          :aria-label="'忽略问题 ' + row.title"
          @click="emit('ignore', row)"
        >
          <template #icon>
            <EyeOff :size="16" :stroke-width="1.75" aria-hidden="true" />
          </template>
          忽略
        </Button>

        <Button
          v-if="isAdmin && row.ignored"
          variant="ghost"
          size="sm"
          :aria-label="'取消忽略 ' + row.title"
          @click="emit('unignore', row)"
        >
          <template #icon>
            <RotateCcw :size="16" :stroke-width="1.75" aria-hidden="true" />
          </template>
          取消忽略
        </Button>
      </div>

      <span
        v-if="!canView(row) && !isAdmin"
        class="text-text-muted"
      >
        —
      </span>
    </template>
  </DataTable>
</template>
