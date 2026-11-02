import { computed, ref, watch, type ComputedRef } from 'vue'
import { toast } from 'vue-sonner'

import { ApiError } from '@/api/client'
import { downloadDocument, getDocument } from '@/api/documents'
import { getInvoice, listInvoicePayments } from '@/api/invoices'
import type {
  DocumentDetail,
  Invoice,
  InvoicePaymentAllocation,
} from '@/api/types'

function messageOf(caught: unknown, fallback: string): string {
  return caught instanceof ApiError ? caught.message : fallback
}

function extensionForMime(mime: string): string {
  if (mime === 'application/pdf') return 'pdf'
  if (mime === 'image/png') return 'png'
  if (mime === 'image/webp') return 'webp'
  if (mime === 'image/jpeg') return 'jpg'
  return 'bin'
}

/** 发票详情：主数据、付款分配、源文件元数据与下载。 */
export function useInvoiceDetail(invoiceId: ComputedRef<number>) {
  const invoice = ref<Invoice | null>(null)
  const payments = ref<InvoicePaymentAllocation[]>([])
  const document = ref<DocumentDetail | null>(null)
  const loading = ref(true)
  const error = ref('')
  const paymentsLoading = ref(false)
  const paymentsError = ref('')
  const documentLoading = ref(false)
  const documentError = ref('')
  const downloading = ref(false)

  let invoiceSeq = 0
  let paymentsSeq = 0
  let documentSeq = 0

  const paidCents = computed(() => invoice.value?.paid_cents ?? 0)
  const unpaidCents = computed(() => {
    if (!invoice.value) return 0
    return Math.max(0, invoice.value.total_cents - invoice.value.paid_cents)
  })

  async function loadPayments(id: number): Promise<void> {
    const current = ++paymentsSeq
    paymentsLoading.value = true
    paymentsError.value = ''
    try {
      const response = await listInvoicePayments(id)
      if (current !== paymentsSeq) return
      payments.value = response.items
    } catch (caught) {
      if (current !== paymentsSeq) return
      payments.value = []
      paymentsError.value = messageOf(caught, '付款记录加载失败，请重试。')
    } finally {
      if (current === paymentsSeq) paymentsLoading.value = false
    }
  }

  async function loadDocument(id: number | null): Promise<void> {
    documentSeq += 1
    const current = documentSeq
    document.value = null
    documentError.value = ''
    if (id === null) {
      documentLoading.value = false
      return
    }
    documentLoading.value = true
    try {
      const detail = await getDocument(id)
      if (current !== documentSeq) return
      document.value = detail
    } catch (caught) {
      if (current !== documentSeq) return
      documentError.value = messageOf(caught, '文件信息加载失败，请重试。')
    } finally {
      if (current === documentSeq) documentLoading.value = false
    }
  }

  async function load(): Promise<void> {
    const id = invoiceId.value
    const current = ++invoiceSeq
    invoice.value = null
    error.value = ''
    paymentsSeq += 1
    payments.value = []
    paymentsError.value = ''
    paymentsLoading.value = false
    documentSeq += 1
    document.value = null
    documentError.value = ''
    documentLoading.value = false

    if (!Number.isInteger(id) || id <= 0) {
      loading.value = false
      error.value = '发票不存在或已被删除。'
      return
    }

    loading.value = true
    try {
      const data = await getInvoice(id)
      if (current !== invoiceSeq) return
      invoice.value = data
      loading.value = false
      void loadPayments(id)
      void loadDocument(data.source_document_id)
    } catch (caught) {
      if (current !== invoiceSeq) return
      loading.value = false
      error.value = messageOf(caught, '发票加载失败，请稍后重试。')
    }
  }

  function reload(): void {
    void load()
  }

  function reloadPayments(): void {
    if (invoice.value) void loadPayments(invoice.value.id)
  }

  function reloadDocument(): void {
    void loadDocument(invoice.value?.source_document_id ?? null)
  }

  function applyUpdated(updated: Invoice): void {
    invoice.value = updated
    if (updated.source_document_id === null) {
      document.value = null
      documentError.value = ''
    }
  }

  async function downloadSourceFile(): Promise<void> {
    const current = invoice.value
    if (!current || current.source_document_id === null) return
    downloading.value = true
    try {
      const blob = await downloadDocument(current.source_document_id, 'latest')
      const originalName = document.value?.document.current_version.original_name
      const filename =
        originalName && originalName.trim() !== ''
          ? originalName
          : current.invoice_number + '.' + extensionForMime(blob.type)
      const url = URL.createObjectURL(blob)
      const anchor = window.document.createElement('a')
      anchor.href = url
      anchor.download = filename
      window.document.body.append(anchor)
      anchor.click()
      anchor.remove()
      window.setTimeout(() => URL.revokeObjectURL(url), 0)
      toast.success('源文件已开始下载')
    } catch (caught) {
      toast.error(messageOf(caught, '源文件下载失败，请稍后重试。'))
    } finally {
      downloading.value = false
    }
  }

  watch(invoiceId, () => void load(), { immediate: true })

  return {
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
    load,
    reload,
    reloadPayments,
    reloadDocument,
    applyUpdated,
    downloadSourceFile,
  }
}
