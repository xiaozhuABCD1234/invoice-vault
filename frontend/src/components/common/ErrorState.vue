<script setup lang="ts">
import { CircleAlert, RotateCw } from '@lucide/vue'

import Button from '@/components/ui/Button.vue'

withDefaults(
  defineProps<{
    title?: string
    message?: string
    retryLabel?: string
  }>(),
  {
    title: '加载失败',
    message: '请检查网络连接后重试。',
    retryLabel: '重试',
  },
)

const emit = defineEmits<{
  (event: 'retry'): void
}>()
</script>

<template>
  <div
    class="flex flex-col items-center justify-center px-6 py-12 text-center"
    role="alert"
  >
    <div
      class="mb-3 flex size-10 items-center justify-center rounded-pill bg-danger-soft text-danger"
      aria-hidden="true"
    >
      <CircleAlert :size="20" :stroke-width="1.75" />
    </div>
    <p class="text-body font-medium text-text">{{ title }}</p>
    <p class="mt-1 max-w-md text-body text-text-secondary">{{ message }}</p>
    <slot />
    <Button
      variant="secondary"
      size="sm"
      class="mt-4"
      @click="emit('retry')"
    >
      <template #icon>
        <RotateCw :size="16" :stroke-width="1.75" aria-hidden="true" />
      </template>
      {{ retryLabel }}
    </Button>
  </div>
</template>
