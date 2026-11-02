<script setup lang="ts">
import { TriangleAlert } from '@lucide/vue'

import Button from '@/components/ui/Button.vue'
import Dialog from '@/components/ui/Dialog.vue'

withDefaults(
  defineProps<{
    title: string
    consequence: string
    confirmLabel: string
    cancelLabel?: string
    loading?: boolean
  }>(),
  {
    cancelLabel: '取消',
    loading: false,
  },
)

const open = defineModel<boolean>('open', { default: false })

const emit = defineEmits<{
  (event: 'confirm'): void
}>()

function cancel(): void {
  if (open.value) open.value = false
}
</script>

<template>
  <Dialog
    v-model:open="open"
    :title="title"
    width="sm"
    :show-close="!loading"
  >
    <div class="flex gap-3">
      <span
        class="flex size-8 shrink-0 items-center justify-center rounded-pill bg-danger-soft text-danger"
        aria-hidden="true"
      >
        <TriangleAlert :size="18" :stroke-width="1.75" />
      </span>
      <p class="text-body text-text-secondary">{{ consequence }}</p>
    </div>

    <template #footer>
      <Button
        variant="secondary"
        :disabled="loading"
        @click="cancel"
      >
        {{ cancelLabel }}
      </Button>
      <Button
        variant="danger"
        :loading="loading"
        @click="emit('confirm')"
      >
        {{ confirmLabel }}
      </Button>
    </template>
  </Dialog>
</template>
