<script setup lang="ts">
import { computed, type Component } from 'vue'
import { Inbox } from '@lucide/vue'

const props = withDefaults(
  defineProps<{
    title?: string
    description?: string
    icon?: Component
  }>(),
  {
    title: '暂无数据',
    description: '',
  },
)

const iconComponent = computed(() => props.icon ?? Inbox)
</script>

<template>
  <div class="flex flex-col items-center justify-center px-6 py-12 text-center">
    <div
      class="mb-3 flex size-10 items-center justify-center rounded-pill bg-surface-muted text-text-muted"
      aria-hidden="true"
    >
      <component :is="iconComponent" :size="20" :stroke-width="1.75" />
    </div>
    <p class="text-body font-medium text-text">{{ title }}</p>
    <p v-if="description" class="mt-1 max-w-md text-body text-text-secondary">
      {{ description }}
    </p>
    <div v-if="$slots.action" class="mt-4">
      <slot name="action" />
    </div>
  </div>
</template>
