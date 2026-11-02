<script setup lang="ts">
import { ref, watch } from 'vue'
import { toast } from 'vue-sonner'
import { CircleAlert } from '@lucide/vue'

import { ApiError } from '@/api/client'
import { updateInvoice } from '@/api/invoices'
import type {
  Invoice,
  InvoiceForm,
  InvoiceStatus,
  InvoiceUpdate,
} from '@/api/types'
import Button from '@/components/ui/Button.vue'
import Dialog from '@/components/ui/Dialog.vue'
import { parseYuanToCents } from '@/lib/money'
import InvoiceEditAmountFields from './InvoiceEditAmountFields.vue'
import InvoiceEditBasicFields from './InvoiceEditBasicFields.vue'
import InvoiceItemsEditor from './InvoiceItemsEditor.vue'
import {
  invoiceToDraft,
  parseItemDrafts,
  type InvoiceFormDraft,
} from './invoice-draft'

const props = defineProps<{
  invoice: Invoice
}>()

const open = defineModel<boolean>('open', { default: false })

const emit = defineEmits<{
  (event: 'saved', invoice: Invoice): void
}>()

const draft = ref<InvoiceFormDraft>(invoiceToDraft(props.invoice))
const errors = ref<Record<string, string>>({})
const formError = ref('')
const saving = ref(false)

watch(open, (value) => {
  if (!value) return
  draft.value = invoiceToDraft(props.invoice)
  errors.value = {}
  formError.value = ''
})

function validate(): boolean {
  const next: Record<string, string> = {}
  if (draft.value.invoice_number.trim() === '') next.invoice_number = '请填写发票号码'
  if (draft.value.issue_date === '') next.issue_date = '请选择开票日期'
  if (draft.value.seller_name.trim() === '') next.seller_name = '请填写销方名称'
  if (draft.value.category_id === '') next.category_id = '请选择类别'

  const amountExTax = parseYuanToCents(draft.value.amount_ex_tax)
  const tax = parseYuanToCents(draft.value.tax)
  const total = parseYuanToCents(draft.value.total)
  if (amountExTax === null) next.amount_ex_tax = '请输入有效的不含税金额'
  if (tax === null) next.tax = '请输入有效的税额'
  if (total === null) next.total = '请输入有效的价税合计'
  if (amountExTax !== null && tax !== null && total !== null) {
    if (Math.abs(amountExTax + tax - total) > 1) {
      next.total = '价税合计需等于不含税金额与税额之和'
    }
  }

  if (parseItemDrafts(draft.value.items) === null) {
    next.items = '请检查明细行的名称、数量、单价与金额。'
  }

  errors.value = next
  return Object.keys(next).length === 0
}

async function submit(): Promise<void> {
  formError.value = ''
  if (!validate()) return

  const items = parseItemDrafts(draft.value.items)
  if (items === null) return

  const payload: InvoiceUpdate = {
    invoice_number: draft.value.invoice_number.trim(),
    issue_date: draft.value.issue_date,
    seller_name: draft.value.seller_name.trim(),
    buyer_name: draft.value.buyer_name.trim() || null,
    category_id: Number(draft.value.category_id),
    requester_id: draft.value.requester_id ? Number(draft.value.requester_id) : null,
    owner_id: draft.value.owner_id ? Number(draft.value.owner_id) : null,
    invoice_form: (draft.value.invoice_form === 'paper'
      ? 'paper'
      : 'electronic') as InvoiceForm,
    status: (draft.value.status || 'active') as InvoiceStatus,
    amount_ex_tax_cents: parseYuanToCents(draft.value.amount_ex_tax) ?? 0,
    tax_cents: parseYuanToCents(draft.value.tax) ?? 0,
    total_cents: parseYuanToCents(draft.value.total) ?? 0,
    note: draft.value.note.trim() || null,
    product_url: draft.value.product_url.trim() || null,
    items,
  }

  saving.value = true
  try {
    const updated = await updateInvoice(props.invoice.id, payload)
    toast.success('发票已更新')
    emit('saved', updated)
    open.value = false
  } catch (caught) {
    formError.value =
      caught instanceof ApiError ? caught.message : '保存失败，请稍后重试。'
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <Dialog
    v-model:open="open"
    title="编辑发票"
    description="修改后将重算付款状态；明细合计与总额不一致时仅提示，不阻止保存。"
    width="lg"
  >
    <form class="space-y-5" novalidate @submit.prevent="submit">
      <div
        v-if="formError"
        class="flex items-start gap-2 rounded-control border border-danger bg-danger-soft p-3 text-body text-danger"
        role="alert"
      >
        <CircleAlert
          class="mt-1 shrink-0"
          :size="16"
          :stroke-width="1.75"
          aria-hidden="true"
        />
        <span>{{ formError }}</span>
      </div>

      <InvoiceEditBasicFields v-model:draft="draft" :errors="errors" />
      <InvoiceEditAmountFields v-model:draft="draft" :errors="errors" />

      <div>
        <InvoiceItemsEditor v-model:items="draft.items" />
        <p v-if="errors.items" class="mt-2 text-meta text-danger" role="alert">
          {{ errors.items }}
        </p>
      </div>
    </form>

    <template #footer>
      <Button variant="secondary" :disabled="saving" @click="open = false">
        取消
      </Button>
      <Button :loading="saving" @click="submit">保存发票</Button>
    </template>
  </Dialog>
</template>
