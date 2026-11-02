<script setup lang="ts">
import { ref } from 'vue'
import { Plus } from '@lucide/vue'

import PageHeader from '@/components/common/PageHeader.vue'
import Button from '@/components/ui/Button.vue'
import Pagination from '@/components/ui/Pagination.vue'
import PaymentCreateDialog from '@/components/payment/PaymentCreateDialog.vue'
import PaymentFilters from '@/components/payment/PaymentFilters.vue'
import PaymentTable from '@/components/payment/PaymentTable.vue'
import { usePaymentList } from '@/composables/usePaymentList'

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
} = usePaymentList()

const creating = ref(false)

function onCreated(): void {
  void load()
}
</script>

<template>
  <div class="space-y-4">
    <PageHeader
      title="付款"
      description="登记付款记录，并把款项分配到对应发票。"
    >
      <template #actions>
        <Button @click="creating = true">
          <template #icon>
            <Plus :size="18" :stroke-width="1.75" aria-hidden="true" />
          </template>
          新建付款
        </Button>
      </template>
    </PageHeader>

    <PaymentFilters
      :filters="filters"
      :has-filters="hasFilters"
      @update="setFilters"
      @reset="resetFilters"
    />

    <div>
      <PaymentTable
        :rows="rows"
        :loading="loading"
        :error="error || null"
        :sort="sort"
        @update:sort="onSortChange"
        @retry="load"
        @create="creating = true"
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

    <PaymentCreateDialog v-model:open="creating" @created="onCreated" />
  </div>
</template>
