<script setup lang="ts">
import { onBeforeUnmount, ref, watch } from 'vue'
import { Search, X } from '@lucide/vue'

import { ApiError } from '@/api/client'
import { listInvoices } from '@/api/invoices'
import type { Invoice } from '@/api/types'
import FormField from '@/components/ui/FormField.vue'
import Input from '@/components/ui/Input.vue'
import MoneyText from '@/components/common/MoneyText.vue'
import Skeleton from '@/components/ui/Skeleton.vue'
import Button from '@/components/ui/Button.vue'

const selected = defineModel<Invoice | null>({ default: null })

const emit = defineEmits<{
  (event: 'select', invoice: Invoice | null): void
}>()

const query = ref('')
const results = ref<Invoice[]>([])
const loading = ref(false)
const error = ref('')

let searchTimer: ReturnType<typeof setTimeout> | undefined
let searchSeq = 0

async function loadInvoices(): Promise<void> {
  const current = ++searchSeq
  loading.value = true
  error.value = ''
  try {
    const page = await listInvoices({
      q: query.value.trim() || undefined,
      page_size: 20,
    })
    if (current !== searchSeq) return
    results.value = page.items
  } catch (caught) {
    if (current !== searchSeq) return
    results.value = []
    error.value =
      caught instanceof ApiError ? caught.message : '发票搜索失败，请重试。'
  } finally {
    if (current === searchSeq) loading.value = false
  }
}

function scheduleSearch(): void {
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    void loadInvoices()
  }, 250)
}

watch(query, () => {
  if (selected.value) return
  scheduleSearch()
})

function select(invoice: Invoice): void {
  selected.value = invoice
  results.value = []
  emit('select', invoice)
}

function clear(): void {
  selected.value = null
  emit('select', null)
  void loadInvoices()
}

void loadInvoices()

onBeforeUnmount(() => {
  if (searchTimer) clearTimeout(searchTimer)
})
</script>

<template>
  <div class="space-y-2">
    <div v-if="!selected" class="space-y-2">
      <FormField id="allocation-invoice-search" label="选择发票" required>
        <template #default="{ id, describedBy }">
          <div class="relative">
            <Search
              class="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-text-muted"
              :size="16"
              :stroke-width="1.75"
              aria-hidden="true"
            />
            <Input
              :id="id"
              v-model="query"
              type="search"
              placeholder="搜发票号 / 店铺"
              class="pl-9"
              :aria-describedby="describedBy"
            />
          </div>
        </template>
      </FormField>

      <div
        v-if="loading"
        class="space-y-2 rounded-control border border-border p-3"
        role="status"
        aria-live="polite"
      >
        <Skeleton class="h-4 w-2/3" />
        <Skeleton class="h-4 w-1/2" />
        <span class="sr-only">正在搜索发票</span>
      </div>

      <div
        v-else-if="error"
        class="flex flex-wrap items-center gap-2 rounded-control border border-danger bg-danger-soft p-3 text-meta text-danger"
        role="alert"
      >
        {{ error }}
        <button
          type="button"
          class="font-medium text-primary hover:underline"
          @click="loadInvoices"
        >
          重试
        </button>
      </div>

      <p
        v-else-if="results.length === 0"
        class="rounded-control border border-border p-3 text-body text-text-muted"
      >
        没有匹配的发票，请调整关键词。
      </p>

      <ul v-else class="max-h-64 divide-y divide-border overflow-y-auto rounded-control border border-border">
        <li v-for="invoice in results" :key="invoice.id">
          <button
            type="button"
            class="flex w-full flex-col gap-1 px-3 py-3 text-left hover:bg-surface-muted"
            @click="select(invoice)"
          >
            <span class="flex flex-wrap items-baseline gap-2">
              <span class="font-mono text-body text-text">{{ invoice.invoice_number }}</span>
              <span class="text-meta text-text-secondary">{{ invoice.seller_name }}</span>
            </span>
            <span class="flex flex-wrap items-center gap-3 text-meta text-text-secondary">
              <span class="inline-flex items-center gap-1">
                总额
                <MoneyText :cents="invoice.total_cents" align="left" class="inline-block" />
              </span>
              <span class="inline-flex items-center gap-1">
                已付
                <MoneyText :cents="invoice.paid_cents" align="left" class="inline-block" />
              </span>
            </span>
          </button>
        </li>
      </ul>
    </div>

    <div v-else class="rounded-control border border-border bg-surface-muted p-3">
      <div class="flex items-start justify-between gap-3">
        <div class="min-w-0">
          <p class="break-all font-mono text-body text-text">{{ selected.invoice_number }}</p>
          <p class="mt-1 text-meta text-text-secondary">{{ selected.seller_name }}</p>
          <p class="mt-1 flex flex-wrap items-center gap-3 text-meta text-text-secondary">
            <span class="inline-flex items-center gap-1">
              总额
              <MoneyText :cents="selected.total_cents" align="left" class="inline-block" />
            </span>
            <span class="inline-flex items-center gap-1">
              已付
              <MoneyText :cents="selected.paid_cents" align="left" class="inline-block" />
            </span>
          </p>
        </div>
        <Button
          variant="ghost"
          size="sm"
          aria-label="重新选择发票"
          @click="clear"
        >
          <template #icon>
            <X :size="16" :stroke-width="1.75" aria-hidden="true" />
          </template>
          更换
        </Button>
      </div>
    </div>
  </div>
</template>
