<script setup lang="ts">
import MoneyText from '@/components/common/MoneyText.vue'
import ErrorState from '@/components/common/ErrorState.vue'
import Skeleton from '@/components/ui/Skeleton.vue'
import type { ReconciliationSummary } from '@/api/types'

defineProps<{
  summary: ReconciliationSummary | null
  loading: boolean
  error: string | null
  issueCount: number
}>()

const emit = defineEmits<{
  (event: 'retry'): void
}>()
</script>

<template>
  <section aria-label="对账汇总">
    <div
      v-if="loading"
      class="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4"
      role="status"
      aria-live="polite"
    >
      <div
        v-for="index in 4"
        :key="index"
        class="rounded-card border border-border bg-surface p-4"
      >
        <Skeleton class="h-3 w-24" />
        <Skeleton class="mt-3 h-8 w-32" />
        <Skeleton class="mt-2 h-3 w-40" />
      </div>
      <span class="sr-only">正在加载对账汇总</span>
    </div>

    <div
      v-else-if="error"
      class="rounded-card border border-border bg-surface"
    >
      <ErrorState
        title="对账汇总加载失败"
        :message="error"
        @retry="emit('retry')"
      />
    </div>

    <dl
      v-else-if="summary"
      class="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4"
    >
      <div class="rounded-card border border-border bg-surface p-4">
        <dt class="text-meta text-text-muted">开票总额</dt>
        <dd class="mt-1">
          <MoneyText
            :cents="summary.invoice_total_cents"
            strong
            align="left"
            class="text-kpi"
          />
        </dd>
        <p class="mt-1 text-meta text-text-secondary">
          {{ summary.invoice_count }} 张发票
        </p>
      </div>

      <div class="rounded-card border border-border bg-surface p-4">
        <dt class="text-meta text-text-muted">已付 / 未付</dt>
        <dd class="mt-1">
          <MoneyText
            :cents="summary.invoice_paid_cents"
            strong
            align="left"
            class="text-kpi"
          />
        </dd>
        <p class="mt-1 flex flex-wrap items-center gap-1 text-meta text-text-secondary">
          未付
          <MoneyText
            :cents="summary.invoice_unpaid_cents"
            align="left"
            class="inline-block"
          />
        </p>
      </div>

      <div class="rounded-card border border-border bg-surface p-4">
        <dt class="text-meta text-text-muted">付款总额</dt>
        <dd class="mt-1">
          <MoneyText
            :cents="summary.payment_total_cents"
            strong
            align="left"
            class="text-kpi"
          />
        </dd>
        <p class="mt-1 text-meta text-text-secondary">
          {{ summary.payment_count }} 笔 · 已分配
          <MoneyText
            :cents="summary.payment_allocated_cents"
            align="left"
            class="inline-block"
          />
        </p>
      </div>

      <div class="rounded-card border border-border bg-surface p-4">
        <dt class="text-meta text-text-muted">未分配 / 缺口</dt>
        <dd class="mt-1">
          <MoneyText
            :cents="summary.payment_unallocated_cents"
            strong
            align="left"
            class="text-kpi"
          />
        </dd>
        <p class="mt-1 text-meta text-text-secondary">
          共 {{ issueCount }} 个对账问题
        </p>
      </div>
    </dl>
  </section>
</template>
