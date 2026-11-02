<script setup lang="ts">
import { computed } from 'vue'

import FormField from '@/components/ui/FormField.vue'
import Input from '@/components/ui/Input.vue'
import Select from '@/components/ui/Select.vue'
import { useCategoryOptions, useUserOptions } from '@/composables/useReferenceOptions'
import {
  UNSET_SELECT_VALUE,
  fromSelectValue,
  toSelectValue,
} from '@/composables/selectValue'
import type { InvoiceFormDraft } from './invoice-draft'
import { INVOICE_FORM_OPTIONS, INVOICE_STATUS_OPTIONS } from './invoice-options'

const draft = defineModel<InvoiceFormDraft>('draft', { required: true })

defineProps<{
  errors: Record<string, string>
}>()

const {
  categories,
  loading: categoriesLoading,
  error: categoriesError,
  reload: reloadCategories,
} = useCategoryOptions()
const {
  users,
  loading: usersLoading,
  error: usersError,
  reload: reloadUsers,
} = useUserOptions()

const categoryOptions = computed(() => [
  { value: UNSET_SELECT_VALUE, label: '请选择类别' },
  ...categories.value
    .filter((category) => category.is_active)
    .map((category) => ({ value: String(category.id), label: category.name })),
])

const userOptions = computed(() => [
  { value: UNSET_SELECT_VALUE, label: '未指定' },
  ...users.value
    .filter((user) => user.is_active)
    .map((user) => ({ value: String(user.id), label: user.display_name })),
])

function set<K extends keyof InvoiceFormDraft>(
  key: K,
  value: InvoiceFormDraft[K],
): void {
  draft.value = { ...draft.value, [key]: value }
}

const categoryModel = computed({
  get: () => toSelectValue(draft.value.category_id),
  set: (value: string) => set('category_id', fromSelectValue(value)),
})
const requesterModel = computed({
  get: () => toSelectValue(draft.value.requester_id),
  set: (value: string) => set('requester_id', fromSelectValue(value)),
})
const ownerModel = computed({
  get: () => toSelectValue(draft.value.owner_id),
  set: (value: string) => set('owner_id', fromSelectValue(value)),
})
</script>

<template>
  <div class="space-y-4">
    <div class="grid gap-4 sm:grid-cols-2">
      <FormField id="invoice-edit-number" label="发票号码" required :error="errors.invoice_number">
        <template #default="{ id, invalid, describedBy }">
          <Input
            :id="id"
            :model-value="draft.invoice_number"
            :invalid="invalid"
            :aria-describedby="describedBy"
            @update:model-value="set('invoice_number', $event)"
          />
        </template>
      </FormField>

      <FormField id="invoice-edit-date" label="开票日期" required :error="errors.issue_date">
        <template #default="{ id, invalid, describedBy }">
          <Input
            :id="id"
            :model-value="draft.issue_date"
            type="date"
            :invalid="invalid"
            :aria-describedby="describedBy"
            @update:model-value="set('issue_date', $event)"
          />
        </template>
      </FormField>

      <FormField id="invoice-edit-seller" label="销方" required :error="errors.seller_name">
        <template #default="{ id, invalid, describedBy }">
          <Input
            :id="id"
            :model-value="draft.seller_name"
            :invalid="invalid"
            :aria-describedby="describedBy"
            @update:model-value="set('seller_name', $event)"
          />
        </template>
      </FormField>

      <FormField id="invoice-edit-buyer" label="购方">
        <template #default="{ id }">
          <Input
            :id="id"
            :model-value="draft.buyer_name"
            @update:model-value="set('buyer_name', $event)"
          />
        </template>
      </FormField>

      <FormField id="invoice-edit-category" label="类别" required :error="errors.category_id">
        <template #default="{ id, invalid }">
          <Select
            :id="id"
            v-model="categoryModel"
            :options="categoryOptions"
            :invalid="invalid"
            :disabled="categoriesLoading"
          />
        </template>
      </FormField>

      <FormField id="invoice-edit-form" label="发票形式">
        <template #default="{ id }">
          <Select
            :id="id"
            :model-value="draft.invoice_form"
            :options="INVOICE_FORM_OPTIONS"
            @update:model-value="set('invoice_form', $event)"
          />
        </template>
      </FormField>

      <FormField id="invoice-edit-requester" label="申购人">
        <template #default="{ id }">
          <Select
            :id="id"
            v-model="requesterModel"
            :options="userOptions"
            :disabled="usersLoading"
          />
        </template>
      </FormField>

      <FormField id="invoice-edit-owner" label="负责人">
        <template #default="{ id }">
          <Select
            :id="id"
            v-model="ownerModel"
            :options="userOptions"
            :disabled="usersLoading"
          />
        </template>
      </FormField>

      <FormField id="invoice-edit-status" label="发票状态">
        <template #default="{ id }">
          <Select
            :id="id"
            :model-value="draft.status"
            :options="INVOICE_STATUS_OPTIONS"
            @update:model-value="set('status', $event)"
          />
        </template>
      </FormField>
    </div>

    <p v-if="categoriesError" class="flex flex-wrap items-center gap-2 text-meta text-danger" role="alert">
      {{ categoriesError }}
      <button type="button" class="font-medium text-primary hover:underline" @click="reloadCategories">
        重试
      </button>
    </p>
    <p v-if="usersError" class="flex flex-wrap items-center gap-2 text-meta text-danger" role="alert">
      {{ usersError }}
      <button type="button" class="font-medium text-primary hover:underline" @click="reloadUsers">
        重试
      </button>
    </p>
  </div>
</template>
