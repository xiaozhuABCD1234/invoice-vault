<script setup lang="ts">
import { emptyText } from '@/lib/format'

export interface DetailField {
  key: string
  label: string
  value?: string | number | null
  /** 长文本（备注、链接）占满整行。 */
  span?: boolean
}

defineProps<{
  fields: DetailField[]
}>()
</script>

<template>
  <dl class="grid gap-x-6 gap-y-4 sm:grid-cols-2 xl:grid-cols-3">
    <div
      v-for="field in fields"
      :key="field.key"
      :class="field.span ? 'sm:col-span-2 xl:col-span-3' : ''"
    >
      <dt class="text-meta text-text-muted">{{ field.label }}</dt>
      <dd class="mt-1 break-words text-body text-text">
        <slot :name="field.key" :field="field">
          {{ emptyText(field.value) }}
        </slot>
      </dd>
    </div>
  </dl>
</template>
