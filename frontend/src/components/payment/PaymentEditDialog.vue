<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { toast } from 'vue-sonner'
import { CircleAlert } from '@lucide/vue'

import { ApiError } from '@/api/client'
import { updatePayment } from '@/api/payments'
import type { Payment, PaymentMethod } from '@/api/types'
import Button from '@/components/ui/Button.vue'
import Dialog from '@/components/ui/Dialog.vue'
import FormField from '@/components/ui/FormField.vue'
import Input from '@/components/ui/Input.vue'
import { parseYuanToCents } from '@/lib/money'
import PaymentFormFields from './PaymentFormFields.vue'
import {
  paymentToDraft,
  type PaymentFormDraft,
} from './payment-draft'
import { toIsoTimestamp } from './payment-datetime'

const props = defineProps<{
  payment: Payment
}>()

const open = defineModel<boolean>('open', { default: false })

const emit = defineEmits<{
  (event: 'saved', payment: Payment): void
}>()

const draft = ref<PaymentFormDraft>(paymentToDraft(props.payment))
const payerName = ref(props.payment.payer_name)
const errors = ref<Record<string, string>>({})
const formError = ref('')
const saving = ref(false)

const isTeacherAdvance = computed(
  () => draft.value.method === 'teacher_advance',
)

watch(open, (value) => {
  if (!value) return
  draft.value = paymentToDraft(props.payment)
  payerName.value = props.payment.payer_name
  errors.value = {}
  formError.value = ''
})

function validate(): boolean {
  const next: Record<string, string> = {}
  const amountCents = parseYuanToCents(draft.value.amount)
  if (amountCents === null || amountCents <= 0) {
    next.amount = '请输入大于 0 的付款金额'
  } else if (amountCents < props.payment.allocated_cents) {
    next.amount = '付款金额不能小于已分配金额'
  }
  if (toIsoTimestamp(draft.value.paidAt) === null) {
    next.paid_at = '请选择付款时间'
  }
  if (draft.value.method === '') next.method = '请选择付款方式'
  if (payerName.value.trim() === '') next.payer_name = '请填写付款人'
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
    const updated = await updatePayment(props.payment.id, {
      amount_cents: amountCents,
      paid_at: paidAtIso,
      payer_name: payerName.value.trim(),
      method: draft.value.method as PaymentMethod,
      external_txn_ref: draft.value.txnRef.trim() || null,
      requested_at: isTeacherAdvance.value
        ? toIsoTimestamp(draft.value.requestedAt)
        : null,
      note: draft.value.note.trim() || null,
    })
    toast.success('付款记录已更新')
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
    title="编辑付款"
    description="修改金额、付款时间与方式；金额不能小于已分配金额。"
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
          <FormField id="payment-edit-payer" label="付款人" required :error="errors.payer_name">
            <template #default="{ id, invalid, describedBy }">
              <Input
                :id="id"
                v-model="payerName"
                :invalid="invalid"
                :aria-describedby="describedBy"
              />
            </template>
          </FormField>
        </template>
      </PaymentFormFields>
    </form>

    <template #footer>
      <Button variant="secondary" :disabled="saving" @click="open = false">
        取消
      </Button>
      <Button :loading="saving" @click="submit">保存付款</Button>
    </template>
  </Dialog>
</template>
