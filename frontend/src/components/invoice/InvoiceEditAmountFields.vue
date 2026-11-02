<script setup lang="ts">
import FormField from '@/components/ui/FormField.vue'
import Input from '@/components/ui/Input.vue'
import Textarea from '@/components/ui/Textarea.vue'
import type { InvoiceFormDraft } from './invoice-draft'

const draft = defineModel<InvoiceFormDraft>('draft', { required: true })

defineProps<{
  errors: Record<string, string>
}>()

function set<K extends keyof InvoiceFormDraft>(
  key: K,
  value: InvoiceFormDraft[K],
): void {
  draft.value = { ...draft.value, [key]: value }
}
</script>

<template>
  <div class="space-y-4">
    <div class="grid gap-4 sm:grid-cols-3">
      <FormField id="invoice-edit-ex-tax" label="不含税金额（元）" required :error="errors.amount_ex_tax">
        <template #default="{ id, invalid, describedBy }">
          <Input
            :id="id"
            :model-value="draft.amount_ex_tax"
            inputmode="decimal"
            :invalid="invalid"
            :aria-describedby="describedBy"
            @update:model-value="set('amount_ex_tax', $event)"
          />
        </template>
      </FormField>

      <FormField id="invoice-edit-tax" label="税额（元）" required :error="errors.tax">
        <template #default="{ id, invalid, describedBy }">
          <Input
            :id="id"
            :model-value="draft.tax"
            inputmode="decimal"
            :invalid="invalid"
            :aria-describedby="describedBy"
            @update:model-value="set('tax', $event)"
          />
        </template>
      </FormField>

      <FormField id="invoice-edit-total" label="价税合计（元）" required :error="errors.total">
        <template #default="{ id, invalid, describedBy }">
          <Input
            :id="id"
            :model-value="draft.total"
            inputmode="decimal"
            :invalid="invalid"
            :aria-describedby="describedBy"
            @update:model-value="set('total', $event)"
          />
        </template>
      </FormField>
    </div>

    <FormField id="invoice-edit-product-url" label="商品链接">
      <Input
        id="invoice-edit-product-url"
        :model-value="draft.product_url"
        placeholder="https://"
        @update:model-value="set('product_url', $event)"
      />
    </FormField>

    <FormField id="invoice-edit-note" label="备注">
      <Textarea
        id="invoice-edit-note"
        :model-value="draft.note"
        :rows="3"
        @update:model-value="set('note', $event)"
      />
    </FormField>
  </div>
</template>
