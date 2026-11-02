<script setup lang="ts">
import { X } from '@lucide/vue'

import Button from '@/components/ui/Button.vue'
import FormField from '@/components/ui/FormField.vue'
import Input from '@/components/ui/Input.vue'

defineProps<{
  error?: string
}>()

const dateFrom = defineModel<string>('dateFrom', { default: '' })
const dateTo = defineModel<string>('dateTo', { default: '' })

function clear(): void {
  dateFrom.value = ''
  dateTo.value = ''
}
</script>

<template>
  <div class="rounded-card border border-border bg-surface p-4">
    <div class="flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-end">
      <div class="w-full sm:w-40">
        <FormField id="dashboard-date-from" label="开始日期">
          <template #default="{ id, describedBy }">
            <Input
              :id="id"
              v-model="dateFrom"
              type="date"
              :aria-describedby="describedBy"
            />
          </template>
        </FormField>
      </div>

      <div class="w-full sm:w-40">
        <FormField id="dashboard-date-to" label="结束日期">
          <template #default="{ id, describedBy }">
            <Input
              :id="id"
              v-model="dateTo"
              type="date"
              :aria-describedby="describedBy"
            />
          </template>
        </FormField>
      </div>

      <Button
        variant="ghost"
        size="sm"
        :disabled="dateFrom === '' && dateTo === ''"
        @click="clear"
      >
        <template #icon>
          <X :size="16" :stroke-width="1.75" aria-hidden="true" />
        </template>
        清除日期
      </Button>
    </div>

    <p
      v-if="error"
      class="mt-2 text-meta text-danger"
      role="alert"
      aria-live="polite"
    >
      {{ error }}
    </p>
  </div>
</template>
