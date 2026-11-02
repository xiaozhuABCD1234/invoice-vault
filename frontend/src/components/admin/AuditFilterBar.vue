<script setup lang="ts">
import { RotateCw, Search } from '@lucide/vue'

import Button from '@/components/ui/Button.vue'
import FormField from '@/components/ui/FormField.vue'
import Input from '@/components/ui/Input.vue'

defineProps<{
  error?: string
}>()

const action = defineModel<string>('action', { default: '' })
const entityType = defineModel<string>('entityType', { default: '' })
const entityId = defineModel<string>('entityId', { default: '' })
const actorId = defineModel<string>('actorId', { default: '' })
const dateFrom = defineModel<string>('dateFrom', { default: '' })
const dateTo = defineModel<string>('dateTo', { default: '' })

const emit = defineEmits<{
  (event: 'submit'): void
  (event: 'reset'): void
}>()
</script>

<template>
  <form
    class="rounded-card border border-border bg-surface p-4"
    @submit.prevent="emit('submit')"
  >
    <div class="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
      <FormField id="audit-filter-action" label="动作">
        <template #default="{ id, describedBy }">
          <Input
            :id="id"
            v-model="action"
            :aria-describedby="describedBy"
            placeholder="如 document.create"
          />
        </template>
      </FormField>

      <FormField id="audit-filter-entity-type" label="实体类型">
        <template #default="{ id, describedBy }">
          <Input
            :id="id"
            v-model="entityType"
            :aria-describedby="describedBy"
            placeholder="如 invoice"
          />
        </template>
      </FormField>

      <FormField id="audit-filter-entity-id" label="实体 ID">
        <template #default="{ id, describedBy }">
          <Input
            :id="id"
            v-model="entityId"
            type="text"
            :aria-describedby="describedBy"
            placeholder="数字或字符串 ID"
          />
        </template>
      </FormField>

      <FormField id="audit-filter-actor-id" label="操作人 ID">
        <template #default="{ id, describedBy }">
          <Input
            :id="id"
            v-model="actorId"
            type="text"
            inputmode="numeric"
            :aria-describedby="describedBy"
            placeholder="数字 ID"
          />
        </template>
      </FormField>

      <FormField id="audit-filter-date-from" label="开始日期">
        <template #default="{ id, describedBy }">
          <Input
            :id="id"
            v-model="dateFrom"
            type="date"
            :aria-describedby="describedBy"
          />
        </template>
      </FormField>

      <FormField id="audit-filter-date-to" label="结束日期">
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

    <p
      v-if="error"
      class="mt-3 text-meta text-danger"
      role="alert"
      aria-live="polite"
    >
      {{ error }}
    </p>

    <div class="mt-3 flex flex-wrap items-center gap-2">
      <Button type="submit" variant="secondary">
        <template #icon>
          <Search :size="18" :stroke-width="1.75" aria-hidden="true" />
        </template>
        查询
      </Button>
      <Button variant="ghost" @click="emit('reset')">
        <template #icon>
          <RotateCw :size="18" :stroke-width="1.75" aria-hidden="true" />
        </template>
        重置
      </Button>
    </div>
  </form>
</template>
