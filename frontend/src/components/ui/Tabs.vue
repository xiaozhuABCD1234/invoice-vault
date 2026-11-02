<script setup lang="ts">
import { computed } from 'vue'
import type { AcceptableValue } from 'reka-ui'
import { TabsContent, TabsList, TabsRoot, TabsTrigger } from 'reka-ui'

export interface TabItem {
  value: string
  label: string
}

const props = defineProps<{
  items: TabItem[]
}>()

const model = defineModel<string>()

const current = computed(() => model.value ?? props.items[0]?.value ?? '')

function updateValue(value: AcceptableValue): void {
  model.value = String(value)
}
</script>

<template>
  <TabsRoot :model-value="current" @update:model-value="updateValue">
    <TabsList class="inline-flex items-center gap-1 rounded-control bg-surface-muted p-1">
      <TabsTrigger
        v-for="item in items"
        :key="item.value"
        :value="item.value"
        class="inline-flex h-11 items-center justify-center whitespace-nowrap rounded-tag border border-transparent px-3 text-body font-medium text-text-secondary transition-colors duration-150 hover:text-text data-[state=active]:border-border data-[state=active]:bg-surface data-[state=active]:text-text sm:h-8"
      >
        {{ item.label }}
      </TabsTrigger>
    </TabsList>

    <TabsContent
      v-for="item in items"
      :key="item.value"
      :value="item.value"
      class="mt-4 focus-visible:outline-none"
    >
      <slot :name="item.value" />
    </TabsContent>
  </TabsRoot>
</template>
