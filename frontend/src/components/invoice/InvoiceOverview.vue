<script setup lang="ts">
import { computed } from 'vue'
import { ExternalLink } from '@lucide/vue'

import MoneyText from '@/components/common/MoneyText.vue'
import DateText from '@/components/common/DateText.vue'
import type { Invoice } from '@/api/types'
import DetailFields, { type DetailField } from './DetailFields.vue'
import { invoiceFormLabel } from './invoice-options'

const props = defineProps<{
  invoice: Invoice
}>()

const fields = computed<DetailField[]>(() => [
  { key: 'seller_name', label: '销方', value: props.invoice.seller_name },
  { key: 'buyer_name', label: '购方', value: props.invoice.buyer_name },
  { key: 'issue_date', label: '开票日期' },
  { key: 'category_name', label: '类别', value: props.invoice.category_name },
  { key: 'requester_name', label: '申购人', value: props.invoice.requester_name },
  { key: 'owner_name', label: '负责人', value: props.invoice.owner_name },
  {
    key: 'invoice_form',
    label: '发票形式',
    value: invoiceFormLabel(props.invoice.invoice_form),
  },
])

const detailFields = computed<DetailField[]>(() => [
  { key: 'note', label: '备注', value: props.invoice.note, span: true },
  {
    key: 'product_url',
    label: '商品链接',
    value: props.invoice.product_url,
    span: true,
  },
])

const unpaidCents = computed(() =>
  Math.max(0, props.invoice.total_cents - props.invoice.paid_cents),
)
</script>

<template>
  <section
    class="rounded-card border border-border bg-surface p-4 md:p-6"
    aria-labelledby="invoice-overview-title"
  >
    <h2
      id="invoice-overview-title"
      class="text-heading font-semibold text-text"
    >
      概览
    </h2>

    <div class="mt-4">
      <DetailFields :fields="fields">
        <template #issue_date>
          <DateText :value="invoice.issue_date" />
        </template>
      </DetailFields>
    </div>

    <dl class="mt-6 grid grid-cols-2 gap-4 border-t border-border pt-4 md:grid-cols-3 xl:grid-cols-5">
      <div>
        <dt class="text-meta text-text-muted">价税合计</dt>
        <dd class="mt-1">
          <MoneyText :cents="invoice.total_cents" strong align="left" />
        </dd>
      </div>
      <div>
        <dt class="text-meta text-text-muted">不含税</dt>
        <dd class="mt-1">
          <MoneyText :cents="invoice.amount_ex_tax_cents" align="left" />
        </dd>
      </div>
      <div>
        <dt class="text-meta text-text-muted">税额</dt>
        <dd class="mt-1">
          <MoneyText :cents="invoice.tax_cents" align="left" />
        </dd>
      </div>
      <div>
        <dt class="text-meta text-text-muted">已付</dt>
        <dd class="mt-1">
          <MoneyText :cents="invoice.paid_cents" align="left" />
        </dd>
      </div>
      <div>
        <dt class="text-meta text-text-muted">未付</dt>
        <dd class="mt-1">
          <MoneyText :cents="unpaidCents" strong align="left" />
        </dd>
      </div>
    </dl>

    <div class="mt-6 border-t border-border pt-4">
      <DetailFields :fields="detailFields">
        <template #product_url>
          <a
            v-if="invoice.product_url"
            :href="invoice.product_url"
            target="_blank"
            rel="noopener noreferrer"
            class="inline-flex max-w-full items-center gap-1 break-all text-primary hover:underline"
          >
            <span class="break-all">{{ invoice.product_url }}</span>
            <ExternalLink
              class="shrink-0"
              :size="16"
              :stroke-width="1.75"
              aria-hidden="true"
            />
          </a>
          <span v-else class="text-text-muted">—</span>
        </template>
        <template #note="{ field }">
          <span v-if="field.value" class="whitespace-pre-line">{{ field.value }}</span>
          <span v-else class="text-text-muted">—</span>
        </template>
      </DetailFields>
    </div>
  </section>
</template>
