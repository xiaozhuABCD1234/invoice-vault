<script setup lang="ts">
import { computed } from 'vue'
import { RotateCcw } from '@lucide/vue'

import Button from '@/components/ui/Button.vue'
import { fromSelectValue, toSelectValue } from '@/composables/selectValue'
import Select from '@/components/ui/Select.vue'
import { ISSUE_TYPE_OPTIONS } from './reconciliation-options'

const props = defineProps<{
  type: string
  includeIgnored: boolean
}>()

const emit = defineEmits<{
  (event: 'update:type', value: string): void
  (event: 'update:includeIgnored', value: boolean): void
  (event: 'reset'): void
}>()

const typeModel = computed({
  get: () => toSelectValue(props.type),
  set: (value: string) => emit('update:type', fromSelectValue(value)),
})

function onIncludeIgnoredChange(event: Event): void {
  const target = event.target
  if (!(target instanceof HTMLInputElement)) return
  emit('update:includeIgnored', target.checked)
}
</script>

<template>
  <section
    aria-label="对账筛选"
    class="rounded-card border border-border bg-surface p-4"
  >
    <div class="flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-end">
      <div class="w-full sm:w-56">
        <label
          for="reconciliation-type"
          class="mb-1 block text-body font-medium text-text"
        >
          问题类型
        </label>
        <Select
          id="reconciliation-type"
          v-model="typeModel"
          :options="ISSUE_TYPE_OPTIONS"
        />
      </div>

      <label
        for="reconciliation-include-ignored"
        class="inline-flex min-h-11 items-center gap-2 text-body text-text md:min-h-9"
      >
        <input
          id="reconciliation-include-ignored"
          type="checkbox"
          class="size-4 rounded-tag border-border accent-primary"
          :checked="includeIgnored"
          @change="onIncludeIgnoredChange"
        />
        显示已忽略
      </label>

      <Button
        variant="secondary"
        :disabled="type === '' && !includeIgnored"
        @click="emit('reset')"
      >
        <template #icon>
          <RotateCcw :size="16" :stroke-width="1.75" aria-hidden="true" />
        </template>
        重置筛选
      </Button>
    </div>
  </section>
</template>
