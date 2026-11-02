import { computed, onBeforeUnmount, ref, watch } from 'vue'

import { listInvoices } from '@/api/invoices'
import { ApiError } from '@/api/client'
import type {
  Invoice,
  InvoiceListQuery,
  InvoicePaymentStatus,
  InvoiceStatus,
} from '@/api/types'
import type { DataTableSort } from '@/components/common/data-table'
import {
  parseEnum,
  parseIsoDate,
  parsePage,
  parsePageSize,
  parsePositiveInt,
  parseSort,
  parseSortValue,
  sortValue,
} from './listQuery'
import { useListUrlState } from './useListUrlState'

export interface InvoiceListFilters {
  q: string
  status: string
  payment_status: string
  category_id: string
  date_from: string
  date_to: string
}

export const INVOICE_STATUS_VALUES: InvoiceStatus[] = [
  'review_pending',
  'active',
  'void',
  'duplicate',
]

export const INVOICE_PAYMENT_STATUS_VALUES: InvoicePaymentStatus[] = [
  'unpaid',
  'partial',
  'paid',
]

const SORT_FIELDS = [
  'invoice_number',
  'issue_date',
  'seller_name',
  'total_cents',
  'paid_cents',
  'created_at',
] as const

const DEFAULT_SORT = 'issue_date:desc'

export function useInvoiceList() {
  const { state } = useListUrlState({
    defaults: {
      q: '',
      status: '',
      payment_status: '',
      category_id: '',
      date_from: '',
      date_to: '',
      page: 1,
      page_size: 20,
      sort: DEFAULT_SORT,
    },
    parsers: {
      status: (raw) => parseEnum(INVOICE_STATUS_VALUES, raw),
      payment_status: (raw) => parseEnum(INVOICE_PAYMENT_STATUS_VALUES, raw),
      category_id: (raw) => {
        const value = parsePositiveInt(raw)
        return value === undefined ? undefined : String(value)
      },
      date_from: parseIsoDate,
      date_to: parseIsoDate,
      page: parsePage,
      page_size: parsePageSize,
      sort: (raw) => parseSort(raw, SORT_FIELDS),
    },
  })

  const rows = ref<Invoice[]>([])
  const total = ref(0)
  const loading = ref(false)
  const error = ref('')
  let seq = 0
  let timer: ReturnType<typeof setTimeout> | undefined

  const filters = computed<InvoiceListFilters>(() => ({
    q: state.q,
    status: state.status,
    payment_status: state.payment_status,
    category_id: state.category_id,
    date_from: state.date_from,
    date_to: state.date_to,
  }))

  const sort = computed<DataTableSort | null>(() => parseSortValue(state.sort))

  const hasFilters = computed(
    () =>
      state.q !== '' ||
      state.status !== '' ||
      state.payment_status !== '' ||
      state.category_id !== '' ||
      state.date_from !== '' ||
      state.date_to !== '',
  )

  function buildQuery(): InvoiceListQuery {
    return {
      page: state.page,
      page_size: state.page_size,
      sort: state.sort,
      q: state.q.trim() || undefined,
      status: (state.status || undefined) as InvoiceStatus | undefined,
      payment_status: (state.payment_status || undefined) as
        | InvoicePaymentStatus
        | undefined,
      category_id: state.category_id ? Number(state.category_id) : undefined,
      date_from: state.date_from || undefined,
      date_to: state.date_to || undefined,
    }
  }

  async function load(): Promise<void> {
    const current = ++seq
    loading.value = true
    error.value = ''
    try {
      const page = await listInvoices(buildQuery())
      if (current !== seq) return
      rows.value = page.items
      total.value = page.total
      if (page.items.length === 0 && state.page > 1 && page.total > 0) {
        state.page = Math.max(1, Math.ceil(page.total / state.page_size))
        return
      }
    } catch (caught) {
      if (current !== seq) return
      rows.value = []
      total.value = 0
      error.value =
        caught instanceof ApiError
          ? caught.message
          : '发票加载失败，请稍后重试。'
    } finally {
      if (current === seq) loading.value = false
    }
  }

  function scheduleLoad(): void {
    if (timer) clearTimeout(timer)
    timer = setTimeout(() => {
      void load()
    }, 150)
  }

  watch(state, scheduleLoad, { deep: true })

  function setFilters(patch: Partial<InvoiceListFilters>): void {
    Object.assign(state, patch)
    state.page = 1
  }

  function resetFilters(): void {
    Object.assign(state, {
      q: '',
      status: '',
      payment_status: '',
      category_id: '',
      date_from: '',
      date_to: '',
      page: 1,
    })
  }

  function onSortChange(next: DataTableSort): void {
    state.sort = sortValue(next)
    state.page = 1
  }

  function goToPage(page: number): void {
    state.page = page
  }

  function setPageSize(size: number): void {
    state.page_size = size
    state.page = 1
  }

  void load()

  onBeforeUnmount(() => {
    if (timer) clearTimeout(timer)
  })

  return {
    state,
    filters,
    sort,
    hasFilters,
    rows,
    total,
    loading,
    error,
    load,
    setFilters,
    resetFilters,
    onSortChange,
    goToPage,
    setPageSize,
  }
}
