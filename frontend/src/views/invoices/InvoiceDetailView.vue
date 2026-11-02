<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute } from 'vue-router'
import { Download, Pencil } from '@lucide/vue'

import Button from '@/components/ui/Button.vue'
import Tabs from '@/components/ui/Tabs.vue'
import ErrorState from '@/components/common/ErrorState.vue'
import TableSkeleton from '@/components/common/TableSkeleton.vue'
import InvoiceDetailHeader from '@/components/invoice/InvoiceDetailHeader.vue'
import InvoiceEditDialog from '@/components/invoice/InvoiceEditDialog.vue'
import InvoiceFilesPanel from '@/components/invoice/InvoiceFilesPanel.vue'
import InvoiceItemsPanel from '@/components/invoice/InvoiceItemsPanel.vue'
import InvoiceMetaPanel from '@/components/invoice/InvoiceMetaPanel.vue'
import InvoiceOverview from '@/components/invoice/InvoiceOverview.vue'
import InvoicePaymentsPanel from '@/components/invoice/InvoicePaymentsPanel.vue'
import { useInvoiceDetail } from '@/composables/useInvoiceDetail'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const auth = useAuthStore()

const invoiceId = computed(() => Number(route.params.id))

const {
  invoice,
  payments,
  document,
  loading,
  error,
  paymentsLoading,
  paymentsError,
  documentLoading,
  documentError,
  downloading,
  paidCents,
  unpaidCents,
  reload,
  reloadPayments,
  reloadDocument,
  applyUpdated,
  downloadSourceFile,
} = useInvoiceDetail(invoiceId)

const activeTab = ref('detail')
const editing = ref(false)

const tabs = [
  { value: 'detail', label: '详情' },
  { value: 'items', label: '明细' },
  { value: 'payments', label: '付款' },
  { value: 'files', label: '文件' },
]

function onSaved(updated: typeof invoice.value): void {
  if (updated) applyUpdated(updated)
}
</script>

<template>
  <div>
    <TableSkeleton v-if="loading" :rows="5" :columns="3" />

    <div v-else-if="error" class="rounded-card border border-border bg-surface">
      <ErrorState
        title="发票加载失败"
        :message="error"
        @retry="reload"
      />
    </div>

    <template v-else-if="invoice">
      <InvoiceDetailHeader :invoice="invoice">
        <template #actions>
          <template v-if="auth.isAdmin">
            <Button
              variant="secondary"
              :loading="downloading"
              :disabled="invoice.source_document_id === null"
              @click="downloadSourceFile"
            >
              <template #icon>
                <Download :size="16" :stroke-width="1.75" aria-hidden="true" />
              </template>
              下载源文件
            </Button>
            <Button variant="secondary" @click="editing = true">
              <template #icon>
                <Pencil :size="16" :stroke-width="1.75" aria-hidden="true" />
              </template>
              编辑发票
            </Button>
          </template>
        </template>
      </InvoiceDetailHeader>

      <div class="space-y-4">
        <InvoiceOverview :invoice="invoice" />

        <Tabs v-model="activeTab" :items="tabs">
          <template #detail>
            <InvoiceMetaPanel :invoice="invoice" />
          </template>

          <template #items>
            <InvoiceItemsPanel
              :items="invoice.items"
              :total-cents="invoice.total_cents"
            />
          </template>

          <template #payments>
            <InvoicePaymentsPanel
              :allocations="payments"
              :loading="paymentsLoading"
              :error="paymentsError || null"
              :paid-cents="paidCents"
              :unpaid-cents="unpaidCents"
              @retry="reloadPayments"
            />
          </template>

          <template #files>
            <InvoiceFilesPanel
              :document-id="invoice.source_document_id"
              :document="document"
              :loading="documentLoading"
              :error="documentError || null"
              @retry="reloadDocument"
            />
          </template>
        </Tabs>
      </div>

      <InvoiceEditDialog
        v-if="auth.isAdmin"
        v-model:open="editing"
        :invoice="invoice"
        @saved="onSaved"
      />
    </template>
  </div>
</template>
