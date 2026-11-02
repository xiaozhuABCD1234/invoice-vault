<script setup lang="ts">
import { useRouter } from 'vue-router'
import { Paperclip, Plus } from '@lucide/vue'

import DataTable from '@/components/common/DataTable.vue'
import DateText from '@/components/common/DateText.vue'
import MoneyText from '@/components/common/MoneyText.vue'
import StatusBadge from '@/components/common/StatusBadge.vue'
import Button from '@/components/ui/Button.vue'
import type { DataTableColumn, DataTableSort } from '@/components/common/data-table'
import type { Payment } from '@/api/types'
import { paymentMethodLabel } from './payment-options'

defineProps<{
  rows: Payment[]
  loading: boolean
  error: string | null
  sort: DataTableSort | null
}>()

const emit = defineEmits<{
  (event: 'update:sort', value: DataTableSort): void
  (event: 'retry'): void
  (event: 'create'): void
}>()

const router = useRouter()

const columns: DataTableColumn[] = [
  { key: 'payer_name', label: '付款人', width: 150, sortable: true },
  { key: 'method', label: '方式', width: 120, nowrap: true },
  { key: 'paid_at', label: '付款时间', width: 168, nowrap: true, sortable: true },
  {
    key: 'amount_cents',
    label: '金额',
    width: 132,
    align: 'right',
    nowrap: true,
    sortable: true,
  },
  {
    key: 'allocated_cents',
    label: '已分配',
    width: 132,
    align: 'right',
    nowrap: true,
  },
  { key: 'status', label: '状态', width: 124, align: 'center' },
  { key: 'evidence', label: '凭证', width: 92, align: 'center' },
  { key: 'actions', label: '操作', width: 96, align: 'center', fixed: 'right' },
]

function goDetail(id: number): void {
  void router.push('/payments/' + id)
}
</script>

<template>
  <DataTable
    :rows="rows"
    :columns="columns"
    :loading="loading"
    :error="error"
    :sort="sort"
    row-key="id"
    empty="暂无付款记录"
    empty-description="登记付款后，可在此处把款项分配到发票。"
    @update:sort="emit('update:sort', $event)"
    @retry="emit('retry')"
  >
    <template #cell-payer_name="{ row }">
      <RouterLink
        :to="'/payments/' + row.id"
        class="inline-flex min-h-11 items-center rounded-tag text-body text-primary hover:underline md:min-h-0"
      >
        {{ row.payer_name || '—' }}
      </RouterLink>
    </template>

    <template #cell-method="{ row }">
      {{ paymentMethodLabel(row.method) }}
    </template>

    <template #cell-paid_at="{ row }">
      <DateText :value="row.paid_at" mode="datetime" />
    </template>

    <template #cell-amount_cents="{ value }">
      <MoneyText :cents="Number(value)" strong />
    </template>

    <template #cell-allocated_cents="{ value }">
      <MoneyText :cents="Number(value)" />
    </template>

    <template #cell-status="{ value }">
      <StatusBadge kind="payment_status" :status="String(value)" />
    </template>

    <template #cell-evidence="{ row }">
      <span
        v-if="row.evidence_document_id !== null && row.evidence_document_id !== undefined"
        class="inline-flex items-center gap-1 text-meta text-text-secondary"
      >
        <Paperclip :size="16" :stroke-width="1.75" aria-hidden="true" />
        有
      </span>
      <span
        v-else
        class="inline-flex items-center gap-1 text-meta text-text-muted"
      >
        <Paperclip :size="16" :stroke-width="1.75" aria-hidden="true" />
        无
      </span>
    </template>

    <template #cell-actions="{ row }">
      <Button variant="ghost" size="sm" @click="goDetail(row.id)">查看</Button>
    </template>

    <template #empty-action>
      <Button variant="secondary" @click="emit('create')">
        <template #icon>
          <Plus :size="16" :stroke-width="1.75" aria-hidden="true" />
        </template>
        新建付款
      </Button>
    </template>
  </DataTable>
</template>
