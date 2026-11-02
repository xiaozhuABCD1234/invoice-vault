<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { toast } from 'vue-sonner'
import { CircleAlert } from '@lucide/vue'

import { ApiError } from '@/api/client'
import { createAllocation, updateAllocation } from '@/api/payments'
import type { Allocation, Invoice, Payment } from '@/api/types'
import Button from '@/components/ui/Button.vue'
import Dialog from '@/components/ui/Dialog.vue'
import FormField from '@/components/ui/FormField.vue'
import Input from '@/components/ui/Input.vue'
import MoneyText from '@/components/common/MoneyText.vue'
import Textarea from '@/components/ui/Textarea.vue'
import { formatCents, centsToYuanInput, parseYuanToCents } from '@/lib/money'
import AllocationInvoicePicker from './AllocationInvoicePicker.vue'

const props = defineProps<{
  payment: Payment
  mode: 'create' | 'edit'
  allocation?: Allocation | null
}>()

const open = defineModel<boolean>('open', { default: false })

const emit = defineEmits<{
  (event: 'saved'): void
}>()

const selected = ref<Invoice | null>(null)
const amount = ref('')
const note = ref('')
const errors = ref<Record<string, string>>({})
const formError = ref('')
const saving = ref(false)

const paymentRemainingCents = computed(() => {
  const extra =
    props.mode === 'edit' && props.allocation?.status === 'active'
      ? props.allocation.amount_cents
      : 0
  return Math.max(
    0,
    props.payment.amount_cents - props.payment.allocated_cents + extra,
  )
})

const selectedInvoiceRemainingCents = computed(() => {
  if (!selected.value) return 0
  return Math.max(0, selected.value.total_cents - selected.value.paid_cents)
})

const maxCents = computed(() => {
  if (props.mode === 'edit') return paymentRemainingCents.value
  if (!selected.value) return paymentRemainingCents.value
  return Math.min(
    paymentRemainingCents.value,
    selectedInvoiceRemainingCents.value,
  )
})

function resetForm(): void {
  selected.value = null
  amount.value = ''
  note.value = ''
  errors.value = {}
  formError.value = ''
  if (props.mode === 'edit' && props.allocation) {
    amount.value = centsToYuanInput(props.allocation.amount_cents)
    note.value = props.allocation.note ?? ''
  }
}

watch(
  open,
  (value) => {
    if (value) resetForm()
  },
  { immediate: true },
)

function onInvoiceSelected(invoice: Invoice | null): void {
  selected.value = invoice
  if (!invoice) {
    amount.value = ''
    return
  }
  const remaining = Math.max(0, invoice.total_cents - invoice.paid_cents)
  const initial = Math.min(remaining, paymentRemainingCents.value)
  amount.value = initial > 0 ? centsToYuanInput(initial) : ''
}

function validate(): boolean {
  const next: Record<string, string> = {}
  if (props.mode === 'create' && !selected.value) {
    next.invoice = '请选择要分配的发票'
  }

  const amountCents = parseYuanToCents(amount.value)
  if (amountCents === null || amountCents <= 0) {
    next.amount = '请输入大于 0 的分配金额'
  } else if (amountCents > maxCents.value) {
    next.amount = '分配金额不能超过剩余额度 ' + formatCents(maxCents.value)
  }

  errors.value = next
  return Object.keys(next).length === 0
}

async function submit(): Promise<void> {
  formError.value = ''
  if (!validate()) return

  const amountCents = parseYuanToCents(amount.value)
  if (amountCents === null) return

  saving.value = true
  try {
    if (props.mode === 'create' && selected.value) {
      await createAllocation(props.payment.id, {
        invoice_id: selected.value.id,
        amount_cents: amountCents,
        note: note.value.trim() || null,
      })
    } else if (props.mode === 'edit' && props.allocation) {
      await updateAllocation(props.allocation.id, {
        amount_cents: amountCents,
        note: note.value.trim() || null,
      })
    } else {
      return
    }
    toast.success(props.mode === 'create' ? '分配已创建' : '分配已更新')
    emit('saved')
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
    :title="mode === 'create' ? '新增分配' : '编辑分配'"
    :description="
      mode === 'create'
        ? '从发票中选择一笔，把付款金额分配过去。'
        : '调整分配金额或备注，不能超过付款剩余额度。'
    "
    width="md"
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

      <template v-if="mode === 'create'">
        <AllocationInvoicePicker
          v-model="selected"
          @select="onInvoiceSelected"
        />
        <p v-if="errors.invoice" class="text-meta text-danger" role="alert">
          {{ errors.invoice }}
        </p>
      </template>

      <FormField id="allocation-amount" label="分配金额（元）" required :error="errors.amount">
        <template #default="{ id, invalid, describedBy }">
          <Input
            :id="id"
            v-model="amount"
            inputmode="decimal"
            placeholder="0.00"
            :invalid="invalid"
            :aria-describedby="describedBy"
          />
        </template>
      </FormField>

      <p class="text-meta text-text-muted">
        付款剩余额度
        <MoneyText :cents="paymentRemainingCents" align="left" class="inline-block" />
        <template v-if="mode === 'create' && selected">
          ；发票未付
          <MoneyText
            :cents="selectedInvoiceRemainingCents"
            align="left"
            class="inline-block"
          />
          ；本次最多
          <MoneyText :cents="maxCents" align="left" class="inline-block" />
        </template>
      </p>

      <FormField id="allocation-note" label="备注">
        <template #default="{ id }">
          <Textarea :id="id" v-model="note" :rows="2" />
        </template>
      </FormField>
    </form>

    <template #footer>
      <Button variant="secondary" :disabled="saving" @click="open = false">
        取消
      </Button>
      <Button :loading="saving" @click="submit">
        {{ mode === 'create' ? '创建分配' : '保存分配' }}
      </Button>
    </template>
  </Dialog>
</template>
