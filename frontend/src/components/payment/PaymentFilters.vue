<script setup lang="ts">
import { computed } from 'vue'
import { RotateCcw } from '@lucide/vue'

import type { PaymentListFilters } from '@/composables/usePaymentList'
import {
  fromSelectValue,
  toSelectValue,
  withUnsetOption,
} from '@/composables/selectValue'
import Button from '@/components/ui/Button.vue'
import FormField from '@/components/ui/FormField.vue'
import Input from '@/components/ui/Input.vue'
import Select from '@/components/ui/Select.vue'
import {
  PAYMENT_METHOD_OPTIONS,
  PAYMENT_STATUS_OPTIONS,
} from './payment-options'

const props = defineProps<{
  filters: PaymentListFilters
  hasFilters: boolean
}>()

const emit = defineEmits<{
  (event: 'update', patch: Partial<PaymentListFilters>): void
  (event: 'reset'): void
}>()

const statusOptions = withUnsetOption(PAYMENT_STATUS_OPTIONS, '全部状态')
const methodOptions = withUnsetOption(PAYMENT_METHOD_OPTIONS, '全部方式')

const statusModel = computed({
  get: () => toSelectValue(props.filters.status),
  set: (value: string) => update('status', fromSelectValue(value)),
})
const methodModel = computed({
  get: () => toSelectValue(props.filters.method),
  set: (value: string) => update('method', fromSelectValue(value)),
})

function update<K extends keyof PaymentListFilters>(
  key: K,
  value: PaymentListFilters[K],
): void {
  emit('update', { [key]: value } as Partial<PaymentListFilters>)
}
</script>

<template>
  <section
    aria-label="付款筛选"
    class="rounded-card border border-border bg-surface p-4"
  >
    <div class="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3 wide:grid-cols-6">
      <FormField id="payment-filter-q" label="关键词">
        <template #default="{ id, describedBy }">
          <Input
            :id="id"
            :model-value="filters.q"
            type="search"
            placeholder="付款人 / 流水号"
            :aria-describedby="describedBy"
            @update:model-value="update('q', $event)"
          />
        </template>
      </FormField>

      <FormField id="payment-filter-status" label="状态">
        <template #default="{ id }">
          <Select
            :id="id"
            v-model="statusModel"
            :options="statusOptions"
          />
        </template>
      </FormField>

      <FormField id="payment-filter-method" label="方式">
        <template #default="{ id }">
          <Select
            :id="id"
            v-model="methodModel"
            :options="methodOptions"
          />
        </template>
      </FormField>

      <FormField id="payment-filter-from" label="付款日期起">
        <template #default="{ id }">
          <Input
            :id="id"
            :model-value="filters.date_from"
            type="date"
            @update:model-value="update('date_from', $event)"
          />
        </template>
      </FormField>

      <FormField id="payment-filter-to" label="付款日期止">
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
  </section>
</template>
