<script setup lang="ts">
import { computed } from 'vue'

import FormField from '@/components/ui/FormField.vue'
import Input from '@/components/ui/Input.vue'
import Select from '@/components/ui/Select.vue'
import { useUserOptions } from '@/composables/useReferenceOptions'
import {
  UNSET_SELECT_VALUE,
  fromSelectValue,
  toSelectValue,
} from '@/composables/selectValue'

defineProps<{
  error?: string
}>()

const payerUserId = defineModel<string>('userId', { default: '' })
const payerName = defineModel<string>('name', { default: '' })

const {
  users,
  loading,
  error: optionsError,
  reload,
} = useUserOptions()

const payerModel = computed({
  get: () => toSelectValue(payerUserId.value),
  set: (value: string) => {
    payerUserId.value = fromSelectValue(value)
  },
})

const payerOptions = computed(() => [
  { value: UNSET_SELECT_VALUE, label: '外部付款人（手填名称）' },
  ...users.value
    .filter((user) => user.is_active)
    .map((user) => ({ value: String(user.id), label: user.display_name })),
])
</script>

<template>
  <div class="space-y-3">
    <FormField
      id="payment-payer"
      label="付款人"
      required
      :error="error"
    >
      <template #default="{ id, invalid }">
        <Select
          :id="id"
          v-model="payerModel"
          :options="payerOptions"
          :invalid="invalid"
          :disabled="loading"
        />
      </template>
    </FormField>

    <FormField
      v-if="payerUserId === ''"
      id="payment-payer-name"
      label="外部付款人名称"
    >
      <template #default="{ id }">
        <Input
          :id="id"
          :model-value="payerName"
          placeholder="例如：供应商代收"
          @update:model-value="payerName = $event"
        />
      </template>
    </FormField>

    <p v-if="optionsError" class="flex flex-wrap items-center gap-2 text-meta text-danger" role="alert">
      {{ optionsError }}
      <button
        type="button"
        class="font-medium text-primary hover:underline"
        @click="reload"
      >
        重试
      </button>
    </p>
  </div>
</template>
