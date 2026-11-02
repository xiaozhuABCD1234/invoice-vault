<script setup lang="ts">
import { computed } from 'vue'
import { Pencil, Undo2 } from '@lucide/vue'

import DataTable from '@/components/common/DataTable.vue'
import DateText from '@/components/common/DateText.vue'
import MoneyText from '@/components/common/MoneyText.vue'
import StatusBadge from '@/components/common/StatusBadge.vue'
import Button from '@/components/ui/Button.vue'
import type { DataTableColumn } from '@/components/common/data-table'
import type { AllocationRow } from './allocation'

const props = defineProps<{
  rows: AllocationRow[]
}>()

const emit = defineEmits<{
  (event: 'edit', row: AllocationRow): void
  (event: 'reverse', row: AllocationRow): void
}>()

const hasManageable = computed(() =>
  props.rows.some((row) => row.can_manage),
)

const columns = computed<DataTableColumn[]>(() => {
  const base: DataTableColumn[] = [
    { key: 'invoice_number', label: '发票号码', width: 172, nowrap: true },
    { key: 'seller_name', label: '店铺', width: 180 },
    {
      key: 'amount_cents',
      label: '分配金额',
      width: 132,
      align: 'right',
      nowrap: true,
    },
    { key: 'status', label: '状态', width: 108, align: 'center' },
    { key: 'created_at', label: '创建时间', width: 168, nowrap: true },
    { key: 'note', label: '备注', width: 180 },
  ]
  if (hasManageable.value) {
    base.push({
      key: 'actions',
      label: '操作',
      width: 156,
      align: 'center',
      fixed: 'right',
    })
  }
  return base
})
</script>

<template>
  <DataTable
    :rows="rows"
    :columns="columns"
    row-key="id"
    empty="暂无分配"
    empty-description="该付款还未分配到任何发票。"
  >
    <template #cell-invoice_number="{ row }">
      <RouterLink
        v-if="row.invoice_number"
        :to="'/invoices/' + row.invoice_id"
        class="inline-flex min-h-11 items-center rounded-tag font-mono text-body text-primary hover:underline md:min-h-0"
      >
        {{ row.invoice_number }}
      </RouterLink>
      <span v-else class="font-mono text-text-muted">#{{ row.invoice_id }}</span>
    </template>

    <template #cell-seller_name="{ value }">
      <span class="block break-words">{{ value ?? '—' }}</span>
    </template>

    <template #cell-amount_cents="{ value }">
      <MoneyText :cents="Number(value)" strong />
    </template>

    <template #cell-status="{ value }">
      <StatusBadge kind="allocation_status" :status="String(value)" />
    </template>

    <template #cell-created_at="{ value }">
      <DateText :value="String(value)" mode="datetime" />
    </template>

    <template #cell-note="{ value }">
      <span class="block break-words">{{ value ?? '—' }}</span>
    </template>

    <template #cell-actions="{ row }">
      <div v-if="row.can_manage" class="flex items-center justify-center gap-1">
        <Button
          variant="ghost"
          size="sm"
          :aria-label="'编辑分配 ' + row.id"
          @click="emit('edit', row)"
        >
          <template #icon>
            <Pencil :size="16" :stroke-width="1.75" aria-hidden="true" />
          </template>
          编辑
        </Button>
        <Button
          v-if="row.status === 'active'"
          variant="ghost"
          size="sm"
          :aria-label="'撤销分配 ' + row.id"
          @click="emit('reverse', row)"
        >
          <template #icon>
            <Undo2 :size="16" :stroke-width="1.75" aria-hidden="true" />
          </template>
          撤销
        </Button>
      </div>
      <span v-else class="text-text-muted">—</span>
    </template>
  </DataTable>
</template>
