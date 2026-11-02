<script setup lang="ts">
import { computed } from 'vue'

import DateText from '@/components/common/DateText.vue'
import { emptyText } from '@/lib/format'
import type { Invoice } from '@/api/types'
import DetailFields, { type DetailField } from './DetailFields.vue'
import { formatTaxRateBp } from './invoice-format'

const props = defineProps<{
  invoice: Invoice
}>()

const fields = computed<DetailField[]>(() => [
  { key: 'invoice_code', label: '发票代码', value: props.invoice.invoice_code },
  { key: 'invoice_type', label: '发票类型', value: props.invoice.invoice_type },
  { key: 'seller_tax_id', label: '销方税号', value: props.invoice.seller_tax_id },
  { key: 'buyer_tax_id', label: '购方税号', value: props.invoice.buyer_tax_id },
  { key: 'currency', label: '币种', value: props.invoice.currency },
  { key: 'tax_rate', label: '税率', value: formatTaxRateBp(props.invoice.tax_rate_bp) },
  { key: 'created_at', label: '创建时间' },
  { key: 'updated_at', label: '更新时间' },
  { key: 'confirmed_by', label: '确认人 ID', value: emptyText(props.invoice.confirmed_by) },
  { key: 'confirmed_at', label: '确认时间' },
  {
    key: 'source_document_id',
    label: '源文件 ID',
    value: emptyText(props.invoice.source_document_id),
  },
  {
    key: 'extraction_job_id',
    label: '抽取任务 ID',
    value: emptyText(props.invoice.extraction_job_id),
  },
])
</script>

<template>
  <section
    class="rounded-card border border-border bg-surface p-4 md:p-6"
    aria-label="发票附加信息"
  >
    <DetailFields :fields="fields">
      <template #created_at>
        <DateText :value="invoice.created_at" mode="datetime" />
      </template>
      <template #updated_at>
        <DateText :value="invoice.updated_at" mode="datetime" />
      </template>
      <template #confirmed_at>
        <DateText :value="invoice.confirmed_at" mode="datetime" />
      </template>
    </DetailFields>
  </section>
</template>
