<script setup lang="ts">
import { computed } from 'vue'
import { Paperclip, TriangleAlert } from '@lucide/vue'

import DateText from '@/components/common/DateText.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import FilePreview from '@/components/common/FilePreview.vue'
import MoneyText from '@/components/common/MoneyText.vue'
import StatusBadge from '@/components/common/StatusBadge.vue'
import DetailFields, {
  type DetailField,
} from '@/components/invoice/DetailFields.vue'
import type { Payment } from '@/api/types'
import { paymentMethodLabel } from './payment-options'

const props = defineProps<{
  payment: Payment
}>()

const fields = computed<DetailField[]>(() => [
  { key: 'payer_name', label: '付款人', value: props.payment.payer_name },
  {
    key: 'method',
    label: '付款方式',
    value: paymentMethodLabel(props.payment.method),
  },
  { key: 'paid_at', label: '付款时间' },
  { key: 'status', label: '付款状态' },
  { key: 'external_txn_ref', label: '流水号', value: props.payment.external_txn_ref },
  { key: 'requested_at', label: '代付时间' },
  { key: 'note', label: '备注', value: props.payment.note, span: true },
])

const unallocatedCents = computed(() =>
  Math.max(0, props.payment.amount_cents - props.payment.allocated_cents),
)

const activeAllocations = computed(
  () =>
    (props.payment.allocations ?? []).filter(
      (allocation) => allocation.status === 'active',
    ).length,
)
</script>

<template>
  <section
    class="rounded-card border border-border bg-surface p-4 md:p-6"
    aria-labelledby="payment-overview-title"
  >
    <h2
      id="payment-overview-title"
      class="text-heading font-semibold text-text"
    >
      概览
    </h2>

    <div class="mt-4">
      <DetailFields :fields="fields">
        <template #paid_at>
          <DateText :value="payment.paid_at" mode="datetime" />
        </template>
        <template #requested_at>
          <DateText :value="payment.requested_at" mode="datetime" />
        </template>
        <template #status>
          <StatusBadge kind="payment_status" :status="payment.status" />
        </template>
        <template #note="{ field }">
          <span v-if="field.value" class="whitespace-pre-line">{{ field.value }}</span>
          <span v-else class="text-text-muted">—</span>
        </template>
      </DetailFields>
    </div>

    <dl class="mt-6 grid grid-cols-1 gap-4 border-t border-border pt-4 sm:grid-cols-3">
      <div>
        <dt class="text-meta text-text-muted">付款金额</dt>
        <dd class="mt-1">
          <MoneyText :cents="payment.amount_cents" strong align="left" />
        </dd>
      </div>
      <div>
        <dt class="text-meta text-text-muted">已分配</dt>
        <dd class="mt-1">
          <MoneyText :cents="payment.allocated_cents" align="left" />
        </dd>
      </div>
      <div>
        <dt class="text-meta text-text-muted">未分配</dt>
        <dd class="mt-1">
          <MoneyText :cents="unallocatedCents" strong align="left" />
        </dd>
      </div>
    </dl>

    <p class="mt-3 text-meta text-text-secondary">
      生效分配 {{ activeAllocations }} 笔
    </p>

    <div
      v-if="payment.status === 'partially_allocated'"
      class="mt-4 flex items-start gap-2 rounded-control border border-warning bg-warning-soft p-3 text-body text-warning"
      role="status"
    >
      <TriangleAlert
        class="mt-1 shrink-0"
        :size="16"
        :stroke-width="1.75"
        aria-hidden="true"
      />
      <p class="flex flex-wrap items-center gap-1">
        该付款仅部分分配到发票，仍有
        <MoneyText :cents="unallocatedCents" align="left" class="inline-block" />
        未分配。
      </p>
    </div>

    <div class="mt-6 border-t border-border pt-4">
      <h3 class="mb-3 flex items-center gap-2 text-heading font-semibold text-text">
        <Paperclip :size="18" :stroke-width="1.75" aria-hidden="true" />
        付款凭证
      </h3>
      <FilePreview
        v-if="payment.evidence_document_id !== null && payment.evidence_document_id !== undefined"
        :document-id="payment.evidence_document_id"
        :height="420"
      />
      <EmptyState
        v-else
        title="暂无付款凭证"
        description="该付款未上传凭证，对账时会被标记为缺少凭证。"
      />
    </div>
  </section>
</template>
