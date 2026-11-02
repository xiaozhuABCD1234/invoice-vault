import { computed, onBeforeUnmount, ref, watch } from 'vue'

import { listPayments } from '@/api/payments'
import { ApiError } from '@/api/client'
import type { Payment, PaymentListQuery, PaymentMethod, PaymentStatus } from '@/api/types'
import type { DataTableSort } from '@/components/common/data-table'
import {
  parseEnum,
  parseIsoDate,
  parsePage,
  parsePageSize,
  parseSort,
  parseSortValue,
  sortValue,
} from './listQuery'
import { useListUrlState } from './useListUrlState'

export interface PaymentListFilters {
  q: string
  status: string
  method: string
  date_from: string
  date_to: string
}

export const PAYMENT_STATUS_VALUES: PaymentStatus[] = [
  'unallocated',
  'partially_allocated',
  'fully_allocated',
  'void',
]

export const PAYMENT_METHOD_VALUES: PaymentMethod[] = [
  'personal_advance',
  'teacher_advance',
  'bank_transfer',
  'alipay',
  'wechat',
  'card',
  'cash',
  'other',
]

const SORT_FIELDS = ['paid_at', 'amount_cents', 'payer_name', 'created_at'] as const
const DEFAULT_SORT = 'paid_at:desc'

export function usePaymentList() {
  const { state } = useListUrlState({
    defaults: {
      q: '',
      status: '',
      method: '',
      date_from: '',
      date_to: '',
      page: 1,
      page_size: 20,
      sort: DEFAULT_SORT,
    },
    parsers: {
      status: (raw) => parseEnum(PAYMENT_STATUS_VALUES, raw),
      method: (raw) => parseEnum(PAYMENT_METHOD_VALUES, raw),
      date_from: parseIsoDate,
      date_to: parseIsoDate,
      page: parsePage,
      page_size: parsePageSize,
      sort: (raw) => parseSort(raw, SORT_FIELDS),
    },
  })

  const rows = ref<Payment[]>([])
  const total = ref(0)
  const loading = ref(false)
  const error = ref('')
  let seq = 0
  let timer: ReturnType<typeof setTimeout> | undefined

  const filters = computed<PaymentListFilters>(() => ({
    q: state.q,
    status: state.status,
    method: state.method,
    date_from: state.date_from,
    date_to: state.date_to,
  }))

  const sort = computed<DataTableSort | null>(() => parseSortValue(state.sort))

  const hasFilters = computed(
    () =>
      state.q !== '' ||
      state.status !== '' ||
      state.method !== '' ||
      state.date_from !== '' ||
      state.date_to !== '',
  )

  function buildQuery(): PaymentListQuery {
    return {
      page: state.page,
      page_size: state.page_size,
      sort: state.sort,
      q: state.q.trim() || undefined,
      status: (state.status || undefined) as PaymentStatus | undefined,
      method: (state.method || undefined) as PaymentMethod | undefined,
      date_from: state.date_from || undefined,
      date_to: state.date_to || undefined,
    }
  }

  async function load(): Promise<void> {
    const current = ++seq
    loading.value = true
    error.value = ''
    try {
      const page = await listPayments(buildQuery())
      if (current !== seq) return
      rows.value = page.items
      total.value = page.total
      if (page.items.length === 0 && state.page > 1 && page.total > 0) {
        state.page = Math.max(1, Math.ceil(page.total / state.page_size))
      }
    } catch (caught) {
      if (current !== seq) return
      rows.value = []
      total.value = 0
      error.value =
        caught instanceof ApiError
          ? caught.message
          : '付款记录加载失败，请稍后重试。'
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

  function setFilters(patch: Partial<PaymentListFilters>): void {
    Object.assign(state, patch)
    state.page = 1
  }

  function resetFilters(): void {
    Object.assign(state, {
      q: '',
      status: '',
      method: '',
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
