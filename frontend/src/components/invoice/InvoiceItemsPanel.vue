<script setup lang="ts">
import { computed } from 'vue'
import { TriangleAlert } from '@lucide/vue'

import DataTable from '@/components/common/DataTable.vue'
import MoneyText from '@/components/common/MoneyText.vue'
import { formatCents } from '@/lib/money'
import type { DataTableColumn } from '@/components/common/data-table'
import type { InvoiceItem } from '@/api/types'
import { formatUnitPrice } from './invoice-format'

const props = defineProps<{
  items: InvoiceItem[]
  totalCents: number
}>()

const columns: DataTableColumn[] = [
  { key: 'name', label: '名称', width: 220 },
  { key: 'quantity', label: '数量', width: 96, align: 'right', nowrap: true },
  {
    key: 'unit_price_millis',
    label: '单价',
    width: 132,
    align: 'right',
    nowrap: true,
  },
  { key: 'amount_cents', label: '金额', width: 132, align: 'right', nowrap: true },
  { key: 'note', label: '备注', width: 200 },
]

const itemsTotalCents = computed(() =>
  props.items.reduce((sum, item) => sum + item.amount_cents, 0),
)

const differenceCents = computed(
  () => props.totalCents - itemsTotalCents.value,
)

const hasDifference = computed(() => Math.abs(differenceCents.value) > 1)
</script>

<template>
  <section class="space-y-3" aria-label="发票明细">
    <div
      v-if="hasDifference"
      class="flex items-start gap-2 rounded-card border border-warning bg-warning-soft p-3 text-body text-warning"
      role="status"
    >
      <TriangleAlert
        class="mt-1 shrink-0"
        :size="18"
        :stroke-width="1.75"
        aria-hidden="true"
      />
      <p>
        明细合计 {{ formatCents(itemsTotalCents) }} 与发票总额
        {{ formatCents(totalCents) }} 相差
        {{ formatCents(Math.abs(differenceCents)) }}，请核对明细。
      </p>
    </div>

    <DataTable
      :rows="items"
      :columns="columns"
      row-key="id"
      empty="暂无明细"
      empty-description="该发票没有登记商品明细。"
    >
      <template #cell-quantity="{ value }">
        <span class="tabular-nums">{{ value ?? '—' }}</span>
      </template>

      <template #cell-unit_price_millis="{ value }">
        <span class="tabular-nums">{{ formatUnitPrice(Number(value)) }}</span>
      </template>

      <template #cell-amount_cents="{ value }">
        <MoneyText :cents="Number(value)" />
      </template>
    </DataTable>

    <div class="flex flex-col gap-2 rounded-card border border-border bg-surface px-4 py-3 text-body sm:flex-row sm:items-center sm:justify-between">
      <span class="text-text-secondary">
        明细合计
        <MoneyText :cents="itemsTotalCents" strong class="inline-block" />
      </span>
      <span class="text-text-secondary">
        发票总额
        <MoneyText :cents="totalCents" strong class="inline-block" />
      </span>
    </div>
  </section>
</template>
