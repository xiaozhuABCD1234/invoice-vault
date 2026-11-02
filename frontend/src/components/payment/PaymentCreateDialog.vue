<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { toast } from 'vue-sonner'
import { CircleAlert } from '@lucide/vue'

import { ApiError } from '@/api/client'
import { createPayment } from '@/api/payments'
import type { Payment, PaymentMethod } from '@/api/types'
import Button from '@/components/ui/Button.vue'
import Dialog from '@/components/ui/Dialog.vue'
import { parseYuanToCents } from '@/lib/money'
import { emptyPaymentDraft, type PaymentFormDraft } from './payment-draft'
import { toIsoTimestamp } from './payment-datetime'
import PaymentFormFields from './PaymentFormFields.vue'
import PaymentPayerField from './PaymentPayerField.vue'

const open = defineModel<boolean>('open', { default: false })

const emit = defineEmits<{
  (event: 'created', payment: Payment): void
}>()

const draft = ref<PaymentFormDraft>(emptyPaymentDraft())
const payerUserId = ref('')
const payerName = ref('')
const errors = ref<Record<string, string>>({})
const formError = ref('')
const saving = ref(false)

const isTeacherAdvance = computed(
  () => draft.value.method === 'teacher_advance',
)

function resetForm(): void {
  draft.value = emptyPaymentDraft()
  payerUserId.value = ''
  payerName.value = ''
  errors.value = {}
  formError.value = ''
}

watch(open, (value) => {
  if (value) resetForm()
})

function validate(): boolean {
  const next: Record<string, string> = {}
  const amountCents = parseYuanToCents(draft.value.amount)
  if (amountCents === null || amountCents <= 0) {
    next.amount = '请输入大于 0 的付款金额'
  }
  if (toIsoTimestamp(draft.value.paidAt) === null) {
    next.paid_at = '请选择付款时间'
  }
  if (draft.value.method === '') next.method = '请选择付款方式'
  if (payerUserId.value === '' && payerName.value.trim() === '') {
    next.payer = '请选择付款人，或填写外部付款人名称'
  }
  if (isTeacherAdvance.value && draft.value.requestedAt !== '') {
    if (toIsoTimestamp(draft.value.requestedAt) === null) {
      next.requested_at = '请填写有效的代付时间'
    }
  }
  errors.value = next
  return Object.keys(next).length === 0
}

async function submit(): Promise<void> {
  formError.value = ''
  if (!validate()) return

  const amountCents = parseYuanToCents(draft.value.amount)
  const paidAtIso = toIsoTimestamp(draft.value.paidAt)
  if (amountCents === null || paidAtIso === null) return

  saving.value = true
  try {
    const payment = await createPayment({
      amount_cents: amountCents,
      paid_at: paidAtIso,
      method: draft.value.method as PaymentMethod,
      payer_user_id: payerUserId.value ? Number(payerUserId.value) : null,
      payer_name:
        payerUserId.value === '' ? payerName.value.trim() || null : null,
      external_txn_ref: draft.value.txnRef.trim() || null,
      requested_at: isTeacherAdvance.value
        ? toIsoTimestamp(draft.value.requestedAt)
        : null,
      note: draft.value.note.trim() || null,
    })
    toast.success('付款记录已创建')
    emit('created', payment)
    open.value = false
  } catch (caught) {
    formError.value =
      caught instanceof ApiError ? caught.message : '创建失败，请稍后重试。'
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <Dialog
    v-model:open="open"
    title="新建付款"
    description="登记一笔付款，创建后可把金额分配到发票。"
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

      <PaymentFormFields v-model:draft="draft" :errors="errors">
        <template #after-method>
          <PaymentPayerField
            v-model:user-id="payerUserId"
            v-model:name="payerName"
            :error="errors.payer"
          />
        </template>
      </PaymentFormFields>
    </form>

    <template #footer>
      <Button variant="secondary" :disabled="saving" @click="open = false">
        取消
      </Button>
      <Button :loading="saving" @click="submit">创建付款</Button>
    </template>
  </Dialog>
</template>
