<script setup lang="ts">
import { computed } from 'vue'

import ErrorState from '@/components/common/ErrorState.vue'
import PageHeader from '@/components/common/PageHeader.vue'
import DashboardChartCard from '@/components/dashboard/DashboardChartCard.vue'
import DashboardDateFilter from '@/components/dashboard/DashboardDateFilter.vue'
import DashboardGapsSection from '@/components/dashboard/DashboardGapsSection.vue'
import DashboardKpiGrid from '@/components/dashboard/DashboardKpiGrid.vue'
import {
  buildCategoryOption,
  buildMonthOption,
  buildPayerOption,
} from '@/components/dashboard/dashboard-charts'
import { useDashboard } from '@/composables/useDashboard'

const {
  dateFrom,
  dateTo,
  rangeError,
  summary,
  loading,
  error,
  reload,
} = useDashboard()

const totals = computed(() => summary.value?.totals ?? null)
const gaps = computed(() => summary.value?.gaps ?? null)
const categories = computed(() => summary.value?.by_category ?? [])
const months = computed(() => summary.value?.by_month ?? [])
const payers = computed(() => summary.value?.by_payer ?? [])

const categoryOption = computed(() =>
  categories.value.length > 0 ? buildCategoryOption(categories.value) : null,
)
const monthOption = computed(() =>
  months.value.length > 0 ? buildMonthOption(months.value) : null,
)
const payerOption = computed(() =>
  payers.value.length > 0 ? buildPayerOption(payers.value) : null,
)
</script>

<template>
  <div>
    <PageHeader
      title="仪表盘"
      description="汇总发票、付款与对账缺口，按日期范围筛选。"
    />

    <DashboardDateFilter
      v-model:date-from="dateFrom"
      v-model:date-to="dateTo"
      :error="rangeError"
    />

    <div
      v-if="error"
      class="mt-6 rounded-card border border-border bg-surface"
    >
      <ErrorState
        title="仪表盘数据加载失败"
        :message="error"
        @retry="reload"
      />
    </div>

    <template v-else>
      <div class="mt-6">
        <DashboardKpiGrid :totals="totals" :loading="loading" />
      </div>

      <div class="mt-6 grid gap-6 xl:grid-cols-2">
        <DashboardChartCard
          title="按类别开票金额"
          description="按金额降序，长名称悬停查看全文。"
          :option="categoryOption"
          :empty="!loading && categories.length === 0"
          :loading="loading"
          export-name="按类别开票金额"
          @retry="reload"
        />

        <DashboardChartCard
          title="按月份开票金额趋势"
          description="按开票月份汇总，横轴为 YYYY-MM。"
          :option="monthOption"
          :empty="!loading && months.length === 0"
          :loading="loading"
          export-name="按月份开票金额趋势"
          @retry="reload"
        />

        <DashboardChartCard
          class="xl:col-span-2"
          title="按付款人付款金额"
          description="按付款人汇总付款金额，金额降序。"
          :option="payerOption"
          :empty="!loading && payers.length === 0"
          :loading="loading"
          export-name="按付款人付款金额"
          height-class="h-72"
          @retry="reload"
        />
      </div>

      <DashboardGapsSection :gaps="gaps" :loading="loading" />
    </template>
  </div>
</template>
