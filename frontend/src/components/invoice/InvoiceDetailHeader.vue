<script setup lang="ts">
import { onBeforeUnmount, ref } from 'vue'
import { toast } from 'vue-sonner'
import { ArrowLeft, Check, Copy } from '@lucide/vue'
import { RouterLink } from 'vue-router'

import Button from '@/components/ui/Button.vue'
import StatusBadge from '@/components/common/StatusBadge.vue'
import type { Invoice } from '@/api/types'

const props = defineProps<{
  invoice: Invoice
}>()

const copied = ref(false)
let copyTimer: ReturnType<typeof setTimeout> | undefined

onBeforeUnmount(() => {
  if (copyTimer) clearTimeout(copyTimer)
})

async function copyNumber(): Promise<void> {
  try {
    await navigator.clipboard.writeText(props.invoice.invoice_number)
    copied.value = true
    toast.success('发票号码已复制')
    if (copyTimer) clearTimeout(copyTimer)
    copyTimer = setTimeout(() => {
      copied.value = false
    }, 2000)
  } catch {
    toast.error('复制失败，请手动选择发票号码')
  }
}
</script>

<template>
  <header class="mb-6 space-y-3">
    <nav aria-label="面包屑">
      <ol class="flex flex-wrap items-center gap-1 text-meta text-text-muted">
        <li>
          <RouterLink to="/invoices" class="hover:text-text">发票</RouterLink>
        </li>
        <li class="flex items-center gap-1">
          <span aria-hidden="true">/</span>
          <span aria-current="page">详情</span>
        </li>
      </ol>
    </nav>

    <div class="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
      <div class="flex min-w-0 items-start gap-2">
        <RouterLink
          to="/invoices"
          class="mt-1 inline-flex size-11 shrink-0 items-center justify-center rounded-control text-text-secondary transition-colors duration-150 hover:bg-surface-muted hover:text-text md:size-8"
          aria-label="返回发票列表"
        >
          <ArrowLeft :size="18" :stroke-width="1.75" aria-hidden="true" />
        </RouterLink>
        <div class="min-w-0 space-y-2">
          <h1 class="flex flex-wrap items-center gap-2 text-heading font-semibold tracking-heading text-text sm:text-section md:text-page">
            <span class="break-all font-mono">{{ invoice.invoice_number }}</span>
            <Button
              variant="ghost"
              size="sm"
              class="size-11 shrink-0 px-0 md:size-8"
              aria-label="复制发票号码"
              @click="copyNumber"
            >
              <template #icon>
                <Check
                  v-if="copied"
                  :size="16"
                  :stroke-width="1.75"
                  aria-hidden="true"
                />
                <Copy
                  v-else
                  :size="16"
                  :stroke-width="1.75"
                  aria-hidden="true"
                />
              </template>
            </Button>
          </h1>
          <div class="flex flex-wrap items-center gap-2">
            <StatusBadge kind="invoice_status" :status="invoice.status" />
            <StatusBadge
              kind="payment_status"
              :status="invoice.payment_status"
            />
          </div>
        </div>
      </div>

      <div
        v-if="$slots.actions"
        class="flex shrink-0 flex-wrap items-center gap-2"
      >
        <slot name="actions" />
      </div>
    </div>
  </header>
</template>
