<script setup lang="ts">
import { computed } from 'vue'
import { RotateCcw } from '@lucide/vue'

import type { InvoiceListFilters } from '@/composables/useInvoiceList'
import {
  UNSET_SELECT_VALUE,
  fromSelectValue,
  toSelectValue,
  withUnsetOption,
} from '@/composables/selectValue'
import Button from '@/components/ui/Button.vue'
import FormField from '@/components/ui/FormField.vue'
import Input from '@/components/ui/Input.vue'
import Select from '@/components/ui/Select.vue'
import type { Category } from '@/api/types'
import {
  INVOICE_PAYMENT_STATUS_OPTIONS,
  INVOICE_STATUS_OPTIONS,
} from './invoice-options'

const props = defineProps<{
  filters: InvoiceListFilters
  categories: Category[]
  categoriesLoading?: boolean
  categoriesError?: string
  hasFilters: boolean
}>()

const emit = defineEmits<{
  (event: 'update', patch: Partial<InvoiceListFilters>): void
  (event: 'reset'): void
  (event: 'retry-categories'): void
}>()

const statusOptions = withUnsetOption(INVOICE_STATUS_OPTIONS, '全部状态')
const paymentStatusOptions = withUnsetOption(
  INVOICE_PAYMENT_STATUS_OPTIONS,
  '全部付款状态',
)

const statusModel = computed({
  get: () => toSelectValue(props.filters.status),
  set: (value: string) => update('status', fromSelectValue(value)),
})
const paymentStatusModel = computed({
  get: () => toSelectValue(props.filters.payment_status),
  set: (value: string) => update('payment_status', fromSelectValue(value)),
})
const categoryModel = computed({
  get: () => toSelectValue(props.filters.category_id),
  set: (value: string) => update('category_id', fromSelectValue(value)),
})

const categoryOptions = computed(() => [
  { value: UNSET_SELECT_VALUE, label: '全部类别' },
  ...props.categories
    .filter((category) => category.is_active)
    .map((category) => ({ value: String(category.id), label: category.name })),
])

function update<K extends keyof InvoiceListFilters>(
  key: K,
  value: InvoiceListFilters[K],
): void {
  emit('update', { [key]: value } as Partial<InvoiceListFilters>)
}
</script>

<template>
  <section
    aria-label="发票筛选"
    class="rounded-card border border-border bg-surface p-4"
  >
    <div class="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4 wide:grid-cols-7">
      <FormField id="invoice-filter-q" label="关键词">
        <template #default="{ id, describedBy }">
          <Input
            :id="id"
            :model-value="filters.q"
            type="search"
            placeholder="发票号 / 店铺"
            :aria-describedby="describedBy"
            @update:model-value="update('q', $event)"
          />
        </template>
      </FormField>

      <FormField id="invoice-filter-status" label="发票状态">
        <template #default="{ id }">
          <Select
            :id="id"
            v-model="statusModel"
            :options="statusOptions"
          />
        </template>
      </FormField>

      <FormField id="invoice-filter-payment" label="付款状态">
        <template #default="{ id }">
          <Select
            :id="id"
            v-model="paymentStatusModel"
            :options="paymentStatusOptions"
          />
        </template>
      </FormField>

      <FormField id="invoice-filter-category" label="类别">
        <template #default="{ id }">
          <Select
            :id="id"
            v-model="categoryModel"
            :options="categoryOptions"
            :disabled="categoriesLoading"
          />
        </template>
      </FormField>

      <FormField id="invoice-filter-from" label="开票日期起">
        <template #default="{ id }">
          <Input
            :id="id"
            :model-value="filters.date_from"
            type="date"
            @update:model-value="update('date_from', $event)"
          />
        </template>
      </FormField>

      <FormField id="invoice-filter-to" label="开票日期止">
        <template #default="{ id }">
          <Input
            :id="id"
            :model-value="filters.date_to"
            type="date"
            @update:model-value="update('date_to', $event)"
          />
        </template>
      </FormField>

      <div class="flex items-end">
        <Button
          variant="secondary"
          class="w-full"
          :disabled="!hasFilters"
          @click="emit('reset')"
        >
          <template #icon>
            <RotateCcw :size="16" :stroke-width="1.75" aria-hidden="true" />
          </template>
          重置筛选
        </Button>
      </div>
    </div>

    <p
      v-if="categoriesError"
      class="mt-3 flex flex-wrap items-center gap-2 text-meta text-danger"
      role="alert"
    >
      {{ categoriesError }}
      <button
        type="button"
        class="font-medium text-primary underline-offset-2 hover:underline"
        @click="emit('retry-categories')"
      >
        重试
      </button>
    </p>
  </section>
</template>
