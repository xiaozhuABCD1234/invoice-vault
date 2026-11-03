<script setup lang="ts">
import { computed } from 'vue'
import { RotateCcw } from '@lucide/vue'

import type {
  ExtractionSettingsRevision,
  ExtractionSettingsRevisionAction,
} from '@/api/types'
import DataTable from '@/components/common/DataTable.vue'
import StatusBadge from '@/components/common/StatusBadge.vue'
import type { DataTableColumn } from '@/components/common/data-table'
import Button from '@/components/ui/Button.vue'
import { formatDateTime } from '@/lib/date'
import type { StatusTone } from '@/lib/status'
import { changedFieldLabels, settingsActionLabel } from './extraction-settings'

interface HistoryRow extends ExtractionSettingsRevision {
  changed: string
}

const props = withDefaults(
  defineProps<{
    items: ExtractionSettingsRevision[]
    loading?: boolean
    error?: string | null
  }>(),
  {
    loading: false,
    error: null,
  },
)

const emit = defineEmits<{
  (event: 'rollback', revision: ExtractionSettingsRevision): void
  (event: 'retry'): void
}>()

const columns: DataTableColumn[] = [
  { key: 'created_at', label: '时间', width: 150, nowrap: true },
  { key: 'action', label: '类型', width: 100 },
  { key: 'actor', label: '操作人', width: 110 },
  { key: 'changed', label: '变更内容' },
  { key: 'revision', label: '版本', width: 80, align: 'right', nowrap: true },
  { key: 'actions', label: '操作', width: 100, align: 'right', fixed: 'right' },
]

const rows = computed<HistoryRow[]>(() =>
  props.items.map((item, index) => {
    const previous = props.items[index + 1] ?? null
    const labels = changedFieldLabels(
      item.values,
      previous?.values ?? null,
      item.action,
    )
    return {
      ...item,
      changed: labels.length > 0 ? labels.join('、') : '无变化',
    }
  }),
)

const latestId = computed<number | null>(() => props.items[0]?.id ?? null)

function actionTone(action: ExtractionSettingsRevisionAction): StatusTone {
  if (action === 'rollback') return 'warning'
  if (action === 'reset') return 'neutral'
  return 'info'
}
</script>

<template>
  <DataTable
    :rows="rows"
    :columns="columns"
    row-key="id"
    :min-width="820"
    :loading="loading"
    :error="error"
    empty="暂无变更记录"
    empty-description="保存设置或恢复默认后，这里会记录每次版本，可随时回滚。"
    @retry="emit('retry')"
  >
    <template #cell-created_at="{ row }">
      <span class="tabular-nums text-text-secondary">
        {{ formatDateTime(row.created_at) }}
      </span>
    </template>

    <template #cell-action="{ row }">
      <StatusBadge
        :tone="actionTone(row.action)"
        :label="settingsActionLabel(row.action)"
      />
    </template>

    <template #cell-actor="{ row }">
      <span class="text-text-secondary">{{ row.actor_name ?? '—' }}</span>
    </template>

    <template #cell-changed="{ value }">
      <span class="text-text-secondary">{{ value }}</span>
    </template>

    <template #cell-revision="{ row }">
      <span class="tabular-nums text-text-muted">#{{ row.id }}</span>
    </template>

    <template #cell-actions="{ row }">
      <div class="flex justify-end">
        <Button
          variant="secondary"
          size="sm"
          :disabled="row.id === latestId || loading"
          :aria-label="'回滚到版本 ' + row.id"
          @click="emit('rollback', row)"
        >
          <template #icon>
            <RotateCcw :size="16" :stroke-width="1.75" aria-hidden="true" />
          </template>
          回滚
        </Button>
      </div>
    </template>
  </DataTable>
</template>
