<script setup lang="ts">
import { computed } from 'vue'

import FormField from '@/components/ui/FormField.vue'
import Input from '@/components/ui/Input.vue'
import Select from '@/components/ui/Select.vue'
import Textarea from '@/components/ui/Textarea.vue'
import type { PaymentFormDraft } from './payment-draft'
import { PAYMENT_METHOD_OPTIONS } from './payment-options'

const draft = defineModel<PaymentFormDraft>('draft', { required: true })

defineProps<{
  errors: Record<string, string>
}>()

const isTeacherAdvance = computed(
  () => draft.value.method === 'teacher_advance',
)

function set<K extends keyof PaymentFormDraft>(
  key: K,
  value: PaymentFormDraft[K],
): void {
  draft.value = { ...draft.value, [key]: value }
}
</script>

<template>
  <div class="grid gap-4 sm:grid-cols-2">
    <FormField id="payment-form-amount" label="付款金额（元）" required :error="errors.amount">
      <template #default="{ id, invalid, describedBy }">
        <Input
          :id="id"
          :model-value="draft.amount"
          inputmode="decimal"
          placeholder="0.00"
          :invalid="invalid"
          :aria-describedby="describedBy"
          @update:model-value="set('amount', $event)"
        />
      </template>
    </FormField>

    <FormField id="payment-form-paid-at" label="付款时间" required :error="errors.paid_at">
      <template #default="{ id, invalid, describedBy }">
        <Input
          :id="id"
          :model-value="draft.paidAt"
          type="datetime-local"
          :invalid="invalid"
          :aria-describedby="describedBy"
          @update:model-value="set('paidAt', $event)"
        />
      </template>
    </FormField>

    <FormField id="payment-form-method" label="付款方式" required :error="errors.method">
      <template #default="{ id, invalid }">
        <Select
          :id="id"
          :model-value="draft.method"
          :options="PAYMENT_METHOD_OPTIONS"
          placeholder="请选择付款方式"
          :invalid="invalid"
          @update:model-value="set('method', $event)"
        />
      </template>
    </FormField>

    <slot name="after-method" />

    <FormField
      v-if="isTeacherAdvance"
      id="payment-form-requested-at"
      label="代付时间"
      :error="errors.requested_at"
      class="sm:col-span-2"
    >
      <template #default="{ id, invalid, describedBy }">
        <Input
          :id="id"
          :model-value="draft.requestedAt"
          type="datetime-local"
          :invalid="invalid"
          :aria-describedby="describedBy"
          @update:model-value="set('requestedAt', $event)"
        />
      </template>
    </FormField>

    <FormField id="payment-form-txn-ref" label="流水号" class="sm:col-span-2">
      <template #default="{ id }">
        <Input
          :id="id"
          :model-value="draft.txnRef"
          @update:model-value="set('txnRef', $event)"
        />
      </template>
    </FormField>

    <FormField id="payment-form-note" label="备注" class="sm:col-span-2">
      <template #default="{ id }">
        <Textarea
          :id="id"
          :model-value="draft.note"
          :rows="3"
          @update:model-value="set('note', $event)"
        />
      </template>
    </FormField>
  </div>
</template>
