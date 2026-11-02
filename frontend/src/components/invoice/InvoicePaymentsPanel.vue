<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'

import DataTable from '@/components/common/DataTable.vue'
import DateText from '@/components/common/DateText.vue'
import MoneyText from '@/components/common/MoneyText.vue'
import StatusBadge from '@/components/common/StatusBadge.vue'
import Button from '@/components/ui/Button.vue'
import { paymentMethodLabel } from '@/components/payment/payment-options'
import type { DataTableColumn } from '@/components/common/data-table'
import type { InvoicePaymentAllocation } from '@/api/types'

const props = defineProps<{
  allocations: InvoicePaymentAllocation[]
  loading: boolean
  error: string | null
  paidCents: number
  unpaidCents: number
}>()

const emit = defineEmits<{
  (event: 'retry'): void
}>()

const router = useRouter()

const columns: DataTableColumn[] = [
  { key: 'payer_name', label: '付款人', width: 140 },
  { key: 'method', label: '方式', width: 120, nowrap: true },
  { key: 'paid_at', label: '付款时间', width: 168, nowrap: true },
  {
    key: 'amount_cents',
    label: '分配金额',
    width: 136,
    align: 'right',
    nowrap: true,
  },
  { key: 'status', label: '分配状态', width: 116, align: 'center' },
]

const activeCount = computed(
  () => props.allocations.filter((item) => item.status === 'active').length,
)

function goPayments(): void {
  void router.push('/payments')
}
</script>

<template>
  <section class="space-y-3" aria-label="发票付款记录">
    <dl class="grid grid-cols-1 gap-4 rounded-card border border-border bg-surface p-4 sm:grid-cols-3">
      <div>
        <dt class="text-meta text-text-muted">已付</dt>
        <dd class="mt-1">
          <MoneyText :cents="paidCents" strong />
        </dd>
      </div>
      <div>
        <dt class="text-meta text-text-muted">未付</dt>
        <dd class="mt-1">
          <MoneyText :cents="unpaidCents" strong />
        </dd>
      </div>
      <div>
        <dt class="text-meta text-text-muted">生效分配</dt>
        <dd class="mt-1 text-body tabular-nums text-text">{{ activeCount }} 笔</dd>
      </div>
    </dl>

    <DataTable
      :rows="allocations"
      :columns="columns"
      :loading="loading"
      :error="error"
      row-key="id"
      empty="暂无付款记录"
      empty-description="该发票还未收到任何付款分配。"
      @retry="emit('retry')"
    >
      <template #cell-payer_name="{ row }">
        {{ row.payment?.payer_name ?? '—' }}
      </template>

      <template #cell-method="{ row }">
        {{ paymentMethodLabel(row.payment?.method) }}
      </template>

      <template #cell-paid_at="{ row }">
        <DateText :value="row.payment?.paid_at" mode="datetime" />
      </template>

      <template #cell-amount_cents="{ value }">
        <MoneyText :cents="Number(value)" />
      </template>

      <template #cell-status="{ value }">
        <StatusBadge kind="allocation_status" :status="String(value)" />
      </template>

      <template #empty-action>
        <Button variant="secondary" @click="goPayments">去付款</Button>
      </template>
    </DataTable>
  </section>
</template>
