<script setup lang="ts">
import PageHeader from '@/components/common/PageHeader.vue'
import Pagination from '@/components/ui/Pagination.vue'
import InvoiceFilters from '@/components/invoice/InvoiceFilters.vue'
import InvoiceTable from '@/components/invoice/InvoiceTable.vue'
import { useInvoiceList } from '@/composables/useInvoiceList'
import { useCategoryOptions } from '@/composables/useReferenceOptions'

const {
  state,
  filters,
  sort,
  hasFilters,
  rows,
  total,
  loading,
  error,
  load,
  setFilters,
  resetFilters,
  onSortChange,
  goToPage,
  setPageSize,
} = useInvoiceList()

const {
  categories,
  loading: categoriesLoading,
  error: categoriesError,
  reload: reloadCategories,
} = useCategoryOptions()
</script>

<template>
  <div class="space-y-4">
    <PageHeader
      title="发票"
      description="按发票号、店铺、状态与日期查询发票，进入详情维护明细与付款分配。"
    />

    <InvoiceFilters
      :filters="filters"
      :categories="categories"
      :categories-loading="categoriesLoading"
      :categories-error="categoriesError"
      :has-filters="hasFilters"
      @update="setFilters"
      @reset="resetFilters"
      @retry-categories="reloadCategories"
    />

    <div>
      <InvoiceTable
        :rows="rows"
        :loading="loading"
        :error="error || null"
        :sort="sort"
        @update:sort="onSortChange"
        @retry="load"
      />
      <Pagination
        v-if="!loading && !error && total > 0"
        class="mt-3 rounded-card border border-border bg-surface"
        :page="state.page"
        :page-size="state.page_size"
        :total="total"
        @update:page="goToPage"
        @update:page-size="setPageSize"
      />
    </div>
  </div>
</template>
