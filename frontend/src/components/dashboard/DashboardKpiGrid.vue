<script setup lang="ts">
import { ArrowLeftRight, Paperclip, ReceiptText, Wallet } from '@lucide/vue'

import type { DashboardTotals } from '@/api/types'
import MoneyText from '@/components/common/MoneyText.vue'
import DashboardKpiCard from './DashboardKpiCard.vue'

withDefaults(
  defineProps<{
    totals: DashboardTotals | null
    loading?: boolean
  }>(),
  {
    loading: false,
  },
)
</script>

<template>
  <div class="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
    <DashboardKpiCard
      label="发票数"
      :icon="ReceiptText"
      :loading="loading"
    >
      <template #value>
        <p class="text-kpi font-semibold tabular-nums text-text">
          {{ totals?.invoice_count ?? '—' }}
        </p>
      </template>
      <template #meta>
        <span>当前日期范围内的有效发票</span>
      </template>
    </DashboardKpiCard>

    <DashboardKpiCard
      label="开票总额"
      :icon="Wallet"
      :loading="loading"
    >
      <template #value>
        <MoneyText
          :cents="totals?.invoice_total_cents"
          strong
          align="left"
          class="text-kpi"
        />
      </template>
      <template #meta>
        <div class="space-y-0.5">
          <div class="flex items-center justify-between gap-3">
            <span>已付</span>
            <MoneyText :cents="totals?.paid_cents" />
          </div>
          <div class="flex items-center justify-between gap-3">
            <span>未付</span>
            <MoneyText :cents="totals?.unpaid_cents" />
          </div>
        </div>
      </template>
    </DashboardKpiCard>

    <DashboardKpiCard
      label="付款总额"
      :icon="ArrowLeftRight"
      :loading="loading"
    >
      <template #value>
        <MoneyText
          :cents="totals?.payment_total_cents"
          strong
          align="left"
          class="text-kpi"
        />
      </template>
      <template #meta>
        <span>全部付款记录合计</span>
      </template>
    </DashboardKpiCard>

    <DashboardKpiCard
      label="缺凭证数"
      :icon="Paperclip"
      :loading="loading"
    >
      <template #value>
        <p class="text-kpi font-semibold tabular-nums text-text">
          {{ totals?.missing_evidence_count ?? '—' }}
        </p>
      </template>
      <template #meta>
        <span>需补充付款凭证的记录</span>
      </template>
    </DashboardKpiCard>
  </div>
</template>
