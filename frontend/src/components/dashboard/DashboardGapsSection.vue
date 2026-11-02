<script setup lang="ts">
import { Paperclip, ReceiptText, Wallet } from '@lucide/vue'
import { RouterLink } from 'vue-router'

import type { DashboardGaps } from '@/api/types'
import DashboardGapCard from './DashboardGapCard.vue'

withDefaults(
  defineProps<{
    gaps: DashboardGaps | null
    loading?: boolean
  }>(),
  {
    loading: false,
  },
)
</script>

<template>
  <section class="mt-6 space-y-3">
    <div class="flex flex-wrap items-end justify-between gap-2">
      <div>
        <h2 class="text-section font-semibold text-text">对账缺口</h2>
        <p class="text-body text-text-secondary">
          点击缺口卡片前往对账页处理。
        </p>
      </div>
      <RouterLink
        to="/reconciliation"
        class="inline-flex min-h-11 items-center text-body font-medium text-primary transition-colors duration-150 hover:text-primary-hover md:min-h-0"
      >
        前往对账
      </RouterLink>
    </div>

    <div class="grid gap-4 sm:grid-cols-3">
      <DashboardGapCard
        label="未付清发票"
        hint="已生效但付款未分配满"
        :count="gaps?.invoice_unpaid"
        :icon="ReceiptText"
        to="/reconciliation"
        :loading="loading"
      />
      <DashboardGapCard
        label="未分配付款"
        hint="付款金额尚未核销到发票"
        :count="gaps?.payment_unallocated"
        :icon="Wallet"
        to="/reconciliation"
        :loading="loading"
      />
      <DashboardGapCard
        label="缺凭证"
        hint="非老师代付但缺少付款凭证"
        :count="gaps?.missing_evidence"
        :icon="Paperclip"
        to="/reconciliation"
        :loading="loading"
      />
    </div>
  </section>
</template>
