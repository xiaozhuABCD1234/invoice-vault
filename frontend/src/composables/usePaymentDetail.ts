import { computed, ref, watch, type ComputedRef } from 'vue'

import { ApiError } from '@/api/client'
import { getInvoice } from '@/api/invoices'
import { getPayment } from '@/api/payments'
import type { Allocation, Invoice, Payment } from '@/api/types'

function messageOf(caught: unknown, fallback: string): string {
  return caught instanceof ApiError ? caught.message : fallback
}

/** 付款详情：付款主数据与分配行所需的发票摘要（缺失时补取）。 */
export function usePaymentDetail(paymentId: ComputedRef<number>) {
  const payment = ref<Payment | null>(null)
  const invoices = ref<Map<number, Invoice>>(new Map())
  const loading = ref(true)
  const error = ref('')

  let paymentSeq = 0
  let invoiceSeq = 0

  async function loadInvoices(allocations: Allocation[]): Promise<void> {
    const current = ++invoiceSeq
    const missingIds = Array.from(
      new Set(
        allocations
          .filter((allocation) => !allocation.invoice_number)
          .map((allocation) => allocation.invoice_id),
      ),
    )
    if (missingIds.length === 0) {
      invoices.value = new Map()
      return
    }

    const results = await Promise.allSettled(
      missingIds.map(async (id) => {
        const invoice = await getInvoice(id)
        return [id, invoice] as const
      }),
    )
    if (current !== invoiceSeq) return

    const next = new Map<number, Invoice>()
    for (const result of results) {
      if (result.status === 'fulfilled') {
        next.set(result.value[0], result.value[1])
      }
    }
    invoices.value = next
  }

  async function load(): Promise<void> {
    const id = paymentId.value
    const current = ++paymentSeq
    payment.value = null
    invoices.value = new Map()
    error.value = ''
    invoiceSeq += 1

    if (!Number.isInteger(id) || id <= 0) {
      loading.value = false
      error.value = '付款记录不存在或已被删除。'
      return
    }

    loading.value = true
    try {
      const data = await getPayment(id)
      if (current !== paymentSeq) return
      payment.value = data
      loading.value = false
      void loadInvoices(data.allocations)
    } catch (caught) {
      if (current !== paymentSeq) return
      loading.value = false
      error.value = messageOf(caught, '付款记录加载失败，请稍后重试。')
    }
  }

  function reload(): void {
    void load()
  }

  function applyUpdated(updated: Payment): void {
    payment.value = updated
  }

  const allocatedCents = computed(() => payment.value?.allocated_cents ?? 0)
  const unallocatedCents = computed(() => {
    if (!payment.value) return 0
    return Math.max(0, payment.value.amount_cents - payment.value.allocated_cents)
  })

  watch(paymentId, () => void load(), { immediate: true })

  return {
    payment,
    invoices,
    loading,
    error,
    allocatedCents,
    unallocatedCents,
    load,
    reload,
    applyUpdated,
  }
}
