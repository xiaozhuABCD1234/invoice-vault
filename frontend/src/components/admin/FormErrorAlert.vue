<script setup lang="ts">
import { CircleAlert } from '@lucide/vue'

defineProps<{
  message: string | null
}>()
</script>

<template>
  <div
    v-if="message"
    role="alert"
    aria-live="assertive"
    class="flex items-start gap-2 rounded-control border border-danger bg-danger-soft p-3 text-body text-danger"
  >
    <CircleAlert
      class="mt-0.5 shrink-0"
      :size="16"
      :stroke-width="1.75"
      aria-hidden="true"
    />
    <p class="min-w-0 break-words">{{ message }}</p>
  </div>
</template>
