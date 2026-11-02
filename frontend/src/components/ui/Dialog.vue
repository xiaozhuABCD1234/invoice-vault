<script setup lang="ts">
import { X } from '@lucide/vue'
import {
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogOverlay,
  DialogPortal,
  DialogRoot,
  DialogTitle,
  DialogTrigger,
} from 'reka-ui'

type DialogWidth = 'sm' | 'md' | 'lg'

withDefaults(
  defineProps<{
    title: string
    description?: string
    width?: DialogWidth
    showClose?: boolean
  }>(),
  {
    width: 'md',
    showClose: true,
  },
)

const open = defineModel<boolean>('open', { default: false })

const widthClasses: Record<DialogWidth, string> = {
  sm: 'max-w-dialog-sm',
  md: 'max-w-dialog-md',
  lg: 'max-w-dialog-lg',
}
</script>

<template>
  <DialogRoot v-model:open="open">
    <DialogTrigger v-if="$slots.trigger" as-child>
      <slot name="trigger" />
    </DialogTrigger>

    <DialogPortal>
      <DialogOverlay class="fixed inset-0 z-40 bg-text/40" />
      <DialogContent
        :class="[
          'fixed inset-x-4 top-1/2 z-50 mx-auto flex max-h-screen w-auto -translate-y-1/2 flex-col overflow-hidden rounded-dialog border border-border bg-surface shadow-dialog focus-visible:outline-none',
          widthClasses[width],
        ]"
      >
        <header class="flex items-start justify-between gap-4 border-b border-border p-6 pb-4">
          <div class="min-w-0 space-y-1">
            <DialogTitle class="text-heading font-semibold text-text">
              {{ title }}
            </DialogTitle>
            <DialogDescription
              v-if="description"
              class="text-body text-text-secondary"
            >
              {{ description }}
            </DialogDescription>
            <DialogDescription v-else class="sr-only">
              按 Esc 键关闭。
            </DialogDescription>
          </div>
          <DialogClose v-if="showClose" as-child>
            <button
              type="button"
              class="inline-flex size-11 shrink-0 items-center justify-center rounded-control text-text-muted transition-colors duration-150 hover:bg-surface-muted hover:text-text md:size-8"
              aria-label="关闭"
            >
              <X :size="18" :stroke-width="1.75" aria-hidden="true" />
            </button>
          </DialogClose>
        </header>

        <div class="min-h-0 flex-1 overflow-y-auto p-6">
          <slot />
        </div>

        <footer
          v-if="$slots.footer"
          class="flex flex-wrap justify-end gap-2 border-t border-border p-6 pt-4"
        >
          <slot name="footer" />
        </footer>
      </DialogContent>
    </DialogPortal>
  </DialogRoot>
</template>
