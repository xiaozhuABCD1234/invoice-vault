<script setup lang="ts">
import { useRouter } from 'vue-router'
import { Upload } from '@lucide/vue'

import DataTable from '@/components/common/DataTable.vue'
import DateText from '@/components/common/DateText.vue'
import MoneyText from '@/components/common/MoneyText.vue'
import StatusBadge from '@/components/common/StatusBadge.vue'
import Button from '@/components/ui/Button.vue'
import type { DataTableColumn, DataTableSort } from '@/components/common/data-table'
import type { Invoice } from '@/api/types'

defineProps<{
  rows: Invoice[]
  loading: boolean
  error: string | null
  sort: DataTableSort | null
}>()

const emit = defineEmits<{
  (event: 'update:sort', value: DataTableSort): void
  (event: 'retry'): void
}>()

const router = useRouter()

const columns: DataTableColumn[] = [
  {
    key: 'invoice_number',
    label: '发票号码',
    width: 172,
    fixed: 'left',
    nowrap: true,
    sortable: true,
  },
  { key: 'issue_date', label: '开票日期', width: 116, nowrap: true, sortable: true },
  { key: 'seller_name', label: '店铺', width: 190, sortable: true },
  { key: 'category_name', label: '类别', width: 112 },
  { key: 'requester_name', label: '申购人', width: 104 },
  {
    key: 'total_cents',
    label: '价税合计',
    width: 132,
    align: 'right',
    nowrap: true,
    sortable: true,
  },
  {
    key: 'paid_cents',
    label: '已付',
    width: 128,
    align: 'right',
    nowrap: true,
    sortable: true,
  },
  { key: 'payment_status', label: '付款状态', width: 120, align: 'center' },
  { key: 'status', label: '发票状态', width: 112, align: 'center' },
]

function goUpload(): void {
  void router.push('/uploads')
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
    empty="暂无发票"
    empty-description="调整筛选条件，或先上传发票并完成审核。"
    @update:sort="emit('update:sort', $event)"
    @retry="emit('retry')"
  >
    <template #cell-invoice_number="{ row }">
      <RouterLink
        :to="'/invoices/' + row.id"
        class="inline-flex min-h-11 items-center rounded-tag font-mono text-body text-primary hover:underline md:min-h-0"
      >
        {{ row.invoice_number }}
      </RouterLink>
    </template>

    <template #cell-issue_date="{ row }">
      <DateText :value="row.issue_date" />
    </template>

    <template #cell-seller_name="{ row }">
      <span class="block break-words">{{ row.seller_name }}</span>
    </template>

    <template #cell-category_name="{ value }">
      {{ value ?? '—' }}
    </template>

    <template #cell-requester_name="{ value }">
      {{ value ?? '—' }}
    </template>

    <template #cell-total_cents="{ value }">
      <MoneyText :cents="Number(value)" strong />
    </template>

    <template #cell-paid_cents="{ value }">
      <MoneyText :cents="Number(value)" />
    </template>

    <template #cell-payment_status="{ value }">
      <StatusBadge kind="payment_status" :status="String(value)" />
    </template>

    <template #cell-status="{ value }">
      <StatusBadge kind="invoice_status" :status="String(value)" />
    </template>

    <template #empty-action>
      <Button variant="secondary" @click="goUpload">
        <template #icon>
          <Upload :size="16" :stroke-width="1.75" aria-hidden="true" />
        </template>
        去上传
      </Button>
    </template>
  </DataTable>
</template>
